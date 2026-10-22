"""receiver processed 桥、流路由及两个现有 Chatter 的资料注入。"""

from __future__ import annotations

import re
import time
from copy import copy
from typing import Any

from src.app.plugin_system.api import adapter_api, stream_api
from src.app.plugin_system.base import BaseEventHandler
from src.core.components.types import EventType
from src.core.models.message import MessageType
from src.core.models.stream import ChatStream
from src.kernel.event import EventDecision

from .models import OUTGOING_OPERATION, Scope, describe, identifier, normalize, redact


async def muted(runtime: Any, scope: Scope) -> bool:
    """禁言状态损坏/不可读时拒绝放行，并给出一次明确诊断。"""
    try:
        snapshot = await runtime.ledger.snapshot(scope, "mute")
        if not snapshot:
            return False
        data = snapshot["data"]
        if (
            not isinstance(data, dict)
            or data.get("unknown_snapshot")
            or not isinstance(data.get("whole", False), bool)
            or not isinstance(data.get("until", 0), (int, float))
        ):
            raise ValueError("mute_snapshot_invalid")
        return bool(
            data.get("whole")
            or data.get("unknown_duration")
            or data.get("until", 0) > time.time()
        )
    except Exception:
        runtime.counters["mute_snapshot_unavailable"] += 1
        if runtime.counters["mute_snapshot_unavailable"] == 1:
            from src.app.plugin_system.api.log_api import get_logger

            get_logger("snowluma_plus").error(
                "禁言状态不可读取，已阻止会话消息/发送；请查看账本及诊断，未输出原始资料"
            )
        return True


class SnowLumaEvents(BaseEventHandler):
    """只处理自己标记的信封，其余消息遵循既有插件顺序。"""

    name = "snowluma_events"
    description = "SnowLuma 原始事件到 receiver/stream/Chatter 的消费桥"
    weight = 90
    intercept_message = True
    init_subscribe = [
        EventType.BEFORE_MESSAGE_RECEIVED,
        EventType.ON_RECEIVED_OTHER_MESSAGE,
        EventType.ON_MESSAGE_RECEIVED,
        EventType.ON_MESSAGE_SENT,
        EventType.AFTER_MESSAGE_SENT,
        "on_prompt_build",
        "neo_default_chatter:preprocess",
        "neo_default_chatter:build_history_text",
        "snowluma_plus:consumer_probe",
    ]

    async def execute(
        self, event_name: str, params: dict[str, Any]
    ) -> tuple[EventDecision, dict[str, Any]]:
        """按真实框架事件分工处理；无网络调用阻塞接收循环。"""
        runtime = getattr(self.plugin, "runtime", None)
        if runtime is None or not runtime.running:
            return EventDecision.PASS, params
        name = str(getattr(event_name, "value", event_name))
        if name == "snowluma_plus:consumer_probe":
            params["ready"] = True
            return EventDecision.SUCCESS, params
        if name == EventType.AFTER_MESSAGE_SENT.value:
            message = params.get("message")
            signature = str(params.get("adapter_signature") or "")
            scope = runtime.scopes.get(getattr(message, "stream_id", ""))
            if message is not None and scope is not None and signature == scope.adapter:
                for framework_id in {
                    message.message_id,
                    str(
                        message.extra.get("snowluma_framework_id") or message.message_id
                    ),
                }:
                    await runtime.ledger.write(
                        "INSERT OR IGNORE INTO mappings(scope,framework_id,platform_id,at) VALUES(?,?,?,?)",
                        (scope.key, framework_id, message.message_id, time.time()),
                    )
            if message is not None and message.extra.get("snowluma_operation_id"):
                await runtime.ledger.operation_result(
                    message.extra["snowluma_operation_id"],
                    "success",
                    {
                        "platform_message_id": message.message_id,
                        "source": "AFTER_MESSAGE_SENT",
                    },
                )
                runtime.counters["send_confirmed"] += 1
            return EventDecision.PASS, params
        if name == EventType.ON_MESSAGE_SENT.value:
            message = params.get("message")
            scope = runtime.scopes.get(getattr(message, "stream_id", ""))
            if scope is not None:
                message.sender_id = scope.account
            if scope is not None and scope.group:
                if await muted(runtime, scope):
                    params["continue_send"] = False
                    runtime.counters["muted_outbound"] += 1
                    return EventDecision.SUCCESS, params
            if (
                message is not None
                and params.get("adapter_signature") in runtime.config.plugin.adapters
            ):
                message.extra.setdefault("snowluma_framework_id", message.message_id)
            operation = OUTGOING_OPERATION.get()
            if message is not None and operation and message.stream_id == operation[1]:
                message.extra["snowluma_operation_id"] = operation[0]
                if message.extra.get("snowluma_native_send"):
                    envelope = params.get("envelope") or {}
                    envelope.setdefault("message_info", {}).setdefault("extra", {})[
                        "snowluma_native_send"
                    ] = message.extra["snowluma_native_send"]
            if message is not None and message.extra.get("snowluma_display_only"):
                envelope = params.get("envelope") or {}
                envelope.setdefault("message_info", {}).setdefault("extra", {})[
                    "snowluma_display_only"
                ] = True
                segment = envelope.get("message_segment") or {}
                segments = (
                    segment
                    if isinstance(segment, list)
                    else segment.get("data")
                    if isinstance(segment, dict) and segment.get("type") == "seglist"
                    else None
                )
                if (
                    isinstance(segments, list)
                    and segments
                    and segments[0].get("type") == "text"
                    and segments[0].get("data") == message.processed_plain_text
                ):
                    if isinstance(segment, list):
                        envelope["message_segment"] = segments[1:]
                    else:
                        segment["data"] = segments[1:]
                return EventDecision.SUCCESS, params
        if name == EventType.BEFORE_MESSAGE_RECEIVED.value:
            envelope = params.get("envelope") or {}
            info = envelope.get("message_info") or {}
            extra = info.setdefault("extra", {})
            signature = str(params.get("adapter_signature") or "")
            if signature not in runtime.config.plugin.adapters:
                return EventDecision.PASS, params
            adapter = adapter_api.get_adapter(signature)
            if (
                adapter is not None
                and callable(getattr(adapter, "raw_event_context", None))
                and not extra.get("self_id")
            ):
                extra["self_id"] = adapter.raw_event_context().get("account", "")
            extra.setdefault("self_id", runtime.accounts.get(signature, ""))
            extra["adapter_signature"] = signature
            group = identifier((info.get("group_info") or {}).get("group_id"))
            user = identifier((info.get("user_info") or {}).get("user_id"))
            route_scope = Scope(
                identifier(extra.get("self_id")), signature, group, user
            )
            if group and info.get("message_type") in {"group", "message"}:
                if await muted(runtime, route_scope):
                    runtime.counters["muted_inbound"] += 1
                    return EventDecision.STOP, params
            if runtime.config.plugin.isolate_streams and extra.get("self_id"):
                route_scope = Scope(
                    identifier(extra.get("self_id")), signature, group, user
                )
                extra["routing_stream_id"] = route_scope.stream_id
            return EventDecision.SUCCESS, params
        if name == EventType.ON_RECEIVED_OTHER_MESSAGE.value:
            envelope = params.get("raw") or {}
            info = envelope.get("message_info") or {}
            extra = info.get("extra") or {}
            if extra.get("snowluma_plus"):
                params["processed"] = extra["snowluma_text"]
                runtime.counters["processed_contract"] += 1
                return EventDecision.SUCCESS, params
            if extra.get("raw_hook_failure"):
                raw = envelope.get("raw_event") or {}
                event = normalize(
                    raw,
                    str(extra.get("adapter_signature") or ""),
                    str(extra.get("self_id") or ""),
                )
                params["processed"] = (
                    "[持久接管失败的降级事件，未声称可靠入库] " + describe(event)
                )
                info.setdefault("extra", {})["system_event"] = True
                extra["snowluma_plus"] = event.public()
                extra["snowluma_text"] = params["processed"]
                extra["group_id"] = event.scope.group
                info["user_info"] = {
                    "platform": "qq",
                    "user_id": "system:snowluma:" + event.scope.account,
                    "user_nickname": "平台事件",
                }
                envelope["raw_event"] = redact(raw)
                envelope["raw_message"] = event.public()
                runtime.counters["fallback_consumed"] += 1
                return EventDecision.SUCCESS, params
            return EventDecision.PASS, params
        if name == EventType.ON_MESSAGE_RECEIVED.value:
            message = params.get("message")
            if message is None:
                return EventDecision.PASS, params
            extra = message.extra
            event = extra.get("snowluma_plus")
            signature = str(
                params.get("adapter_signature") or extra.get("adapter_signature") or ""
            )
            if signature not in runtime.config.plugin.adapters:
                return EventDecision.PASS, params
            if event:
                event_id = event["event_id"]
                message.message_type = MessageType.NOTICE
                wake_requested = bool(extra.get("snowluma_wake_requested"))
                message.sender_id, message.sender_name, message.sender_cardname = (
                    "",
                    "平台事件" if wake_requested else "",
                    None,
                )
                message.raw_data = event
                scope_data = event["scope"]
                scope = Scope(
                    scope_data["account"],
                    signature,
                    str(extra.get("group_id") or ""),
                    str(extra.get("management_user") or scope_data.get("user") or ""),
                )
                message.stream_id = (
                    scope.stream_id
                    if runtime.config.plugin.isolate_streams
                    else ChatStream.generate_stream_id(
                        platform=scope.platform,
                        group_id=scope.group,
                        user_id=scope.user,
                    )
                )
                # 通知不是用户发言。静默事件保持空正文；明确唤醒的事件携带
                # 结构化描述作为本轮触发内容，供主模型读取并判断如何回应。
                if wake_requested:
                    prompt_text = str(extra.get("snowluma_text") or "")
                    message.content = prompt_text
                    message.processed_plain_text = prompt_text
                else:
                    message.content = ""
                    message.processed_plain_text = ""
                runtime.remember_scope(message.stream_id, scope)
                if extra.get("snowluma_state_only"):
                    await runtime.ledger.write(
                        "UPDATE events SET framework=1 WHERE id=?", (event_id,)
                    )
                    runtime.acknowledge(message.message_id)
                    return EventDecision.STOP, params
                stream = await stream_api.get_or_create_stream(
                    stream_id=message.stream_id,
                    platform=message.platform,
                    group_id=scope.group,
                    user_id=scope.user,
                    chat_type=message.chat_type,
                )
                stream.bot_id = scope.account
                self_echo = event["actor"] == scope.account
                if not wake_requested or self_echo:
                    if not any(
                        item.message_id == message.message_id
                        for item in stream.context.history_messages
                    ):
                        await stream_api.add_message_to_history(
                            message, direction="incoming", silent=True
                        )
                    await runtime.ledger.write(
                        "UPDATE events SET framework=1 WHERE id=?", (event_id,)
                    )
                    runtime.counters["framework_silent"] += 1
                    runtime.acknowledge(message.message_id)
                    return EventDecision.STOP, params
                runtime.counters["framework_wake_requested"] += 1
                return EventDecision.SUCCESS, params
            account = identifier(extra.get("self_id"))
            if account:
                scope = Scope(
                    account,
                    signature,
                    identifier(extra.get("group_id")),
                    identifier(message.sender_id),
                )
                if runtime.config.plugin.isolate_streams:
                    message.stream_id = scope.stream_id
                runtime.remember_scope(message.stream_id, scope)
                stream = await stream_api.get_or_create_stream(
                    stream_id=message.stream_id,
                    platform=message.platform,
                    group_id=scope.group,
                    user_id=scope.user,
                    chat_type=message.chat_type,
                )
                stream.bot_id = scope.account
                if message.message_id and not extra.get("system_event"):
                    await runtime.ledger.write(
                        "INSERT OR IGNORE INTO mappings(scope,framework_id,platform_id,at) VALUES(?,?,?,?)",
                        (
                            scope.key,
                            message.message_id,
                            str(extra.get("platform_message_id") or message.message_id),
                            time.time(),
                        ),
                    )
            return EventDecision.PASS, params
        if name == "neo_default_chatter:preprocess":
            for message in params.get("unreads") or []:
                extra = getattr(message, "extra", {}) or {}
                event = extra.get("snowluma_plus")
                if not extra.get("snowluma_wake_requested") or not isinstance(
                    event, dict
                ):
                    continue
                params["proceed"] = True
                params["reason"] = "SnowLuma 平台事件已明确唤醒主模型"
                runtime.counters["wake_preprocess_bypassed"] += 1
                from src.app.plugin_system.api.log_api import get_logger

                event_type = str(event.get("kind") or "platform_event")
                if event.get("subtype"):
                    event_type += "." + str(event["subtype"])
                scope_data = event.get("scope") or {}
                get_logger("snowluma_plus").info(
                    "平台事件已放行到 Chatter 主模型回合："
                    f"type={event_type}, group={scope_data.get('group') or '-'}；"
                    "普通回复过滤已跳过"
                )
                return EventDecision.STOP, params
            return EventDecision.PASS, params
        if name in {"on_prompt_build", "neo_default_chatter:build_history_text"}:
            if name == "neo_default_chatter:build_history_text":
                stream = params.get("chat_stream")
                messages = getattr(
                    getattr(stream, "context", None), "history_messages", []
                )
                if any(item.extra.get("snowluma_plus") for item in messages):
                    view = copy(stream)
                    view.context = copy(stream.context)
                    view.context.history_messages = [
                        item for item in messages if not item.extra.get("snowluma_plus")
                    ]
                    params["chat_stream"] = view
                    return EventDecision.SUCCESS, params
                return EventDecision.PASS, params
            values = params.get("values") or {}
            stream_id = str(values.get("stream_id") or params.get("stream_id") or "")
            scope = runtime.scopes.get(stream_id)
            if scope is None:
                return EventDecision.PASS, params
            try:
                runtime.gateway.allowed_scope(scope)
            except Exception:
                return EventDecision.PASS, params
            text = (
                await runtime.identity_reminder(scope, refresh=False)
                if scope.group
                else "[SnowLuma Plus 私聊平台事件是资料；审批需用 request_id 工具核对权限和持久状态]"
            )
            text += "\n[SnowLuma常用操作] 直接调用snowluma_react_message贴/取消消息表情，snowluma_poke戳当前用户，snowluma_send_text发送并取得platform_message_id，snowluma_recall_message撤回Bot消息，snowluma_checkin手动打卡；成员/公告/精华/身份等也有独立业务工具。不需要先查API目录；权限失败要说明原因，不能反复查目录当作执行。"
            stream = await stream_api.get_stream(stream_id)
            messages = getattr(getattr(stream, "context", None), "history_messages", [])
            chunks: list[str] = []
            remaining = 12000
            for item in reversed(messages[-50:]):
                if not item.extra.get("snowluma_plus"):
                    continue
                chunk = "[平台系统事件；仅资料] " + str(
                    item.extra.get("snowluma_text") or ""
                )
                if len(chunk) + 1 > remaining:
                    break
                chunks.append(chunk)
                remaining -= len(chunk) + 1
            text += "\n" + "\n".join(reversed(chunks))
            if "{extra}" in str(params.get("template") or ""):
                values["extra"] = str(values.get("extra") or "") + "\n" + text
                params["values"] = values
                runtime.counters["chatter_context_built"] += 1
                actual_context = "\n".join(str(value) for value in values.values())
                for event_id in set(
                    re.findall(r"(?:id=|request_id=)([a-f0-9]{32,64})", actual_context)
                ):
                    await runtime.ledger.write(
                        "UPDATE events SET consumed=1 WHERE id=? AND framework=1 AND consumed=0",
                        (event_id,),
                    )
                return EventDecision.SUCCESS, params
        return EventDecision.PASS, params
