# API 逐项覆盖矩阵

由当前Expand定义自动生成：Expand 1.0.22，220 项主API；加入参考目录额外6项后共 226 项。SnowLuma本地源码 1.14.14。参考full目录声明的1.14.22与本地1.14.14分开记录，未把较新目录当作当前协议支持。

`源码注册`只代表本地注册名称证据，**不是运行实例已支持或真实副作用实测**。所有常用封装复用下列Service，兼容分支见备注。别名在同一行执行相同授权。参数详情以 resources/catalog.json 的arguments/required为实际Plus调用契约；native_parameters用于审计候选，不是完整TypeScript类型推断。

|Action / 别名|类别|源码注册|风险|可访问路径|兼容备注|
|---|---|---|---|---|---|
|`send_group_msg`|message|是|write|snowluma_send（正常框架链路）；通用入口拒绝消息载荷旁路||
|`send_private_msg`|message|是|write|snowluma_send（正常框架链路）；通用入口拒绝消息载荷旁路||
|`send_msg`|message|是|write|snowluma_send（正常框架链路）；通用入口拒绝消息载荷旁路||
|`delete_msg`|message|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_msg`|message|是|read|snowluma_api_read + 原Expand Service||
|`get_forward_msg`|message|是|read|snowluma_api_read + 原Expand Service||
|`send_like`|message|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`send_poke`|message|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`send_forward_msg`|message|是|write|snowluma_send（正常框架链路）；通用入口拒绝消息载荷旁路||
|`send_group_forward_msg`|message|是|write|snowluma_send（正常框架链路）；通用入口拒绝消息载荷旁路||
|`send_private_forward_msg`|message|是|write|snowluma_send（正常框架链路）；通用入口拒绝消息载荷旁路||
|`get_group_msg_history`|message|是|read|snowluma_api_read + 原Expand Service||
|`get_friend_msg_history`|message|是|read|snowluma_api_read + 原Expand Service||
|`forward_friend_single_msg`|message|是|write|snowluma_send（正常框架链路）；通用入口拒绝消息载荷旁路||
|`forward_group_single_msg`|message|是|write|snowluma_send（正常框架链路）；通用入口拒绝消息载荷旁路||
|`mark_msg_as_read`|message|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`mark_group_msg_as_read`|message|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`mark_private_msg_as_read`|message|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`_mark_all_as_read`|message|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`upload_forward_msg` / upload_foward_msg|message|是|write|snowluma_send（正常框架链路）；通用入口拒绝消息载荷旁路||
|`set_group_kick`|group|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_ban`|group|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_anonymous_ban`|group|是|write|Expand明确标记不兼容；保留目录及原Service，不假称可用||
|`set_group_whole_ban`|group|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_admin`|group|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_anonymous`|group|是|write|Expand明确标记不兼容；保留目录及原Service，不假称可用||
|`set_group_card`|group|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_name`|group|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_leave`|group|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_special_title`|group|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_member_invite_policy`|group|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_member_permissions`|group|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_new_member_history_visibility`|group|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_group_admin_settings`|group|是|read|snowluma_api_read + 原Expand Service||
|`upload_group_file`|file|是|write|snowluma_manage（操作者/群/action白名单） + 公开命令兼容|使用公开适配器命令发送已核验同主机的规范路径，避免Expand PathMapper在检查之后重映射为未核验远端路径；普通聊天文件优先snowluma_send|
|`upload_private_file`|file|是|write|snowluma_manage（操作者/群/action白名单） + 公开命令兼容|使用公开适配器命令发送已核验同主机的规范路径，避免Expand PathMapper在检查之后重映射为未核验远端路径；普通聊天文件优先snowluma_send|
|`get_file`|file|是|read|snowluma_api_read + 原Expand Service||
|`get_image`|file|是|read|snowluma_api_read + 原Expand Service||
|`get_record`|file|是|read|snowluma_api_read + 原Expand Service||
|`send_online_file`|file|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`send_online_folder`|file|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`get_online_file_msg`|file|未确认|read|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`receive_online_file`|file|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`refuse_online_file`|file|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`cancel_online_file`|file|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`clean_stream_temp_file`|file|是|stream_unavailable|协议有流式注册；单请求通道不承载多帧，明确拒绝；不伪实现||
|`upload_file_stream`|file|是|stream_unavailable|协议有流式注册；单请求通道不承载多帧，明确拒绝；不伪实现||
|`download_file_stream`|file|是|stream_unavailable|协议有流式注册；单请求通道不承载多帧，明确拒绝；不伪实现||
|`download_file_record_stream`|file|是|stream_unavailable|协议有流式注册；单请求通道不承载多帧，明确拒绝；不伪实现||
|`download_file_image_stream`|file|是|stream_unavailable|协议有流式注册；单请求通道不承载多帧，明确拒绝；不伪实现||
|`get_login_info`|account|是|read|snowluma_api_read + 原Expand Service||
|`get_stranger_info`|account|是|read|snowluma_api_read + 原Expand Service||
|`get_friend_list`|account|是|read|snowluma_api_read + 原Expand Service||
|`get_group_list`|account|是|read|snowluma_api_read + 原Expand Service||
|`get_group_member_list`|account|是|read|snowluma_api_read + 原Expand Service||
|`get_group_member_info`|account|是|read|snowluma_api_read + 原Expand Service||
|`get_group_info`|account|是|read|snowluma_api_read + 原Expand Service||
|`get_group_detail_info`|account|是|read|snowluma_api_read + 原Expand Service||
|`get_group_honor_info`|account|是|read|snowluma_api_read + 原Expand Service||
|`get_robot_uin_range`|account|未确认|read|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`set_msg_emoji_like`|napcat_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_essence_msg_list`|napcat_ext|是|read|snowluma_api_read + 原Expand Service||
|`get_online_clients`|napcat_ext|是|read|snowluma_api_read + 原Expand Service||
|`get_cookies`|napcat_ext|是|blocked|保留原Expand Service给可信插件；不向LLM暴露凭证/进程/原始包||
|`get_csrf_token`|napcat_ext|是|blocked|保留原Expand Service给可信插件；不向LLM暴露凭证/进程/原始包||
|`get_status`|napcat_ext|是|read|snowluma_api_read + 原Expand Service||
|`set_restart`|napcat_ext|是|blocked|保留原Expand Service给可信插件；不向LLM暴露凭证/进程/原始包||
|`clean_cache`|napcat_ext|是|blocked|保留原Expand Service给可信插件；不向LLM暴露凭证/进程/原始包||
|`can_send_image`|napcat_ext|是|read|snowluma_api_read + 原Expand Service||
|`can_send_record`|napcat_ext|是|read|snowluma_api_read + 原Expand Service||
|`get_version_info`|napcat_ext|是|read|snowluma_api_read + 原Expand Service||
|`set_essence_msg`|napcat_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`delete_essence_msg`|napcat_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_group_at_all_remain`|napcat_ext|是|read|snowluma_api_read + 原Expand Service||
|`fetch_ptt_text` / get_ptt_text, get_record_text, voice_msg_to_text|napcat_ext|是|read|snowluma_api_read + 原Expand Service||
|`get_group_file_url`|group_file|是|read|snowluma_api_read + 原Expand Service||
|`get_group_root_files`|group_file|是|read|snowluma_api_read + 原Expand Service||
|`get_group_files_by_folder`|group_file|是|read|snowluma_api_read + 原Expand Service||
|`delete_group_file`|group_file|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`create_group_file_folder`|group_file|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`delete_group_folder` / delete_group_file_folder|group_file|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_group_file_system_info`|group_file|是|read|snowluma_api_read + 原Expand Service||
|`move_group_file`|group_file|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`rename_group_file`|group_file|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`rename_group_file_folder`|group_file|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`trans_group_file`|group_file|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_private_file_url`|group_file|是|read|snowluma_api_read + 原Expand Service||
|`_send_group_notice`|group_notice|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`_get_group_notice`|group_notice|是|read|snowluma_api_read + 原Expand Service||
|`_del_group_notice` / _delete_group_notice|group_notice|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_portrait`|group_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_remark`|group_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_add_option`|group_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_search`|group_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_robot_add_option`|group_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_kick_members`|group_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_group_shut_list`|group_ext|是|read|snowluma_api_read + 原Expand Service||
|`get_group_ignored_notifies`|group_ext|是|read|snowluma_api_read + 原Expand Service||
|`get_group_ignore_add_request`|group_ext|是|read|snowluma_api_read + 原Expand Service||
|`get_group_info_ex`|group_ext|是|read|snowluma_api_read + 原Expand Service||
|`get_group_share_link`|group_ext|未确认|read|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`set_group_sign` / send_group_sign|group_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_group_signed_list`|group_ext|是|read|snowluma_api_read + 原Expand Service||
|`set_friend_add_request`|request|是|approval_only|snowluma_requests / snowluma_approve；通用入口拒绝flag||
|`set_group_add_request`|request|是|approval_only|snowluma_requests / snowluma_approve；通用入口拒绝flag||
|`get_group_system_msg`|request|是|read|snowluma_api_read + 原Expand Service||
|`get_doubt_friends_add_request`|request|是|read|snowluma_api_read + 原Expand Service||
|`set_doubt_friends_add_request`|request|是|write|snowluma_requests / snowluma_approve；通用入口拒绝flag||
|`delete_friend`|user_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_friend_remark`|user_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_friends_with_category`|user_ext|是|read|snowluma_api_read + 原Expand Service||
|`get_unidirectional_friend_list`|user_ext|是|read|snowluma_api_read + 原Expand Service||
|`set_qq_profile`|user_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_qq_avatar`|user_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_self_longnick`|user_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_recent_contact`|user_ext|是|read|snowluma_api_read + 原Expand Service||
|`get_profile_like`|user_ext|是|read|snowluma_api_read + 原Expand Service||
|`set_friends_category`|user_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_online_status`|status|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_diy_online_status`|status|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_input_status`|status|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`nc_get_user_status`|status|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`friend_poke`|poke|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`group_poke`|poke|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`fetch_custom_face`|emoji_ext|是|read|snowluma_api_read + 原Expand Service||
|`add_custom_face`|emoji_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`delete_custom_face`|emoji_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`fetch_custom_face_detail`|emoji_ext|是|read|snowluma_api_read + 原Expand Service||
|`set_custom_face_desc`|emoji_ext|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`modify_custom_face`|emoji_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`move_custom_face_to_front`|emoji_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`fetch_emoji_like`|emoji_ext|是|read|snowluma_api_read + 公开命令兼容|公共Service缺少cookie且将emojiId写为emoji_id；Plus通过公开适配器命令最小兼容，cursor为分页游标，非账号Cookie|
|`get_emoji_likes`|emoji_ext|是|read|snowluma_api_read + 原Expand Service||
|`get_msg_emoji_likes`|emoji_ext|是|read|snowluma_api_read + 原Expand Service||
|`set_group_reaction`|emoji_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`fetch_sys_faces`|emoji_ext|是|read|snowluma_api_read + 原Expand Service||
|`fetch_face_entity`|emoji_ext|是|read|snowluma_api_read + 原Expand Service||
|`search_sys_faces`|emoji_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`fetch_super_face_id`|emoji_ext|是|read|snowluma_api_read + 原Expand Service||
|`get_ai_characters`|ai_voice|是|read|snowluma_api_read + 原Expand Service||
|`get_ai_record`|ai_voice|是|read|snowluma_api_read + 原Expand Service||
|`send_group_ai_record`|ai_voice|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_clientkey`|cred|是|blocked|保留原Expand Service给可信插件；不向LLM暴露凭证/进程/原始包||
|`get_credentials`|cred|是|blocked|保留原Expand Service给可信插件；不向LLM暴露凭证/进程/原始包||
|`get_rkey` / nc_get_rkey|cred|是|blocked|保留原Expand Service给可信插件；不向LLM暴露凭证/进程/原始包||
|`get_rkey_server`|cred|是|blocked|保留原Expand Service给可信插件；不向LLM暴露凭证/进程/原始包||
|`check_url_safely`|cred|是|blocked|保留原Expand Service给可信插件；不向LLM暴露凭证/进程/原始包||
|`ocr_image` / .ocr_image|cred|是|blocked|保留原Expand Service给可信插件；不向LLM暴露凭证/进程/原始包||
|`download_file`|cred|是|blocked|保留原Expand Service给可信插件；不向LLM暴露凭证/进程/原始包||
|`request_decrypt_key`|cred|是|blocked|保留原Expand Service给可信插件；不向LLM暴露凭证/进程/原始包||
|`_get_model_show` / ._get_model_show|misc|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`_set_model_show` / ._set_model_show|misc|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`bot_exit`|misc|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`nc_get_packet_status`|misc|是|blocked|保留原Expand Service给可信插件；不向LLM暴露凭证/进程/原始包||
|`click_inline_keyboard_button`|misc|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_mini_app_ark`|misc|是|read|snowluma_api_read + 原Expand Service||
|`translate_en2zh`|misc|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`create_collection`|misc|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_collection_list`|misc|是|read|snowluma_api_read + 原Expand Service||
|`send_packet` / .send_packet|misc|是|blocked|保留原Expand Service给可信插件；不向LLM暴露凭证/进程/原始包||
|`send_pb`|misc|未确认|blocked|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`handle_quick_operation` / .handle_quick_operation|misc|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`get_word_slices` / .get_word_slices|misc|未确认|read|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`create_flash_task`|flash|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`send_flash_msg`|flash|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_flash_file_list`|flash|是|read|snowluma_api_read + 原Expand Service||
|`get_flash_file_url`|flash|是|read|snowluma_api_read + 原Expand Service||
|`get_share_link`|flash|是|read|snowluma_api_read + 原Expand Service||
|`download_fileset` / download_flash_file|flash|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_fileset_info` / get_flash_file_info|flash|是|read|snowluma_api_read + 原Expand Service||
|`get_fileset_id`|flash|是|read|snowluma_api_read + 原Expand Service||
|`list_filesets`|flash|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`delete_flash_file`|flash|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`rename_flash_file`|flash|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_qun_album_list` / get_group_album_list|group_album|是|read|snowluma_api_read + 原Expand Service||
|`upload_image_to_qun_album` / upload_group_album|group_album|是|write|snowluma_manage（操作者/群/action白名单） + 公开命令兼容|公共Service缺少SnowLuma必填album_name；Plus通过公开适配器命令补齐，不修改Expand响应契约|
|`get_group_album_media_list`|group_album|是|read|snowluma_api_read + 原Expand Service||
|`do_group_album_comment`|group_album|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_album_media_like`|group_album|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`cancel_group_album_media_like`|group_album|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`del_group_album_media`|group_album|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_group_todo`|group_todo|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`complete_group_todo`|group_todo|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`cancel_group_todo`|group_todo|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_group_todo_list`|group_todo|是|read|snowluma_api_read + 原Expand Service||
|`get_qzone_msg_list`|qzone|是|read|snowluma_api_read + 原Expand Service||
|`get_qzone_feeds`|qzone|是|read|snowluma_api_read + 原Expand Service||
|`send_qzone_msg`|qzone|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`delete_qzone_msg`|qzone|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`like_qzone`|qzone|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`unlike_qzone`|qzone|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`comment_qzone`|qzone|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_qzone_ban`|qzone|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`set_qzone_msg_right`|qzone|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`share_peer`|ark|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`send_ark_share`|ark|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`share_group_ex`|ark|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`send_group_ark_share`|ark|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`send_tuwen_ark`|ark|是|write|原Expand ark_service供可信插件；Plus拒绝原始旁路消息发送，普通分享使用snowluma_send||
|`batch_delete_group_member`|group_ext|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`set_group_msg_mask`|group_ext|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`create_group_album`|group_album|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`delete_group_album`|group_album|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`get_flash_file_download_urls`|flash|未确认|read|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`upload_flash_file`|flash|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`reshare_flash_file`|flash|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`set_group_file_forever`|group_file|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`get_profile_like_me`|user_ext|未确认|read|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`get_profile_like_count`|user_ext|未确认|read|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`get_qq_avatar`|user_ext|未确认|read|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`set_friend_category`|user_ext|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`_get_friend_dress`|user_ext|是|write|snowluma_manage（操作者/群/action白名单） + 原Expand Service||
|`get_recommend_face`|emoji_ext|未确认|read|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`unset_msg_emoji_like`|emoji_ext|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`get_config`|misc|未确认|read|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`set_config`|misc|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`get_event`|misc|未确认|read|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`llonebot_debug`|misc|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`scan_qrcode`|misc|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`get_guild_list`|misc|未确认|read|当前源码未注册；自动调用拒绝（非运行实例实测）||
|`test_download_stream`|流式接口|是|stream_unavailable|协议有流式注册；单请求通道不承载多帧，明确拒绝；不伪实现|参考目录版本1.14.22；当前本地源码1.14.14必须另行确认注册。Expand无Service时才使用公开适配器命令。|
|`send_custom_face`|消息|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）|参考目录版本1.14.22；当前本地源码1.14.14必须另行确认注册。Expand无Service时才使用公开适配器命令。|
|`upload_video_to_qun_album`|群相册|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）|参考目录版本1.14.22；当前本地源码1.14.14必须另行确认注册。Expand无Service时才使用公开适配器命令。|
|`add_group_tag`|群管理|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）|参考目录版本1.14.22；当前本地源码1.14.14必须另行确认注册。Expand无Service时才使用公开适配器命令。|
|`delete_group_tag`|群管理|未确认|write|当前源码未注册；自动调用拒绝（非运行实例实测）|参考目录版本1.14.22；当前本地源码1.14.14必须另行确认注册。Expand无Service时才使用公开适配器命令。|
|`get_group_tags`|群管理|未确认|read|当前源码未注册；自动调用拒绝（非运行实例实测）|参考目录版本1.14.22；当前本地源码1.14.14必须另行确认注册。Expand无Service时才使用公开适配器命令。|

目录源码摘要：

- Expand api_defs SHA256：`672c0e01aefff5cd705b8aab6ddc8c69569183b27b2a460c87cf269412dd3592`
- SnowLuma actions源码合集 SHA256：`14177bc893881f454e091ade535ed910e8fe3397de33c73497e8decc13e96752`
- 生成命令：`.venv/Scripts/python.exe plugins/snowluma_plus/scripts/generate_catalog.py`。当前生成器只执行已审计的本地Expand纯定义文件，不导入其他插件运行时。
