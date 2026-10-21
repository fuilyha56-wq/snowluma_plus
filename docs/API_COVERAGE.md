# API 逐项覆盖矩阵

由当前Expand定义自动生成：Expand 1.0.22，220 项主API；加入参考目录额外6项后共 226 项。SnowLuma本地源码 1.14.14。参考full目录声明的1.14.22与本地1.14.14分开记录，未把较新目录当作当前协议支持。

`源码注册`只代表本地注册名称证据，**不是运行实例已支持或真实副作用实测**。所有常用封装复用下列Service，兼容分支见备注。别名在同一行执行相同授权。参数详情以 resources/catalog.json 的arguments/required为实际Plus调用契约；native_parameters用于审计候选，不是完整TypeScript类型推断。

|Action / 别名|类别|源码注册|风险|可访问路径|兼容备注|
|---|---|---|---|---|---|
|`send_group_msg`|message|是|write|snowluma_send_text / snowluma_send_face / snowluma_reply_message / 媒体发送组件||
|`send_private_msg`|message|是|write|snowluma_send_text / snowluma_send_face / snowluma_reply_message / 媒体发送组件||
|`send_msg`|message|是|write|snowluma_send_text / snowluma_send_face / snowluma_reply_message / 媒体发送组件||
|`delete_msg`|message|是|write|snowluma_recall_message||
|`get_msg`|message|是|read|snowluma_message_detail||
|`get_forward_msg`|message|是|read|snowluma_get_forward_msg||
|`send_like`|message|是|write|snowluma_profile_like||
|`send_poke`|message|是|write|snowluma_poke||
|`send_forward_msg`|message|是|write|snowluma_forward_messages（框架正常发送）||
|`send_group_forward_msg`|message|是|write|snowluma_forward_messages（框架正常发送）||
|`send_private_forward_msg`|message|是|write|snowluma_forward_messages（框架正常发送）||
|`get_group_msg_history`|message|是|read|snowluma_message_history||
|`get_friend_msg_history`|message|是|read|snowluma_message_history||
|`forward_friend_single_msg`|message|是|write|snowluma_forward_messages（框架正常发送）||
|`forward_group_single_msg`|message|是|write|snowluma_forward_messages（框架正常发送）||
|`mark_msg_as_read`|message|是|write|snowluma_mark_msg_as_read||
|`mark_group_msg_as_read`|message|是|write|snowluma_mark_group_msg_as_read||
|`mark_private_msg_as_read`|message|是|write|snowluma_mark_private_msg_as_read||
|`_mark_all_as_read`|message|是|write|snowluma_mark_all_as_read||
|`upload_forward_msg` / upload_foward_msg|message|是|write|snowluma_forward_messages（框架正常发送）||
|`set_group_kick`|group|是|write|snowluma_kick_member||
|`set_group_ban`|group|是|write|snowluma_mute_member / snowluma_unmute_member||
|`set_group_anonymous_ban`|group|是|write|当前审计源码未确认支持||
|`set_group_whole_ban`|group|是|write|snowluma_whole_group_mute||
|`set_group_admin`|group|是|write|snowluma_set_group_admin||
|`set_group_anonymous`|group|是|write|当前审计源码未确认支持||
|`set_group_card`|group|是|write|snowluma_set_member_card||
|`set_group_name`|group|是|write|snowluma_rename_group||
|`set_group_leave`|group|是|write|snowluma_set_group_leave||
|`set_group_special_title`|group|是|write|snowluma_set_member_title||
|`set_group_member_invite_policy`|group|是|write|snowluma_set_group_member_invite_policy||
|`set_group_member_permissions`|group|是|write|snowluma_set_group_member_permissions||
|`set_group_new_member_history_visibility`|group|是|write|snowluma_set_group_new_member_history_visibility||
|`get_group_admin_settings`|group|是|read|snowluma_get_group_admin_settings||
|`upload_group_file`|file|是|write|snowluma_upload_group_file|使用公开适配器命令发送已核验同主机的规范路径，避免Expand PathMapper在检查之后重映射为未核验远端路径；普通聊天文件优先snowluma_send|
|`upload_private_file`|file|是|write|snowluma_upload_private_file|使用公开适配器命令发送已核验同主机的规范路径，避免Expand PathMapper在检查之后重映射为未核验远端路径；普通聊天文件优先snowluma_send|
|`get_file`|file|是|read|snowluma_get_file||
|`get_image`|file|是|read|snowluma_get_image||
|`get_record`|file|是|read|snowluma_get_record||
|`send_online_file`|file|未确认|write|当前审计源码未确认支持||
|`send_online_folder`|file|未确认|write|当前审计源码未确认支持||
|`get_online_file_msg`|file|未确认|read|当前审计源码未确认支持||
|`receive_online_file`|file|未确认|write|当前审计源码未确认支持||
|`refuse_online_file`|file|未确认|write|当前审计源码未确认支持||
|`cancel_online_file`|file|未确认|write|当前审计源码未确认支持||
|`clean_stream_temp_file`|file|是|stream_unavailable|stream_unavailable||
|`upload_file_stream`|file|是|stream_unavailable|stream_unavailable||
|`download_file_stream`|file|是|stream_unavailable|stream_unavailable||
|`download_file_record_stream`|file|是|stream_unavailable|stream_unavailable||
|`download_file_image_stream`|file|是|stream_unavailable|stream_unavailable||
|`get_login_info`|account|是|read|snowluma_get_login_info||
|`get_stranger_info`|account|是|read|snowluma_get_stranger_info||
|`get_friend_list`|account|是|read|snowluma_get_friend_list||
|`get_group_list`|account|是|read|snowluma_get_group_list||
|`get_group_member_list`|account|是|read|snowluma_find_member||
|`get_group_member_info`|account|是|read|snowluma_find_member / snowluma_bot_identity||
|`get_group_info`|account|是|read|snowluma_group_info||
|`get_group_detail_info`|account|是|read|snowluma_get_group_detail_info||
|`get_group_honor_info`|account|是|read|snowluma_group_honor||
|`get_robot_uin_range`|account|未确认|read|当前审计源码未确认支持||
|`set_msg_emoji_like`|napcat_ext|是|write|snowluma_react_message||
|`get_essence_msg_list`|napcat_ext|是|read|snowluma_list_essence||
|`get_online_clients`|napcat_ext|是|read|snowluma_get_online_clients||
|`get_cookies`|napcat_ext|是|blocked|blocked||
|`get_csrf_token`|napcat_ext|是|blocked|blocked||
|`get_status`|napcat_ext|是|read|snowluma_get_status||
|`set_restart`|napcat_ext|是|blocked|blocked||
|`clean_cache`|napcat_ext|是|blocked|blocked||
|`can_send_image`|napcat_ext|是|read|snowluma_can_send_image||
|`can_send_record`|napcat_ext|是|read|snowluma_can_send_record||
|`get_version_info`|napcat_ext|是|read|snowluma_get_version_info||
|`set_essence_msg`|napcat_ext|是|write|snowluma_set_essence||
|`delete_essence_msg`|napcat_ext|是|write|snowluma_remove_essence||
|`get_group_at_all_remain`|napcat_ext|是|read|snowluma_get_group_at_all_remain||
|`fetch_ptt_text` / get_ptt_text, get_record_text, voice_msg_to_text|napcat_ext|是|read|snowluma_fetch_ptt_text||
|`get_group_file_url`|group_file|是|read|snowluma_file_url||
|`get_group_root_files`|group_file|是|read|snowluma_list_files||
|`get_group_files_by_folder`|group_file|是|read|snowluma_list_files||
|`delete_group_file`|group_file|是|write|snowluma_delete_group_file||
|`create_group_file_folder`|group_file|是|write|snowluma_create_group_file_folder||
|`delete_group_folder` / delete_group_file_folder|group_file|是|write|snowluma_delete_group_folder||
|`get_group_file_system_info`|group_file|是|read|snowluma_get_group_file_system_info||
|`move_group_file`|group_file|是|write|snowluma_move_group_file||
|`rename_group_file`|group_file|是|write|snowluma_rename_group_file||
|`rename_group_file_folder`|group_file|是|write|snowluma_rename_group_file_folder||
|`trans_group_file`|group_file|是|write|snowluma_trans_group_file||
|`get_private_file_url`|group_file|是|read|snowluma_file_url||
|`_send_group_notice`|group_notice|是|write|snowluma_publish_notice||
|`_get_group_notice`|group_notice|是|read|snowluma_list_notices||
|`_del_group_notice` / _delete_group_notice|group_notice|是|write|snowluma_delete_notice||
|`set_group_portrait`|group_ext|是|write|snowluma_set_group_portrait||
|`set_group_remark`|group_ext|是|write|snowluma_set_group_remark||
|`set_group_add_option`|group_ext|是|write|snowluma_set_group_add_option||
|`set_group_search`|group_ext|是|write|snowluma_set_group_search||
|`set_group_robot_add_option`|group_ext|是|write|snowluma_set_group_robot_add_option||
|`set_group_kick_members`|group_ext|是|write|snowluma_set_group_kick_members||
|`get_group_shut_list`|group_ext|是|read|snowluma_get_group_shut_list||
|`get_group_ignored_notifies`|group_ext|是|read|snowluma_get_group_ignored_notifies||
|`get_group_ignore_add_request`|group_ext|是|read|snowluma_get_group_ignore_add_request||
|`get_group_info_ex`|group_ext|是|read|snowluma_get_group_info_ex||
|`get_group_share_link`|group_ext|未确认|read|当前审计源码未确认支持||
|`set_group_sign` / send_group_sign|group_ext|是|write|snowluma_checkin||
|`get_group_signed_list`|group_ext|是|read|snowluma_get_group_signed_list||
|`set_friend_add_request`|request|是|approval_only|approval_only||
|`set_group_add_request`|request|是|approval_only|approval_only||
|`get_group_system_msg`|request|是|read|snowluma_get_group_system_msg||
|`get_doubt_friends_add_request`|request|是|read|snowluma_get_doubt_friends_add_request||
|`set_doubt_friends_add_request`|request|是|write|snowluma_set_doubt_friends_add_request||
|`delete_friend`|user_ext|是|write|snowluma_delete_friend||
|`set_friend_remark`|user_ext|是|write|snowluma_set_friend_remark||
|`get_friends_with_category`|user_ext|是|read|snowluma_get_friends_with_category||
|`get_unidirectional_friend_list`|user_ext|是|read|snowluma_get_unidirectional_friend_list||
|`set_qq_profile`|user_ext|是|write|snowluma_set_qq_profile||
|`set_qq_avatar`|user_ext|是|write|snowluma_set_qq_avatar||
|`set_self_longnick`|user_ext|是|write|snowluma_set_self_longnick||
|`get_recent_contact`|user_ext|是|read|snowluma_get_recent_contact||
|`get_profile_like`|user_ext|是|read|snowluma_get_profile_like||
|`set_friends_category`|user_ext|是|write|snowluma_set_friends_category||
|`set_online_status`|status|是|write|snowluma_set_online_status||
|`set_diy_online_status`|status|是|write|snowluma_set_diy_online_status||
|`set_input_status`|status|是|write|snowluma_set_input_status||
|`nc_get_user_status`|status|是|write|snowluma_nc_get_user_status||
|`friend_poke`|poke|是|write|snowluma_poke||
|`group_poke`|poke|是|write|snowluma_poke||
|`fetch_custom_face`|emoji_ext|是|read|snowluma_fetch_custom_face||
|`add_custom_face`|emoji_ext|是|write|snowluma_add_custom_face||
|`delete_custom_face`|emoji_ext|是|write|snowluma_delete_custom_face||
|`fetch_custom_face_detail`|emoji_ext|是|read|snowluma_emoji(kind=custom)||
|`set_custom_face_desc`|emoji_ext|未确认|write|当前审计源码未确认支持||
|`modify_custom_face`|emoji_ext|是|write|snowluma_modify_custom_face||
|`move_custom_face_to_front`|emoji_ext|是|write|snowluma_move_custom_face_to_front||
|`fetch_emoji_like`|emoji_ext|是|read|snowluma_reaction_users|公共Service缺少cookie且将emojiId写为emoji_id；Plus通过公开适配器命令最小兼容，cursor为分页游标，非账号Cookie|
|`get_emoji_likes`|emoji_ext|是|read|snowluma_get_emoji_likes||
|`get_msg_emoji_likes`|emoji_ext|是|read|snowluma_message_reactions||
|`set_group_reaction`|emoji_ext|是|write|snowluma_set_group_reaction||
|`fetch_sys_faces`|emoji_ext|是|read|snowluma_find_face||
|`fetch_face_entity`|emoji_ext|是|read|snowluma_fetch_face_entity||
|`search_sys_faces`|emoji_ext|是|write|snowluma_find_face||
|`fetch_super_face_id`|emoji_ext|是|read|snowluma_emoji(kind=super)||
|`get_ai_characters`|ai_voice|是|read|snowluma_get_ai_characters||
|`get_ai_record`|ai_voice|是|read|snowluma_get_ai_record||
|`send_group_ai_record`|ai_voice|是|write|snowluma_send_group_ai_record||
|`get_clientkey`|cred|是|blocked|blocked||
|`get_credentials`|cred|是|blocked|blocked||
|`get_rkey` / nc_get_rkey|cred|是|blocked|blocked||
|`get_rkey_server`|cred|是|blocked|blocked||
|`check_url_safely`|cred|是|blocked|blocked||
|`ocr_image` / .ocr_image|cred|是|blocked|blocked||
|`download_file`|cred|是|blocked|blocked||
|`request_decrypt_key`|cred|是|blocked|blocked||
|`_get_model_show` / ._get_model_show|misc|是|write|snowluma_get_model_show||
|`_set_model_show` / ._set_model_show|misc|是|write|snowluma_set_model_show||
|`bot_exit`|misc|是|write|snowluma_bot_exit||
|`nc_get_packet_status`|misc|是|blocked|blocked||
|`click_inline_keyboard_button`|misc|是|write|snowluma_click_inline_keyboard_button||
|`get_mini_app_ark`|misc|是|read|snowluma_get_mini_app_ark||
|`translate_en2zh`|misc|是|write|snowluma_translate_en2zh||
|`create_collection`|misc|是|write|snowluma_create_collection||
|`get_collection_list`|misc|是|read|snowluma_get_collection_list||
|`send_packet` / .send_packet|misc|是|blocked|blocked||
|`send_pb`|misc|未确认|blocked|当前审计源码未确认支持||
|`handle_quick_operation` / .handle_quick_operation|misc|未确认|write|当前审计源码未确认支持||
|`get_word_slices` / .get_word_slices|misc|未确认|read|当前审计源码未确认支持||
|`create_flash_task`|flash|是|write|snowluma_create_flash_task||
|`send_flash_msg`|flash|是|write|可信Expand Service；SnowLuma只返回占位message_id=0，无法确认正常消息发送与撤回||
|`get_flash_file_list`|flash|是|read|snowluma_get_flash_file_list||
|`get_flash_file_url`|flash|是|read|snowluma_get_flash_file_url||
|`get_share_link`|flash|是|read|snowluma_get_share_link||
|`download_fileset` / download_flash_file|flash|是|write|snowluma_download_fileset||
|`get_fileset_info` / get_flash_file_info|flash|是|read|snowluma_get_fileset_info||
|`get_fileset_id`|flash|是|read|snowluma_get_fileset_id||
|`list_filesets`|flash|是|write|snowluma_list_filesets||
|`delete_flash_file`|flash|是|write|snowluma_delete_flash_file||
|`rename_flash_file`|flash|是|write|snowluma_rename_flash_file||
|`get_qun_album_list` / get_group_album_list|group_album|是|read|snowluma_get_qun_album_list||
|`upload_image_to_qun_album` / upload_group_album|group_album|是|write|snowluma_upload_image_to_qun_album|公共Service缺少SnowLuma必填album_name；Plus通过公开适配器命令补齐，不修改Expand响应契约|
|`get_group_album_media_list`|group_album|是|read|snowluma_get_group_album_media_list||
|`do_group_album_comment`|group_album|是|write|snowluma_do_group_album_comment||
|`set_group_album_media_like`|group_album|是|write|snowluma_set_group_album_media_like||
|`cancel_group_album_media_like`|group_album|是|write|snowluma_cancel_group_album_media_like||
|`del_group_album_media`|group_album|是|write|snowluma_del_group_album_media||
|`set_group_todo`|group_todo|是|write|snowluma_set_group_todo||
|`complete_group_todo`|group_todo|是|write|snowluma_complete_group_todo||
|`cancel_group_todo`|group_todo|是|write|snowluma_cancel_group_todo||
|`get_group_todo_list`|group_todo|是|read|snowluma_get_group_todo_list||
|`get_qzone_msg_list`|qzone|是|read|snowluma_get_qzone_msg_list||
|`get_qzone_feeds`|qzone|是|read|snowluma_get_qzone_feeds||
|`send_qzone_msg`|qzone|是|write|snowluma_send_qzone_msg||
|`delete_qzone_msg`|qzone|是|write|snowluma_delete_qzone_msg||
|`like_qzone`|qzone|是|write|snowluma_like_qzone||
|`unlike_qzone`|qzone|是|write|snowluma_unlike_qzone||
|`comment_qzone`|qzone|是|write|snowluma_comment_qzone||
|`set_qzone_ban`|qzone|是|write|snowluma_set_qzone_ban||
|`set_qzone_msg_right`|qzone|是|write|snowluma_set_qzone_msg_right||
|`share_peer`|ark|是|read|snowluma_share_peer|SnowLuma extended.ts声明readOnly=true：仅获取推荐卡片内容；名称中的send不代表发送消息|
|`send_ark_share`|ark|是|read|snowluma_send_ark_share|SnowLuma extended.ts声明readOnly=true：仅获取推荐卡片内容；名称中的send不代表发送消息|
|`share_group_ex`|ark|是|read|snowluma_share_group_ex|SnowLuma extended.ts声明readOnly=true：仅获取推荐卡片内容；名称中的send不代表发送消息|
|`send_group_ark_share`|ark|是|read|snowluma_send_group_ark_share|SnowLuma extended.ts声明readOnly=true：仅获取推荐卡片内容；名称中的send不代表发送消息|
|`send_tuwen_ark`|ark|是|write|可信Expand Service；模型不旁路框架发送图文转发||
|`batch_delete_group_member`|group_ext|未确认|write|当前审计源码未确认支持||
|`set_group_msg_mask`|group_ext|未确认|write|当前审计源码未确认支持||
|`create_group_album`|group_album|未确认|write|当前审计源码未确认支持||
|`delete_group_album`|group_album|未确认|write|当前审计源码未确认支持||
|`get_flash_file_download_urls`|flash|未确认|read|当前审计源码未确认支持||
|`upload_flash_file`|flash|未确认|write|当前审计源码未确认支持||
|`reshare_flash_file`|flash|未确认|write|当前审计源码未确认支持||
|`set_group_file_forever`|group_file|未确认|write|当前审计源码未确认支持||
|`get_profile_like_me`|user_ext|未确认|read|当前审计源码未确认支持||
|`get_profile_like_count`|user_ext|未确认|read|当前审计源码未确认支持||
|`get_qq_avatar`|user_ext|未确认|read|当前审计源码未确认支持||
|`set_friend_category`|user_ext|未确认|write|当前审计源码未确认支持||
|`_get_friend_dress`|user_ext|是|write|snowluma_get_friend_dress||
|`get_recommend_face`|emoji_ext|未确认|read|当前审计源码未确认支持||
|`unset_msg_emoji_like`|emoji_ext|未确认|write|当前审计源码未确认支持||
|`get_config`|misc|未确认|read|当前审计源码未确认支持||
|`set_config`|misc|未确认|write|当前审计源码未确认支持||
|`get_event`|misc|未确认|read|当前审计源码未确认支持||
|`llonebot_debug`|misc|未确认|write|当前审计源码未确认支持||
|`scan_qrcode`|misc|未确认|write|当前审计源码未确认支持||
|`get_guild_list`|misc|未确认|read|当前审计源码未确认支持||
|`test_download_stream`|流式接口|是|stream_unavailable|stream_unavailable|参考目录版本1.14.22；当前本地源码1.14.14必须另行确认注册。Expand无Service时才使用公开适配器命令。|
|`send_custom_face`|消息|未确认|write|当前审计源码未确认支持|参考目录版本1.14.22；当前本地源码1.14.14必须另行确认注册。Expand无Service时才使用公开适配器命令。|
|`upload_video_to_qun_album`|群相册|未确认|write|当前审计源码未确认支持|参考目录版本1.14.22；当前本地源码1.14.14必须另行确认注册。Expand无Service时才使用公开适配器命令。|
|`add_group_tag`|群管理|未确认|write|当前审计源码未确认支持|参考目录版本1.14.22；当前本地源码1.14.14必须另行确认注册。Expand无Service时才使用公开适配器命令。|
|`delete_group_tag`|群管理|未确认|write|当前审计源码未确认支持|参考目录版本1.14.22；当前本地源码1.14.14必须另行确认注册。Expand无Service时才使用公开适配器命令。|
|`get_group_tags`|群管理|未确认|read|当前审计源码未确认支持|参考目录版本1.14.22；当前本地源码1.14.14必须另行确认注册。Expand无Service时才使用公开适配器命令。|

目录源码摘要：

- Expand api_defs SHA256：`672c0e01aefff5cd705b8aab6ddc8c69569183b27b2a460c87cf269412dd3592`
- SnowLuma actions源码合集 SHA256：`14177bc893881f454e091ade535ed910e8fe3397de33c73497e8decc13e96752`
- 生成命令：`.venv/Scripts/python.exe plugins/snowluma_plus/scripts/generate_catalog.py`。当前生成器只执行已审计的本地Expand纯定义文件，不导入其他插件运行时。
