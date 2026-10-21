"""异步 Sink 确认、多账号隔离、真实 Chatter 上下文和禁言保护。"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from plugins.onebot_expand.event_handler import SelfIdInjectHandler
from plugins.onebot_adapter.src.handlers.to_core import (
    message_handler as adapter_messages,
)
from src.app.plugin_system.api import stream_api
from src.core.components.base.chatter import BaseChatter
from src.core.components.types import EventType
from src.core.transport.sink.core_sink_impl import InProcessCoreSinkImpl
from src.kernel.event import EventDecision

from ..gateway import BusinessError
from ..models import Scope
from .conftest import ACCOUNT, ADAPTER, GROUP, OPERATOR, USER, drain, raw_notice


async def test_actual_async_core_sink_waits_for_persistence(env):
    """Sink.send 仅派发任务，Plus 必须等待真实 receiver 入库。"""

    async def receive(envelope):
        """真正的核心接收入口。"""
        await env.receiver.receive_envelope(envelope, ADAPTER)

    sink = InProcessCoreSinkImpl(receive)
    env.adapter.core_sink = sink
    try:
        await env.adapter.on_platform_message(
            raw_notice("group_card", card_new="异步新名片")
        )
        await drain(env)
        assert (await env.runtime.ledger.rows("SELECT state,framework FROM events"))[
            0
        ] == {"state": "delivered", "framework": 1}
    finally:
        await sink.close()


async def test_consumer_absence_does_not_mark_delivery_success(env):
    """没有 processed 消费者时保留账本，而不是将 Sink 成功当作业务成功。"""
    env.manager._unregister_handler_locked(
        "snowluma_plus:event_handler:snowluma_events"
    )
    env.config.events.delivery_timeout_seconds = 0.1
    await env.adapter.on_platform_message(raw_notice("group_card"))
    row = (await env.runtime.ledger.pending())[0]
    with pytest.raises(BusinessError, match="consumer_delivery_timeout"):
        await env.runtime.deliver(row)
    assert (await env.runtime.ledger.rows("SELECT state,framework FROM events"))[0] == {
        "state": "pending",
        "framework": 0,
    }


async def test_accounts_share_group_number_but_never_chat_stream(env):
    """同群号在不同登录账号下具有不同实际框架流，旧账号工具也被拒绝。"""
    await env.adapter.on_platform_message(raw_notice("group_card", card_new="账号一"))
    await drain(env)
    other = "90002"
    await env.adapter.on_platform_message(
        raw_notice("group_card", self_id=other, card_new="账号二")
    )
    await drain(env)
    first = await stream_api.get_stream(Scope(ACCOUNT, ADAPTER, GROUP).stream_id)
    second = await stream_api.get_stream(Scope(other, ADAPTER, GROUP).stream_id)
    assert (
        first is not None and second is not None and first.stream_id != second.stream_id
    )
    assert (
        len(first.context.history_messages) == len(second.context.history_messages) == 1
    )
    assert "账号一" in first.context.history_messages[0].extra["snowluma_text"]
    assert "账号二" not in first.context.history_messages[0].extra["snowluma_text"]
    with pytest.raises(BusinessError, match="账号"):
        env.runtime.gateway.allowed_scope(Scope(ACCOUNT, ADAPTER, GROUP))


async def test_both_real_chatter_context_builders_include_identity(env, monkeypatch):
    """直接调用现有两个 Chatter 的真实构建/贡献入口，而非仅检查 reminder 存储。"""
    from plugins.neo_default_chatter.utils.prompt_builder import NeoChatterPromptBuilder
    from plugins.neo_default_chatter.utils.prompts import user_prompt
    from plugins.neo_fatum_chatter.context.sources.plugin_source import (
        collect_plugin_turn_contributions,
    )
    import src.core.prompt.manager as prompt_manager

    scope = Scope(ACCOUNT, ADAPTER, GROUP)
    await env.runtime.ledger.save_snapshot(
        scope,
        "identity",
        {
            "bot": {"user_id": ACCOUNT, "role": "admin", "title": "雪光"},
            "bot_honor": {"talkative": [{"user_id": ACCOUNT}]},
        },
        True,
    )
    await env.adapter.on_platform_message(
        raw_notice("notify", sub_type="title", title="雪光")
    )
    await drain(env)
    stream = await stream_api.get_stream(scope.stream_id)
    history = "\n".join(
        BaseChatter.format_message_line(message)
        for message in stream.context.history_messages
    )
    pm = prompt_manager.PromptManager()
    monkeypatch.setattr(prompt_manager, "_global_manager", pm)
    pm.get_or_create(name="neo_default_chatter_user_prompt", template=user_prompt)
    ndfc = await NeoChatterPromptBuilder.build_user_prompt(
        stream, history, "", "其他插件资料"
    )
    assert "雪光" in ndfc and "会话资料" in ndfc and "其他插件资料" in ndfc
    nfc = await collect_plugin_turn_contributions(
        prompt_name="nfc", content=history, stream_id=scope.stream_id
    )
    assert any("雪光" in item.content and "会话资料" in item.content for item in nfc)
    assert (await env.runtime.ledger.rows("SELECT consumed FROM events"))[0][
        "consumed"
    ] == 1


async def test_ban_guard_sees_enhanced_notice_and_real_normal_message(env, monkeypatch):
    """新 notice 保留 raw_event，原 Expand 禁言保护在真实 MessageHandler 输入下继续工作。"""
    guard = SelfIdInjectHandler(SimpleNamespace())
    await env.manager.register_handler(
        "onebot_expand:event_handler:self_id_inject_handler", guard
    )
    observed = []

    async def observe(_, params):
        """只观察普通消息是否穿过过滤，不取代框架接收或归一化。"""
        observed.append(params["message"].message_id)
        return EventDecision.PASS, params

    env.bus.subscribe(EventType.ON_MESSAGE_RECEIVED.value, observe, priority=-10)
    monkeypatch.setattr(
        adapter_messages,
        "get_group_info",
        AsyncMock(return_value={"group_name": "离线群"}),
    )
    await env.adapter.on_platform_message(
        raw_notice(
            "group_ban",
            user_id=ACCOUNT,
            operator_id=OPERATOR,
            sub_type="ban",
            duration=60,
        )
    )
    await drain(env)
    raw = {
        "post_type": "message",
        "message_type": "group",
        "self_id": ACCOUNT,
        "group_id": GROUP,
        "user_id": USER,
        "sender": {"user_id": USER, "nickname": "离线成员", "role": "member"},
        "time": time.time(),
        "message": [{"type": "text", "data": {"text": "普通消息"}}],
    }
    await env.adapter.on_platform_message({**raw, "message_id": "normal-muted"})
    assert "normal-muted" not in observed
    await env.adapter.on_platform_message(
        raw_notice(
            "group_ban",
            user_id=ACCOUNT,
            operator_id=OPERATOR,
            sub_type="lift_ban",
            duration=0,
        )
    )
    await drain(env)
    await env.adapter.on_platform_message({**raw, "message_id": "normal-unmuted"})
    assert "normal-unmuted" in observed


async def test_order_preserved_across_retry_but_other_group_progresses(env):
    """同一会话后续事件不能越过待重试头部，其他群仍可处理。"""
    for group in (GROUP, GROUP, "20002"):
        await env.adapter.on_platform_message(raw_notice("group_card", group_id=group))
    rows = await env.runtime.ledger.pending()
    assert len(rows) == 2
    await env.runtime.ledger.failed(rows[0], "fixture_failure", 3)
    available = await env.runtime.ledger.pending()
    assert len(available) == 1 and available[0]["id"] == rows[1]["id"]


async def test_core_is_unchanged_and_plugin_routes_before_distribution(env):
    """宿主忽略扩展字段，只有插件事件消费者建立账号隔离流。"""
    from src.core.transport.message_receive.utils import extract_stream_id

    info = {
        "platform": "qq",
        "group_info": {"group_id": GROUP},
        "extra": {"routing_stream_id": "a" * 64},
    }
    assert extract_stream_id(info) != "a" * 64
    await env.adapter.on_platform_message(raw_notice("group_card"))
    await drain(env)
    assert await stream_api.get_stream(Scope(ACCOUNT, ADAPTER, GROUP).stream_id)
