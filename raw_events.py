"""通用原始事件扩展契约；无订阅时不改变适配器行为。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

RawCallback = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
RAW_EVENT_API_VERSION = 1
RAW_EVENT_STATUSES = frozenset({"unhandled", "handled", "ignored", "failed"})


class RawEventHooks:
    """实例级有序回调集合，显式区分接管、忽略、失败和未处理。"""

    def __init__(self) -> None:
        """建立空集合。"""
        self.handlers: dict[str, RawCallback] = {}

    def register(self, owner: str, callback: RawCallback) -> None:
        """注册拥有者；重复同一回调幂等，不允许覆盖其他实现。"""
        if not owner or not callable(callback):
            raise ValueError("owner 和 callback 必须有效")
        existing = self.handlers.get(owner)
        if existing is not None and existing != callback:
            raise RuntimeError(f"原始事件处理器冲突: {owner}")
        self.handlers[owner] = callback

    def unregister(self, owner: str) -> None:
        """注销拥有者，不影响其他处理器。"""
        self.handlers.pop(owner, None)

    async def dispatch(self, raw: dict[str, Any]) -> dict[str, Any]:
        """顺序执行；失败保留原始数据供适配器通用降级。"""
        for owner, callback in tuple(self.handlers.items()):
            try:
                result = await callback(raw)
                if (
                    not isinstance(result, dict)
                    or result.get("status") not in RAW_EVENT_STATUSES
                ):
                    raise ValueError("处理器返回了无效的原始事件状态")
            except Exception as exc:
                return {
                    "status": "failed",
                    "owner": owner,
                    "reason": type(exc).__name__,
                }
            if result["status"] != "unhandled":
                return {**result, "owner": owner}
        return {"status": "unhandled"}


def fallback_envelope(raw: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """不查询协议端的保真降级，供下游诊断和其他类型消费者处理。"""
    import time
    import uuid

    info: dict[str, Any] = {
        "platform": "qq",
        "message_id": f"raw-fallback:{uuid.uuid4().hex}",
        "time": time.time(),
        "message_type": str(raw.get("post_type") or "notice"),
        "extra": {"raw_hook_failure": result, "self_id": str(raw.get("self_id") or "")},
    }
    if raw.get("group_id"):
        info["group_info"] = {
            "platform": "qq",
            "group_id": str(raw["group_id"]),
            "group_name": "",
        }
    if raw.get("user_id"):
        info["user_info"] = {
            "platform": "qq",
            "user_id": str(raw["user_id"]),
            "user_nickname": "",
        }
    return {
        "direction": "incoming",
        "message_info": info,
        "raw_event": raw,
        "raw_message": raw,
        "message_segment": {"type": "text", "data": ""},
    }
