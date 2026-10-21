"""生成的直接业务组件；由generate_business_tools.py维护，业务实现独立编写。"""

from __future__ import annotations
from typing import Annotated, Any
from .typed import TypedRead, TypedWrite


class ApiGetForwardMsg(TypedRead):
    name = "snowluma_get_forward_msg"
    description = "直接获取合并转发消息内容。直接填写参数即可，无需查询API目录。"
    api_action = "get_forward_msg"

    async def execute(
        self, *, message_id: Annotated[str, "消息ID，支持平台ID及framework:前缀"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"message_id": message_id})


class ApiMarkMsgAsRead(TypedWrite):
    name = "snowluma_mark_msg_as_read"
    description = "直接标记消息已读（go-cqhttp兼容）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "mark_msg_as_read"

    async def execute(
        self,
        *,
        message_id: Annotated[str, "消息ID，支持平台ID及framework:前缀"],
        target_id: Annotated[str | None, "接口参数：target_id"] = None,
    ) -> tuple[bool, str | dict]:
        return await self.call({"message_id": message_id, "target_id": target_id})


class ApiMarkGroupMsgAsRead(TypedWrite):
    name = "snowluma_mark_group_msg_as_read"
    description = "直接标记群消息已读（扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "mark_group_msg_as_read"

    async def execute(
        self,
        *,
        message_id: Annotated[str, "消息ID，支持平台ID及framework:前缀"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"message_id": message_id, "group_id": group_id})


class ApiMarkPrivateMsgAsRead(TypedWrite):
    name = "snowluma_mark_private_msg_as_read"
    description = "直接标记私聊消息已读（扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "mark_private_msg_as_read"

    async def execute(
        self,
        *,
        message_id: Annotated[str, "消息ID，支持平台ID及framework:前缀"],
        user_id: Annotated[str | None, "目标QQ号，完整数字字符串"] = None,
    ) -> tuple[bool, str | dict]:
        return await self.call({"message_id": message_id, "user_id": user_id})


class ApiMarkAllAsRead(TypedWrite):
    name = "snowluma_mark_all_as_read"
    description = "直接标记全部已读（扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "_mark_all_as_read"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiSetGroupAdmin(TypedWrite):
    name = "snowluma_set_group_admin"
    description = "直接设置/取消管理员。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_group_admin"

    async def execute(
        self,
        *,
        user_id: Annotated[str, "目标QQ号，完整数字字符串"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
        enable: Annotated[bool, "是否启用"] = True,
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {"user_id": user_id, "group_id": group_id, "enable": enable}
        )


class ApiSetGroupLeave(TypedWrite):
    name = "snowluma_set_group_leave"
    description = "直接退出群聊。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_group_leave"

    async def execute(
        self,
        *,
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
        is_dismiss: Annotated[bool, "接口参数：is_dismiss"] = False,
    ) -> tuple[bool, str | dict]:
        return await self.call({"group_id": group_id, "is_dismiss": is_dismiss})


class ApiSetGroupMemberInvitePolicy(TypedWrite):
    name = "snowluma_set_group_member_invite_policy"
    description = "直接设置群成员邀请策略（NapCat / SnowLuma 扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_group_member_invite_policy"

    async def execute(
        self,
        *,
        policy: Annotated[str, "接口参数：policy"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"policy": policy, "group_id": group_id})


class ApiSetGroupMemberPermissions(TypedWrite):
    name = "snowluma_set_group_member_permissions"
    description = "直接设置群成员功能权限（NapCat / SnowLuma 扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_group_member_permissions"

    async def execute(
        self,
        *,
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
        allow_member_upload_album: Annotated[
            bool | None, "接口参数：allow_member_upload_album"
        ] = None,
        allow_member_temporary_session: Annotated[
            bool | None, "接口参数：allow_member_temporary_session"
        ] = None,
        allow_member_create_group: Annotated[
            bool | None, "接口参数：allow_member_create_group"
        ] = None,
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {
                "group_id": group_id,
                "allow_member_upload_album": allow_member_upload_album,
                "allow_member_temporary_session": allow_member_temporary_session,
                "allow_member_create_group": allow_member_create_group,
            }
        )


class ApiSetGroupNewMemberHistoryVisibility(TypedWrite):
    name = "snowluma_set_group_new_member_history_visibility"
    description = "直接设置新成员历史消息可见性（NapCat / SnowLuma 扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_group_new_member_history_visibility"

    async def execute(
        self,
        *,
        visible: Annotated[bool, "接口参数：visible"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"visible": visible, "group_id": group_id})


class ApiGetGroupAdminSettings(TypedRead):
    name = "snowluma_get_group_admin_settings"
    description = "直接获取群管理设置当前值（SnowLuma 扩展，返回加群选项/邀请策略/成员权限/搜索开关等）。直接填写参数即可，无需查询API目录。"
    api_action = "get_group_admin_settings"

    async def execute(
        self, *, group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = ""
    ) -> tuple[bool, str | dict]:
        return await self.call({"group_id": group_id})


class ApiUploadGroupFile(TypedWrite):
    name = "snowluma_upload_group_file"
    description = "直接上传群文件。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "upload_group_file"

    async def execute(
        self,
        *,
        file_path: Annotated[str, "本机文件绝对路径，须授权"],
        name: Annotated[str, "名称"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {"file_path": file_path, "name": name, "group_id": group_id}
        )


class ApiUploadPrivateFile(TypedWrite):
    name = "snowluma_upload_private_file"
    description = "直接上传私聊文件。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "upload_private_file"

    async def execute(
        self,
        *,
        user_id: Annotated[str, "目标QQ号，完整数字字符串"],
        file_path: Annotated[str, "本机文件绝对路径，须授权"],
        name: Annotated[str, "名称"],
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {"user_id": user_id, "file_path": file_path, "name": name}
        )


class ApiGetFile(TypedRead):
    name = "snowluma_get_file"
    description = "直接获取文件信息（NapCat 扩展）。直接填写参数即可，无需查询API目录。"
    api_action = "get_file"

    async def execute(
        self, *, file_id: Annotated[str, "平台文件ID"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"file_id": file_id})


class ApiGetImage(TypedRead):
    name = "snowluma_get_image"
    description = "直接获取图片信息。直接填写参数即可，无需查询API目录。"
    api_action = "get_image"

    async def execute(
        self, *, file: Annotated[str, "文件来源，须通过本地允许目录及同主机检查"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"file": file})


class ApiGetRecord(TypedRead):
    name = "snowluma_get_record"
    description = "直接获取语音文件信息。直接填写参数即可，无需查询API目录。"
    api_action = "get_record"

    async def execute(
        self,
        *,
        file: Annotated[str, "文件来源，须通过本地允许目录及同主机检查"],
        out_format: Annotated[str, "接口参数：out_format"] = "mp3",
    ) -> tuple[bool, str | dict]:
        return await self.call({"file": file, "out_format": out_format})


class ApiGetLoginInfo(TypedRead):
    name = "snowluma_get_login_info"
    description = "直接获取 Bot 登录信息。直接填写参数即可，无需查询API目录。"
    api_action = "get_login_info"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiGetStrangerInfo(TypedRead):
    name = "snowluma_get_stranger_info"
    description = "直接获取陌生人信息。直接填写参数即可，无需查询API目录。"
    api_action = "get_stranger_info"

    async def execute(
        self,
        *,
        user_id: Annotated[str, "目标QQ号，完整数字字符串"],
        no_cache: Annotated[bool, "是否绕过缓存"] = False,
    ) -> tuple[bool, str | dict]:
        return await self.call({"user_id": user_id, "no_cache": no_cache})


class ApiGetFriendList(TypedRead):
    name = "snowluma_get_friend_list"
    description = "直接获取好友列表。直接填写参数即可，无需查询API目录。"
    api_action = "get_friend_list"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiGetGroupList(TypedRead):
    name = "snowluma_get_group_list"
    description = "直接获取群列表。直接填写参数即可，无需查询API目录。"
    api_action = "get_group_list"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiGetGroupDetailInfo(TypedRead):
    name = "snowluma_get_group_detail_info"
    description = (
        "直接获取群详细信息（NapCat 扩展）。直接填写参数即可，无需查询API目录。"
    )
    api_action = "get_group_detail_info"

    async def execute(
        self, *, group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = ""
    ) -> tuple[bool, str | dict]:
        return await self.call({"group_id": group_id})


class ApiGetOnlineClients(TypedRead):
    name = "snowluma_get_online_clients"
    description = "直接获取在线客户端列表。直接填写参数即可，无需查询API目录。"
    api_action = "get_online_clients"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiGetStatus(TypedRead):
    name = "snowluma_get_status"
    description = "直接获取协议端运行状态。直接填写参数即可，无需查询API目录。"
    api_action = "get_status"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiCanSendImage(TypedRead):
    name = "snowluma_can_send_image"
    description = "直接检查是否支持发送图片。直接填写参数即可，无需查询API目录。"
    api_action = "can_send_image"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiCanSendRecord(TypedRead):
    name = "snowluma_can_send_record"
    description = "直接检查是否支持发送语音。直接填写参数即可，无需查询API目录。"
    api_action = "can_send_record"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiGetVersionInfo(TypedRead):
    name = "snowluma_get_version_info"
    description = "直接获取协议端版本信息。直接填写参数即可，无需查询API目录。"
    api_action = "get_version_info"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiGetGroupAtAllRemain(TypedRead):
    name = "snowluma_get_group_at_all_remain"
    description = (
        "直接获取@全体剩余次数（go-cqhttp兼容）。直接填写参数即可，无需查询API目录。"
    )
    api_action = "get_group_at_all_remain"

    async def execute(
        self, *, group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = ""
    ) -> tuple[bool, str | dict]:
        return await self.call({"group_id": group_id})


class ApiFetchPttText(TypedRead):
    name = "snowluma_fetch_ptt_text"
    description = "直接获取语音转文字（扩展）。直接填写参数即可，无需查询API目录。"
    api_action = "fetch_ptt_text"

    async def execute(
        self, *, message_id: Annotated[str, "消息ID，支持平台ID及framework:前缀"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"message_id": message_id})


class ApiDeleteGroupFile(TypedWrite):
    name = "snowluma_delete_group_file"
    description = "直接删除群文件（go-cqhttp 兼容）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "delete_group_file"

    async def execute(
        self,
        *,
        file_id: Annotated[str, "平台文件ID"],
        busid: Annotated[int, "平台文件业务编号"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {"file_id": file_id, "busid": busid, "group_id": group_id}
        )


class ApiCreateGroupFileFolder(TypedWrite):
    name = "snowluma_create_group_file_folder"
    description = "直接创建群文件夹（go-cqhttp 兼容）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "create_group_file_folder"

    async def execute(
        self,
        *,
        name: Annotated[str, "名称"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
        parent_id: Annotated[str, "接口参数：parent_id"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {"name": name, "group_id": group_id, "parent_id": parent_id}
        )


class ApiDeleteGroupFolder(TypedWrite):
    name = "snowluma_delete_group_folder"
    description = "直接删除群文件夹（go-cqhttp 兼容）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "delete_group_folder"

    async def execute(
        self,
        *,
        folder_id: Annotated[str, "目录ID"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"folder_id": folder_id, "group_id": group_id})


class ApiGetGroupFileSystemInfo(TypedRead):
    name = "snowluma_get_group_file_system_info"
    description = (
        "直接获取群文件系统信息（go-cqhttp 兼容）。直接填写参数即可，无需查询API目录。"
    )
    api_action = "get_group_file_system_info"

    async def execute(
        self, *, group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = ""
    ) -> tuple[bool, str | dict]:
        return await self.call({"group_id": group_id})


class ApiMoveGroupFile(TypedWrite):
    name = "snowluma_move_group_file"
    description = "直接移动群文件（扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "move_group_file"

    async def execute(
        self,
        *,
        file_id: Annotated[str, "平台文件ID"],
        parent_directory: Annotated[str, "接口参数：parent_directory"],
        target_directory: Annotated[str, "接口参数：target_directory"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {
                "file_id": file_id,
                "parent_directory": parent_directory,
                "target_directory": target_directory,
                "group_id": group_id,
            }
        )


class ApiRenameGroupFile(TypedWrite):
    name = "snowluma_rename_group_file"
    description = "直接重命名群文件（扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "rename_group_file"

    async def execute(
        self,
        *,
        file_id: Annotated[str, "平台文件ID"],
        current_parent_directory: Annotated[str, "接口参数：current_parent_directory"],
        new_name: Annotated[str, "接口参数：new_name"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {
                "file_id": file_id,
                "current_parent_directory": current_parent_directory,
                "new_name": new_name,
                "group_id": group_id,
            }
        )


class ApiRenameGroupFileFolder(TypedWrite):
    name = "snowluma_rename_group_file_folder"
    description = "直接重命名群文件夹（SnowLuma 扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "rename_group_file_folder"

    async def execute(
        self,
        *,
        folder_id: Annotated[str, "目录ID"],
        new_folder_name: Annotated[str, "接口参数：new_folder_name"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {
                "folder_id": folder_id,
                "new_folder_name": new_folder_name,
                "group_id": group_id,
            }
        )


class ApiTransGroupFile(TypedWrite):
    name = "snowluma_trans_group_file"
    description = "直接转存群文件（扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "trans_group_file"

    async def execute(
        self,
        *,
        file_id: Annotated[str, "平台文件ID"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"file_id": file_id, "group_id": group_id})


class ApiSetGroupPortrait(TypedWrite):
    name = "snowluma_set_group_portrait"
    description = "直接设置群头像。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_group_portrait"

    async def execute(
        self,
        *,
        file: Annotated[str, "文件来源，须通过本地允许目录及同主机检查"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"file": file, "group_id": group_id})


class ApiSetGroupRemark(TypedWrite):
    name = "snowluma_set_group_remark"
    description = "直接设置群备注。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_group_remark"

    async def execute(
        self,
        *,
        remark: Annotated[str, "接口参数：remark"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"remark": remark, "group_id": group_id})


class ApiSetGroupAddOption(TypedWrite):
    name = "snowluma_set_group_add_option"
    description = "直接设置加群选项。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_group_add_option"

    async def execute(
        self,
        *,
        add_type: Annotated[int, "接口参数：add_type"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"add_type": add_type, "group_id": group_id})


class ApiSetGroupSearch(TypedWrite):
    name = "snowluma_set_group_search"
    description = "直接允许群被搜索。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_group_search"

    async def execute(
        self, *, group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = ""
    ) -> tuple[bool, str | dict]:
        return await self.call({"group_id": group_id})


class ApiSetGroupRobotAddOption(TypedWrite):
    name = "snowluma_set_group_robot_add_option"
    description = "直接设置群机器人加群选项。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_group_robot_add_option"

    async def execute(
        self,
        *,
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
        robot_member_switch: Annotated[bool, "接口参数：robot_member_switch"] = True,
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {"group_id": group_id, "robot_member_switch": robot_member_switch}
        )


class ApiSetGroupKickMembers(TypedWrite):
    name = "snowluma_set_group_kick_members"
    description = "直接批量踢出群成员。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_group_kick_members"

    async def execute(
        self,
        *,
        user_id_list: Annotated[list[int], "接口参数：user_id_list"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
        reject_add_request: Annotated[bool, "接口参数：reject_add_request"] = False,
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {
                "user_id_list": user_id_list,
                "group_id": group_id,
                "reject_add_request": reject_add_request,
            }
        )


class ApiGetGroupShutList(TypedRead):
    name = "snowluma_get_group_shut_list"
    description = "直接获取群禁言列表。直接填写参数即可，无需查询API目录。"
    api_action = "get_group_shut_list"

    async def execute(
        self, *, group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = ""
    ) -> tuple[bool, str | dict]:
        return await self.call({"group_id": group_id})


class ApiGetGroupIgnoredNotifies(TypedRead):
    name = "snowluma_get_group_ignored_notifies"
    description = "直接获取被过滤的入群请求。直接填写参数即可，无需查询API目录。"
    api_action = "get_group_ignored_notifies"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiGetGroupIgnoreAddRequest(TypedRead):
    name = "snowluma_get_group_ignore_add_request"
    description = "直接获取被忽略的入群请求。直接填写参数即可，无需查询API目录。"
    api_action = "get_group_ignore_add_request"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiGetGroupInfoEx(TypedRead):
    name = "snowluma_get_group_info_ex"
    description = "直接获取群信息扩展。直接填写参数即可，无需查询API目录。"
    api_action = "get_group_info_ex"

    async def execute(
        self, *, group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = ""
    ) -> tuple[bool, str | dict]:
        return await self.call({"group_id": group_id})


class ApiGetGroupSignedList(TypedRead):
    name = "snowluma_get_group_signed_list"
    description = "直接获取群今日打卡列表。直接填写参数即可，无需查询API目录。"
    api_action = "get_group_signed_list"

    async def execute(
        self, *, group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = ""
    ) -> tuple[bool, str | dict]:
        return await self.call({"group_id": group_id})


class ApiGetGroupSystemMsg(TypedRead):
    name = "snowluma_get_group_system_msg"
    description = "直接获取群系统消息（OB11标准）。直接填写参数即可，无需查询API目录。"
    api_action = "get_group_system_msg"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiGetDoubtFriendsAddRequest(TypedRead):
    name = "snowluma_get_doubt_friends_add_request"
    description = "直接获取可疑好友申请（扩展）。直接填写参数即可，无需查询API目录。"
    api_action = "get_doubt_friends_add_request"

    async def execute(
        self, *, count: Annotated[int, "条数"] = 20
    ) -> tuple[bool, str | dict]:
        return await self.call({"count": count})


class ApiSetDoubtFriendsAddRequest(TypedWrite):
    name = "snowluma_set_doubt_friends_add_request"
    description = "直接处理可疑好友申请（扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_doubt_friends_add_request"

    async def execute(
        self,
        *,
        flag: Annotated[str, "接口参数：flag"],
        approve: Annotated[bool, "接口参数：approve"] = True,
    ) -> tuple[bool, str | dict]:
        return await self.call({"flag": flag, "approve": approve})


class ApiDeleteFriend(TypedWrite):
    name = "snowluma_delete_friend"
    description = "直接删除好友。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "delete_friend"

    async def execute(
        self,
        *,
        user_id: Annotated[str, "目标QQ号，完整数字字符串"],
        block: Annotated[bool, "接口参数：block"] = False,
    ) -> tuple[bool, str | dict]:
        return await self.call({"user_id": user_id, "block": block})


class ApiSetFriendRemark(TypedWrite):
    name = "snowluma_set_friend_remark"
    description = "直接设置好友备注。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_friend_remark"

    async def execute(
        self,
        *,
        user_id: Annotated[str, "目标QQ号，完整数字字符串"],
        remark: Annotated[str, "接口参数：remark"],
    ) -> tuple[bool, str | dict]:
        return await self.call({"user_id": user_id, "remark": remark})


class ApiGetFriendsWithCategory(TypedRead):
    name = "snowluma_get_friends_with_category"
    description = "直接获取分组好友列表。直接填写参数即可，无需查询API目录。"
    api_action = "get_friends_with_category"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiGetUnidirectionalFriendList(TypedRead):
    name = "snowluma_get_unidirectional_friend_list"
    description = "直接获取单向好友列表。直接填写参数即可，无需查询API目录。"
    api_action = "get_unidirectional_friend_list"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiSetQqProfile(TypedWrite):
    name = "snowluma_set_qq_profile"
    description = "直接设置QQ资料（go-cqhttp 兼容）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_qq_profile"

    async def execute(
        self,
        *,
        nickname: Annotated[str, "接口参数：nickname"] = "",
        personal_note: Annotated[str, "接口参数：personal_note"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"nickname": nickname, "personal_note": personal_note})


class ApiSetQqAvatar(TypedWrite):
    name = "snowluma_set_qq_avatar"
    description = "直接设置QQ头像。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_qq_avatar"

    async def execute(
        self, *, file: Annotated[str, "文件来源，须通过本地允许目录及同主机检查"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"file": file})


class ApiSetSelfLongnick(TypedWrite):
    name = "snowluma_set_self_longnick"
    description = "直接设置个性签名。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_self_longnick"

    async def execute(
        self, *, long_nick: Annotated[str, "接口参数：long_nick"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"long_nick": long_nick})


class ApiGetRecentContact(TypedRead):
    name = "snowluma_get_recent_contact"
    description = "直接获取最近联系人。直接填写参数即可，无需查询API目录。"
    api_action = "get_recent_contact"

    async def execute(
        self, *, count: Annotated[int, "条数"] = 10
    ) -> tuple[bool, str | dict]:
        return await self.call({"count": count})


class ApiGetProfileLike(TypedRead):
    name = "snowluma_get_profile_like"
    description = "直接获取资料点赞。直接填写参数即可，无需查询API目录。"
    api_action = "get_profile_like"

    async def execute(
        self,
        *,
        user_id: Annotated[str, "目标QQ号，完整数字字符串"],
        start: Annotated[int, "接口参数：start"] = 0,
        count: Annotated[int, "条数"] = 10,
    ) -> tuple[bool, str | dict]:
        return await self.call({"user_id": user_id, "start": start, "count": count})


class ApiSetFriendsCategory(TypedWrite):
    name = "snowluma_set_friends_category"
    description = "直接按分类 ID 或名称设置好友分类（SnowLuma 扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_friends_category"

    async def execute(
        self,
        *,
        uin: Annotated[str, "目标QQ号"],
        category_id: Annotated[str | None, "接口参数：category_id"] = None,
        category_name: Annotated[str | None, "接口参数：category_name"] = None,
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {"uin": uin, "category_id": category_id, "category_name": category_name}
        )


class ApiSetOnlineStatus(TypedWrite):
    name = "snowluma_set_online_status"
    description = "直接设置在线状态。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_online_status"

    async def execute(
        self,
        *,
        status: Annotated[int, "平台状态编号"],
        ext_status: Annotated[int, "接口参数：ext_status"] = 0,
        battery_status: Annotated[int, "接口参数：battery_status"] = 0,
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {
                "status": status,
                "ext_status": ext_status,
                "battery_status": battery_status,
            }
        )


class ApiSetDiyOnlineStatus(TypedWrite):
    name = "snowluma_set_diy_online_status"
    description = "直接设置自定义在线状态。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_diy_online_status"

    async def execute(
        self,
        *,
        face_id: Annotated[str, "接口参数：face_id"],
        face_type: Annotated[int, "接口参数：face_type"] = 1,
        wording: Annotated[str, "接口参数：wording"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {"face_id": face_id, "face_type": face_type, "wording": wording}
        )


class ApiSetInputStatus(TypedWrite):
    name = "snowluma_set_input_status"
    description = "直接设置输入状态。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_input_status"

    async def execute(
        self,
        *,
        user_id: Annotated[str, "目标QQ号，完整数字字符串"],
        event_type: Annotated[int, "接口参数：event_type"],
    ) -> tuple[bool, str | dict]:
        return await self.call({"user_id": user_id, "event_type": event_type})


class ApiNcGetUserStatus(TypedWrite):
    name = "snowluma_nc_get_user_status"
    description = "直接获取用户状态。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "nc_get_user_status"

    async def execute(
        self, *, user_id: Annotated[str, "目标QQ号，完整数字字符串"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"user_id": user_id})


class ApiFetchCustomFace(TypedRead):
    name = "snowluma_fetch_custom_face"
    description = "直接获取收藏表情。直接填写参数即可，无需查询API目录。"
    api_action = "fetch_custom_face"

    async def execute(
        self, *, count: Annotated[int, "条数"] = 48
    ) -> tuple[bool, str | dict]:
        return await self.call({"count": count})


class ApiAddCustomFace(TypedWrite):
    name = "snowluma_add_custom_face"
    description = "直接添加收藏表情。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "add_custom_face"

    async def execute(
        self, *, file: Annotated[str, "文件来源，须通过本地允许目录及同主机检查"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"file": file})


class ApiDeleteCustomFace(TypedWrite):
    name = "snowluma_delete_custom_face"
    description = "直接删除收藏表情。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "delete_custom_face"

    async def execute(
        self, *, emoji_id: Annotated[str, "真实表情ID"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"emoji_id": emoji_id})


class ApiModifyCustomFace(TypedWrite):
    name = "snowluma_modify_custom_face"
    description = "直接修改收藏表情备注（SnowLuma 扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "modify_custom_face"

    async def execute(
        self,
        *,
        emoji_id: Annotated[str, "真实表情ID"],
        desc: Annotated[str, "接口参数：desc"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"emoji_id": emoji_id, "desc": desc})


class ApiMoveCustomFaceToFront(TypedWrite):
    name = "snowluma_move_custom_face_to_front"
    description = "直接收藏表情移到最前（SnowLuma 扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "move_custom_face_to_front"

    async def execute(
        self, *, emoji_id: Annotated[str, "真实表情ID"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"emoji_id": emoji_id})


class ApiGetEmojiLikes(TypedRead):
    name = "snowluma_get_emoji_likes"
    description = "直接获取表情回应用户。直接填写参数即可，无需查询API目录。"
    api_action = "get_emoji_likes"

    async def execute(
        self,
        *,
        message_id: Annotated[str, "消息ID，支持平台ID及framework:前缀"],
        emoji_id: Annotated[str, "真实表情ID"],
    ) -> tuple[bool, str | dict]:
        return await self.call({"message_id": message_id, "emoji_id": emoji_id})


class ApiSetGroupReaction(TypedWrite):
    name = "snowluma_set_group_reaction"
    description = "直接群聊消息表情回应（SnowLuma 扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_group_reaction"

    async def execute(
        self,
        *,
        message_id: Annotated[str, "消息ID，支持平台ID及framework:前缀"],
        code: Annotated[str, "接口参数：code"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
        is_set: Annotated[bool, "接口参数：is_set"] = True,
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {
                "message_id": message_id,
                "code": code,
                "group_id": group_id,
                "is_set": is_set,
            }
        )


class ApiFetchFaceEntity(TypedRead):
    name = "snowluma_fetch_face_entity"
    description = (
        "直接获取系统表情实体（SnowLuma 扩展）。直接填写参数即可，无需查询API目录。"
    )
    api_action = "fetch_face_entity"

    async def execute(
        self,
        *,
        face_id: Annotated[str, "接口参数：face_id"],
        refresh: Annotated[bool, "是否刷新"] = False,
    ) -> tuple[bool, str | dict]:
        return await self.call({"face_id": face_id, "refresh": refresh})


class ApiGetAiCharacters(TypedRead):
    name = "snowluma_get_ai_characters"
    description = "直接获取AI语音角色。直接填写参数即可，无需查询API目录。"
    api_action = "get_ai_characters"

    async def execute(
        self,
        *,
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
        chat_type: Annotated[int | None, "接口参数：chat_type"] = None,
    ) -> tuple[bool, str | dict]:
        return await self.call({"group_id": group_id, "chat_type": chat_type})


class ApiGetAiRecord(TypedRead):
    name = "snowluma_get_ai_record"
    description = "直接生成AI语音。直接填写参数即可，无需查询API目录。"
    api_action = "get_ai_record"

    async def execute(
        self,
        *,
        character: Annotated[str, "接口参数：character"],
        text: Annotated[str, "文字"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {"character": character, "text": text, "group_id": group_id}
        )


class ApiSendGroupAiRecord(TypedWrite):
    name = "snowluma_send_group_ai_record"
    description = "直接发送群AI语音。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "send_group_ai_record"

    async def execute(
        self,
        *,
        character: Annotated[str, "接口参数：character"],
        text: Annotated[str, "文字"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {"character": character, "text": text, "group_id": group_id}
        )


class ApiGetModelShow(TypedWrite):
    name = "snowluma_get_model_show"
    description = "直接获取机型展示。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "_get_model_show"

    async def execute(
        self, *, model: Annotated[str, "接口参数：model"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"model": model})


class ApiSetModelShow(TypedWrite):
    name = "snowluma_set_model_show"
    description = "直接设置机型展示。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "_set_model_show"

    async def execute(
        self,
        *,
        model: Annotated[str, "接口参数：model"],
        show: Annotated[str, "接口参数：show"],
    ) -> tuple[bool, str | dict]:
        return await self.call({"model": model, "show": show})


class ApiBotExit(TypedWrite):
    name = "snowluma_bot_exit"
    description = "直接退出机器人。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "bot_exit"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiClickInlineKeyboardButton(TypedWrite):
    name = "snowluma_click_inline_keyboard_button"
    description = "直接点击内联键盘按钮。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "click_inline_keyboard_button"

    async def execute(
        self,
        *,
        bot_appid: Annotated[int, "接口参数：bot_appid"],
        msg_seq: Annotated[int, "接口参数：msg_seq"],
        button_id: Annotated[str, "接口参数：button_id"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {
                "bot_appid": bot_appid,
                "msg_seq": msg_seq,
                "button_id": button_id,
                "group_id": group_id,
            }
        )


class ApiGetMiniAppArk(TypedRead):
    name = "snowluma_get_mini_app_ark"
    description = "直接获取小程序卡片。直接填写参数即可，无需查询API目录。"
    api_action = "get_mini_app_ark"

    async def execute(
        self,
        *,
        type: Annotated[str, "类型"],
        title: Annotated[str, "标题"],
        desc: Annotated[str, "接口参数：desc"],
        pic_url: Annotated[str, "接口参数：pic_url"],
        jump_url: Annotated[str, "接口参数：jump_url"],
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {
                "type": type,
                "title": title,
                "desc": desc,
                "pic_url": pic_url,
                "jump_url": jump_url,
            }
        )


class ApiTranslateEn2Zh(TypedWrite):
    name = "snowluma_translate_en2zh"
    description = "直接英译中。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "translate_en2zh"

    async def execute(
        self, *, words: Annotated[list[str], "接口参数：words"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"words": words})


class ApiCreateCollection(TypedWrite):
    name = "snowluma_create_collection"
    description = "直接创建收藏。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "create_collection"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiGetCollectionList(TypedRead):
    name = "snowluma_get_collection_list"
    description = "直接获取收藏列表。直接填写参数即可，无需查询API目录。"
    api_action = "get_collection_list"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiCreateFlashTask(TypedWrite):
    name = "snowluma_create_flash_task"
    description = "直接创建闪传任务。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "create_flash_task"

    async def execute(
        self,
        *,
        files: Annotated[list[dict[str, Any]], "接口参数：files"],
        name: Annotated[str, "名称"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"files": files, "name": name})


class ApiGetFlashFileList(TypedRead):
    name = "snowluma_get_flash_file_list"
    description = "直接获取闪传文件列表。直接填写参数即可，无需查询API目录。"
    api_action = "get_flash_file_list"

    async def execute(
        self, *, fileset_id: Annotated[str, "接口参数：fileset_id"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"fileset_id": fileset_id})


class ApiGetFlashFileUrl(TypedRead):
    name = "snowluma_get_flash_file_url"
    description = "直接获取闪传文件URL。直接填写参数即可，无需查询API目录。"
    api_action = "get_flash_file_url"

    async def execute(
        self,
        *,
        fileset_id: Annotated[str, "接口参数：fileset_id"],
        file_name: Annotated[str, "接口参数：file_name"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"fileset_id": fileset_id, "file_name": file_name})


class ApiGetShareLink(TypedRead):
    name = "snowluma_get_share_link"
    description = "直接获取文件分享链接。直接填写参数即可，无需查询API目录。"
    api_action = "get_share_link"

    async def execute(
        self, *, fileset_id: Annotated[str, "接口参数：fileset_id"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"fileset_id": fileset_id})


class ApiDownloadFileset(TypedWrite):
    name = "snowluma_download_fileset"
    description = "直接下载文件集。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "download_fileset"

    async def execute(
        self, *, fileset_id: Annotated[str, "接口参数：fileset_id"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"fileset_id": fileset_id})


class ApiGetFilesetInfo(TypedRead):
    name = "snowluma_get_fileset_info"
    description = "直接获取文件集信息。直接填写参数即可，无需查询API目录。"
    api_action = "get_fileset_info"

    async def execute(
        self, *, fileset_id: Annotated[str, "接口参数：fileset_id"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"fileset_id": fileset_id})


class ApiGetFilesetId(TypedRead):
    name = "snowluma_get_fileset_id"
    description = "直接从分享码获取fileset_id。直接填写参数即可，无需查询API目录。"
    api_action = "get_fileset_id"

    async def execute(
        self, *, share_code: Annotated[str, "接口参数：share_code"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"share_code": share_code})


class ApiListFilesets(TypedWrite):
    name = "snowluma_list_filesets"
    description = "直接列出当前账号所有闪传文件集（SnowLuma 扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "list_filesets"

    async def execute(self) -> tuple[bool, str | dict]:
        return await self.call({})


class ApiDeleteFlashFile(TypedWrite):
    name = "snowluma_delete_flash_file"
    description = "直接删除闪传文件（SnowLuma 扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "delete_flash_file"

    async def execute(
        self, *, fileset_id: Annotated[str, "接口参数：fileset_id"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"fileset_id": fileset_id})


class ApiRenameFlashFile(TypedWrite):
    name = "snowluma_rename_flash_file"
    description = "直接重命名闪传文件（SnowLuma 扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "rename_flash_file"

    async def execute(
        self,
        *,
        fileset_id: Annotated[str, "接口参数：fileset_id"],
        new_name: Annotated[str, "接口参数：new_name"],
    ) -> tuple[bool, str | dict]:
        return await self.call({"fileset_id": fileset_id, "new_name": new_name})


class ApiGetQunAlbumList(TypedRead):
    name = "snowluma_get_qun_album_list"
    description = "直接获取群相册列表。直接填写参数即可，无需查询API目录。"
    api_action = "get_qun_album_list"

    async def execute(
        self, *, group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = ""
    ) -> tuple[bool, str | dict]:
        return await self.call({"group_id": group_id})


class ApiUploadImageToQunAlbum(TypedWrite):
    name = "snowluma_upload_image_to_qun_album"
    description = "直接上传图片到群相册。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "upload_image_to_qun_album"

    async def execute(
        self,
        *,
        file: Annotated[str, "文件来源，须通过本地允许目录及同主机检查"],
        album_id: Annotated[str, "群相册ID"],
        album_name: Annotated[str, "群相册名称"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {
                "file": file,
                "album_id": album_id,
                "album_name": album_name,
                "group_id": group_id,
            }
        )


class ApiGetGroupAlbumMediaList(TypedRead):
    name = "snowluma_get_group_album_media_list"
    description = "直接获取群相册媒体列表。直接填写参数即可，无需查询API目录。"
    api_action = "get_group_album_media_list"

    async def execute(
        self,
        *,
        album_id: Annotated[str, "群相册ID"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"album_id": album_id, "group_id": group_id})


class ApiDoGroupAlbumComment(TypedWrite):
    name = "snowluma_do_group_album_comment"
    description = "直接评论群相册。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "do_group_album_comment"

    async def execute(
        self,
        *,
        album_id: Annotated[str, "群相册ID"],
        lloc: Annotated[str, "接口参数：lloc"],
        content: Annotated[str, "内容"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {
                "album_id": album_id,
                "lloc": lloc,
                "content": content,
                "group_id": group_id,
            }
        )


class ApiSetGroupAlbumMediaLike(TypedWrite):
    name = "snowluma_set_group_album_media_like"
    description = "直接点赞群相册。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_group_album_media_like"

    async def execute(
        self,
        *,
        album_id: Annotated[str, "群相册ID"],
        batch_id: Annotated[str, "接口参数：batch_id"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {"album_id": album_id, "batch_id": batch_id, "group_id": group_id}
        )


class ApiCancelGroupAlbumMediaLike(TypedWrite):
    name = "snowluma_cancel_group_album_media_like"
    description = "直接取消点赞群相册。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "cancel_group_album_media_like"

    async def execute(
        self,
        *,
        album_id: Annotated[str, "群相册ID"],
        batch_id: Annotated[str, "接口参数：batch_id"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {"album_id": album_id, "batch_id": batch_id, "group_id": group_id}
        )


class ApiDelGroupAlbumMedia(TypedWrite):
    name = "snowluma_del_group_album_media"
    description = "直接删除群相册媒体。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "del_group_album_media"

    async def execute(
        self,
        *,
        album_id: Annotated[str, "群相册ID"],
        lloc: Annotated[str, "接口参数：lloc"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {"album_id": album_id, "lloc": lloc, "group_id": group_id}
        )


class ApiSetGroupTodo(TypedWrite):
    name = "snowluma_set_group_todo"
    description = "直接设置群待办。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_group_todo"

    async def execute(
        self,
        *,
        message_id: Annotated[str, "消息ID，支持平台ID及framework:前缀"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"message_id": message_id, "group_id": group_id})


class ApiCompleteGroupTodo(TypedWrite):
    name = "snowluma_complete_group_todo"
    description = "直接完成群待办。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "complete_group_todo"

    async def execute(
        self,
        *,
        message_id: Annotated[str, "消息ID，支持平台ID及framework:前缀"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"message_id": message_id, "group_id": group_id})


class ApiCancelGroupTodo(TypedWrite):
    name = "snowluma_cancel_group_todo"
    description = "直接取消群待办。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "cancel_group_todo"

    async def execute(
        self,
        *,
        message_id: Annotated[str, "消息ID，支持平台ID及framework:前缀"],
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"message_id": message_id, "group_id": group_id})


class ApiGetGroupTodoList(TypedRead):
    name = "snowluma_get_group_todo_list"
    description = (
        "直接获取群待办列表（SnowLuma 扩展）。直接填写参数即可，无需查询API目录。"
    )
    api_action = "get_group_todo_list"

    async def execute(
        self, *, group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = ""
    ) -> tuple[bool, str | dict]:
        return await self.call({"group_id": group_id})


class ApiGetQzoneMsgList(TypedRead):
    name = "snowluma_get_qzone_msg_list"
    description = "直接获取QQ空间说说列表。直接填写参数即可，无需查询API目录。"
    api_action = "get_qzone_msg_list"

    async def execute(
        self,
        *,
        pos: Annotated[int, "接口参数：pos"] = 0,
        num: Annotated[int, "接口参数：num"] = 10,
    ) -> tuple[bool, str | dict]:
        return await self.call({"pos": pos, "num": num})


class ApiGetQzoneFeeds(TypedRead):
    name = "snowluma_get_qzone_feeds"
    description = "直接获取QQ空间好友动态。直接填写参数即可，无需查询API目录。"
    api_action = "get_qzone_feeds"

    async def execute(
        self,
        *,
        page_num: Annotated[int, "接口参数：page_num"] = 0,
        count: Annotated[int, "条数"] = 10,
    ) -> tuple[bool, str | dict]:
        return await self.call({"page_num": page_num, "count": count})


class ApiSendQzoneMsg(TypedWrite):
    name = "snowluma_send_qzone_msg"
    description = "直接发表说说（支持纯文字或带图，可设置查看权限）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "send_qzone_msg"

    async def execute(
        self,
        *,
        content: Annotated[str, "内容"],
        images: Annotated[list[str] | None, "接口参数：images"] = None,
        ugc_right: Annotated[int, "接口参数：ugc_right"] = 1,
        target_uins: Annotated[list[int] | None, "接口参数：target_uins"] = None,
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {
                "content": content,
                "images": images,
                "ugc_right": ugc_right,
                "target_uins": target_uins,
            }
        )


class ApiDeleteQzoneMsg(TypedWrite):
    name = "snowluma_delete_qzone_msg"
    description = "直接删除说说。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "delete_qzone_msg"

    async def execute(
        self, *, tid: Annotated[str, "接口参数：tid"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"tid": tid})


class ApiLikeQzone(TypedWrite):
    name = "snowluma_like_qzone"
    description = "直接给说说点赞。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "like_qzone"

    async def execute(
        self,
        *,
        tid: Annotated[str, "接口参数：tid"],
        target_uin: Annotated[int | None, "接口参数：target_uin"] = None,
    ) -> tuple[bool, str | dict]:
        return await self.call({"tid": tid, "target_uin": target_uin})


class ApiUnlikeQzone(TypedWrite):
    name = "snowluma_unlike_qzone"
    description = "直接取消点赞。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "unlike_qzone"

    async def execute(
        self,
        *,
        tid: Annotated[str, "接口参数：tid"],
        target_uin: Annotated[int | None, "接口参数：target_uin"] = None,
    ) -> tuple[bool, str | dict]:
        return await self.call({"tid": tid, "target_uin": target_uin})


class ApiCommentQzone(TypedWrite):
    name = "snowluma_comment_qzone"
    description = "直接评论说说（支持纯文字或带图）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "comment_qzone"

    async def execute(
        self,
        *,
        tid: Annotated[str, "接口参数：tid"],
        content: Annotated[str, "内容"],
        target_uin: Annotated[int | None, "接口参数：target_uin"] = None,
        images: Annotated[list[str] | None, "接口参数：images"] = None,
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {"tid": tid, "content": content, "target_uin": target_uin, "images": images}
        )


class ApiSetQzoneBan(TypedWrite):
    name = "snowluma_set_qzone_ban"
    description = "直接拉黑或解除拉黑某人（机器人自身 QQ 空间黑名单；SnowLuma 扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_qzone_ban"

    async def execute(
        self,
        *,
        user_id: Annotated[str, "目标QQ号，完整数字字符串"],
        enable: Annotated[bool, "是否启用"] = True,
    ) -> tuple[bool, str | dict]:
        return await self.call({"user_id": user_id, "enable": enable})


class ApiSetQzoneMsgRight(TypedWrite):
    name = "snowluma_set_qzone_msg_right"
    description = "直接修改一条已发说说的查看权限（SnowLuma 扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "set_qzone_msg_right"

    async def execute(
        self,
        *,
        tid: Annotated[str, "接口参数：tid"],
        ugc_right: Annotated[int, "接口参数：ugc_right"],
        target_uins: Annotated[list[int] | None, "接口参数：target_uins"] = None,
    ) -> tuple[bool, str | dict]:
        return await self.call(
            {"tid": tid, "ugc_right": ugc_right, "target_uins": target_uins}
        )


class ApiSharePeer(TypedRead):
    name = "snowluma_share_peer"
    description = "直接获取用户/群推荐Ark卡片内容。直接填写参数即可，无需查询API目录。"
    api_action = "share_peer"

    async def execute(
        self,
        *,
        user_id: Annotated[str | None, "目标QQ号，完整数字字符串"] = None,
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"user_id": user_id, "group_id": group_id})


class ApiSendArkShare(TypedRead):
    name = "snowluma_send_ark_share"
    description = "直接获取用户/群推荐Ark卡片内容。直接填写参数即可，无需查询API目录。"
    api_action = "send_ark_share"

    async def execute(
        self,
        *,
        user_id: Annotated[str | None, "目标QQ号，完整数字字符串"] = None,
        group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = "",
    ) -> tuple[bool, str | dict]:
        return await self.call({"user_id": user_id, "group_id": group_id})


class ApiShareGroupEx(TypedRead):
    name = "snowluma_share_group_ex"
    description = "直接获取群推荐Ark卡片内容。直接填写参数即可，无需查询API目录。"
    api_action = "share_group_ex"

    async def execute(
        self, *, group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = ""
    ) -> tuple[bool, str | dict]:
        return await self.call({"group_id": group_id})


class ApiSendGroupArkShare(TypedRead):
    name = "snowluma_send_group_ark_share"
    description = "直接获取群推荐Ark卡片内容。直接填写参数即可，无需查询API目录。"
    api_action = "send_group_ark_share"

    async def execute(
        self, *, group_id: Annotated[str, "目标群号，空为当前群；跨群需授权"] = ""
    ) -> tuple[bool, str | dict]:
        return await self.call({"group_id": group_id})


class ApiGetFriendDress(TypedWrite):
    name = "snowluma_get_friend_dress"
    description = "直接获取指定 QQ 号正在使用的个性装扮（挂件/名片/来电/输入状态等，SnowLuma 扩展）。直接填写参数即可，无需查询API目录。需相应动作/群/操作者授权，保留真实执行审计。"
    api_action = "_get_friend_dress"

    async def execute(
        self, *, user_id: Annotated[str, "目标QQ号，完整数字字符串"]
    ) -> tuple[bool, str | dict]:
        return await self.call({"user_id": user_id})


GENERATED_COMPONENTS = [
    ApiGetForwardMsg,
    ApiMarkMsgAsRead,
    ApiMarkGroupMsgAsRead,
    ApiMarkPrivateMsgAsRead,
    ApiMarkAllAsRead,
    ApiSetGroupAdmin,
    ApiSetGroupLeave,
    ApiSetGroupMemberInvitePolicy,
    ApiSetGroupMemberPermissions,
    ApiSetGroupNewMemberHistoryVisibility,
    ApiGetGroupAdminSettings,
    ApiUploadGroupFile,
    ApiUploadPrivateFile,
    ApiGetFile,
    ApiGetImage,
    ApiGetRecord,
    ApiGetLoginInfo,
    ApiGetStrangerInfo,
    ApiGetFriendList,
    ApiGetGroupList,
    ApiGetGroupDetailInfo,
    ApiGetOnlineClients,
    ApiGetStatus,
    ApiCanSendImage,
    ApiCanSendRecord,
    ApiGetVersionInfo,
    ApiGetGroupAtAllRemain,
    ApiFetchPttText,
    ApiDeleteGroupFile,
    ApiCreateGroupFileFolder,
    ApiDeleteGroupFolder,
    ApiGetGroupFileSystemInfo,
    ApiMoveGroupFile,
    ApiRenameGroupFile,
    ApiRenameGroupFileFolder,
    ApiTransGroupFile,
    ApiSetGroupPortrait,
    ApiSetGroupRemark,
    ApiSetGroupAddOption,
    ApiSetGroupSearch,
    ApiSetGroupRobotAddOption,
    ApiSetGroupKickMembers,
    ApiGetGroupShutList,
    ApiGetGroupIgnoredNotifies,
    ApiGetGroupIgnoreAddRequest,
    ApiGetGroupInfoEx,
    ApiGetGroupSignedList,
    ApiGetGroupSystemMsg,
    ApiGetDoubtFriendsAddRequest,
    ApiSetDoubtFriendsAddRequest,
    ApiDeleteFriend,
    ApiSetFriendRemark,
    ApiGetFriendsWithCategory,
    ApiGetUnidirectionalFriendList,
    ApiSetQqProfile,
    ApiSetQqAvatar,
    ApiSetSelfLongnick,
    ApiGetRecentContact,
    ApiGetProfileLike,
    ApiSetFriendsCategory,
    ApiSetOnlineStatus,
    ApiSetDiyOnlineStatus,
    ApiSetInputStatus,
    ApiNcGetUserStatus,
    ApiFetchCustomFace,
    ApiAddCustomFace,
    ApiDeleteCustomFace,
    ApiModifyCustomFace,
    ApiMoveCustomFaceToFront,
    ApiGetEmojiLikes,
    ApiSetGroupReaction,
    ApiFetchFaceEntity,
    ApiGetAiCharacters,
    ApiGetAiRecord,
    ApiSendGroupAiRecord,
    ApiGetModelShow,
    ApiSetModelShow,
    ApiBotExit,
    ApiClickInlineKeyboardButton,
    ApiGetMiniAppArk,
    ApiTranslateEn2Zh,
    ApiCreateCollection,
    ApiGetCollectionList,
    ApiCreateFlashTask,
    ApiGetFlashFileList,
    ApiGetFlashFileUrl,
    ApiGetShareLink,
    ApiDownloadFileset,
    ApiGetFilesetInfo,
    ApiGetFilesetId,
    ApiListFilesets,
    ApiDeleteFlashFile,
    ApiRenameFlashFile,
    ApiGetQunAlbumList,
    ApiUploadImageToQunAlbum,
    ApiGetGroupAlbumMediaList,
    ApiDoGroupAlbumComment,
    ApiSetGroupAlbumMediaLike,
    ApiCancelGroupAlbumMediaLike,
    ApiDelGroupAlbumMedia,
    ApiSetGroupTodo,
    ApiCompleteGroupTodo,
    ApiCancelGroupTodo,
    ApiGetGroupTodoList,
    ApiGetQzoneMsgList,
    ApiGetQzoneFeeds,
    ApiSendQzoneMsg,
    ApiDeleteQzoneMsg,
    ApiLikeQzone,
    ApiUnlikeQzone,
    ApiCommentQzone,
    ApiSetQzoneBan,
    ApiSetQzoneMsgRight,
    ApiSharePeer,
    ApiSendArkShare,
    ApiShareGroupEx,
    ApiSendGroupArkShare,
    ApiGetFriendDress,
]
