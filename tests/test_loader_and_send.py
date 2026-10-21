"""真实插件加载、公共 Expand Service 与框架发送链路离线验证。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.app.plugin_system.api import adapter_api, stream_api
from src.core.components.loader import load_manifest
from src.core.models.message import Message
from src.core.models.stream import ChatStream
from src.core.transport.message_send import message_sender

from ..components import SendAction
from ..models import Scope
from .conftest import ACCOUNT, ADAPTER, GROUP, OPERATOR, USER


@pytest.mark.parametrize("archive", [False, True], ids=["source", "mfp"])
async def test_actual_plugin_manager_load_service_tool_and_unload(
    env, monkeypatch, tmp_path, archive
):
    """使用真实 PluginManager/注册表/ServiceManager，不只证明模块能 import。"""
    import src.core.components.registry as registry_module
    import src.core.managers.plugin_manager as manager_module
    import src.core.managers.config_manager as config_module
    from plugins.onebot_expand.services.account_service import AccountService
    from plugins.onebot_expand import api_client

    await env.runtime.stop()
    monkeypatch.chdir(tmp_path)
    registry = registry_module.ComponentRegistry()
    monkeypatch.setattr(registry_module, "_global_registry", registry)
    pm = manager_module.PluginManager()
    import src.core.components.loader as loader_module

    monkeypatch.setattr(
        loader_module,
        "_plugin_registry",
        {
            key: value
            for key, value in loader_module._plugin_registry.items()
            if key != "snowluma_plus"
        },
    )
    monkeypatch.setattr(manager_module, "_global_plugin_manager", pm)
    cm = config_module.ConfigManager()
    cm._configs["snowluma_plus"] = env.config
    monkeypatch.setattr(config_module, "get_config_manager", lambda: cm)
    pm._loaded_plugins["onebot_expand"] = SimpleNamespace(config=SimpleNamespace())
    registry.register(AccountService, "onebot_expand:service:account_service")
    calls = []

    async def protocol(**kwargs):
        """唯一测试替身位于协议边界，框架与 Service 代码真实执行。"""
        calls.append(kwargs)
        return {
            "status": "ok",
            "retcode": 0,
            "data": {"group_id": GROUP, "group_name": "离线群"},
        }

    monkeypatch.setattr(api_client, "send_adapter_command", protocol)
    root = Path(__file__).resolve().parents[1]
    if archive:
        import tempfile

        monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
        version = json.loads((root / "manifest.json").read_text(encoding="utf-8"))[
            "version"
        ]
        root = root / f"dist/snowluma_plus-{version}.mfp"
        if not root.is_file():
            from ..scripts.build_package import build

            build()
    manifest = await load_manifest(str(root))
    try:
        assert await pm.load_plugin_from_manifest(str(root), manifest)
        plugin = pm.get_plugin("snowluma_plus")
        assert plugin.runtime.running and ADAPTER in plugin.runtime.bound
        if archive:
            import sys

            module_file = Path(sys.modules[type(plugin.runtime).__module__].__file__)
            assert module_file.is_relative_to(tmp_path)
        assert (
            len(registry.get_by_plugin("snowluma_plus")) == len(manifest.include) + 1
        )  # 15业务组件及1配置组件
        assert len(plugin.runtime.tasks) == 3
        tool_cls = registry.get("snowluma_plus:tool:snowluma_group")
        tool = tool_cls(plugin)
        message = Message(
            sender_id=USER,
            stream_id="service-test",
            platform="qq",
            group_id=GROUP,
            self_id=ACCOUNT,
            adapter_signature=ADAPTER,
        )
        tool._bind_runtime_context(message=message)
        success, result = await tool.execute("overview")
        assert success and result["data"]["group_name"] == "离线群"
        assert calls[0]["command_name"] == "get_group_info"
        assert calls[0]["command_data"]["group_id"] == GROUP
    finally:
        if pm.get_plugin("snowluma_plus"):
            assert await pm.unload_plugin("snowluma_plus")
            await asyncio.sleep(0)
    assert not hasattr(env.adapter, "raw_event_context")


@pytest.mark.parametrize(
    "kind,content,expected",
    [
        ("face", "66", "face"),
        ("share", GROUP, "contact"),
        ("text", "正常文本", "text"),
        ("file", "", "file"),
    ],
)
async def test_send_uses_framework_adapter_and_history(
    env, monkeypatch, tmp_path, kind, content, expected
):
    """实际 MessageSender->Converter->Adapter，协议边界替身返回真实形状 ID。"""
    scope = Scope(ACCOUNT, ADAPTER, GROUP, OPERATOR)
    stream_id = ChatStream.generate_stream_id(platform="qq", group_id=GROUP)
    stream = await stream_api.get_or_create_stream(
        stream_id=stream_id, platform="qq", group_id=GROUP, chat_type="group"
    )
    env.runtime.scopes[stream_id] = scope
    env.config.access.allowed_actions = ["send_group_msg"]
    env.config.access.write_groups = [GROUP]
    sender = message_sender.MessageSender()
    sender.set_adapter_manager(
        SimpleNamespace(get_adapter=lambda signature: env.adapter)
    )
    monkeypatch.setattr(message_sender, "_global_message_sender", sender)
    backend = AsyncMock(
        return_value={"status": "ok", "retcode": 0, "data": {"message_id": 123456}}
    )
    env.adapter.send_onebot_api = backend
    env.adapter.send_handler.send_message_to_onebot = backend
    monkeypatch.setattr(adapter_api, "send_adapter_command", backend)
    if kind == "file":
        source = tmp_path / "测试文件.txt"
        source.write_text("离线文件发送验证", encoding="utf-8")
        env.config.files.allow_local_upload = True
        env.config.files.same_host = True
        env.config.files.roots = [str(tmp_path)]
        content = str(source)
    action = SendAction(stream, env.plugin)
    action._bind_runtime_context(
        message=Message(sender_id=OPERATOR, stream_id=stream_id, platform="qq")
    )
    success, result = await action.execute(kind, content)
    assert success, result
    assert backend.await_count == 1
    sent = backend.call_args.args[-1]["message"]
    assert len(sent) == 1 and sent[0]["type"] == expected
    assert stream.context.history_messages[-1].message_id == "123456"
    assert env.runtime.counters["send_confirmed"] == 1
    assert (await env.runtime.ledger.rows("SELECT state FROM operations"))[0][
        "state"
    ] == "success"


async def test_framework_interception_cannot_report_sent_success(env, monkeypatch):
    """核心将拦截当作成功返回时，Plus 还要求 AFTER_MESSAGE_SENT 事实。"""
    from src.app.plugin_system.api import send_api

    scope = Scope(ACCOUNT, ADAPTER, GROUP, OPERATOR)
    stream = SimpleNamespace(stream_id="intercepted")
    env.runtime.scopes[stream.stream_id] = scope
    env.config.access.allowed_actions = ["send_group_msg"]
    env.config.access.write_groups = [GROUP]
    monkeypatch.setattr(send_api, "send_text", AsyncMock(return_value=True))
    action = SendAction(stream, env.plugin)
    action._bind_runtime_context(
        message=Message(sender_id=OPERATOR, stream_id=stream.stream_id)
    )
    success, result = await action.execute("text", "不应宣称发出")
    assert not success and "未确认" in result
    assert (await env.runtime.ledger.rows("SELECT state FROM operations"))[0][
        "state"
    ] == "uncertain"


async def test_fetch_reaction_users_compatibility_native_payload(env, monkeypatch):
    """证明实际参数缺口的最小兼容分支，不伪造翻页。"""
    call = AsyncMock(
        return_value={
            "status": "ok",
            "retcode": 0,
            "data": {"emojiLikesList": [], "isLastPage": True, "cookie": ""},
        }
    )
    monkeypatch.setattr(adapter_api, "send_adapter_command", call)
    scope = Scope(ACCOUNT, ADAPTER, GROUP, USER)
    response = await env.runtime.gateway.call(
        scope,
        USER,
        "fetch_emoji_like",
        {"message_id": "777", "emoji_id": "66", "count": 10, "cursor": "20"},
    )
    assert response["data"]["isLastPage"]
    assert call.call_args.args[2] == {
        "message_id": "777",
        "emojiId": "66",
        "count": 10,
        "cookie": "20",
    }
