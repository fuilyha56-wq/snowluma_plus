# 常用直接业务组件

查询使用Tool、写入使用Action，均可由当前框架LLM执行器直接调用。新增157项明确参数组件中，以下39项是手工业务封装，另118项来自已审计契约的静态签名生成。模型只填业务参数，不需要action或params_json。

|名称|参数|用途|
|---|---|---|
|`snowluma_group_info`|`refresh=False`|直接查看当前群名称、群号、人数和群资料，无需查API目录。|
|`snowluma_find_member`|`query='', offset=0, limit=10, refresh=False`|直接按QQ号、昵称、群名片或头衔查群成员；“我”指真实发言人，同名返回候选。|
|`snowluma_bot_identity`|`refresh=True`|直接查询Bot在本群的身份、管理员权限、群头衔；不需要先查目录。|
|`snowluma_group_honor`|`query=''`|直接查询本群龙王、群聊之火等荣誉，可按成员搜索。|
|`snowluma_active_members`|`limit=10, offset=0, refresh=False`|直接查询本群滚动近24小时活跃成员和消息条数；可回填Bot可见历史。|
|`snowluma_list_notices`|`query='', limit=10, offset=0`|直接查看当前群最新公告或按内容搜索；返回公告ID和完整性。|
|`snowluma_list_essence`|`query='', limit=10, offset=0`|直接查看本群精华消息，支持内容搜索和分页。|
|`snowluma_message_history`|`query='', limit=15, offset=0`|直接查询当前群/私聊最近消息及真实消息ID，支持内容检索。|
|`snowluma_recent_bot_messages`|`limit=10`|直接查看Bot近期发出的消息和可用于撤回的消息ID。|
|`snowluma_message_detail`|`message_id`|直接查看指定消息详情，message_id使用平台真实消息ID或framework:前缀。|
|`snowluma_message_reactions`|`message_id`|直接查询某条消息收到的表情回应及数量。|
|`snowluma_reaction_users`|`message_id, emoji_id, cursor='', limit=10`|直接分页查询谁给消息贴了某个表情；cursor使用上次结果提供的值。|
|`snowluma_find_face`|`query='', limit=15`|直接按中文名查QQ原生表情真实ID，用于发送原生表情或贴表情回应。|
|`snowluma_checkin_status`|`无`|直接查询本群今天的打卡记录与结果，不执行打卡。|
|`snowluma_react_message`|`emoji='赞', message_id='', remove=False`|给消息贴表情回应或取消回应；默认当前真实用户的这条消息。支持中文表情名或数字ID，直接执行，无需查询API。|
|`snowluma_recall_message`|`message_id`|直接撤回指定消息。普通互动只可撤回Bot自己的消息；撤回成员消息需要管理授权。|
|`snowluma_mute_member`|`member, duration_seconds=600`|直接禁言指定群成员，duration_seconds为秒；需授权并检查Bot平台权限。|
|`snowluma_unmute_member`|`member`|直接解除指定群成员禁言；仍需群管理授权。|
|`snowluma_whole_group_mute`|`enabled`|直接开启或关闭本群全员禁言；需管理授权。|
|`snowluma_kick_member`|`member, reject_rejoin=False`|直接移出指定群成员；需独立授权并核验成员层级，不支持模糊猜人。|
|`snowluma_set_member_card`|`member, card`|直接修改指定成员的群名片；需相应动作授权。|
|`snowluma_set_member_title`|`member, title`|直接设置群成员专属头衔；需动作授权和Bot群主身份。|
|`snowluma_rename_group`|`name`|直接修改当前群名称；需群管理授权。|
|`snowluma_publish_notice`|`content`|直接发布当前群公告，成功后同步公告差异；需独立授权。|
|`snowluma_delete_notice`|`notice_id`|直接删除指定公告；notice_id是公告ID，需独立授权。|
|`snowluma_set_essence`|`message_id`|直接把指定本群消息设为精华；需独立授权。|
|`snowluma_remove_essence`|`message_id`|直接取消指定本群消息的精华；需独立授权。|
|`snowluma_profile_like`|`user_id, times=1`|直接为指定QQ主页点赞，只需QQ号和次数。当前真实发言人1至10次属于普通互动；其他目标需动作授权。|
|`snowluma_send_text`|`text`|直接在当前群/私聊发普通文字；发送结果提供平台消息ID以便撤回。|
|`snowluma_send_face`|`emoji='微笑'`|直接发送QQ原生表情，支持中文名或真实ID；不是贴在消息上的回应。|
|`snowluma_reply_message`|`text, message_id`|直接引用当前会话指定消息并发送文字。|
|`snowluma_forward_messages`|`message_ids`|直接合并转发当前会话1至10条已有消息；需发送授权。|
|`snowluma_send_file`|`path`|直接发送已获准的本机文件；文件外发、同主机及允许目录策略仍生效。|
|`snowluma_send_image`|`path`|直接发送已获准的本机图片；需文件外发及目录策略授权。|
|`snowluma_poke`|`member='我'`|直接戳一戳当前真实发言人，默认戳请求者自己；指定其他成员需要独立动作授权，无需查询API。|
|`snowluma_list_files`|`query='', folder_id='', offset=0, limit=10`|直接查看或搜索当前群文件列表，支持目录与分页。|
|`snowluma_file_url`|`file_id, busid=0, file_hash=''`|直接获取当前会话平台文件的下载链接，不自动下载；私聊文件需file_hash。|
|`snowluma_send_voice`|`path`|直接发送已获准的本机语音，需文件外发及目录策略授权。|
|`snowluma_send_video`|`path`|直接发送已获准的本机视频，需文件外发及目录策略授权。|

## 调用例子

```python
snowluma_find_member(query="我")
snowluma_list_notices(limit=5)
snowluma_react_message(emoji="赞")
snowluma_poke()
snowluma_profile_like(user_id="当前发言人的真实QQ", times=3)
snowluma_send_text(text="测试消息")  # 返回platform_message_id
snowluma_recall_message(message_id="上一步实际返回的ID")
snowluma_checkin()
snowluma_mute_member(member="明确成员QQ", duration_seconds=60)  # 独立管理授权
snowluma_get_stranger_info(user_id="当前发言人的真实QQ")
```

默认黑名单为空，当前获准会话普通互动可以直接使用；审批、文件、管理和跨会话访问仍按配置单独授权。失败时说明原因，不反复查询目录或改参数碰运气。完整接口去向见[DIRECT_TOOLS.md](DIRECT_TOOLS.md)。
