"""直接面向业务的常用工具和动作；模型无需发现协议名或拼JSON。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated
from src.app.plugin_system.base import BaseTool
from .compat import BoundAction
from .components import (
    GroupQuery,
    NoticeQuery,
    MessageQuery,
    FileQuery,
    EmojiQuery,
    StatusQuery,
    ManageAction,
    SendAction,
    context,
    platform_message,
)
from .gateway import BusinessError


def face_id(value: str) -> str:
    """按真实静态映射解析常用中文名称，歧义明确报错。"""
    if value.isdecimal():
        return value
    query = {"点赞": "赞", "笑脸": "微笑"}.get(value.strip(), value.strip())
    rows = json.loads(
        (Path(__file__).parent / "resources/faces.json").read_text(encoding="utf-8")
    )
    matches = [
        row
        for row in rows
        if row["name"].removeprefix("[表情：").removesuffix("]") == query
    ]
    if len(matches) != 1:
        raise BusinessError("表情名称未能唯一匹配，请用snowluma_find_face查询真实ID")
    return matches[0]["id"]


class _Query(BaseTool):
    async def query(self, cls, **kwargs):
        tool = cls(self.plugin)
        tool._bind_runtime_context(
            stream_id=self.stream_id, message=self.trigger_message
        )
        return await tool.execute(**kwargs)


class _Action(BoundAction):
    associated_types = ["text"]
    associated_platforms = ["qq"]

    async def reference(self, value: str = "") -> str:
        runtime, scope, _, _ = await context(self)
        message = self.trigger_message
        raw = value.strip()
        current = str(message.message_id)
        if not raw or raw in {current, "framework:" + current}:
            rows = await runtime.ledger.rows(
                "SELECT platform_id FROM mappings WHERE scope=? AND framework_id=?",
                (scope.key, current),
            )
            if rows:
                return rows[0]["platform_id"]
        return await platform_message(
            runtime,
            scope,
            raw if raw.startswith(("framework:", "platform:")) else "platform:" + raw,
        )

    async def manage(
        self, action: str, params: dict, target: str = "", basic: bool = False
    ):
        try:
            component = ManageAction(self.chat_stream, self.plugin)
            component._bind_runtime_context(message=self.trigger_message)
            runtime, scope, operator, _ = await context(self)
            explicitly_authorized = (
                operator in runtime.config.access.operators
                and runtime.gateway.canonical(action)
                in {
                    runtime.gateway.canonical(item)
                    for item in runtime.config.access.allowed_actions
                }
                and (
                    not scope.group or scope.group in runtime.config.access.write_groups
                )
            )
            component._basic_interaction = basic and not explicitly_authorized
            if "message_id" in params:
                params["message_id"] = await self.reference(str(params["message_id"]))
                component._validated_message_id = params["message_id"]
            return await component.execute(
                action, json.dumps(params, ensure_ascii=False), target
            )
        except (BusinessError, ValueError, OSError) as exc:
            return False, str(exc)
        except asyncio.TimeoutError:
            return False, "调用结果不确定，请核实平台；不要自动重复写入"

    async def send(self, kind: str, content: str, message_id: str = ""):
        component = SendAction(self.chat_stream, self.plugin)
        component._bind_runtime_context(message=self.trigger_message)
        if message_id and not message_id.startswith(("framework:", "platform:")):
            message_id = "platform:" + message_id
        return await component.execute(kind, content, message_id)


class GroupInfo(_Query):
    name = "snowluma_group_info"
    description = "直接查看当前群名称、群号、人数和群资料，无需查API目录。"
    associated_platforms = ["qq"]

    async def execute(self, refresh: bool = False) -> tuple[bool, str | dict]:
        """直接查看当前群名称、群号、人数和群资料，无需查API目录。"""
        return await self.query(GroupQuery, view="overview", refresh=refresh)


class Members(_Query):
    name = "snowluma_find_member"
    description = (
        "直接按QQ号、昵称、群名片或头衔查群成员；“我”指真实发言人，同名返回候选。"
    )
    associated_platforms = ["qq"]

    async def execute(
        self,
        query: Annotated[str, "成员QQ/昵称/名片/头衔；空列出成员"] = "",
        offset: int = 0,
        limit: int = 10,
        refresh: bool = False,
    ) -> tuple[bool, str | dict]:
        """直接按QQ号、昵称、群名片或头衔查群成员；“我”指真实发言人，同名返回候选。"""
        return await self.query(
            GroupQuery,
            view="member",
            query=query,
            offset=offset,
            limit=limit,
            refresh=refresh,
        )


class BotIdentity(_Query):
    name = "snowluma_bot_identity"
    description = "直接查询Bot在本群的身份、管理员权限、群头衔；不需要先查目录。"
    associated_platforms = ["qq"]

    async def execute(self, refresh: bool = True) -> tuple[bool, str | dict]:
        """直接查询Bot在本群的身份、管理员权限、群头衔；不需要先查目录。"""
        return await self.query(GroupQuery, view="identity", refresh=refresh)


class Honor(_Query):
    name = "snowluma_group_honor"
    description = "直接查询本群龙王、群聊之火等荣誉，可按成员搜索。"
    associated_platforms = ["qq"]

    async def execute(self, query: str = "") -> tuple[bool, str | dict]:
        """直接查询本群龙王、群聊之火等荣誉，可按成员搜索。"""
        return await self.query(GroupQuery, view="honor", query=query)


class Active(_Query):
    name = "snowluma_active_members"
    description = "直接查询本群滚动近24小时活跃成员和消息条数；可回填Bot可见历史。"
    associated_platforms = ["qq"]

    async def execute(
        self, limit: int = 10, offset: int = 0, refresh: bool = False
    ) -> tuple[bool, str | dict]:
        """直接查询本群滚动近24小时活跃成员和消息条数；可回填Bot可见历史。"""
        return await self.query(
            GroupQuery, view="active", limit=limit, offset=offset, refresh=refresh
        )


class Notices(_Query):
    name = "snowluma_list_notices"
    description = "直接查看当前群最新公告或按内容搜索；返回公告ID和完整性。"
    associated_platforms = ["qq"]

    async def execute(
        self, query: str = "", limit: int = 10, offset: int = 0
    ) -> tuple[bool, str | dict]:
        """直接查看当前群最新公告或按内容搜索；返回公告ID和完整性。"""
        return await self.query(NoticeQuery, query=query, limit=limit, offset=offset)


class Essence(_Query):
    name = "snowluma_list_essence"
    description = "直接查看本群精华消息，支持内容搜索和分页。"
    associated_platforms = ["qq"]

    async def execute(
        self, query: str = "", limit: int = 10, offset: int = 0
    ) -> tuple[bool, str | dict]:
        """直接查看本群精华消息，支持内容搜索和分页。"""
        return await self.query(
            MessageQuery, view="essence", query=query, limit=limit, offset=offset
        )


class History(_Query):
    name = "snowluma_message_history"
    description = "直接查询当前群/私聊最近消息及真实消息ID，支持内容检索。"
    associated_platforms = ["qq"]

    async def execute(
        self, query: str = "", limit: int = 15, offset: int = 0
    ) -> tuple[bool, str | dict]:
        """直接查询当前群/私聊最近消息及真实消息ID，支持内容检索。"""
        return await self.query(
            MessageQuery, view="history", query=query, limit=limit, offset=offset
        )


class RecentBot(_Query):
    name = "snowluma_recent_bot_messages"
    description = "直接查看Bot近期发出的消息和可用于撤回的消息ID。"
    associated_platforms = ["qq"]

    async def execute(self, limit: int = 10) -> tuple[bool, str | dict]:
        """直接查看Bot近期发出的消息和可用于撤回的消息ID。"""
        return await self.query(MessageQuery, view="bot_recent", limit=limit)


class Detail(_Query):
    name = "snowluma_message_detail"
    description = "直接查看指定消息详情，message_id使用平台真实消息ID或framework:前缀。"
    associated_platforms = ["qq"]

    async def execute(self, message_id: str) -> tuple[bool, str | dict]:
        """直接查看指定消息详情，message_id使用平台真实消息ID或framework:前缀。"""
        return await self.query(
            MessageQuery,
            view="detail",
            message_id=message_id
            if message_id.startswith(("platform:", "framework:"))
            else "platform:" + message_id,
        )


class Reactions(_Query):
    name = "snowluma_message_reactions"
    description = "直接查询某条消息收到的表情回应及数量。"
    associated_platforms = ["qq"]

    async def execute(self, message_id: str) -> tuple[bool, str | dict]:
        """直接查询某条消息收到的表情回应及数量。"""
        return await self.query(
            MessageQuery,
            view="reactions",
            message_id=message_id
            if message_id.startswith(("platform:", "framework:"))
            else "platform:" + message_id,
        )


class ReactionUsers(_Query):
    name = "snowluma_reaction_users"
    description = "直接分页查询谁给消息贴了某个表情；cursor使用上次结果提供的值。"
    associated_platforms = ["qq"]

    async def execute(
        self, message_id: str, emoji_id: str, cursor: str = "", limit: int = 10
    ) -> tuple[bool, str | dict]:
        """直接分页查询谁给消息贴了某个表情；cursor使用上次结果提供的值。"""
        return await self.query(
            MessageQuery,
            view="reaction_users",
            message_id=message_id
            if message_id.startswith(("platform:", "framework:"))
            else "platform:" + message_id,
            emoji_id=emoji_id,
            cursor=cursor,
            limit=limit,
        )


class Faces(_Query):
    name = "snowluma_find_face"
    description = "直接按中文名查QQ原生表情真实ID，用于发送原生表情或贴表情回应。"
    associated_platforms = ["qq"]

    async def execute(
        self, query: str = "", limit: int = 15
    ) -> tuple[bool, str | dict]:
        """直接按中文名查QQ原生表情真实ID，用于发送原生表情或贴表情回应。"""
        return await self.query(EmojiQuery, query=query, limit=limit)


class CheckinStatus(_Query):
    name = "snowluma_checkin_status"
    description = "直接查询本群今天的打卡记录与结果，不执行打卡。"
    associated_platforms = ["qq"]

    async def execute(self) -> tuple[bool, str | dict]:
        """直接查询本群今天的打卡记录与结果，不执行打卡。"""
        return await self.query(StatusQuery, view="checkin")


class React(_Action):
    name = "snowluma_react_message"
    description = "给消息贴表情回应或取消回应；默认当前真实用户的这条消息。支持中文表情名或数字ID，直接执行，无需查询API。"

    async def execute(
        self,
        emoji: Annotated[str, "中文表情名或真实ID，例如赞、微笑、76"] = "赞",
        message_id: Annotated[str, "消息ID；空为本次触发消息"] = "",
        remove: bool = False,
    ) -> tuple[bool, str]:
        """给消息贴表情回应或取消回应；默认当前真实用户的这条消息。支持中文表情名或数字ID，直接执行，无需查询API。"""
        try:
            return await self.manage(
                "set_msg_emoji_like",
                {
                    "message_id": message_id,
                    "emoji_id": face_id(emoji),
                    "set": not remove,
                },
                basic=True,
            )
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class Recall(_Action):
    name = "snowluma_recall_message"
    description = (
        "直接撤回指定消息。普通互动只可撤回Bot自己的消息；撤回成员消息需要管理授权。"
    )

    async def execute(
        self,
        message_id: Annotated[
            str, "要撤回的真实消息ID；可用发送结果中的platform_message_id"
        ],
    ) -> tuple[bool, str]:
        """直接撤回指定消息。普通互动只可撤回Bot自己的消息；撤回成员消息需要管理授权。"""
        try:
            return await self.manage(
                "delete_msg", {"message_id": message_id}, basic=True
            )
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class Mute(_Action):
    name = "snowluma_mute_member"
    description = "直接禁言指定群成员，duration_seconds为秒；需授权并检查Bot平台权限。"

    async def execute(
        self,
        member: Annotated[str, "成员QQ、昵称或群名片"],
        duration_seconds: int = 600,
    ) -> tuple[bool, str]:
        """直接禁言指定群成员，duration_seconds为秒；需授权并检查Bot平台权限。"""
        try:
            return await self.manage(
                "set_group_ban", {"duration": duration_seconds}, target=member
            )
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class Unmute(_Action):
    name = "snowluma_unmute_member"
    description = "直接解除指定群成员禁言；仍需群管理授权。"

    async def execute(self, member: str) -> tuple[bool, str]:
        """直接解除指定群成员禁言；仍需群管理授权。"""
        try:
            return await self.manage("set_group_ban", {"duration": 0}, target=member)
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class WholeMute(_Action):
    name = "snowluma_whole_group_mute"
    description = "直接开启或关闭本群全员禁言；需管理授权。"

    async def execute(self, enabled: bool) -> tuple[bool, str]:
        """直接开启或关闭本群全员禁言；需管理授权。"""
        try:
            return await self.manage("set_group_whole_ban", {"enable": enabled})
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class Kick(_Action):
    name = "snowluma_kick_member"
    description = "直接移出指定群成员；需独立授权并核验成员层级，不支持模糊猜人。"

    async def execute(
        self, member: str, reject_rejoin: bool = False
    ) -> tuple[bool, str]:
        """直接移出指定群成员；需独立授权并核验成员层级，不支持模糊猜人。"""
        try:
            return await self.manage(
                "set_group_kick", {"reject_add_request": reject_rejoin}, target=member
            )
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class Card(_Action):
    name = "snowluma_set_member_card"
    description = "直接修改指定成员的群名片；需相应动作授权。"

    async def execute(self, member: str, card: str) -> tuple[bool, str]:
        """直接修改指定成员的群名片；需相应动作授权。"""
        try:
            return await self.manage("set_group_card", {"card": card}, target=member)
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class Title(_Action):
    name = "snowluma_set_member_title"
    description = "直接设置群成员专属头衔；需动作授权和Bot群主身份。"

    async def execute(self, member: str, title: str) -> tuple[bool, str]:
        """直接设置群成员专属头衔；需动作授权和Bot群主身份。"""
        try:
            return await self.manage(
                "set_group_special_title", {"special_title": title}, target=member
            )
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class GroupName(_Action):
    name = "snowluma_rename_group"
    description = "直接修改当前群名称；需群管理授权。"

    async def execute(self, name: str) -> tuple[bool, str]:
        """直接修改当前群名称；需群管理授权。"""
        try:
            return await self.manage("set_group_name", {"group_name": name})
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class PublishNotice(_Action):
    name = "snowluma_publish_notice"
    description = "直接发布当前群公告，成功后同步公告差异；需独立授权。"

    async def execute(self, content: str) -> tuple[bool, str]:
        """直接发布当前群公告，成功后同步公告差异；需独立授权。"""
        try:
            return await self.manage("_send_group_notice", {"content": content})
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class DeleteNotice(_Action):
    name = "snowluma_delete_notice"
    description = "直接删除指定公告；notice_id是公告ID，需独立授权。"

    async def execute(self, notice_id: str) -> tuple[bool, str]:
        """直接删除指定公告；notice_id是公告ID，需独立授权。"""
        try:
            return await self.manage("_del_group_notice", {"notice_id": notice_id})
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class SetEssence(_Action):
    name = "snowluma_set_essence"
    description = "直接把指定本群消息设为精华；需独立授权。"

    async def execute(self, message_id: str) -> tuple[bool, str]:
        """直接把指定本群消息设为精华；需独立授权。"""
        try:
            return await self.manage("set_essence_msg", {"message_id": message_id})
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class RemoveEssence(_Action):
    name = "snowluma_remove_essence"
    description = "直接取消指定本群消息的精华；需独立授权。"

    async def execute(self, message_id: str) -> tuple[bool, str]:
        """直接取消指定本群消息的精华；需独立授权。"""
        try:
            return await self.manage("delete_essence_msg", {"message_id": message_id})
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class ProfileLike(_Action):
    name = "snowluma_profile_like"
    description = "直接为指定QQ主页点赞，只需QQ号和次数。当前真实发言人1至10次属于普通互动；其他目标需动作授权。"

    async def execute(self, user_id: str, times: int = 1) -> tuple[bool, str]:
        """当前发言人普通点赞；其他目标仍执行独立授权。"""
        try:
            return await self.manage(
                "send_like", {"user_id": user_id, "times": times}, basic=True
            )
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class Text(_Action):
    name = "snowluma_send_text"
    description = "直接在当前群/私聊发普通文字；发送结果提供平台消息ID以便撤回。"

    async def execute(self, text: str) -> tuple[bool, str]:
        """直接在当前群/私聊发普通文字；发送结果提供平台消息ID以便撤回。"""
        try:
            return await self.send("text", text)
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class Face(_Action):
    name = "snowluma_send_face"
    description = "直接发送QQ原生表情，支持中文名或真实ID；不是贴在消息上的回应。"

    async def execute(self, emoji: str = "微笑") -> tuple[bool, str]:
        """直接发送QQ原生表情，支持中文名或真实ID；不是贴在消息上的回应。"""
        try:
            return await self.send("face", face_id(emoji))
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class Reply(_Action):
    name = "snowluma_reply_message"
    description = "直接引用当前会话指定消息并发送文字。"

    async def execute(self, text: str, message_id: str) -> tuple[bool, str]:
        """直接引用当前会话指定消息并发送文字。"""
        try:
            return await self.send("reply", text, message_id)
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class Forward(_Action):
    name = "snowluma_forward_messages"
    description = "直接合并转发当前会话1至10条已有消息；需发送授权。"

    async def execute(self, message_ids: list[str]) -> tuple[bool, str]:
        """直接合并转发当前会话1至10条已有消息；需发送授权。"""
        try:
            return await self.send(
                "forward",
                json.dumps(
                    [
                        value
                        if value.startswith(("platform:", "framework:"))
                        else "platform:" + value
                        for value in message_ids
                    ]
                ),
            )
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class File(_Action):
    name = "snowluma_send_file"
    description = "直接发送已获准的本机文件；文件外发、同主机及允许目录策略仍生效。"

    async def execute(self, path: str) -> tuple[bool, str]:
        """直接发送已获准的本机文件；文件外发、同主机及允许目录策略仍生效。"""
        try:
            return await self.send("file", path)
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class Image(_Action):
    name = "snowluma_send_image"
    description = "直接发送已获准的本机图片；需文件外发及目录策略授权。"

    async def execute(self, path: str) -> tuple[bool, str]:
        """直接发送已获准的本机图片；需文件外发及目录策略授权。"""
        try:
            return await self.send("image", path)
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class Poke(_Action):
    name = "snowluma_poke"
    description = "直接戳一戳当前真实发言人，默认戳请求者自己；指定其他成员需要独立动作授权，无需查询API。"

    async def execute(self, member: str = "我") -> tuple[bool, str]:
        """群内戳成员；私聊只戳当前对方。"""
        try:
            runtime, scope, operator, _ = await context(self)
            target = (
                await runtime.business.resolve_member(scope, member, operator)
                if scope.group
                else operator
            )
            return await self.manage(
                "group_poke" if scope.group else "friend_poke",
                {"user_id": target},
                basic=target == operator,
            )
        except (BusinessError, ValueError) as exc:
            return False, str(exc)


class ListFiles(_Query):
    name = "snowluma_list_files"
    description = "直接查看或搜索当前群文件列表，支持目录与分页。"

    async def execute(
        self, query: str = "", folder_id: str = "", offset: int = 0, limit: int = 10
    ) -> tuple[bool, str | dict]:
        return await self.query(
            FileQuery, query=query, folder_id=folder_id, offset=offset, limit=limit
        )


class FileUrl(_Query):
    name = "snowluma_file_url"
    description = (
        "直接获取当前会话平台文件的下载链接，不自动下载；私聊文件需file_hash。"
    )

    async def execute(
        self, file_id: str, busid: int = 0, file_hash: str = ""
    ) -> tuple[bool, str | dict]:
        return await self.query(
            FileQuery, file_id=file_id, busid=busid, file_hash=file_hash
        )


class Voice(_Action):
    name = "snowluma_send_voice"
    description = "直接发送已获准的本机语音，需文件外发及目录策略授权。"

    async def execute(self, path: str) -> tuple[bool, str]:
        return await self.send("voice", path)


class Video(_Action):
    name = "snowluma_send_video"
    description = "直接发送已获准的本机视频，需文件外发及目录策略授权。"

    async def execute(self, path: str) -> tuple[bool, str]:
        return await self.send("video", path)


DIRECT_COMPONENTS = [
    GroupInfo,
    Members,
    BotIdentity,
    Honor,
    Active,
    Notices,
    Essence,
    History,
    RecentBot,
    Detail,
    Reactions,
    ReactionUsers,
    Faces,
    CheckinStatus,
    React,
    Recall,
    Mute,
    Unmute,
    WholeMute,
    Kick,
    Card,
    Title,
    GroupName,
    PublishNotice,
    DeleteNotice,
    SetEssence,
    RemoveEssence,
    ProfileLike,
    Text,
    Face,
    Reply,
    Forward,
    File,
    Image,
    Poke,
    ListFiles,
    FileUrl,
    Voice,
    Video,
]
