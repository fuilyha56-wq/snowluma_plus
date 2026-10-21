"""明确签名、真实执行器、普通互动与正常发送的业务回归。"""

import inspect
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.app.plugin_system.api import adapter_api, stream_api
from src.core.models.message import Message
from src.core.transport.message_send import message_sender
from src.core.utils import llm_tool_call

from ..components import CheckinAction, ManageAction
from ..direct import DIRECT_COMPONENTS, Poke, ProfileLike, React, Recall, Text
from ..generated import GENERATED_COMPONENTS, ApiGetStrangerInfo, ApiSendGroupAiRecord
from ..models import Scope
from .conftest import ACCOUNT, ADAPTER, GROUP, USER


def test_every_direct_schema_has_business_parameters():
    components = DIRECT_COMPONENTS + GENERATED_COMPONENTS
    names = [cls.name for cls in components]
    assert len(names) == len(set(names)) == 157
    for cls in components:
        schema = cls.to_schema()["function"]["parameters"]
        assert not {"action", "params_json"} & schema["properties"].keys(), cls.name
        signature = inspect.signature(cls.execute)
        assert not any(
            p.kind in {p.VAR_KEYWORD, p.VAR_POSITIONAL}
            for p in signature.parameters.values()
        )
        assert "接口" not in cls.name


async def setup_stream(env):
    scope = Scope(ACCOUNT, ADAPTER, GROUP, USER)
    stream = await stream_api.get_or_create_stream(
        stream_id=scope.stream_id, platform="qq", group_id=GROUP, chat_type="group"
    )
    env.runtime.scopes[stream.stream_id] = scope
    await env.runtime.ledger.write(
        "INSERT OR IGNORE INTO mappings(scope,framework_id,platform_id,at) VALUES(?,?,?,?)",
        (scope.key, "trigger", "771", 1),
    )
    trigger = Message(
        message_id="trigger", sender_id=USER, stream_id=stream.stream_id, platform="qq"
    )
    env.config.access.operators = []
    env.config.access.management_users = []
    env.config.access.allowed_actions = []
    env.config.access.write_groups = []
    return scope, stream, trigger


async def execute(env, cls, trigger, **arguments):
    execution = await llm_tool_call.create_llm_usable_execution(
        cls, plugin=env.plugin, message=trigger, kwargs=arguments
    )
    return await execution.wait_done()


async def test_direct_interactions_do_not_search_catalog_and_keep_permissions(
    env, monkeypatch
):
    scope, stream, trigger = await setup_stream(env)
    monkeypatch.setattr(
        env.runtime.gateway, "search", lambda *a, **k: pytest.fail("不应搜索目录")
    )
    calls = []

    async def protocol(scope, action, params):
        calls.append((action, params))
        data = {
            "message_id": params.get("message_id"),
            "group_id": GROUP,
            "sender": {"user_id": ACCOUNT},
        }
        return {"status": "ok", "retcode": 0, "data": data}

    monkeypatch.setattr(env.runtime.gateway, "raw_call", protocol)
    assert (await execute(env, React, trigger, emoji="赞"))[0]
    assert calls[-1] == (
        "set_msg_emoji_like",
        {"message_id": "771", "emoji_id": "76", "set": True},
    )
    assert (await execute(env, Poke, trigger))[0]
    assert calls[-1] == ("group_poke", {"group_id": GROUP, "user_id": USER})
    assert (await execute(env, ProfileLike, trigger, user_id=USER, times=3))[0]
    assert calls[-1] == ("send_like", {"user_id": USER, "times": 3})
    before = len(calls)
    assert not (await execute(env, ProfileLike, trigger, user_id="10003", times=1))[0]
    assert not (await execute(env, ProfileLike, trigger, user_id=USER, times=11))[0]
    assert len(calls) == before
    generic = ManageAction(stream, env.plugin)
    generic._bind_runtime_context(message=trigger)
    assert not (
        await generic.execute("send_like", json.dumps({"user_id": USER, "times": 1}))
    )[0]
    env.config.access.allow_basic_interactions = False
    assert not (await execute(env, React, trigger))[0]


async def test_direct_send_returns_real_id_then_own_recall(env, monkeypatch):
    scope, stream, trigger = await setup_stream(env)
    sender = message_sender.MessageSender()
    sender.set_adapter_manager(SimpleNamespace(get_adapter=lambda _: env.adapter))
    monkeypatch.setattr(message_sender, "_global_message_sender", sender)
    backend = AsyncMock(
        return_value={"status": "ok", "retcode": 0, "data": {"message_id": 889}}
    )
    env.adapter.send_handler.send_message_to_onebot = backend
    success, result = await execute(env, Text, trigger, text="直接发送测试")
    assert success and "platform_message_id=889" in result
    assert stream.context.history_messages[-1].message_id == "889"
    readback = AsyncMock(
        return_value={
            "status": "ok",
            "retcode": 0,
            "data": {
                "message_id": "889",
                "group_id": GROUP,
                "sender": {"user_id": ACCOUNT},
            },
        }
    )
    monkeypatch.setattr(env.runtime.gateway, "raw_call", readback)
    assert (await execute(env, Recall, trigger, message_id="889"))[0]
    assert readback.call_args.args[1] == "delete_msg"
    readback.return_value["data"]["sender"]["user_id"] = USER
    assert not (await execute(env, Recall, trigger, message_id="889"))[0]
    assert readback.call_args.args[1] == "get_msg"


async def test_generated_explicit_read_passes_id_without_model_json(env, monkeypatch):
    _, _, trigger = await setup_stream(env)
    protocol = AsyncMock(
        return_value={"status": "ok", "retcode": 0, "data": {"user_id": USER}}
    )
    monkeypatch.setattr(env.runtime.gateway, "raw_call", protocol)
    success, result = await execute(env, ApiGetStrangerInfo, trigger, user_id=USER)
    assert success and result["data"]["user_id"] == USER
    assert protocol.call_args.args[1] == "get_stranger_info"
    assert protocol.call_args.args[2]["user_id"] == USER


async def test_generated_ai_speech_uses_framework_history_and_real_ack(
    env, monkeypatch
):
    _, stream, trigger = await setup_stream(env)
    env.config.access.operators = [USER]
    env.config.access.allowed_actions = ["send_group_ai_record"]
    env.config.access.write_groups = [GROUP]
    sender = message_sender.MessageSender()
    sender.set_adapter_manager(SimpleNamespace(get_adapter=lambda _: env.adapter))
    monkeypatch.setattr(message_sender, "_global_message_sender", sender)
    backend = AsyncMock(
        return_value={"status": "ok", "retcode": 0, "data": {"message_id": 890}}
    )
    monkeypatch.setattr(adapter_api, "send_adapter_command", backend)
    success, result = await execute(
        env, ApiSendGroupAiRecord, trigger, character="test-character", text="测试语音"
    )
    assert success, result
    assert backend.call_args.args[1] == "send_group_ai_record"
    assert stream.context.history_messages[-1].message_id == "890"
    assert env.runtime.counters["send_confirmed"] == 1


async def test_multiword_catalog_regression(env):
    for query, expected in [
        ("reaction poke recall", "set_msg_emoji_like"),
        ("贴表情 戳一戳 撤回", "delete_msg"),
    ]:
        result = env.runtime.gateway.search(query, limit=50)
        assert expected in {row["action"] for row in result["items"]}


async def test_manual_checkin_with_default_blacklist_shares_daily_record(
    env, monkeypatch
):
    _, _, trigger = await setup_stream(env)
    protocol = AsyncMock(return_value={"status": "ok", "retcode": 0, "data": None})
    monkeypatch.setattr(env.runtime.gateway, "raw_call", protocol)
    assert (await execute(env, CheckinAction, trigger))[0]
    assert (await execute(env, CheckinAction, trigger))[0]
    assert protocol.await_count == 1
    assert not env.config.checkin.enabled and not env.config.checkin.groups


@pytest.mark.parametrize(
    "field,value",
    [
        ("blocked_users", USER),
        ("blocked_groups", GROUP),
        ("blocked_actions", "set_msg_emoji_like"),
    ],
)
async def test_default_blacklist_has_priority_over_basic_interactions(
    env, monkeypatch, field, value
):
    _, _, trigger = await setup_stream(env)
    setattr(env.config.access, field, [value])
    call = AsyncMock()
    monkeypatch.setattr(env.runtime.gateway, "raw_call", call)
    success, reason = await execute(env, React, trigger)
    assert not success and "黑名单" in reason
    call.assert_not_awaited()
