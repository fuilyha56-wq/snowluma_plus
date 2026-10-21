"""中文业务工具和 Action；所有执行复用同一作用域和授权层。"""

from __future__ import annotations

import asyncio
import base64
import json
import time
import uuid
from pathlib import Path
from typing import Annotated, Any

from src.app.plugin_system.api import send_api
from src.app.plugin_system.base import BaseService, BaseTool
from src.core.models.message import Message, MessageType

from .compat import BoundAction
from .gateway import BusinessError, response_data
from .models import OUTGOING_OPERATION, Scope, identifier, json_text, normalize, redact


async def context(component: Any, group_id: str = "") -> tuple[Any, Scope, str, str]:
    """只信任框架绑定的触发消息；不由模型输入执行人、账号或 flag。"""
    runtime = getattr(component.plugin, "runtime", None)
    if runtime is None or not runtime.running:
        raise BusinessError("SnowLuma Plus 未运行，请查看加载诊断")
    message = getattr(component, "trigger_message", None)
    if message is None or not message.sender_id or message.extra.get("system_event"):
        raise BusinessError("当前调用没有真实用户触发消息；自动事件不能冒用操作权限")
    operator = identifier(message.sender_id)
    stream_id = message.stream_id
    scope = runtime.scopes.get(stream_id)
    if scope is None:
        extra = message.extra
        account, adapter = (
            identifier(extra.get("self_id")),
            str(extra.get("adapter_signature") or ""),
        )
        if not account or not adapter:
            raise BusinessError("当前框架消息缺少账号/适配器来源，不能猜测作用域")
        scope = Scope(account, adapter, identifier(extra.get("group_id")), operator)
    if operator == scope.account:
        raise BusinessError("Bot 自发回声不能触发业务工具")
    if group_id and group_id != scope.group:
        if operator not in runtime.config.access.operators:
            raise BusinessError("跨群查询/操作需要明确操作者授权")
        scope = Scope(scope.account, scope.adapter, group_id, operator)
    runtime.gateway.allowed_scope(scope, operator)
    return runtime, scope, operator, stream_id


def output(runtime: Any, value: Any) -> dict[str, Any]:
    """有效 JSON 预算；超限保留可继续分页的提示，不截断成畸形 JSON。"""
    value = redact(value)
    if len(json_text(value)) <= runtime.config.access.result_chars:
        return value if isinstance(value, dict) else {"data": value}
    return {
        "truncated": True,
        "preview": json_text(value)[: runtime.config.access.result_chars - 200],
        "next": "结果超过字符预算，请缩小检索或分页，不据此判断列表完整",
    }


def parse_params(text: str) -> dict[str, Any]:
    """有预算的工具JSON参数，拒绝过深或过大的对象。"""
    if len(text) > 16000:
        raise BusinessError("参数JSON超过16000字符，请分批或缩小内容")
    try:
        value = json.loads(text)
    except (ValueError, RecursionError) as exc:
        raise BusinessError("params_json不是有效JSON对象") from exc
    if not isinstance(value, dict):
        raise BusinessError("params_json必须为JSON对象")
    pending = [(value, 0)]
    total = 0
    while pending:
        item, depth = pending.pop()
        total += 1
        if depth > 8 or total > 300:
            raise BusinessError("参数JSON过深或元素过多，请拆分调用")
        if isinstance(item, dict):
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)
    return value


def page(rows: list[Any], offset: int, limit: int) -> dict[str, Any]:
    """统一分页约束与总数。"""
    if offset < 0 or not 1 <= limit <= 50:
        raise BusinessError("offset 必须非负，limit 必须为 1..50")
    return {
        "total": len(rows),
        "offset": offset,
        "items": rows[offset : offset + limit],
        "next_offset": offset + limit if offset + limit < len(rows) else None,
    }


async def platform_message(runtime: Any, scope: Scope, value: str) -> str:
    """显式区分框架 ID 和平台 ID，并核实消息属于当前会话。"""
    if value.startswith("framework:"):
        rows = await runtime.ledger.rows(
            "SELECT platform_id FROM mappings WHERE scope=? AND framework_id=?",
            (scope.key, value[len("framework:") :]),
        )
        if not rows:
            raise BusinessError("未找到当前会话的框架到平台消息 ID 映射")
        message_id = rows[0]["platform_id"]
    elif value.startswith("platform:"):
        message_id = value[len("platform:") :]
    else:
        raise BusinessError("消息 ID 必须写 platform:真实平台ID 或 framework:框架ID")
    if not message_id:
        raise BusinessError("消息 ID 为空")
    detail = await runtime.business.read(scope, "get_msg", {"message_id": message_id})
    if not isinstance(detail, dict):
        raise BusinessError("原消息不可查询，无法核实操作范围；事件仍保存在账本")
    if scope.group:
        if identifier(detail.get("group_id")) != scope.group:
            raise BusinessError("消息归属群不一致或协议未提供群字段，拒绝跨群访问")
    else:
        sender = identifier(
            (detail.get("sender") or {}).get("user_id") or detail.get("user_id")
        )
        proof = await runtime.ledger.rows(
            "SELECT platform_id FROM mappings WHERE scope=? AND platform_id=? LIMIT 1",
            (scope.key, message_id),
        )
        if detail.get("group_id") or (sender != scope.user and not proof):
            raise BusinessError(
                "私聊消息归属无法确认；Bot发言须有当前会话的持久映射，不能仅凭sender=Bot跨私聊读取"
            )
    return message_id


async def send_segment(
    scope: Scope,
    stream_id: str,
    kind: str,
    data: dict[str, Any] | list[dict[str, Any]],
    label: str,
) -> bool:
    """框架正常发送结构化媒体；展示文本保留历史，不额外发到 QQ。"""
    message = Message(
        message_id=f"snowluma-send:{uuid.uuid4().hex}",
        platform=scope.platform,
        chat_type="group" if scope.group else "private",
        stream_id=stream_id,
        sender_id=scope.account,
        content=label,
        processed_plain_text=label,
        message_type=MessageType.UNKNOWN,
        target_group_id=scope.group,
        target_user_id=scope.user,
        media=[
            {"type": kind, "data": item}
            for item in (data if isinstance(data, list) else [data])
        ],
        snowluma_display_only=True,
        self_id=scope.account,
    )
    return await send_api.send_message(message, adapter_signature=scope.adapter)


def read_bounded_media(path: str, max_bytes: int) -> str:
    """读取已规范化且授权的本机媒体，读取阶段仍限制大小。"""
    with Path(path).open("rb") as source:
        payload = source.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise BusinessError("媒体在读取时超过大小限制")
    return base64.b64encode(payload).decode("ascii")


class GroupQuery(BaseTool):
    """当前群资料、成员身份和滚动统计。"""

    name = "snowluma_group"
    description = "查本群概况、成员QQ/昵称/名片/头衔/角色、Bot身份与荣誉、最近24小时可见消息活跃排名。可分页搜索，重名返回候选。"
    associated_platforms = ["qq"]

    async def execute(
        self,
        view: Annotated[str, "overview/member/identity/honor/active"],
        query: Annotated[str, "成员关键词、我、QQ号或荣誉类型"] = "",
        group_id: Annotated[str, "默认当前群；跨群需要授权"] = "",
        offset: int = 0,
        limit: int = 10,
        refresh: bool = False,
    ) -> tuple[bool, str | dict]:
        """获取群资料；refresh 主动刷新，过期资料会标明 stale。"""
        try:
            runtime, scope, operator, stream_id = await context(self, group_id)
            if not scope.group:
                raise BusinessError("请在群内调用，或由授权操作者指定 group_id")
            if view == "member":
                snapshot = await runtime.business.members(scope, refresh)
                if query in {"我", "自己", "me"}:
                    query = operator
                rows = [
                    m
                    for m in snapshot["data"]
                    if not query
                    or any(
                        query.lower() in str(m.get(k) or "").lower()
                        for k in (
                            "user_id",
                            "nickname",
                            "card",
                            "title",
                            "special_title",
                            "role",
                        )
                    )
                ]
                result = {
                    **page(rows, offset, limit),
                    **{k: v for k, v in snapshot.items() if k != "data"},
                }
            elif view == "active":
                page([], offset, limit)
                backfill = (
                    await runtime.backfill(scope, stream_id)
                    if refresh and runtime.scopes.get(stream_id) == scope
                    else {"complete": False, "note": "仅Bot可见消息；未声明全量覆盖"}
                )
                result = {
                    "items": await runtime.ledger.ranking(scope, limit, offset),
                    "window_hours": 24,
                    "source": "visible_messages",
                    "coverage": backfill,
                }
            elif view == "identity":
                result = {
                    "identity": await runtime.business.read(
                        scope,
                        "get_group_member_info",
                        {
                            "group_id": scope.group,
                            "user_id": scope.account,
                            "no_cache": refresh,
                        },
                    ),
                    "checked_at": time.time(),
                    "note": "平台身份与触发者动作授权分别检查",
                }
            elif view == "honor":
                honor_types = {
                    "all",
                    "talkative",
                    "performer",
                    "legend",
                    "strong_newbie",
                    "emotion",
                }
                data = await runtime.business.read(
                    scope,
                    "get_group_honor_info",
                    {
                        "group_id": scope.group,
                        "type": query if query in honor_types else "all",
                    },
                )
                if query and query not in honor_types and isinstance(data, dict):
                    data = {
                        key: [
                            row
                            for row in value
                            if query.lower() in json_text(row).lower()
                        ]
                        if isinstance(value, list)
                        else value
                        if not isinstance(value, dict)
                        or query.lower() in json_text(value).lower()
                        else {}
                        for key, value in data.items()
                    }
                result = {"data": data, "checked_at": time.time()}
            elif view == "overview":
                result = {
                    "data": await runtime.business.read(
                        scope,
                        "get_group_info",
                        {"group_id": scope.group, "no_cache": refresh},
                    ),
                    "checked_at": time.time(),
                }
            else:
                raise BusinessError("view 仅支持 overview/member/identity/honor/active")
            if view in {"identity", "overview", "honor"} and not isinstance(
                result.get("identity", result.get("data")), dict
            ):
                raise BusinessError(
                    "平台资料响应不是对象，未将畸形响应当作成功或空资料"
                )
            if view == "identity":
                role = result["identity"].get("role")
                platform_actions = ["set_group_card"]
                if role in {"admin", "owner"}:
                    platform_actions += [
                        "set_group_ban",
                        "set_group_kick",
                        "set_group_whole_ban",
                        "set_group_name",
                        "_send_group_notice",
                        "_del_group_notice",
                        "set_essence_msg",
                        "delete_essence_msg",
                    ]
                if role == "owner":
                    platform_actions += ["set_group_admin", "set_group_special_title"]
                result.update(
                    platform_role_candidates=platform_actions,
                    configured_actions=runtime.config.access.allowed_actions,
                    operator_authorized=operator in runtime.config.access.operators,
                    group_write_authorized=scope.group
                    in runtime.config.access.write_groups,
                )
            if view == "active":
                cached = await runtime.ledger.snapshot(scope, "members")
                members = (
                    {str(row.get("user_id")): row for row in cached["data"]}
                    if cached
                    else {}
                )
                result["items"] = [
                    {
                        **row,
                        "profile": {
                            key: members.get(row["user_id"], {}).get(key)
                            for key in ("nickname", "card", "title", "role")
                        },
                    }
                    for row in result["items"]
                ]
                result["collection_enabled"] = runtime.config.members.enabled
            return True, output(runtime, result)
        except (BusinessError, ValueError, OSError) as exc:
            return False, str(exc)
        except asyncio.TimeoutError:
            return False, "资料查询超时；可稍后重试，未将失败当成空列表"


class NoticeQuery(BaseTool):
    """公告列表、详情与本地搜索。"""

    name = "snowluma_notices"
    description = "看最新群公告、按公告真实ID查详情或搜索内容；显示发布者、时间及媒体原字段，失败不会误报为空。"
    associated_platforms = ["qq"]

    async def execute(
        self,
        query: str = "",
        notice_id: str = "",
        group_id: str = "",
        rebaseline: bool = False,
        offset: int = 0,
        limit: int = 10,
    ) -> tuple[bool, str | dict]:
        """查询当前群公告；notice_id 是平台公告 ID，不能使用消息 ID。"""
        try:
            runtime, scope, operator, _ = await context(self, group_id)
            if rebaseline and operator not in runtime.config.access.operators:
                raise BusinessError("重建公告基线需要操作者权限")
            result = await runtime.business.notices(scope, emit=True, reset=rebaseline)
            rows = [
                r
                for r in result["data"]
                if (not query or query.lower() in json_text(r).lower())
                and (
                    not notice_id
                    or notice_id
                    in {str(r.get(k) or "") for k in ("id", "notice_id", "fid")}
                )
            ]
            return True, output(
                runtime,
                {
                    **{k: v for k, v in result.items() if k != "data"},
                    **page(rows, offset, limit),
                },
            )
        except (BusinessError, ValueError) as exc:
            return False, str(exc)
        except asyncio.TimeoutError:
            return False, "公告查询超时，保留上次完整基线"


class MessageQuery(BaseTool):
    """历史、精华和消息表情回应。"""

    name = "snowluma_messages"
    description = "查询本会话历史/Bot最近消息/精华/消息/表情回应用户。view=history/bot_recent/essence/detail/reactions/reaction_users；ID用platform:或framework:前缀。"
    associated_platforms = ["qq"]

    async def execute(
        self,
        view: str,
        message_id: str = "",
        query: str = "",
        offset: int = 0,
        limit: int = 10,
        emoji_id: str = "",
        cursor: str = "",
    ) -> tuple[bool, str | dict]:
        """查询真实协议内容；不可访问或已撤回时返回失败原因。"""
        try:
            runtime, scope, _, _ = await context(self)
            if view == "reaction_users":
                page([], offset, limit)
                if not emoji_id:
                    raise BusinessError(
                        "reaction_users 需要真实 emoji_id，先查询 reactions"
                    )
                mid = await platform_message(runtime, scope, message_id)
                native_cursor = ""
                if cursor:
                    saved = await runtime.ledger.rows(
                        "SELECT value FROM meta WHERE key=?",
                        (f"reaction-cursor:{cursor}",),
                    )
                    bound = json.loads(saved[0]["value"]) if saved else {}
                    if (
                        bound.get("scope") != scope.key
                        or bound.get("message_id") != mid
                        or bound.get("emoji_id") != emoji_id
                        or bound.get("expires", 0) < time.time()
                    ):
                        raise BusinessError(
                            "分页游标不存在、已过期或属于其他会话/消息/表情"
                        )
                    native_cursor = bound["cookie"]
                data = await runtime.business.read(
                    scope,
                    "fetch_emoji_like",
                    {
                        "message_id": mid,
                        "emoji_id": emoji_id,
                        "count": limit,
                        "cursor": native_cursor,
                    },
                )
                if not isinstance(data, dict) or not isinstance(
                    data.get("emojiLikesList"), list
                ):
                    raise BusinessError("回应用户分页响应畸形")
                next_cursor = ""
                if not data.get("isLastPage", False) and data.get("cookie"):
                    next_cursor = uuid.uuid4().hex
                    await runtime.ledger.write(
                        "INSERT INTO meta(key,value) VALUES(?,?)",
                        (
                            f"reaction-cursor:{next_cursor}",
                            json_text(
                                {
                                    "scope": scope.key,
                                    "message_id": mid,
                                    "emoji_id": emoji_id,
                                    "cookie": data["cookie"],
                                    "expires": time.time() + 600,
                                }
                            ),
                        ),
                    )
                return True, output(
                    runtime,
                    {
                        "items": data["emojiLikesList"],
                        "next_cursor": next_cursor,
                        "complete": bool(data.get("isLastPage")),
                        "source": "platform",
                    },
                )
            if view in {"detail", "reactions"}:
                mid = await platform_message(runtime, scope, message_id)
                action = "get_msg" if view == "detail" else "get_msg_emoji_likes"
                data = await runtime.business.read(scope, action, {"message_id": mid})
            elif view == "essence":
                data = await runtime.business.read(
                    scope, "get_essence_msg_list", {"group_id": scope.group}
                )
            elif view in {"history", "bot_recent"}:
                page([], offset, limit)
                if offset + limit > 50:
                    raise BusinessError(
                        "当前历史工具最多读取最近50条；更早历史请用目录的message_seq分页"
                    )
                if scope.group:
                    data = await runtime.business.read(
                        scope,
                        "get_group_msg_history",
                        {
                            "group_id": scope.group,
                            "count": min(50, max(1, offset + limit)),
                        },
                    )
                else:
                    data = await runtime.business.read(
                        scope,
                        "get_friend_msg_history",
                        {
                            "user_id": scope.user,
                            "count": min(50, max(1, offset + limit)),
                        },
                    )
            else:
                raise BusinessError("view 仅支持 history/essence/detail/reactions")
            rows = (
                data
                if isinstance(data, list)
                else data.get("messages")
                if isinstance(data, dict) and isinstance(data.get("messages"), list)
                else None
            )
            result = {"data": data, "source": "platform", "checked_at": time.time()}
            if rows is not None:
                if view == "bot_recent":
                    rows = [
                        row
                        for row in rows
                        if isinstance(row, dict)
                        and identifier(
                            row.get("user_id")
                            or (row.get("sender") or {}).get("user_id")
                        )
                        == scope.account
                    ]
                result = {
                    **page(
                        [
                            r
                            for r in rows
                            if not query or query.lower() in json_text(r).lower()
                        ],
                        offset,
                        limit,
                    ),
                    "source": "platform",
                    "note": "上游当前页/历史上限，非全量历史证明",
                }
            return True, output(runtime, result)
        except (BusinessError, ValueError) as exc:
            return False, str(exc)
        except asyncio.TimeoutError:
            return False, "消息查询超时；不会编造原文"


class FileQuery(BaseTool):
    """群文件/目录与下载链接。"""

    name = "snowluma_files"
    description = "浏览/搜索当前群根目录或指定目录文件，读取真实下载链接。私聊文件链接需平台file_id和file_hash，路径在协议端解析。"
    associated_platforms = ["qq"]

    async def execute(
        self,
        folder_id: str = "",
        file_id: str = "",
        file_hash: str = "",
        busid: int = 0,
        query: str = "",
        offset: int = 0,
        limit: int = 10,
    ) -> tuple[bool, str | dict]:
        """返回当前目录分页，不把本地路径当作协议端可读取文件。"""
        try:
            runtime, scope, _, _ = await context(self)
            if file_id:
                action = "get_group_file_url" if scope.group else "get_private_file_url"
                params = (
                    {"group_id": scope.group, "file_id": file_id, "busid": busid}
                    if scope.group
                    else {
                        "user_id": scope.user,
                        "file_id": file_id,
                        "file_hash": file_hash,
                    }
                )
                return True, output(
                    runtime,
                    {
                        "data": await runtime.business.read(scope, action, params),
                        "note": "协议端临时链接，可能过期；未自动下载",
                    },
                )
            if not scope.group:
                raise BusinessError(
                    "私聊文件读取需要 file_id/file_hash；当前协议没有通用私聊文件目录"
                )
            action = (
                "get_group_files_by_folder" if folder_id else "get_group_root_files"
            )
            params = {
                "group_id": scope.group,
                **({"folder_id": folder_id} if folder_id else {}),
            }
            data = await runtime.business.read(scope, action, params)
            if not isinstance(data, dict):
                raise BusinessError("群文件响应畸形")
            rows = [
                {"kind": kind, **row}
                for kind in ("files", "folders")
                for row in data.get(kind, [])
                if isinstance(row, dict)
            ]
            return True, output(
                runtime,
                {
                    **page(
                        [
                            r
                            for r in rows
                            if not query or query.lower() in json_text(r).lower()
                        ],
                        offset,
                        limit,
                    ),
                    "source": "platform",
                    "recursive": False,
                },
            )
        except (BusinessError, ValueError) as exc:
            return False, str(exc)
        except asyncio.TimeoutError:
            return False, "文件查询超时；链接或权限可能失效"


class RequestQuery(BaseTool):
    """持久待办与处理历史。"""

    name = "snowluma_requests"
    description = "授权操作者查看好友/加群/邀请待办或处理历史；request_id由插件产生，永不向模型提供审批flag。"

    async def execute(
        self, request_id: str = "", offset: int = 0, limit: int = 10
    ) -> tuple[bool, str | dict]:
        """按当前账号分页；空结果表示没有已到达且持久化的请求。"""
        try:
            runtime, scope, operator, _ = await context(self)
            page([], offset, limit)
            return True, output(
                runtime,
                {
                    "items": await runtime.business.request_list(
                        scope, operator, offset, limit, request_id
                    ),
                    "source": "persistent_requests",
                },
            )
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class CatalogQuery(BaseTool):
    """按需 API 发现与接口参数说明。"""

    name = "snowluma_api_catalog"
    description = "仅用于没有专用工具的低频能力；贴表情/戳人/撤回/发消息/成员/公告等请直接调用对应业务工具，无需查目录。分页检索低频SnowLuma能力：空间、群相册、群待办、账号、在线状态、AI语音、OCR、闪传、收藏、Ark等；显示参数/权限/协议限制。"

    async def execute(
        self, query: str = "", offset: int = 0, limit: int = 8
    ) -> tuple[bool, str | dict]:
        """目录是构建期源码证据，不能当作运行实例已经支持。"""
        try:
            runtime, _, _, _ = await context(self)
            page([], offset, limit)
            return True, output(runtime, runtime.gateway.search(query, offset, limit))
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class ApiQuery(BaseTool):
    """受控通用只读查询。"""

    name = "snowluma_api_read"
    description = "按已发现目录调用低频只读API，params_json为参数对象；当前群作用域自动填入，敏感资料/凭证/流式接口受限。"

    async def execute(
        self, action: str, params_json: str = "{}"
    ) -> tuple[bool, str | dict]:
        """与专用工具共用执行策略，不允许通过通用入口绕过审批或消息范围。"""
        try:
            runtime, scope, operator, _ = await context(self)
            params = parse_params(params_json)
            if not isinstance(params, dict):
                raise BusinessError("params_json 必须为 JSON 对象")
            entry = runtime.gateway.catalog.get(runtime.gateway.canonical(action), {})
            if scope.group and "group_id" in entry.get("arguments", []):
                params.setdefault("group_id", scope.group)
            if "message_id" in params:
                params["message_id"] = await platform_message(
                    runtime, scope, str(params["message_id"])
                )
            response = await runtime.gateway.call(scope, operator, action, params)
            return True, output(
                runtime,
                {
                    "action": action,
                    "data": response_data(response),
                    "source": "protocol_response",
                },
            )
        except (BusinessError, ValueError, TypeError) as exc:
            return False, str(exc)
        except asyncio.TimeoutError:
            return False, "API查询超时；请检查连接后重试"


class StatusQuery(BaseTool):
    """诊断/今日打卡/事件查询。"""

    name = "snowluma_status"
    description = "查看本群今日打卡和最近增强事件；授权操作者可查接管/连接/账本/worker/审批/解析/框架/Chatter消费证据。"

    async def execute(
        self,
        view: str = "checkin",
        offset: int = 0,
        limit: int = 10,
        event_id: str = "",
        query: str = "",
    ) -> tuple[bool, str | dict]:
        """诊断不会向非操作者暴露账号级申请和原始资料。"""
        try:
            runtime, scope, operator, _ = await context(self)
            page([], offset, limit)
            if view == "diagnostics":
                if operator not in runtime.config.access.operators:
                    raise BusinessError("全局诊断只供授权操作者")
                result = await runtime.diagnostics()
            elif view == "checkin":
                result = {
                    "timezone": runtime.config.checkin.timezone,
                    "items": await runtime.ledger.rows(
                        "SELECT id,state,result,at,attempts FROM operations WHERE scope=? AND kind='set_group_sign' ORDER BY at DESC LIMIT ? OFFSET ?",
                        (scope.key, limit, offset),
                    ),
                }
            elif view == "events":
                result = {
                    "items": await runtime.ledger.rows(
                        "SELECT id,source,state,error,received,framework,consumed FROM events WHERE scope=? ORDER BY seq DESC LIMIT ? OFFSET ?",
                        (scope.key, limit, offset),
                    )
                }
            elif view == "operations":
                if operator not in runtime.config.access.operators:
                    raise BusinessError("副作用审计仅供授权操作者查看")
                result = {
                    "items": await runtime.ledger.rows(
                        "SELECT id,kind,operator,source,state,result,at FROM operations WHERE scope=? ORDER BY at DESC LIMIT ? OFFSET ?",
                        (scope.key, limit, offset),
                    )
                }
            elif view == "event":
                if not event_id:
                    raise BusinessError("请提供事件ID；先用view=events列出")
                rows = await runtime.ledger.rows(
                    "SELECT * FROM events WHERE id=? AND account=? AND adapter=?",
                    (event_id, scope.account, scope.adapter),
                )
                if not rows or (
                    rows[0]["scope"] != scope.key
                    and operator not in runtime.config.access.operators
                ):
                    raise BusinessError("事件不存在或不属于当前会话")
                row = rows[0]
                event = normalize(
                    json.loads(row["raw"]), scope.adapter, scope.account, row["source"]
                )
                event.event_id, event.received_at = row["id"], row["received"]
                result = {
                    "event": event.public(),
                    "state": row["state"],
                    "error": row["error"],
                }
            elif view == "search":
                rows = await runtime.ledger.rows(
                    "SELECT id,raw,source,state FROM events WHERE scope=? ORDER BY seq DESC LIMIT 1000",
                    (scope.key,),
                )
                found = [
                    {
                        "id": row["id"],
                        "source": row["source"],
                        "state": row["state"],
                        "data": redact(json.loads(row["raw"])),
                    }
                    for row in rows
                ]
                result = {
                    **page(
                        [
                            row
                            for row in found
                            if query.lower() in json_text(row).lower()
                        ],
                        offset,
                        limit,
                    ),
                    "searched_limit": 1000,
                    "source": "persistent_events",
                }
            else:
                raise BusinessError(
                    "view 仅支持 checkin/events/event/search/diagnostics"
                )
            return True, output(runtime, result)
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class EmojiQuery(BaseTool):
    """QQ 原生 face 与其他图片/回应的明确区分。"""

    name = "snowluma_emoji"
    description = "按中文名/关键词查QQ原生face真实ID；超级表情用目录fetch_super_face_id查询；收藏图片/表情包与消息回应是不同能力。"

    async def execute(
        self,
        query: str = "",
        offset: int = 0,
        limit: int = 15,
        kind: str = "native",
        refresh: bool = False,
    ) -> tuple[bool, str | dict]:
        """native 检索平台目录；super 用数字ID判断；custom 查询收藏图片表情。"""
        try:
            runtime, scope, _, _ = await context(self)
            page([], offset, limit)
            if kind == "super":
                if not query.isdecimal():
                    raise BusinessError("super 需要数字 face ID；先用 native 查询")
                data = await runtime.business.read(
                    scope,
                    "fetch_super_face_id",
                    {"face_id": int(query), "refresh": refresh},
                )
                if not isinstance(data, dict) or not isinstance(
                    data.get("is_super"), bool
                ):
                    raise BusinessError("超级表情判断响应畸形")
                return True, {"face_id": query, **data, "source": "platform"}
            if kind not in {"native", "custom"}:
                raise BusinessError("kind 仅支持 native/super/custom")
            source, error = "platform", ""
            try:
                if kind == "custom":
                    data = await runtime.business.read(
                        scope,
                        "fetch_custom_face_detail",
                        {"count": min(200, offset + limit)},
                    )
                    rows = (
                        data
                        if isinstance(data, list)
                        else data.get("faces")
                        if isinstance(data, dict)
                        else None
                    )
                elif query:
                    data = await runtime.business.read(
                        scope, "search_sys_faces", {"query": query}
                    )
                    rows = data.get("faces") if isinstance(data, dict) else None
                else:
                    data = await runtime.business.read(
                        scope, "fetch_sys_faces", {"refresh": refresh}
                    )
                    rows = (
                        [
                            {"pack_name": pack.get("pack_name"), **face}
                            for pack in data.get("packs", [])
                            for face in pack.get("emojis", [])
                        ]
                        if isinstance(data, dict)
                        and isinstance(data.get("packs"), list)
                        else None
                    )
                if not isinstance(rows, list):
                    raise BusinessError("表情目录响应畸形")
            except (BusinessError, asyncio.TimeoutError) as exc:
                if kind != "native":
                    raise
                source, error = "adapter_static_table", type(exc).__name__
                faces = json.loads(
                    (Path(__file__).parent / "resources/faces.json").read_text(
                        encoding="utf-8"
                    )
                )
                rows = [row for row in faces if not query or query in str(row)]
            return True, output(
                runtime,
                {
                    **page(rows, offset, limit),
                    "kind": kind,
                    "source": source,
                    "stale": source != "platform",
                    "error": error,
                    "note": "静态表不是运行实例完整能力；图片表情与原生face/消息回应不同",
                },
            )
        except (BusinessError, ValueError) as exc:
            return False, str(exc)
        except asyncio.TimeoutError:
            return False, "表情查询超时，未把失败当作无表情"


class ManageAction(BoundAction):
    """已授权群管理、公告与低频动作。"""

    name = "snowluma_manage"
    associated_types = ["text"]
    associated_platforms = ["qq"]
    description = "兼容低频已授权写入。贴表情/戳一戳/撤回/打卡/点赞/管理均已有直接业务动作，应直接调用对应动作；不要用此入口查询目录或反复试探权限。"

    async def execute(
        self, action: str, params_json: str = "{}", target: str = ""
    ) -> tuple[bool, str]:
        """所有副作用进入审计；模型不能提供操作者或审批 flag。"""
        try:
            runtime, scope, operator, _ = await context(self)
            params = parse_params(params_json)
            if not isinstance(params, dict):
                raise BusinessError("params_json 必须为对象")
            canonical = runtime.gateway.canonical(action)
            if canonical == "replay_event":
                if (
                    operator not in runtime.config.access.operators
                    or "replay_event" not in runtime.config.access.allowed_actions
                ):
                    raise BusinessError("失败事件重放需要操作者和replay_event授权")
                changed = await runtime.ledger.write(
                    "UPDATE events SET state='pending',attempts=0,next_at=0,error='' WHERE id=? AND account=? AND adapter=? AND state='failed'",
                    (str(params.get("event_id") or ""), scope.account, scope.adapter),
                )
                return (
                    changed == 1,
                    "失败事件已进入受名单约束的重放队列"
                    if changed
                    else "事件不存在、账号不符或并非failed；未修改状态",
                )
            entry = runtime.gateway.catalog.get(canonical, {})
            if scope.group and "group_id" in entry.get("arguments", []):
                params.setdefault("group_id", scope.group)
            if target:
                params["user_id"] = await runtime.business.resolve_member(
                    scope, target, operator
                )
            if "message_id" in params and params["message_id"] != getattr(
                self, "_validated_message_id", None
            ):
                params["message_id"] = await platform_message(
                    runtime, scope, str(params["message_id"])
                )
            baseline_ready = True
            if canonical in {"_send_group_notice", "_del_group_notice"}:
                runtime.gateway.authorize(scope, operator, canonical, True, params)
                try:
                    baseline = await runtime.business.notices(scope, emit=True)
                    baseline_ready = baseline.get("complete", False)
                except Exception:
                    baseline_ready = False
                    runtime.counters["local_notice_baseline_failed"] += 1
            operation_id = uuid.uuid4().hex
            response = await runtime.gateway.call(
                scope,
                operator,
                canonical,
                params,
                write=True,
                operation_id=operation_id,
                basic_interaction=getattr(self, "_basic_interaction", False),
            )
            if canonical in {"_send_group_notice", "_del_group_notice"}:
                # 成功动作后读取实际快照；失败只影响同步，不把失败说成发布失败。
                try:
                    synchronized = await runtime.business.notices(
                        scope, emit=True, source="local_action"
                    )
                    baseline_ready = (
                        baseline_ready
                        and not synchronized.get("baseline")
                        and synchronized.get("complete", False)
                    )
                except Exception:
                    baseline_ready = False
                    runtime.counters["local_notice_resync_failed"] += 1
                if not baseline_ready:
                    raw = {
                        "post_type": "notice",
                        "notice_type": "group_notice",
                        "sub_type": "local_publish_confirmed"
                        if canonical == "_send_group_notice"
                        else "local_delete_confirmed",
                        "event_id": operation_id,
                        "self_id": scope.account,
                        "group_id": scope.group,
                        "operator_id": operator,
                        "notice_id": params.get("notice_id"),
                        "content": params.get("content"),
                        "note": "协议已确认成功；公告详情差异尚未完整核实，不编造公告ID",
                        "time": time.time(),
                    }
                    try:
                        await runtime.ledger.accept(
                            normalize(raw, scope.adapter, scope.account, "local_action")
                        )
                    except Exception:
                        # 平台写入已经确认；事件记录失败不可诱导重复发布。
                        runtime.counters["local_notice_event_store_failed"] += 1
            return True, json_text(
                output(
                    runtime,
                    {
                        "action": canonical,
                        "result": response_data(response),
                        "source": "protocol_response",
                    },
                )
            )
        except (BusinessError, ValueError, TypeError, OSError) as exc:
            return False, str(exc)
        except asyncio.TimeoutError:
            return (
                False,
                "写入结果不确定；可能已在平台执行，已记录审计，请先核实，勿自动重复",
            )


class ApprovalAction(BoundAction):
    """按内部 request_id 安全审批。"""

    name = "snowluma_approve"
    associated_types = ["text"]
    associated_platforms = ["qq"]
    description = "授权操作者同意/拒绝已到达的好友或群请求，只提交插件request_id，不能拼flag或猜类型；超时不重复提交。"

    async def execute(
        self, request_id: str, approve: bool, reason: str = ""
    ) -> tuple[bool, str]:
        """执行一次审批并返回持久状态。"""
        try:
            runtime, scope, operator, _ = await context(self)
            return True, json_text(
                await runtime.business.approve(
                    scope, operator, request_id, approve, reason
                )
            )
        except BusinessError as exc:
            return False, str(exc)
        except asyncio.TimeoutError:
            return False, "审批结果不确定，禁止自动重试；请到平台核实或检查待办详情"


class CheckinAction(BoundAction):
    """手动与计划任务共用每日成功记录。"""

    name = "snowluma_checkin"
    associated_types = ["text"]
    associated_platforms = ["qq"]
    description = "为当前授权群打卡；手动/定时/补打按账号群和配置时区日期共用记录，成功后同日不重复。"

    async def execute(self) -> tuple[bool, str]:
        """返回已确认成功、失败或结果不确定的真实状态。"""
        try:
            runtime, scope, operator, _ = await context(self)
            result = await runtime.business.checkin(
                scope, operator, basic_interaction=True
            )
            return result.get("state") == "success", json_text(result)
        except BusinessError as exc:
            return False, str(exc)
        except asyncio.TimeoutError:
            return False, "打卡结果不确定，已停止自动重试，请核实今日打卡列表"


class SendAction(BoundAction):
    """通过框架发送原生表情、普通消息、引用、转发和媒体。"""

    name = "snowluma_send"
    associated_types = ["text"]
    associated_platforms = ["qq"]
    description = "通过框架正常发送当前会话的text/face/reply/forward/file/image/emoji/voice/video/share；媒体路径须通过文件策略。发送事实和历史一致。"

    async def execute(
        self, kind: str, content: str, message_id: str = ""
    ) -> tuple[bool, str]:
        """敏感/任意媒体不经通用 API 旁路发送；外发必须通过路径检查。"""
        operation_id = ""
        runtime = None
        send_token = None
        try:
            runtime, scope, operator, stream_id = await context(self)
            action = (
                (
                    "send_group_forward_msg"
                    if scope.group
                    else "send_private_forward_msg"
                )
                if kind == "forward"
                else ("send_group_msg" if scope.group else "send_private_msg")
            )
            runtime.gateway.authorize(
                scope,
                operator,
                action,
                True,
                {
                    "group_id": scope.group,
                    "messages" if kind == "forward" else "message": [],
                }
                if scope.group
                else {
                    "user_id": scope.user,
                    "messages" if kind == "forward" else "message": [],
                },
                trusted=False,
                basic_interaction=kind in {"text", "face", "reply"},
            )
            operation_id = f"send:{uuid.uuid4().hex}"
            await runtime.ledger.claim(
                operation_id, scope, action, operator, "local_action"
            )
            send_token = OUTGOING_OPERATION.set((operation_id, stream_id))
            if kind == "text":
                success = await send_api.send_text(
                    content, stream_id, adapter_signature=scope.adapter
                )
            elif kind == "face":
                if not content.isdecimal():
                    raise BusinessError("face 必须为真实数字 ID，请先查 snowluma_emoji")
                success = await send_segment(
                    scope, stream_id, "face", {"id": content}, f"[QQ原生表情:{content}]"
                )
            elif kind == "reply":
                mid = await platform_message(runtime, scope, message_id)
                # 已有 reply/seglist 类型由适配器按段顺序处理。
                success = await send_api.send_text(
                    content, stream_id, reply_to=mid, adapter_signature=scope.adapter
                )
            elif kind == "forward":
                ids = (
                    json.loads(content)
                    if content.lstrip().startswith("[")
                    else [message_id]
                )
                if (
                    not isinstance(ids, list)
                    or not 1 <= len(ids) <= 10
                    or not all(isinstance(item, str) for item in ids)
                ):
                    raise BusinessError(
                        "合并转发需1..10个带platform:/framework:前缀的消息ID；content可为JSON数组"
                    )
                mids = await asyncio.gather(
                    *(platform_message(runtime, scope, item) for item in ids)
                )
                success = await send_segment(
                    scope,
                    stream_id,
                    "node",
                    [{"id": mid} for mid in mids],
                    f"[合并转发:{len(mids)}条平台消息]",
                )
            elif kind == "file":
                path = runtime.gateway.file_source(content)
                success = await send_api.send_file(
                    path, stream_id, adapter_signature=scope.adapter
                )
            elif kind in {"image", "emoji", "voice", "video"}:
                path = runtime.gateway.file_source(content)
                send = {
                    "image": send_api.send_image,
                    "emoji": send_api.send_emoji,
                    "voice": send_api.send_voice,
                    "video": send_api.send_video,
                }[kind]
                payload = await asyncio.to_thread(
                    read_bounded_media, path, runtime.config.files.max_mb * 1048576
                )
                success = await send(
                    payload, stream_id, adapter_signature=scope.adapter
                )
            elif kind == "share":
                if not content.isdecimal():
                    raise BusinessError("分享目标必须是完整QQ/群号")
                success = await send_segment(
                    scope,
                    stream_id,
                    "contact",
                    {"type": "group" if scope.group else "qq", "id": content},
                    "[QQ分享卡片]",
                )
            else:
                raise BusinessError(
                    "kind 仅支持 text/face/reply/forward/file/image/emoji/voice/video/share"
                )
            recorded = await runtime.ledger.rows(
                "SELECT state,result FROM operations WHERE id=?", (operation_id,)
            )
            success = success and bool(recorded and recorded[0]["state"] == "success")
            if not success:
                await runtime.ledger.operation_result(
                    operation_id,
                    "uncertain",
                    "框架没有 AFTER_MESSAGE_SENT 成功事实，可能被拦截或发送失败，请先核实",
                )
            platform_id = ""
            if success:
                result_data = json.loads(recorded[0]["result"])
                if isinstance(result_data, dict):
                    platform_id = str(result_data.get("platform_message_id") or "")
            return success, (
                "platform_message_id=" + platform_id + "；" if platform_id else ""
            ) + (
                "框架发送已确认成功" if success else "框架未确认成功，先核实平台和历史"
            ) + f"；operation_id={operation_id}"
        except (BusinessError, ValueError, OSError) as exc:
            if operation_id and runtime is not None:
                await runtime.ledger.operation_result(
                    operation_id, "failed", type(exc).__name__
                )
            return False, str(exc)
        except asyncio.TimeoutError:
            if operation_id and runtime is not None:
                await runtime.ledger.operation_result(
                    operation_id, "uncertain", "发送超时，可能已执行"
                )
            return False, "发送结果不确定，请检查历史后再决定是否重发"
        except asyncio.CancelledError:
            if operation_id and runtime is not None:
                await runtime.ledger.operation_result(
                    operation_id, "uncertain", "发送被取消，可能已执行"
                )
            raise
        finally:
            if send_token is not None:
                OUTGOING_OPERATION.reset(send_token)


class SnowLumaService(BaseService):
    """其他插件通过公共组件访问脱敏业务状态。"""

    name = "snowluma_service"
    description = "SnowLuma Plus 诊断与业务状态服务（不绕过授权执行副作用）"

    async def diagnostics(self) -> dict[str, Any]:
        """进程内可信插件调用的脱敏诊断。"""
        runtime = getattr(self.plugin, "runtime", None)
        if runtime is None:
            return {"running": False}
        return await runtime.diagnostics()


COMPONENTS = [
    GroupQuery,
    NoticeQuery,
    MessageQuery,
    FileQuery,
    RequestQuery,
    CatalogQuery,
    ApiQuery,
    StatusQuery,
    EmojiQuery,
    ManageAction,
    ApprovalAction,
    CheckinAction,
    SendAction,
    SnowLumaService,
]
