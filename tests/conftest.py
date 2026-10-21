"""隔离 SQLite/事件总线/适配器，不连接真实 QQ 后端。"""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any

import pytest

from plugins.onebot_adapter.config import OneBotAdapterConfig
from plugins.onebot_adapter.plugin import OneBotAdapter
from src.app.plugin_system.api import adapter_api, config_api, event_api
from src.core.managers import stream_manager
from src.core.managers.event_manager import EventManager
from src.core.models.sql_alchemy import Base
from src.core.transport.message_receive.receiver import MessageReceiver
from src.kernel.db.core.cache import reset_db_cache
from src.kernel.db.core.engine import configure_engine, get_engine, reset_engine_state
from src.kernel.db.core.session import reset_session_factory
from src.kernel.event.core import EventBus

from ..config import SnowLumaConfig
from ..handlers import SnowLumaEvents
from ..runtime import Runtime

ADAPTER = "onebot_adapter:adapter:onebot_adapter"
ACCOUNT, GROUP, USER, OPERATOR = "90001", "20001", "10001", "10002"


@pytest.fixture
async def env(tmp_path: Any, monkeypatch: Any) -> Any:
    """真实 receiver、事件管理器、SQLite 和 StreamManager 的离线环境。"""
    await reset_session_factory()
    await reset_engine_state()
    reset_db_cache()
    configure_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'core.db').as_posix()}",
        apply_optimizations=False,
    )
    engine = await get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sm = stream_manager.StreamManager()
    monkeypatch.setattr(stream_manager, "_global_stream_manager", sm)
    manager = EventManager()
    bus = EventBus()
    manager._event_bus = bus
    monkeypatch.setattr(event_api, "get_event_manager", lambda: manager)
    import src.core.managers.event_manager as core_event_module

    monkeypatch.setattr(core_event_module, "get_event_manager", lambda: manager)
    import src.kernel.event as kernel_event

    monkeypatch.setattr(kernel_event, "get_event_bus", lambda: bus)
    receiver = MessageReceiver()
    receiver._event_manager = manager

    class Sink:
        """按真实 CoreSink 契约送往核心接收入口。"""

        async def send(self, envelope: dict[str, Any]) -> None:
            """记录完整链路中的实际消费。"""
            await receiver.receive_envelope(envelope, ADAPTER)

    adapter_config = OneBotAdapterConfig(
        bot={"qq_id": ACCOUNT, "qq_nickname": "离线测试Bot"}
    )
    adapter_config.bot.qq_id = ACCOUNT
    adapter_config.bot.qq_nickname = "离线测试Bot"
    adapter = OneBotAdapter(Sink(), SimpleNamespace(config=adapter_config))
    monkeypatch.setattr(
        config_api,
        "get_config",
        lambda name: adapter_config if name == "onebot_adapter" else None,
    )
    adapters = {ADAPTER: adapter}
    adapter_manager = SimpleNamespace(
        get_all_adapters=lambda: dict(adapters),
        get_adapter=lambda signature: adapters.get(signature),
        get_bot_info_by_platform=lambda platform: adapter.get_bot_info(),
    )
    monkeypatch.setattr(adapter_api, "_get_adapter_manager", lambda: adapter_manager)
    import src.core.managers.adapter_manager as core_adapter_module

    monkeypatch.setattr(
        core_adapter_module, "get_adapter_manager", lambda: adapter_manager
    )
    config = SnowLumaConfig()
    config.access.operators = [OPERATOR]
    config.access.management_users = [OPERATOR]
    config.access.approval_groups = [GROUP]
    runtime = Runtime(config, tmp_path / "plus.db")
    runtime.running = True
    await runtime.ledger.open()
    await runtime.bind()
    plugin = SimpleNamespace(config=config, runtime=runtime)
    handler = SnowLumaEvents(plugin)
    await manager.register_handler(
        "snowluma_plus:event_handler:snowluma_events", handler
    )
    test_env = SimpleNamespace(
        runtime=runtime,
        config=config,
        plugin=plugin,
        adapter=adapter,
        adapters=adapters,
        adapter_config=adapter_config,
        receiver=receiver,
        manager=manager,
        bus=bus,
        streams=sm,
        handler=handler,
    )
    try:
        yield test_env
    finally:
        await runtime.stop()
        await reset_session_factory()
        await reset_engine_state()
        reset_db_cache()


def raw_notice(kind: str, **fields: Any) -> dict[str, Any]:
    """字段名来自 SnowLuma to-notice.ts；账号/群/成员均为合成值。"""
    return {
        "post_type": "notice",
        "notice_type": kind,
        "self_id": ACCOUNT,
        "group_id": GROUP,
        "user_id": USER,
        "time": time.time(),
        **fields,
    }


async def drain(env: Any) -> None:
    """重放所有可投递账本条目，不绕过适配器的接收入口。"""
    while rows := await env.runtime.ledger.pending():
        for row in rows:
            await env.runtime.deliver(row)
