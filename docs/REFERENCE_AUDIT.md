# 固定版本参考审计

审计日：2026-10-21。下表是源码核对；未向QQ生产对象写入。代码实现独立编写，未复制参考插件实现。目录元数据的许可见 THIRD_PARTY_NOTICES.md。

## [Windpicker-owo/napcat_extension](https://github.com/Windpicker-owo/napcat_extension/tree/7c3c5a3712091eb78bfa0c9b07861fd7dac47912)

版本 `1.0.1`；commit `7c3c5a3712091eb78bfa0c9b07861fd7dac47912`；manifest许可 `未声明/无许可文件，不复制实现`；许可文件 未发现；Python测试/检查文件 0 个。未运行其独立完整测试套件；当前安装Expand的相关回归另见验证报告。

|原组件|Plus去向/限制|
|---|---|
|`config:config`|SnowLumaConfig（按业务组织，不复制旧配置）|
|`action:mute_group_member`|snowluma_manage / set_group_ban|
|`action:unmute_group_member`|snowluma_manage / set_group_ban duration=0|
|`action:react_to_message`|snowluma_manage / set_msg_emoji_like；snowluma_messages 查询|
|`action:poke_group_member`|snowluma_manage / group_poke 或 send_poke|
|`action:recall_message`|snowluma_manage / delete_msg（必须核实消息范围）|
|`action:group_sign`|snowluma_checkin；共用手动/计划/补打记录|
|`action:kick_group_member`|snowluma_manage / set_group_kick|
|`action:send_file`|snowluma_send kind=file；规范路径/大小/类型限制|
|`tool:save_message_file`|snowluma_files / get_file 获取链接；不自动下载任意远端文件到本机|

源码核对包括 manifest、配置声明、注册入口、动作/工具/事件实现，以及仓库可见的测试/检查文件。配置不迁移为生产授权；所有旧owner逻辑由独立操作者/群/action策略替代。

## [fuilyha56-wq/onebot_expand](https://github.com/fuilyha56-wq/onebot_expand/tree/8e7d9436d266751bbf4694fb9e87da8ec8eeed4d)

版本 `1.0.21`；commit `8e7d9436d266751bbf4694fb9e87da8ec8eeed4d`；manifest许可 `AGPL-3.0`；许可文件 LICENSE；Python测试/检查文件 10 个。未运行其独立完整测试套件；当前安装Expand的相关回归另见验证报告。

|原组件|Plus去向/限制|
|---|---|
|`service:message_service`|保留 `message_service` 原响应契约；20 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:group_service`|保留 `group_service` 原响应契约；14 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:file_service`|保留 `file_service` 原响应契约；16 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:account_service`|保留 `account_service` 原响应契约；9 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:napcat_ext_service`|保留 `napcat_ext_service` 原响应契约；14 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:emoji_service`|保留 `emoji_service` 原响应契约；0 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:path_mapper_service`|保留 `path_mapper_service` 原响应契约；0 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:group_file_service`|保留 `group_file_service` 原响应契约；13 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:group_notice_service`|保留 `group_notice_service` 原响应契约；3 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:group_ext_service`|保留 `group_ext_service` 原响应契约；15 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:request_service`|保留 `request_service` 原响应契约；5 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:user_ext_service`|保留 `user_ext_service` 原响应契约；15 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:status_service`|保留 `status_service` 原响应契约；4 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:poke_service`|保留 `poke_service` 原响应契约；2 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:emoji_ext_service`|保留 `emoji_ext_service` 原响应契约；17 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:ai_voice_service`|保留 `ai_voice_service` 原响应契约；3 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:cred_service`|保留 `cred_service` 原响应契约；8 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:misc_service`|保留 `misc_service` 原响应契约；19 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:flash_service`|保留 `flash_service` 原响应契约；14 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:group_album_service`|保留 `group_album_service` 原响应契约；9 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:group_todo_service`|保留 `group_todo_service` 原响应契约；4 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:qzone_service`|保留 `qzone_service` 原响应契约；11 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|
|`service:ark_service`|保留 `ark_service` 原响应契约；5 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力|

源码核对包括 manifest、配置声明、注册入口、动作/工具/事件实现，以及仓库可见的测试/检查文件。配置不迁移为生产授权；所有旧owner逻辑由独立操作者/群/action策略替代。

## [tt-P607/snowluma_extension](https://github.com/tt-P607/snowluma_extension/tree/6c3907b8f691c11529acc0d67bf354769b1dd717)

版本 `1.0.13`；commit `6c3907b8f691c11529acc0d67bf354769b1dd717`；manifest许可 `AGPL-3.0`；许可文件 未发现；Python测试/检查文件 0 个。未运行其独立完整测试套件；当前安装Expand的相关回归另见验证报告。

|原组件|Plus去向/限制|
|---|---|
|`config:config`|SnowLumaConfig（按业务组织，不复制旧配置）|
|`action:mute_group_member`|snowluma_manage / set_group_ban|
|`action:unmute_group_member`|snowluma_manage / set_group_ban duration=0|
|`action:set_group_whole_ban`|snowluma_manage / set_group_whole_ban|
|`action:react_to_message`|snowluma_manage / set_msg_emoji_like；snowluma_messages 查询|
|`action:poke_group_member`|snowluma_manage / group_poke 或 send_poke|
|`action:recall_message`|snowluma_manage / delete_msg（必须核实消息范围）|
|`action:send_share_card`|snowluma_send kind=share；框架 contact 段|
|`action:group_sign`|snowluma_checkin；共用手动/计划/补打记录|
|`action:kick_group_member`|snowluma_manage / set_group_kick|
|`action:set_group_name`|snowluma_manage / set_group_name|
|`action:set_group_card`|snowluma_manage / set_group_card|
|`action:set_group_special_title`|snowluma_manage / set_group_special_title|
|`action:send_group_notice`|snowluma_manage / _send_group_notice；共享公告基线|
|`action:delete_group_notice`|snowluma_manage / _del_group_notice；共享公告基线|
|`action:send_group_forward_msg`|snowluma_send kind=forward；框架发送器和历史|
|`action:set_essence_msg`|snowluma_manage / set_essence_msg|
|`action:delete_essence_msg`|snowluma_manage / delete_essence_msg|
|`action:forward_group_single_msg`|snowluma_send kind=forward（当前群，授权范围）|
|`action:forward_friend_single_msg`|snowluma_send kind=forward（当前私聊）|
|`action:send_like`|snowluma_manage / send_like（默认关闭）|
|`tool:get_group_member_info`|snowluma_group view=member；真实ID/昵称/名片/头衔|
|`tool:get_group_info`|snowluma_group view=overview|
|`tool:get_group_member_list`|snowluma_group view=member；分页搜索|
|`tool:refresh_group_members`|snowluma_group view=member refresh=true；并发合并|
|`tool:get_group_notice`|snowluma_notices（列表/ID详情/搜索）|
|`tool:get_qq_face_list`|snowluma_emoji（原生/超级/收藏分别查询）|
|`tool:get_essence_msg_list`|snowluma_messages view=essence|
|`tool:get_group_honor_info`|snowluma_group view=honor；身份提醒仅放Bot荣誉|
|`tool:get_group_shut_list`|snowluma_api_read / get_group_shut_list|
|`tool:get_bot_messages`|snowluma_messages view=bot_recent；最近协议页并非完整历史|
|`event_handler:face_intercept_handler`|改用显式 snowluma_send kind=face，不重写普通文本/代码/JSON，不二次解析旧标记|
|`event_handler:bot_role_reminder_handler`|后台身份/荣誉缓存 + 两类Chatter真实上下文入口|
|`event_handler:group_members_reminder_handler`|TTL成员索引 + 有预算的24小时活跃成员提醒，不常驻全群名单|
|`action:handle_group_join_request`|snowluma_approve；内部request_id绑定flag、类型和状态|
|`tool:get_group_join_requests`|snowluma_requests；仅已到达真实请求，无法凭日志恢复历史flag|

源码核对包括 manifest、配置声明、注册入口、动作/工具/事件实现，以及仓库可见的测试/检查文件。配置不迁移为生产授权；所有旧owner逻辑由独立操作者/群/action策略替代。

## [xianshu-virtuous/snowluma_full](https://github.com/xianshu-virtuous/snowluma_full/tree/6c3482c3806aa0228e5233eb25cb1a0616634a32)

版本 `0.3.0`；commit `6c3482c3806aa0228e5233eb25cb1a0616634a32`；manifest许可 `MIT`；许可文件 LICENSE；Python测试/检查文件 4 个。未运行其独立完整测试套件；当前安装Expand的相关回归另见验证报告。

|原组件|Plus去向/限制|
|---|---|
|`event_handler:catalog`|固定紧凑组件 + snowluma_api_catalog 分页发现|
|`event_handler:fold`|固定紧凑组件和有预算分页，不更改其他插件工具或缓存，无跨会话展开状态|
|`tool:sl_help`|snowluma_api_catalog（目录、参数、风险、兼容性）|
|`tool:sl_use`|snowluma_api_catalog 分页发现；执行层每次重新授权|
|`tool:sl_requests`|snowluma_requests / snowluma_approve|
|`tool:sl_qzone_read`|snowluma_api_catalog + snowluma_api_read / qzone Service|
|`tool:sl_group_file_list`|snowluma_files；目录/搜索/链接|
|`tool:sl_events`|snowluma_status view=events/event/search；未知字段可检索|
|`tool:sl_user_info`|snowluma_group 或 snowluma_api_read / get_stranger_info（受作用域限制）|
|`tool:sl_msg_history`|snowluma_messages view=history/detail/bot_recent|
|`action:sl_call`|snowluma_api_read + snowluma_manage；凭证/审批/流式有独立边界|
|`action:sl_qzone_post`|snowluma_manage / publish_qzone_detail（明确白名单，默认关闭）|
|`action:sl_qzone_interact`|snowluma_manage / 对应qzone action；不启动新自动互动引擎|
|`action:sl_group_file_upload`|snowluma_send kind=file；目录上传使用已审计的同主机公开命令兼容|
|`action:sl_poke`|snowluma_manage / group_poke 或 friend_poke|
|`action:sl_reaction`|snowluma_manage / set_msg_emoji_like|
|`action:sl_recall`|snowluma_manage / delete_msg|
|`action:sl_essence`|snowluma_messages view=essence + snowluma_manage 设置/移除|
|`action:sl_group_ban`|snowluma_manage / set_group_ban|
|`action:sl_group_whole_ban`|snowluma_manage / set_group_whole_ban|
|`action:sl_group_kick`|snowluma_manage / set_group_kick|
|`action:sl_group_card`|snowluma_manage / set_group_card|
|`action:sl_group_name`|snowluma_manage / set_group_name|

源码核对包括 manifest、配置声明、注册入口、动作/工具/事件实现，以及仓库可见的测试/检查文件。配置不迁移为生产授权；所有旧owner逻辑由独立操作者/群/action策略替代。

