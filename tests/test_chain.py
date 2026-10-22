"""从原始适配器入口穿过 receiver/processed/stream/Chatter 的回归。"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.app.plugin_system.api import stream_api
from src.core.prompt import PromptTemplate
from src.core.components.types import EventType
from src.core.models.message import Message, MessageType
from src.kernel.event import EventDecision

from ..models import Scope, normalize
from .conftest import ACCOUNT, ADAPTER, GROUP, OPERATOR, USER, drain, raw_notice


@pytest.mark.parametrize(
    "kind,subtype",
    [
        ("group_msg_emoji_like", "add"),
        ("group_msg_emoji_like", "remove"),
        ("group_increase", "approve"),
        ("group_decrease", "kick"),
        ("group_admin", "set"),
        ("group_card", ""),
        ("notify", "title"),
        ("notify", "group_name"),
        ("essence", "add"),
        ("group_recall", ""),
        ("group_upload", ""),
    ],
)
async def test_raw_to_chatter_without_original_message(env, monkeypatch, kind, subtype):
    """不查询原消息也能到实际框架历史，默认不唤醒，不伪装用户发言。"""
    env.adapter.notice_handler.handle_notice = AsyncMock(
        side_effect=AssertionError("不应走有丢失问题的旧 notice 转换")
    )
    await env.adapter.on_platform_message(
        raw_notice(
            kind,
            sub_type=subtype,
            message_id="777",
            likes=[{"emoji_id": "66", "count": 1}],
        )
    )
    await drain(env)
    stream_id = Scope(ACCOUNT, ADAPTER, GROUP).stream_id
    stream = await stream_api.get_stream(stream_id)
    assert stream is not None
    assert not stream.context.unread_messages
    assert len(stream.context.history_messages) == 1
    message = stream.context.history_messages[0]
    assert message.sender_id == ""
    formatted = "[平台系统事件] " + message.extra["snowluma_text"]
    assert not message.processed_plain_text and not message.content
    assert "平台系统事件" in formatted and "777" in formatted
    assert "暂不可查询" in formatted
    row = (await env.runtime.ledger.rows("SELECT * FROM events"))[0]
    assert row["framework"] == 1 and row["state"] == "delivered"
    from plugins.neo_fatum_chatter.context.sources.history_source import (
        build_fused_narrative,
    )

    narrative = build_fused_narrative(stream, SimpleNamespace(entries=[]))
    assert "说：" not in narrative
    assert "777" not in narrative
    template = PromptTemplate(name="snowluma-test", template="{history}\n{extra}")
    text = (
        await template.set("stream_id", stream_id)
        .set("history", formatted)
        .set("extra", "保留其他插件提醒")
        .build()
    )
    assert "保留其他插件提醒" in text and "会话资料" in text
    assert (await env.runtime.ledger.rows("SELECT consumed FROM events"))[0][
        "consumed"
    ] == 1


async def test_poke_to_bot_wakes_main_model_with_notice_payload(env, monkeypatch):
    """目标为Bot的戳戳成为模型触发事件，并绕过普通闲聊过滤。"""
    raw = raw_notice(
        "notify", sub_type="poke", target_id=ACCOUNT, message_id="poke-777"
    )
    event = normalize(raw, ADAPTER, ACCOUNT)
    assert env.config.events.wake_types == []
    assert env.runtime.wake_requested(event)

    forwarded = []

    async def capture_core(delivered, adapter):
        forwarded.append(env.runtime.envelope(delivered))

    monkeypatch.setattr(env.runtime, "send_to_core", capture_core)
    assert (await env.runtime.capture(ADAPTER, raw))["status"] == "handled"
    rows = await env.runtime.ledger.pending()
    assert len(rows) == 1
    await env.runtime.deliver(rows[0])
    assert len(forwarded) == 1

    envelope = forwarded[0]
    info = envelope["message_info"]
    extra = info["extra"]
    assert info["message_type"] == "notice"
    assert extra["snowluma_wake_requested"] is True
    assert extra["snowluma_state_only"] is False

    message = Message(
        message_id=info["message_id"],
        time=info["time"],
        content=extra["snowluma_text"],
        processed_plain_text=extra["snowluma_text"],
        message_type=MessageType.UNKNOWN,
        sender_id=info["user_info"]["user_id"],
        sender_name=info["user_info"]["user_nickname"],
        platform=info["platform"],
        chat_type="group",
        stream_id=Scope(ACCOUNT, ADAPTER, GROUP, USER).stream_id,
        raw_data=envelope["raw_message"],
        **extra,
    )
    decision, _ = await env.handler.execute(
        EventType.ON_MESSAGE_RECEIVED.value,
        {"message": message, "adapter_signature": ADAPTER},
    )
    assert decision == EventDecision.SUCCESS
    assert message.message_type == MessageType.NOTICE
    assert message.sender_id == "" and message.sender_name == "平台事件"
    assert "戳一戳" in message.processed_plain_text
    assert USER in message.processed_plain_text
    assert ACCOUNT in message.processed_plain_text

    decision, params = await env.handler.execute(
        "neo_default_chatter:preprocess", {"unreads": [message]}
    )
    assert decision == EventDecision.STOP
    assert params["proceed"] is True
    assert env.runtime.counters["wake_preprocess_bypassed"] == 1

    other_target = normalize(
        {**raw, "target_id": "777"}, ADAPTER, ACCOUNT
    )
    self_poke = normalize(
        {**raw, "user_id": ACCOUNT}, ADAPTER, ACCOUNT
    )
    assert not env.runtime.wake_requested(other_target)
    assert not env.runtime.wake_requested(self_poke)
    env.config.events.wake_bot_pokes = False
    assert not env.runtime.wake_requested(event)


async def test_raw_request_persistent_before_conversion_and_duplicate(env):
    """原始 request 不会落入旧适配器未知分支，flag 仅持久内部使用。"""
    raw = {
        "post_type": "request",
        "request_type": "group",
        "sub_type": "invite",
        "self_id": ACCOUNT,
        "group_id": GROUP,
        "user_id": USER,
        "flag": "fixture-private-flag",
        "comment": "测试邀请",
        "time": 1_792_500_000,
    }
    await env.adapter.on_platform_message(raw)
    await env.adapter.on_platform_message(raw)
    rows = await env.runtime.ledger.rows("SELECT * FROM requests")
    assert len(rows) == 1 and rows[0]["state"] == "pending"
    assert rows[0]["kind"] == "group" and rows[0]["flag"] == "fixture-private-flag"
    await drain(env)
    stream = await stream_api.get_stream(
        Scope(ACCOUNT, ADAPTER, user=OPERATOR).stream_id
    )
    assert stream is not None and len(stream.context.history_messages) == 1
    message = stream.context.history_messages[0]
    assert rows[0]["id"] in message.extra["snowluma_text"]
    assert "fixture-private-flag" not in message.extra["snowluma_text"]
    assert "fixture-private-flag" not in json.dumps(message.raw_data)


async def test_unknown_account_and_missing_fields_keep_ledger(env):
    """无归属字段时保留账号事件，不猜群/发送者；未知字段可追溯。"""
    env.config.events.context_types.append("future_event")
    await env.adapter.on_platform_message(
        {
            "post_type": "notice",
            "notice_type": "future_event",
            "self_id": ACCOUNT,
            "future": {"nested": "保真"},
        }
    )
    await drain(env)
    row = (await env.runtime.ledger.rows("SELECT * FROM events"))[0]
    assert json.loads(row["raw"])["future"] == {"nested": "保真"}
    assert env.runtime.counters["account_event"] == 1
    assert not env.streams._streams


async def test_requests_obey_group_private_and_banned_user_filters(env):
    """request、notice 与消息遵循同一顶层名单，重放再次检查撤销。"""
    env.adapter_config.features.group_list_type = "whitelist"
    env.adapter_config.features.group_list = []
    await env.adapter.on_platform_message(
        {**raw_notice(""), "post_type": "request", "request_type": "group", "flag": "x"}
    )
    assert not await env.runtime.ledger.rows("SELECT * FROM requests")
    env.adapter_config.features.group_list = [GROUP]
    await env.adapter.on_platform_message(raw_notice("group_card"))
    env.adapter_config.features.group_list = []
    await drain(env)
    assert (await env.runtime.ledger.rows("SELECT state,error FROM events"))[0] == {
        "state": "ignored",
        "error": "policy_revoked",
    }
    env.adapter_config.features.private_list_type = "whitelist"
    env.adapter_config.features.private_list = []
    await env.adapter.on_platform_message(
        {
            "post_type": "request",
            "request_type": "friend",
            "self_id": ACCOUNT,
            "user_id": USER,
            "flag": "f",
        }
    )
    assert not await env.runtime.ledger.rows("SELECT * FROM requests")


async def test_queue_full_and_restart_recover_requests(env, tmp_path):
    """唤醒队列满不影响持久请求；重启恢复 processing 为 uncertain。"""
    env.runtime.queue = asyncio.Queue(maxsize=1)
    for index in range(3):
        await env.adapter.on_platform_message(
            {
                "post_type": "request",
                "request_type": "friend",
                "self_id": ACCOUNT,
                "user_id": USER,
                "flag": f"f{index}",
            }
        )
    assert env.runtime.counters["queue_full_recoverable"] == 2
    rows = await env.runtime.ledger.rows("SELECT * FROM requests")
    assert len(rows) == 3
    await env.runtime.ledger.write(
        "UPDATE requests SET state='processing' WHERE id=?", (rows[0]["id"],)
    )
    await env.runtime.ledger.close()
    await env.runtime.ledger.open()
    assert (
        await env.runtime.ledger.rows(
            "SELECT state FROM requests WHERE id=?", (rows[0]["id"],)
        )
    )[0]["state"] == "uncertain"
    assert (
        len(
            await env.runtime.ledger.rows("SELECT id FROM events WHERE state='pending'")
        )
        == 3
    )


async def test_echo_normal_meta_and_unload_preserve_original_chain(env):
    """echo 不入业务层；普通消息/心跳分支保留；关闭后不接管。"""
    future = asyncio.get_running_loop().create_future()
    env.adapter._response_pool["echo-test"] = future
    await env.adapter.on_platform_message(
        {"echo": "echo-test", "status": "ok", "retcode": 0, "data": {}}
    )
    assert future.done()
    env.adapter.message_handler.handle_raw_message = AsyncMock(return_value=None)
    env.adapter.meta_event_handler.handle_meta_event = AsyncMock(return_value=None)
    await env.adapter.on_platform_message(
        {"post_type": "message", "self_id": ACCOUNT, "sender": {"user_id": USER}}
    )
    await env.adapter.on_platform_message(
        {"post_type": "meta_event", "meta_event_type": "heartbeat"}
    )
    env.adapter.message_handler.handle_raw_message.assert_awaited_once()
    env.adapter.meta_event_handler.handle_meta_event.assert_awaited_once()
    await env.runtime.stop()
    env.adapter.notice_handler.handle_notice = AsyncMock(return_value=None)
    await env.adapter.on_platform_message(raw_notice("group_card"))
    env.adapter.notice_handler.handle_notice.assert_awaited_once()


async def test_callbacks_cannot_deadlock_on_same_websocket_api(env):
    """原始接收不会查询平台；响应可在 worker 处理期间继续收取。"""
    env.runtime.gateway.raw_call = AsyncMock(
        side_effect=AssertionError("接收回调不得联网")
    )
    await asyncio.wait_for(
        env.adapter.on_platform_message(
            raw_notice("group_msg_emoji_like", message_id="missing")
        ),
        timeout=1,
    )
    env.runtime.gateway.raw_call.assert_not_awaited()
    assert len(await env.runtime.ledger.pending()) == 1
