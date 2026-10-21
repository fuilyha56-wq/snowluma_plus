"""公共 Expand Service 调用、作用域授权和副作用审计的唯一执行层。"""

from __future__ import annotations

import asyncio
import inspect
import json
import re
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from src.app.plugin_system.api import adapter_api, service_api

from .config import SnowLumaConfig
from .models import Scope, json_text, redact
from .store import Ledger


class BusinessError(Exception):
    """可向模型说明的失败：区分策略、后端、权限、响应和超时。"""


class UncertainError(BusinessError):
    """通道中断/异步/畸形响应，不能确认副作用的最终结果。"""


def response_data(response: Any) -> Any:
    """只有明确成功的协议响应才视为成功，绝不把发出请求等同成功。"""
    if (
        not isinstance(response, dict)
        or response.get("status") not in {"ok", "failed"}
        or type(response.get("retcode")) is not int
    ):
        raise UncertainError(
            "协议未返回确定的同步结果（断线、异步或畸形响应）；写入可能已执行，请先核实"
        )
    if (
        not isinstance(response, dict)
        or response.get("status") != "ok"
        or response.get("retcode") != 0
    ):
        detail = (
            redact(response) if isinstance(response, dict) else type(response).__name__
        )
        raise BusinessError(
            f"协议调用失败或响应畸形：{json_text(detail)[:600]}；请检查连接、权限和运行版本"
        )
    return response.get("data")


class Gateway:
    """所有目录和专用工具共用的检查层，不能从通用入口绕过。"""

    def __init__(self, config: SnowLumaConfig, ledger: Ledger) -> None:
        """读取构建期快照，无跨插件源码导入。"""
        self.config, self.ledger = config, ledger
        catalog = json.loads(
            (Path(__file__).parent / "resources/catalog.json").read_text(
                encoding="utf-8"
            )
        )
        self.catalog = {item["action"]: item for item in catalog["actions"]}
        self.aliases = {
            alias: a["action"] for a in catalog["actions"] for alias in a["aliases"]
        }
        self.rate: dict[str, deque[float]] = defaultdict(deque)
        self.semaphore = asyncio.Semaphore(4)

    def canonical(self, action: str) -> str:
        """别名与主名采用相同授权策略。"""
        return self.aliases.get(action, action)

    def allowed_scope(self, scope: Scope, user: str = "") -> None:
        """每次执行都重新检查当前适配器名单。"""
        if scope.group and scope.group in self.config.access.blocked_groups:
            raise BusinessError("当前群在工具调用群黑名单中")
        if (user or scope.user) in self.config.access.blocked_users:
            raise BusinessError("当前用户在工具调用用户黑名单中")
        if scope.adapter not in self.config.plugin.adapters:
            raise BusinessError("适配器不在插件白名单")
        adapter = adapter_api.get_adapter(scope.adapter)
        if adapter is None or not callable(getattr(adapter, "allows_raw_event", None)):
            raise BusinessError("适配器不可用或插件兼容入口未通过审计；请检查加载诊断")
        if (
            not callable(getattr(adapter, "raw_event_context", None))
            or not adapter.raw_event_context().get("owned")
            or adapter.raw_event_context().get("account") != scope.account
        ):
            raise BusinessError("会话账号与适配器当前登录账号不一致，禁止跨账号执行")
        raw = {
            "post_type": "notice",
            "self_id": scope.account,
            "user_id": user or scope.user or scope.account,
        }
        if scope.group:
            raw["group_id"] = scope.group
        if not adapter.allows_raw_event(raw):
            raise BusinessError("当前群/私聊/用户已被适配器名单禁用")

    def authorize(
        self,
        scope: Scope,
        operator: str,
        action: str,
        write: bool,
        params: dict[str, Any],
        *,
        trusted: bool = False,
        basic_interaction: bool = False,
    ) -> None:
        """检查执行者、范围、风险、参数；trusted 仅供插件绑定的后台任务。"""
        self.allowed_scope(scope, operator if not trusted else "")
        if not operator and not trusted:
            raise BusinessError("缺少框架绑定的真实触发者，不能由模型自行填写操作者")
        entry = self.catalog.get(action)
        if self.canonical(action) in {
            self.canonical(item) for item in self.config.access.blocked_actions
        }:
            raise BusinessError("此接口在工具动作黑名单中")
        if entry is None:
            raise BusinessError("接口不在已审计目录；先使用 snowluma_api_catalog 查询")
        if entry["risk"] in {"blocked", "stream_unavailable", "approval_only"}:
            raise BusinessError(
                f"接口受限：{entry['risk']}；审批必须使用 request_id，流式需独立多帧通道"
            )
        if "flag" in entry.get("arguments", []):
            raise BusinessError(
                "含平台 flag 的接口只允许服务端绑定待办处理，通用入口禁止调用"
            )
        if (
            not entry.get("backend_compatible", entry["expand_compatible"])
            or not entry["source_declared"]
        ):
            raise BusinessError(
                "审计源码未确认 SnowLuma 注册此接口；不能视为支持，见覆盖矩阵"
            )
        if entry["risk"] != "read" and not write:
            raise BusinessError("此接口有副作用，请使用授权 Action")
        basic = (
            basic_interaction
            and self.config.access.allow_basic_interactions
            and action
            in {
                "set_msg_emoji_like",
                "group_poke",
                "friend_poke",
                "send_poke",
                "send_like",
                "delete_msg",
                "send_group_msg",
                "send_private_msg",
                "set_group_sign",
            }
        )
        if (
            basic
            and action in {"group_poke", "friend_poke", "send_poke", "send_like"}
            and str(params.get("user_id")) != operator
        ):
            raise BusinessError(
                "普通互动只允许戳/点赞当前真实触发者；指定其他人需要独立动作授权"
            )
        if (
            basic
            and action == "send_like"
            and (
                type(params.get("times", 1)) is not int
                or not 1 <= params.get("times", 1) <= 10
            )
        ):
            raise BusinessError(
                "普通互动的主页点赞次数必须为1至10；更大次数需独立动作授权"
            )
        if write and not basic:
            if self.canonical(action) not in {
                self.canonical(a) for a in self.config.access.allowed_actions
            }:
                raise BusinessError("此动作未列入 access.allowed_actions")
            if not trusted and operator not in self.config.access.operators:
                raise BusinessError("触发者未获动作授权")
            if scope.group and scope.group not in self.config.access.write_groups:
                raise BusinessError("目标群未列入 access.write_groups")
        group = str(params.get("group_id") or "")
        if group and group != scope.group:
            raise BusinessError("参数群与已解析会话不一致")
        if not scope.group and "group_id" in entry["required"]:
            raise BusinessError("此接口需要明确群会话")
        if (
            (not scope.group or "group_id" not in entry["arguments"])
            and operator not in self.config.access.operators
            and not trusted
        ):
            for key in ("user_id", "uin", "qq"):
                if params.get(key) is not None and str(params[key]) != operator:
                    raise BusinessError("跨用户查询需要配置的操作者权限")
        if (
            action
            in {
                "get_group_list",
                "get_friend_list",
                "get_group_system_msg",
                "get_doubt_friends_add_request",
                "get_login_info",
                "get_online_clients",
            }
            and not trusted
            and operator not in self.config.access.operators
        ):
            raise BusinessError("账号级目录/申请/客户端资料需要操作者权限")
        unknown = set(params) - set(entry["arguments"])
        missing = set(entry["required"]) - set(params)
        if unknown or missing:
            raise BusinessError(
                f"参数不符合公共 Service 契约：多余={sorted(unknown)} 缺少={sorted(missing)}"
            )
        for key in ("group_id", "user_id", "target_id", "uin", "qq"):
            if key in params and (
                isinstance(params[key], bool) or not str(params[key]).isdecimal()
            ):
                raise BusinessError(f"{key} 必须是完整数字标识符，不能传对象或猜测昵称")
        if action == "set_group_ban" and (
            isinstance(params.get("duration", 0), bool)
            or not isinstance(params.get("duration", 0), int)
            or not 0 <= params.get("duration", 0) <= 2592000
        ):
            raise BusinessError("禁言 duration 必须是 0..2592000 的整数秒")
        self._file_values(params)
        queue = self.rate[scope.key]
        now = time.monotonic()
        while queue and queue[0] < now - 60:
            queue.popleft()
        if len(queue) >= self.config.access.calls_per_minute:
            raise BusinessError("会话调用限流，请稍后重试")
        queue.append(now)

    def _file_values(self, params: Any) -> None:
        """递归检查嵌套媒体；通用入口默认不允许可隐藏路径的 JSON/消息包。"""
        if isinstance(params, dict):
            for key, value in params.items():
                if (
                    key
                    in {
                        "file",
                        "file_path",
                        "image",
                        "image_path",
                        "path",
                        "folder",
                        "thumb",
                        "video",
                        "audio",
                        "record",
                        "preview_url",
                        "image_url",
                    }
                    and value
                ):
                    params[key] = self.file_source(str(value))
                if (
                    key
                    in {
                        "message",
                        "messages",
                        "nodes",
                        "json",
                        "xml",
                        "data",
                        "hex",
                        "cmd",
                    }
                    and value
                ):
                    raise BusinessError(
                        "消息/转发/Ark/原始数据必须走专用发送链路，通用入口不接收嵌套载荷"
                    )
                if isinstance(value, (dict, list)):
                    self._file_values(value)
        elif isinstance(params, list):
            for value in params:
                self._file_values(value)

    def file_source(self, value: str) -> str:
        """规范化同主机文件，拒绝 UNC、越界、链接、base64 和未经授权 URL。"""
        policy = self.config.files
        if value.startswith(("http://", "https://")):
            parsed = urlsplit(value)
            if (
                parsed.scheme != "https"
                or parsed.hostname not in policy.url_hosts
                or parsed.username
                or parsed.password
                or parsed.port not in (None, 443)
            ):
                raise BusinessError("网络媒体只允许配置白名单内无凭证的 HTTPS 来源")
            raise BusinessError(
                "URL 大小与重定向尚未核实；请使用受控同主机文件上传，禁止远端任意取址"
            )
        if value.lower().startswith(("base64", "data:", "\\\\", "//")):
            raise BusinessError("不允许 base64、网络共享或不透明文件来源")
        if not policy.allow_local_upload or not policy.same_host:
            raise BusinessError(
                "本地外发关闭；Neo-MoFox 路径检查不能限制另一主机的协议端读取"
            )
        parsed = urlsplit(value)
        candidate = (
            unquote(parsed.path)
            if parsed.scheme == "file" and not parsed.netloc
            else value
        )
        if parsed.scheme == "file" and parsed.netloc:
            raise BusinessError("file URL 不允许远端主机")
        if len(candidate) > 2 and candidate[0] == "/" and candidate[2] == ":":
            candidate = candidate[1:]
        path = Path(candidate)
        if not path.is_absolute():
            raise BusinessError("上传路径必须为绝对路径")
        resolved = path.resolve(strict=True)
        roots = [Path(root).resolve(strict=True) for root in policy.roots]
        if not any(resolved.is_relative_to(root) for root in roots):
            raise BusinessError("文件越过允许根目录")
        if any(
            parent.is_symlink()
            or (
                getattr(parent.stat(follow_symlinks=False), "st_file_attributes", 0)
                & 0x400
            )
            for parent in [path, *path.parents]
        ):
            raise BusinessError("不允许符号链接或共享卷路径")
        if (
            not resolved.is_file()
            or resolved.suffix.lower() not in policy.extensions
            or resolved.stat().st_size > policy.max_mb * 1048576
        ):
            raise BusinessError("文件类型、大小或实际文件不可用")
        return str(resolved)

    async def raw_call(
        self, scope: Scope, action: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """将通道异常变为可解释且不会误触发副作用重试的业务状态。"""
        try:
            return await self._dispatch(scope, action, params)
        except (asyncio.TimeoutError, asyncio.CancelledError, BusinessError):
            raise
        except Exception as exc:
            raise UncertainError(
                f"协议通道或公共Service异常：{type(exc).__name__}；请检查连接和版本，写入结果需核实"
            ) from exc

    async def _dispatch(
        self, scope: Scope, action: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """优先公共 Service；其固定适配器不匹配时走公开命令 API。"""
        entry = self.catalog[action]
        async with self.semaphore:
            if "service" not in entry:
                return await adapter_api.send_adapter_command(
                    scope.adapter, action, params, timeout=30
                )
            if action == "fetch_emoji_like":
                native = {
                    "message_id": params["message_id"],
                    "emojiId": str(params["emoji_id"]),
                    "count": params.get("count", 10),
                    "cookie": params.get("cursor", ""),
                }
                return await adapter_api.send_adapter_command(
                    scope.adapter, action, native, timeout=30
                )
            if action in {"upload_group_file", "upload_private_file"}:
                native = {
                    ("group_id" if scope.group else "user_id"): scope.group
                    or scope.user,
                    "file": params["file_path"],
                    "name": params.get("name", ""),
                }
                return await adapter_api.send_adapter_command(
                    scope.adapter, action, native, timeout=30
                )
            if action == "upload_image_to_qun_album":
                return await adapter_api.send_adapter_command(
                    scope.adapter, action, params, timeout=30
                )
            if scope.adapter == "onebot_adapter:adapter:onebot_adapter":
                service = service_api.get_service(entry["service"])
                if service is None:
                    raise BusinessError(
                        f"缺少公共 Service {entry['service']}，请启用 Expand"
                    )
                method = getattr(service, entry["method"], None)
                if callable(method):
                    try:
                        inspect.signature(method).bind(**params)
                    except TypeError as exc:
                        raise BusinessError(
                            "Expand公共Service参数签名已变化，请重新生成目录"
                        ) from exc
                if method is None or not inspect.iscoroutinefunction(method):
                    raise BusinessError(
                        "Expand Service 版本与目录不一致，请重新生成目录"
                    )
                return await asyncio.wait_for(method(**params), timeout=35)
            return await adapter_api.send_adapter_command(
                scope.adapter, action, params, timeout=30
            )

    async def bot_role(self, scope: Scope) -> dict[str, Any]:
        """管理前即时查询 Bot 角色，缓存不能替代执行检查。"""
        response = await self.raw_call(
            scope,
            "get_group_member_info",
            {"group_id": scope.group, "user_id": scope.account, "no_cache": True},
        )
        data = response_data(response)
        if not isinstance(data, dict):
            raise BusinessError("群身份响应缺少成员对象")
        return data

    async def call(
        self,
        scope: Scope,
        operator: str,
        action: str,
        params: dict[str, Any],
        *,
        write: bool = False,
        trusted: bool = False,
        operation_id: str = "",
        basic_interaction: bool = False,
    ) -> dict[str, Any]:
        """统一调用及副作用结果审计；网络超时不会自动重新发出写入。"""
        action = self.canonical(action)
        params = dict(params)
        if action in {
            "send_group_msg",
            "send_private_msg",
            "send_msg",
            "send_group_forward_msg",
            "send_private_forward_msg",
            "send_forward_msg",
            "forward_group_single_msg",
            "forward_friend_single_msg",
            "upload_forward_msg",
            "send_tuwen_ark",
            "send_group_ai_record",
            "send_flash_msg",
        }:
            raise BusinessError(
                "此消息操作必须通过 snowluma_send 及框架发送链路；原始Expand Service只供可信插件调用"
            )
        self.authorize(
            scope,
            operator,
            action,
            write,
            params,
            trusted=trusted,
            basic_interaction=basic_interaction,
        )
        needs_role = action.startswith("set_group_") or action in {
            "_send_group_notice",
            "_del_group_notice",
            "delete_group_file",
            "delete_group_folder",
            "set_essence_msg",
            "delete_essence_msg",
        }
        if action == "delete_msg" and (scope.group or basic_interaction):
            detail = response_data(
                await self.raw_call(
                    scope, "get_msg", {"message_id": params["message_id"]}
                )
            )
            if not isinstance(detail, dict) or (
                scope.group and str(detail.get("group_id")) != scope.group
            ):
                raise BusinessError("撤回消息的实时群归属无法确认")
            author = str(
                (detail.get("sender") or {}).get("user_id")
                or detail.get("user_id")
                or ""
            )
            if basic_interaction and author != scope.account:
                raise BusinessError(
                    "普通互动仅可撤回Bot自己发送的消息；撤回成员消息需要独立管理授权"
                )
            needs_role = author != scope.account
        own_card = (
            action == "set_group_card" and str(params.get("user_id")) == scope.account
        )
        if (
            write
            and scope.group
            and needs_role
            and action != "set_group_sign"
            and not own_card
        ):
            bot = await self.bot_role(scope)
            role = bot.get("role")
            if role not in {"admin", "owner"}:
                raise BusinessError("Bot 当前不是群主/管理员，平台管理权限不足")
            if (
                action in {"set_group_admin", "set_group_special_title"}
                and role != "owner"
            ):
                raise BusinessError("该管理操作需要群主身份")
            if params.get("user_id") and action in {"set_group_kick", "set_group_ban"}:
                target = response_data(
                    await self.raw_call(
                        scope,
                        "get_group_member_info",
                        {
                            "group_id": scope.group,
                            "user_id": params["user_id"],
                            "no_cache": True,
                        },
                    )
                )
                if (
                    not isinstance(target, dict)
                    or target.get("role") == "owner"
                    or (target.get("role") == "admin" and role != "owner")
                    or str(params["user_id"]) == scope.account
                ):
                    raise BusinessError("目标角色不能由 Bot 管理或为 Bot 自身")
        op = operation_id or uuid.uuid4().hex
        if write and not await self.ledger.claim(
            op, scope, action, operator, "local_action"
        ):
            raise BusinessError("该操作已有持久记录；请查询结果，不要重复提交")
        try:
            response = await self.raw_call(scope, action, params)
            response_data(response)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            if write:
                await self.ledger.operation_result(
                    op, "uncertain", "超时/取消，可能已在平台执行，禁止自动重试"
                )
            raise
        except Exception as exc:
            if write:
                await self.ledger.operation_result(
                    op,
                    "failed"
                    if isinstance(exc, BusinessError)
                    and not isinstance(exc, UncertainError)
                    else "uncertain",
                    type(exc).__name__,
                )
            raise
        if write:
            await self.ledger.operation_result(op, "success", response)
        return response

    def search(self, query: str, offset: int = 0, limit: int = 10) -> dict[str, Any]:
        """分页发现低频能力，只返回当前页，不更改其他插件工具。"""
        words = [
            part for part in re.split(r"[\s,，/;；]+", query.lower().strip()) if part
        ]
        synonyms = {
            "reaction": "emoji_like",
            "表情回应": "emoji_like",
            "贴表情": "emoji_like",
            "戳一戳": "poke",
            "撤回": "delete_msg",
        }
        terms = set(words) | {synonyms[word] for word in words if word in synonyms}
        ranked = [
            (sum(term in json_text(entry).lower() for term in terms), entry)
            for entry in self.catalog.values()
        ]
        found = [
            entry
            for score, entry in sorted(ranked, key=lambda pair: -pair[0])
            if not terms or score
        ]

        return {
            "total": len(found),
            "offset": offset,
            "items": found[offset : offset + limit],
            "next_offset": offset + limit if offset + limit < len(found) else None,
            "compatibility": "本地源码证据；运行实例仍可能拒绝，协议响应才是调用结果",
        }
