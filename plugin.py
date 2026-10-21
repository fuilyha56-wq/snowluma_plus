"""SnowLuma Plus 注册入口与失败回滚。"""

from __future__ import annotations

from src.app.plugin_system.base import BasePlugin, register_plugin

from .components import COMPONENTS
from .config import SnowLumaConfig
from .handlers import SnowLumaEvents
from .runtime import Runtime


@register_plugin
class SnowLumaPlus(BasePlugin):
    """业务增强层，保留 Expand 原始 Service 的协议响应契约。"""

    plugin_name = "snowluma_plus"
    configs: list[type] = [SnowLumaConfig]

    def get_components(self) -> list[type]:
        """组件注册严格跟随插件开关，manifest 是对应静态清单。"""
        if self.config.plugin.enabled:
            self.config.validate_runtime()
        return [SnowLumaEvents, *COMPONENTS] if self.config.plugin.enabled else []

    async def on_plugin_loaded(self) -> None:
        """先验证配置再开启任务；异常时关闭已获取的资源。"""
        self.runtime: Runtime | None = None
        if self.config.plugin.enabled:
            self.runtime = Runtime(self.config)
            try:
                await self.runtime.start()
            except BaseException:
                await self.runtime.stop()
                self.runtime = None
                raise

    async def on_plugin_unloaded(self) -> None:
        """卸载恢复原始适配器链路并清理本插件资源。"""
        runtime = getattr(self, "runtime", None)
        if runtime is not None:
            await runtime.stop()
            self.runtime = None
