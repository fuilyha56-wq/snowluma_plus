"""显式参数组件的统一执行层，沿用业务权限及实际Service响应。"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from src.app.plugin_system.base import BaseTool
from src.app.plugin_system.api import send_api
from src.core.models.message import Message

from .components import context, output, platform_message
from .direct import _Action
from .gateway import BusinessError, response_data
from .models import OUTGOING_OPERATION


class TypedRead(BaseTool):
    """只读工具的绑定和返回规则；具体组件只有明确业务参数。"""

    api_action = ""
    associated_platforms = ["qq"]

    async def call(self, values: dict[str, Any]) -> tuple[bool, str | dict]:
        try:
            params = {
                key: value
                for key, value in values.items()
                if value is not None and not (key == "group_id" and value == "")
            }
            runtime, scope, operator, _ = await context(
                self, str(params.get("group_id") or "")
            )
            entry = runtime.gateway.catalog[self.api_action]
            if scope.group and "group_id" in entry["arguments"]:
                params.setdefault("group_id", scope.group)
            if "message_id" in params:
                reference = str(params["message_id"])
                params["message_id"] = await platform_message(
                    runtime,
                    scope,
                    reference
                    if reference.startswith(("platform:", "framework:"))
                    else "platform:" + reference,
                )
            response = await runtime.gateway.call(
                scope, operator, self.api_action, params
            )
            return True, output(
                runtime,
                {"data": response_data(response), "source": "protocol_response"},
            )
        except (BusinessError, ValueError, TypeError, OSError) as exc:
            return False, str(exc)
        except asyncio.TimeoutError:
            return False, "平台查询超时，未将失败当作空结果或成功"


class TypedWrite(_Action):
    """写入动作也使用显式参数；参数校验和审计不因封装而省略。"""

    api_action = ""

    async def call(self, values: dict[str, Any]) -> tuple[bool, str]:
        params = {
            key: value
            for key, value in values.items()
            if value is not None and not (key == "group_id" and value == "")
        }
        if self.api_action == "send_group_ai_record":
            return await self.send_ai(params)
        return await self.manage(self.api_action, params)

    async def send_ai(self, params: dict[str, Any]) -> tuple[bool, str]:
        """原生AI语音经MessageSender产生历史、AFTER事实及真实消息ID。"""
        runtime, operation, token = None, "", None
        try:
            runtime, scope, operator, stream_id = await context(
                self, str(params.get("group_id") or "")
            )
            if runtime.scopes.get(stream_id) != scope:
                raise BusinessError(
                    "AI语音只在当前会话发送，不能将跨群消息记录到原会话历史"
                )
            params.setdefault("group_id", scope.group)
            runtime.gateway.authorize(scope, operator, self.api_action, True, params)
            operation = "send-ai:" + uuid.uuid4().hex
            await runtime.ledger.claim(
                operation, scope, self.api_action, operator, "local_action"
            )
            token = OUTGOING_OPERATION.set((operation, stream_id))
            label = "[AI语音] " + str(params["text"])
            message = Message(
                message_id=operation,
                platform=scope.platform,
                stream_id=stream_id,
                sender_id=scope.account,
                chat_type="group",
                target_group_id=scope.group,
                content=label,
                processed_plain_text=label,
                snowluma_native_send={"action": self.api_action, "params": params},
            )
            await send_api.send_message(message, adapter_signature=scope.adapter)
            records = await runtime.ledger.rows(
                "SELECT state,result FROM operations WHERE id=?", (operation,)
            )
            if records and records[0]["state"] == "success":
                return True, records[0]["result"]
            await runtime.ledger.operation_result(
                operation, "uncertain", "未收到AFTER_MESSAGE_SENT确认，禁止自动重发"
            )
            return False, "AI语音发送未确认；结果不确定，请勿自动重发"
        except (BusinessError, ValueError, TypeError, OSError) as exc:
            if runtime is not None and operation:
                await runtime.ledger.operation_result(
                    operation, "uncertain", type(exc).__name__
                )
            return False, str(exc)
        except (asyncio.TimeoutError, asyncio.CancelledError) as exc:
            if runtime is not None and operation:
                await runtime.ledger.operation_result(
                    operation, "uncertain", type(exc).__name__
                )
            if isinstance(exc, asyncio.CancelledError):
                raise
            return False, "AI语音结果不确定；请核实平台，不要重发"
        finally:
            if token is not None:
                OUTGOING_OPERATION.reset(token)
