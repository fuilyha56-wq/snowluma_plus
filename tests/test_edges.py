"""权限变化、损坏快照、失败回滚、午夜及协议旁路的边界测试。"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from src.app.plugin_system.api import adapter_api, stream_api
from src.core.models.message import Message
from src.core.models.stream import ChatStream
from src.core.transport.message_send import message_sender

from .. import business as business_module
from .. import runtime as runtime_module
from ..components import SendAction, parse_params, platform_message
from ..gateway import BusinessError, UncertainError
from ..handlers import muted
from ..models import Scope
from ..runtime import Runtime
from .conftest import ACCOUNT, ADAPTER, GROUP, OPERATOR, USER, raw_notice


async def test_permissions_changed_notice_deletion_held_until_rebaseline(env):
    """权限视野改变不冒充删除；显式重建只建立新基线。"""
    scope = Scope(ACCOUNT, ADAPTER, GROUP)
    env.runtime.gateway.raw_call = AsyncMock(
        return_value={"status": "ok", "retcode": 0, "data": [{"notice_id": "n1"}]}
    )
    env.runtime.gateway.bot_role = AsyncMock(return_value={"role": "admin"})
    await env.runtime.business.notices(scope)
    env.runtime.gateway.raw_call.return_value = {
        "status": "ok",
        "retcode": 0,
        "data": [],
    }
    env.runtime.gateway.bot_role.return_value = {"role": "member"}
    result = await env.runtime.business.notices(scope)
    assert not result["complete"] and "权限" in result["note"]
    assert "n1" in (await env.runtime.ledger.snapshot(scope, "notices"))["data"]
    assert not await env.runtime.ledger.rows("SELECT id FROM events")
    assert (await env.runtime.business.notices(scope, reset=True))["baseline"]


async def test_corrupt_member_snapshot_refreshes_without_fabricating_data(env):
    """损坏非关键快照可由成功读取恢复，不将损坏当空名单。"""
    scope = Scope(ACCOUNT, ADAPTER, GROUP)
    await env.runtime.ledger.save_snapshot(scope, "members", [], True)
    await env.runtime.ledger.write(
        "UPDATE snapshots SET data='broken' WHERE kind='members'"
    )
    env.runtime.gateway.raw_call = AsyncMock(
        return_value={
            "status": "ok",
            "retcode": 0,
            "data": [{"user_id": USER, "nickname": "恢复"}],
        }
    )
    result = await env.runtime.business.members(scope)
    assert result["data"][0]["nickname"] == "恢复" and result["complete"]


async def test_mute_durable_isolated_and_corruption_fail_closed(env):
    """禁言先与事件原子落盘；重启、其他账号、损坏状态的策略明确。"""
    scope = Scope(ACCOUNT, ADAPTER, GROUP)
    await env.adapter.on_platform_message(
        raw_notice("group_ban", sub_type="ban", user_id=0, duration=60)
    )
    assert await muted(env.runtime, scope)
    assert not await muted(env.runtime, Scope("90002", ADAPTER, GROUP))
    event_row = (await env.runtime.ledger.pending())[0]
    from ..models import normalize

    event = normalize(
        raw_notice("group_ban", sub_type="ban", user_id=0, duration=60),
        ADAPTER,
        ACCOUNT,
    )
    envelope = env.runtime.envelope(event)
    assert envelope["message_info"]["extra"]["notice_type"] == "group_whole_ban"
    assert isinstance(envelope["message_segment"]["data"], dict)
    await env.runtime.ledger.close()
    await env.runtime.ledger.open()
    assert await muted(env.runtime, scope)
    await env.runtime.ledger.write(
        "UPDATE snapshots SET data='broken' WHERE kind='mute'"
    )
    assert await muted(env.runtime, scope)
    await env.adapter.on_platform_message(
        raw_notice("group_ban", sub_type="lift_ban", user_id=0, duration=0)
    )
    assert len(await env.runtime.ledger.rows("SELECT * FROM events")) == 2
    assert await muted(env.runtime, scope)
    assert event_row["state"] == "pending"


async def test_outgoing_private_bot_id_does_not_prove_peer_scope(env):
    """Bot在任何私聊的sender相同，必须有当前会话的持久映射。"""
    scope = Scope(ACCOUNT, ADAPTER, user=USER)
    env.runtime.gateway.raw_call = AsyncMock(
        return_value={
            "status": "ok",
            "retcode": 0,
            "data": {"sender": {"user_id": ACCOUNT}, "message_type": "private"},
        }
    )
    with pytest.raises(BusinessError, match="私聊"):
        await platform_message(env.runtime, scope, "platform:777")
    await env.runtime.ledger.write(
        "INSERT INTO mappings VALUES(?,?,?,?)", (scope.key, "framework-1", "777", 1)
    )
    assert await platform_message(env.runtime, scope, "framework:framework-1") == "777"


async def test_framework_forward_and_generic_bypass(env, monkeypatch):
    """多条node通过正常框架合并转发；通用动作不能旁路发送。"""
    scope = Scope(ACCOUNT, ADAPTER, GROUP, OPERATOR)
    env.config.access.allowed_actions = ["send_group_forward_msg"]
    env.config.access.write_groups = [GROUP]
    env.runtime.gateway.raw_call = AsyncMock(
        return_value={"status": "ok", "retcode": 0, "data": {"group_id": GROUP}}
    )
    with pytest.raises(BusinessError, match="框架"):
        await env.runtime.gateway.call(
            scope,
            OPERATOR,
            "send_group_forward_msg",
            {"group_id": GROUP, "messages": [{"type": "node"}]},
            write=True,
        )
    stream_id = ChatStream.generate_stream_id(platform="qq", group_id=GROUP)
    stream = await stream_api.get_or_create_stream(
        stream_id=stream_id, platform="qq", group_id=GROUP, chat_type="group"
    )
    env.runtime.scopes[stream_id] = scope
    sender = message_sender.MessageSender()
    sender.set_adapter_manager(
        SimpleNamespace(get_adapter=lambda signature: env.adapter)
    )
    monkeypatch.setattr(message_sender, "_global_message_sender", sender)
    backend = AsyncMock(
        return_value={"status": "ok", "retcode": 0, "data": {"message_id": 456}}
    )
    env.adapter.send_handler.send_message_to_onebot = backend
    monkeypatch.setattr(adapter_api, "send_adapter_command", backend)
    action = SendAction(stream, env.plugin)
    action._bind_runtime_context(
        message=Message(sender_id=OPERATOR, stream_id=stream_id)
    )
    success, message = await action.execute(
        "forward", '["platform:777","platform:778"]'
    )
    assert success, message
    assert backend.call_args.args[1] == "send_group_forward_msg"
    assert len(backend.call_args.args[2]["messages"]) == 2
    assert stream.context.history_messages[-1].message_id == "456"


async def test_start_failure_rolls_back_hook_and_database(env, monkeypatch, tmp_path):
    """任务注册异常关闭新协程、注销句柄、关闭账本。"""
    await env.runtime.stop()
    manager = SimpleNamespace(
        create_task=lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("fixture task failure")
        )
    )
    monkeypatch.setattr(runtime_module, "get_task_manager", lambda: manager)
    runtime = Runtime(env.config, tmp_path / "rollback.db")
    with pytest.raises(RuntimeError, match="fixture"):
        await runtime.start()
    assert not runtime.running and runtime.ledger.db is None
    assert not hasattr(env.adapter, "raw_event_context")


async def test_checkin_midnight_is_uncertain_for_both_dates(env, monkeypatch):
    """在途请求跨午夜不能错误登记某天成功，也不能次日再自动发。"""
    scope = Scope(ACCOUNT, ADAPTER, GROUP)
    env.config.checkin.groups = [GROUP]
    env.config.access.write_groups = [GROUP]
    env.config.access.allowed_actions = ["set_group_sign"]
    values = [
        datetime(2026, 10, 21, 23, 59, 59, tzinfo=ZoneInfo("Asia/Shanghai")),
        datetime(2026, 10, 22, 0, 0, 1, tzinfo=ZoneInfo("Asia/Shanghai")),
    ]

    class Clock:
        """可控配置时区时钟。"""

        @classmethod
        def now(cls, timezone):
            """先调用前一天，再调用次日。"""
            return values.pop(0)

    monkeypatch.setattr(business_module, "datetime", Clock)
    env.runtime.gateway.raw_call = AsyncMock(
        return_value={"status": "ok", "retcode": 0, "data": None}
    )
    with pytest.raises(UncertainError, match="午夜"):
        await env.runtime.business.checkin(scope, OPERATOR)
    assert {
        row["state"]
        for row in await env.runtime.ledger.rows("SELECT state FROM operations")
    } == {"uncertain"}
    assert len(await env.runtime.ledger.rows("SELECT * FROM operations")) == 2


@pytest.mark.parametrize(
    "text", ["[]", "bad", "x" * 16001, '{"x":' * 20 + "0" + "}" * 20]
)
def test_parameter_budget_rejects_invalid_unbounded_inputs(text):
    """参数预算在协议执行之前生效。"""
    with pytest.raises(BusinessError):
        parse_params(text)
