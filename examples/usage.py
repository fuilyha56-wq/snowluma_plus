"""在已加载插件的宿主中只读查询 SnowLuma Plus；不自行建立协议连接。"""

from typing import Any

from src.app.plugin_system.api import service_api


async def inspect_snowluma_plus() -> dict[str, Any]:
    """读取公共Service诊断；可供可信插件的管理命令调用。"""
    service = service_api.get_service("snowluma_plus:service:snowluma_service")
    if service is None:
        return {"running": False, "reason": "SnowLuma Plus Service未注册"}
    return await service.diagnostics()
