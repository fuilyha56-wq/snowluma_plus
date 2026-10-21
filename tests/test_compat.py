"""仅插件内兼容的所有权、重绑、原方法恢复及权限上下文。"""

from __future__ import annotations

import asyncio
import functools
from types import SimpleNamespace

import pytest

from plugins.onebot_adapter.plugin import OneBotAdapter
from src.app.plugin_system.api import stream_api
from src.core.managers.action_manager import ActionManager
from src.core.models.message import Message
from src.core.utils import llm_tool_call

from ..compat import AdapterBinding, BoundAction, check
from ..models import Scope
from .conftest import ACCOUNT, ADAPTER, GROUP, OPERATOR, USER, drain, raw_notice


async def test_replacement_adapter_restores_old_instance_and_rebinds(env):
    old = env.adapter
    new = OneBotAdapter(old.core_sink, SimpleNamespace(config=env.adapter_config))
    env.adapters[ADAPTER] = new
    await env.runtime.bind()
    assert "from_platform_message" not in vars(old)
    assert not hasattr(old, "raw_event_context")
    assert new.raw_event_context()["handlers"] == ["snowluma_plus:raw_v1"]
    await new.on_platform_message(raw_notice("group_card"))
    await drain(env)
    assert await stream_api.get_stream(Scope(ACCOUNT, ADAPTER, GROUP).stream_id)
    await env.runtime.stop()
    assert "from_platform_message" not in vars(new)
    assert "_send_platform_message" not in vars(new)
    assert not hasattr(new, "raw_event_context")


async def test_conflict_disables_capture_and_preserves_later_wrapper(env):
    original = env.adapter.from_platform_message

    @functools.wraps(original)
    async def later(raw):
        return await original(raw)

    env.adapter.from_platform_message = later
    with pytest.raises(RuntimeError, match="替换"):
        await env.runtime.bind()
    assert not env.runtime.bindings[ADAPTER].active
    assert not env.adapter.raw_event_context()["owned"]
    await env.runtime.stop()
    assert env.adapter.from_platform_message is later
    assert env.runtime.counters["compat_restore_conflict"] == 1


def test_fingerprint_rejects_wrapper_even_if_metadata_is_preserved():
    original = OneBotAdapter.from_platform_message

    @functools.wraps(original)
    async def changed(self, raw):
        return await original(self, raw)

    with pytest.raises(RuntimeError, match="未经审计"):
        check(changed, "adapter_receive")


async def test_second_runtime_cannot_overwrite_owned_adapter(env):
    binding = AdapterBinding(env.adapter, ADAPTER, ACCOUNT)
    with pytest.raises(RuntimeError, match="冲突"):
        binding.install()
    assert env.adapter.raw_event_context()["owned"]


async def test_real_action_manager_and_concurrent_factory_bind_exact_message(
    env, monkeypatch
):
    class Identity(BoundAction):
        name = "identity"
        description = "test"

        async def execute(self):
            await asyncio.sleep(0)
            return True, self.trigger_message.sender_id

    scope = Scope(ACCOUNT, ADAPTER, GROUP)
    stream = await stream_api.get_or_create_stream(
        stream_id=scope.stream_id, platform="qq", group_id=GROUP, chat_type="group"
    )
    manager = ActionManager()
    monkeypatch.setattr(manager, "get_action_class", lambda signature: Identity)
    message = Message(sender_id=OPERATOR, stream_id=stream.stream_id, platform="qq")
    assert await manager.execute_action(
        "snowluma_plus:action:identity", env.plugin, message
    ) == (True, OPERATOR)

    async def execute(user):
        execution = await llm_tool_call.create_llm_usable_execution(
            Identity,
            plugin=env.plugin,
            message=Message(sender_id=user, stream_id=stream.stream_id),
        )
        return await execution.wait_done()

    assert await asyncio.gather(execute(USER), execute(OPERATOR)) == [
        (True, USER),
        (True, OPERATOR),
    ]
    assert Identity(stream, env.plugin).trigger_message is None


async def test_private_route_uses_real_peer_with_isolation_disabled(env):
    from src.core.models.stream import ChatStream

    env.config.plugin.isolate_streams = False
    await env.adapter.on_platform_message(raw_notice("friend_add", group_id=None))
    await drain(env)
    stream_id = ChatStream.generate_stream_id(platform="qq", user_id=USER)
    stream = await stream_api.get_stream(stream_id)
    assert stream and stream.context.history_messages[0].sender_id == ""


async def test_default_chatter_public_history_hook_keeps_other_subscribers(env):
    from plugins.neo_default_chatter.utils.event_publisher import NdfcPublisher
    from plugins.neo_default_chatter.components.event_handlers.defaults.build_history_text import (
        BuildHistoryTextDefaultHandler,
    )

    await env.adapter.on_platform_message(raw_notice("group_card"))
    await drain(env)
    stream = await stream_api.get_stream(Scope(ACCOUNT, ADAPTER, GROUP).stream_id)
    handler = BuildHistoryTextDefaultHandler(SimpleNamespace())
    await env.manager.register_handler(
        "neo_default_chatter:event_handler:build_history_text_default", handler
    )
    assert (
        await NdfcPublisher.build_history_text(
            stream_id=stream.stream_id, chat_stream=stream
        )
        == ""
    )
    assert len(stream.context.history_messages) == 1
