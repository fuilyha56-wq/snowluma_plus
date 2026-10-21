"""仅驻留内存的兼容句柄；不修改宿主或其他插件文件。"""

from __future__ import annotations

import functools
import hashlib
import inspect
import json
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from src.app.plugin_system.api import adapter_api, config_api
from src.app.plugin_system.base import BaseAction, PlatformSendResult

from .models import identifier
from .raw_events import RawEventHooks, fallback_envelope

TRIGGER: ContextVar[Any] = ContextVar("snowluma_plus_trigger", default=None)
_MISSING = object()


def fingerprint(function: Any) -> str:
    """精确比较审计过的实现，包装器和未知升级默认不接管。"""
    source = inspect.getsource(function).replace("\r\n", "\n")
    return hashlib.sha256(source.encode()).hexdigest()


def check(function: Any, key: str) -> None:
    """指纹包含函数正文；版本号相同也不能跳过核验。"""
    known = json.loads(
        (Path(__file__).parent / "resources/compatibility.json").read_text(
            encoding="utf-8"
        )
    )
    if (
        hasattr(function, "__wrapped__")
        or fingerprint(function) != known["functions"][key]
    ):
        raise RuntimeError(f"未经审计的兼容入口 {key}；未安装接管，请更新兼容审计")


class Handles:
    """保存实例原属性，发现后续包装时保留对方方法并报告冲突。"""

    def __init__(self) -> None:
        self.entries: list[tuple[Any, str, Any, Any]] = []

    def set(self, owner: Any, name: str, value: Any) -> None:
        """安装单个句柄，调用方负责能力检查。"""
        previous = vars(owner).get(name, _MISSING)
        setattr(owner, name, value)
        self.entries.append((owner, name, previous, value))

    def valid(self) -> bool:
        return all(
            getattr(owner, name, _MISSING) is value
            for owner, name, _, value in self.entries
        )

    def close(self) -> bool:
        """只恢复仍由自己持有的入口；绝不覆盖后安装的包装器。"""
        clean = True
        for owner, name, previous, value in reversed(self.entries):
            if getattr(owner, name, _MISSING) is not value:
                clean = False
                continue
            if previous is _MISSING:
                delattr(owner, name)
            else:
                setattr(owner, name, previous)
        self.entries.clear()
        return clean


class AdapterBinding:
    """OneBot 2.0.0 精确能力检查后的实例包装，沿用已有连接。"""

    def __init__(self, adapter: Any, signature: str, account: str) -> None:
        self.adapter, self.signature, self.account = adapter, signature, account
        self.handles, self.hooks = Handles(), RawEventHooks()
        self.active = False

    def policy(self, raw: dict[str, Any]) -> bool:
        """只读公共配置中的名单及通知开关，不读取连接地址或凭据。"""
        config = config_api.get_config(self.signature.split(":", 1)[0])
        features = getattr(config, "features", None)
        if features is None:
            raise RuntimeError("适配器公共名单配置不可用，拒绝接管")
        post = raw.get("post_type")
        if post not in {"message", "message_sent", "notice", "request"}:
            return True
        user = identifier(
            raw.get("user_id") or (raw.get("sender") or {}).get("user_id")
        )
        if user and user in {str(x) for x in features.ban_user_id}:
            return False
        group = identifier(raw.get("group_id"))
        entries = {
            str(x) for x in (features.group_list if group else features.private_list)
        }
        mode = features.group_list_type if group else features.private_list_type
        if mode not in {"blacklist", "whitelist"}:
            raise RuntimeError("无法识别适配器名单模式")
        target = group or user
        if (target in entries) == (mode == "blacklist"):
            return False
        if post == "notice":
            if (
                raw.get("notice_type") == "group_msg_emoji_like"
                and not features.enable_emoji_like
            ):
                return False
            if raw.get("notice_type") == "notify" and raw.get("sub_type") == "poke":
                if not features.enable_poke:
                    return False
                if (
                    features.ignore_non_self_poke
                    and identifier(raw.get("target_id")) != self.account
                ):
                    return False
        return True

    def context(self) -> dict[str, Any]:
        """公开连接状态与已安装状态，不探测网络。"""
        return {
            "account": self.account,
            "api_version": 1,
            "handlers": list(self.hooks.handlers),
            "connected": bool(self.adapter.is_connected()),
            "owned": self.handles.valid(),
        }

    def install(self) -> None:
        if self.active:
            if not self.handles.valid():
                self.active = False
                self.hooks.handlers.clear()
                raise RuntimeError("适配器兼容句柄被其他实现替换")
            return
        if (
            getattr(self.adapter, "adapter_version", "") != "0.0.1"
            or getattr(self.adapter, "name", "") != "onebot_adapter"
            or getattr(self.adapter, "platform", "") != "qq"
        ):
            # manifest 2.0.0未覆写组件版本，实际继承BaseAdapter的0.0.1。
            raise RuntimeError("未经审计的 OneBot 适配器版本")
        for name in (
            "register_raw_event_handler",
            "unregister_raw_event_handler",
            "raw_event_context",
            "allows_raw_event",
        ):
            if hasattr(self.adapter, name):
                raise RuntimeError(f"原始事件入口冲突：{name}")
        original = self.adapter.from_platform_message
        original_send = self.adapter._send_platform_message
        check(original, "adapter_receive")
        check(original_send, "adapter_send")
        self.policy({"post_type": "meta_event"})

        @functools.wraps(original)
        async def receive(raw: dict[str, Any]) -> Any:
            if not self.active:
                return await original(raw)
            # echo/心跳保留原始路径和时序，绝不进入业务回调。
            if raw.get("post_type") not in {
                "message",
                "message_sent",
                "notice",
                "request",
            }:
                return await original(raw)
            if raw.get("self_id") is not None:
                self.account = identifier(raw["self_id"])
            if not self.policy(raw):
                return None
            result = await self.hooks.dispatch(raw)
            if result["status"] in {"handled", "ignored"}:
                return None
            if result["status"] == "failed" and raw.get("post_type") in {
                "notice",
                "request",
            }:
                envelope = fallback_envelope(raw, result)
                envelope["message_info"]["extra"]["adapter_signature"] = self.signature
                return envelope
            envelope = await original(raw)
            if envelope is not None and raw.get("post_type") == "message":
                info = envelope.setdefault("message_info", {})
                info["message_type"] = str(raw.get("message_type") or "message")
                info.setdefault("extra", {})["self_id"] = self.account
            return envelope

        @functools.wraps(original_send)
        async def send(envelope: dict[str, Any]) -> Any:
            info = envelope.get("message_info") or {}
            extra = info.get("extra") or {}
            special = extra.get("snowluma_native_send")
            if self.active and isinstance(special, dict):
                try:
                    action, payload = special.get("action"), special.get("params")
                    target = identifier((info.get("group_info") or {}).get("group_id"))
                    if (
                        action != "send_group_ai_record"
                        or not isinstance(payload, dict)
                        or not target
                        or str(payload.get("group_id")) != target
                        or set(payload) != {"group_id", "character", "text"}
                    ):
                        raise ValueError("原生发送动作或目标未通过校验")
                    response = await adapter_api.send_adapter_command(
                        self.signature, action, payload
                    )
                    from .gateway import response_data

                    data = response_data(response)
                    mid = (
                        identifier(data.get("message_id"))
                        if isinstance(data, dict)
                        else ""
                    )
                    if not mid or mid == "0":
                        raise ValueError(
                            "平台未返回可确认的消息ID；结果不确定，请勿自动重发"
                        )
                    return PlatformSendResult(
                        success=True, message_id=mid, response=response
                    )
                except Exception as exc:
                    return PlatformSendResult(
                        success=False, error=type(exc).__name__ + ": " + str(exc)[:200]
                    )
            segments = envelope.get("message_segment") or []
            if isinstance(segments, dict):
                segments = (
                    segments.get("data")
                    if segments.get("type") == "seglist"
                    else [segments]
                )
            # 只补齐本插件创建的原生表情、名片与转发。普通发送委托原实现。
            if (
                not self.active
                or not extra.get("snowluma_display_only")
                or not isinstance(segments, list)
                or not segments
            ):
                return await original_send(envelope)
            kinds = {item.get("type") for item in segments}
            if not kinds.issubset({"face", "contact", "node"}):
                return await original_send(envelope)
            try:
                target = identifier((info.get("group_info") or {}).get("group_id"))
                group = bool(target)
                target = target or identifier(
                    (info.get("user_info") or {}).get("user_id")
                )
                if not target.isdecimal():
                    raise ValueError("发送目标缺少真实数字ID")
                native = []
                for item in segments:
                    kind, data = item["type"], item.get("data")
                    if kind == "face":
                        face = identifier(
                            data.get("id") if isinstance(data, dict) else data
                        )
                        if not face.isdecimal():
                            raise ValueError("表情ID无效")
                        native.append({"type": kind, "data": {"id": face}})
                    else:
                        if not isinstance(data, dict) or not identifier(data.get("id")):
                            raise ValueError("名片/转发须含真实ID")
                        if kind == "contact" and data.get("type") not in {
                            "qq",
                            "group",
                        }:
                            raise ValueError("名片类型无效")
                        native.append({"type": kind, "data": data})
                forward = "node" in kinds
                if forward and kinds != {"node"}:
                    raise ValueError("合并转发只允许node段")
                action = ("send_group_" if group else "send_private_") + (
                    "forward_msg" if forward else "msg"
                )
                params = {
                    "group_id" if group else "user_id": int(target),
                    "messages" if forward else "message": native,
                }
                response = await adapter_api.send_adapter_command(
                    self.signature, action, params
                )
                from .gateway import response_data

                data = response_data(response)
                mid = (
                    identifier(data.get("message_id")) if isinstance(data, dict) else ""
                )
                if not mid:
                    raise ValueError("平台未返回消息ID，未确认发送")
                return PlatformSendResult(
                    success=True, message_id=mid, response=response
                )
            except Exception as exc:
                return PlatformSendResult(
                    success=False, error=type(exc).__name__ + ": " + str(exc)[:200]
                )

        try:
            for name, value in (
                ("from_platform_message", receive),
                ("_send_platform_message", send),
                ("register_raw_event_handler", self.hooks.register),
                ("unregister_raw_event_handler", self.hooks.unregister),
                ("raw_event_context", self.context),
                ("allows_raw_event", self.policy),
            ):
                self.handles.set(self.adapter, name, value)
            self.active = True
        except BaseException:
            self.handles.close()
            raise

    def close(self) -> bool:
        self.active = False
        self.hooks.handlers.clear()
        return self.handles.close()


class ActionBinding:
    """仅为本插件 Action 从两条实际执行入口绑定真实触发消息。"""

    def __init__(self) -> None:
        self.handles = Handles()
        self.active = False

    def install(self) -> None:
        if self.active:
            if not self.handles.valid():
                raise RuntimeError("Action兼容入口冲突")
            return
        from src.core.utils import llm_tool_call
        from src.core.managers.action_manager import ActionManager

        original = llm_tool_call.create_llm_usable_execution
        manager_original = ActionManager.execute_action
        check(original, "action_factory")
        check(manager_original, "action_manager")

        @functools.wraps(original)
        async def create(usable_cls: Any, **kwargs: Any) -> Any:
            if not self.active:
                return await original(usable_cls, **kwargs)
            token = TRIGGER.set(kwargs.get("message"))
            try:
                return await original(usable_cls, **kwargs)
            finally:
                TRIGGER.reset(token)

        @functools.wraps(manager_original)
        async def execute(
            manager: Any, signature: str, plugin: Any, message: Any, **kwargs: Any
        ) -> Any:
            if not self.active:
                return await manager_original(
                    manager, signature, plugin, message, **kwargs
                )
            token = TRIGGER.set(message)
            try:
                return await manager_original(
                    manager, signature, plugin, message, **kwargs
                )
            finally:
                TRIGGER.reset(token)

        self.handles.set(llm_tool_call, "create_llm_usable_execution", create)
        self.handles.set(ActionManager, "execute_action", execute)
        self.active = True

    def close(self) -> bool:
        self.active = False
        return self.handles.close()


class BoundAction(BaseAction):
    """权限上下文只保存框架传入的消息，不猜最近发言人。"""

    def __init__(self, chat_stream: Any, plugin: Any) -> None:
        super().__init__(chat_stream, plugin)
        self.trigger_message = TRIGGER.get()

    def _bind_runtime_context(self, *, message: Any = None) -> None:
        """供可信调用方显式绑定；不会注册为模型参数。"""
        self.trigger_message = message
