# 事件路由与证据矩阵

所有notice/request接入点均为 `OneBotAdapter.from_platform_message`：echo先处理，当前名单/禁用用户/互动开关过滤后，插件内经指纹校验的兼容回调先落WAL账本，再由worker处理。使用统一事件v1：event_id、source、scope(platform/account/adapter/group/user)、kind/subtype、actor/target、platform message_id、occurred_at/received_at、data、enrichment、raw_ref。

默认每个允许事件都持久化，并发布 `snowluma_plus:event`（配置disabled_types时仅保留账本，不发布）。context类型通过真实CoreSink→receiver→ON_RECEIVED_OTHER_MESSAGE.processed→ON_MESSAGE_RECEIVED→stream历史；默认wake_types为空。`framework`是实际入流/入库证据，`consumed`是事件ID进入Chatter实际构建上下文的证据，均不是远端LLM已经作答证明。

|上游原始类型/子类型|用途/默认上下文|来源|主要验证|
|---|---|---|---|
|group_increase approve/invite|结构事件、历史、成员/身份缓存失效；不默认唤醒|platform|test_chain 参数化全链路|
|group_decrease leave/kick/kick_me/disband|结构事件、历史、缓存失效；不猜退出原因|platform|同上|
|group_admin set/unset|结构事件、历史、角色缓存失效|platform|同上、即时角色执行测试|
|group_card|结构事件、历史、索引失效|platform|同上、原始重复保留|
|notify.title / notify.group_name|结构事件、历史；头衔更新使资料失效|platform|同上、两类Chatter真实构建|
|group_ban ban/lift_ban（user_id=0为全员）|结构事件、历史；raw_event供Expand现有禁言保护|platform|test_delivery_and_context真实禁言/解禁链路|
|group_whole_ban / group_whole_ban_status|结构事件/账本；保留enable给Expand状态保护，默认不制造聊天噪声|兼容扩展platform；本地转换未见独立原生类型|原Expand状态回归|
|notify.poke|结构事件、历史；遵守原enable_poke及目标限制，不自动回戳|platform|回声/开关/无网络回调测试|
|group_msg_emoji_like add/remove|结构事件、历史；不需要查原文；likes/emoji_id/count保真|platform|日志原消息缺失回归和取消回应|
|group_recall / friend_recall|结构事件、历史；平台ID与原文可访问性分开|platform|参数化链路/消息ID权限测试|
|essence add/delete|结构事件、历史|platform|参数化链路/精华工具|
|group_upload|结构事件、历史，file.id/name/size/busid保真|platform|参数化链路/文件策略/发送回归|
|friend_add|结构事件、正确私聊历史|platform|统一模型/路由|
|request friend|即时持久待办；可选通知授权管理私聊；不伪装申请者聊天|platform|原始入口/去重/并发/超时/重启|
|request group add/invite（含invited_id）|即时持久待办、群范围核验；Bot受邀和邀请其他成员分开检查角色|platform|同上、服务端字段绑定|
|notify.profile_like|缺少群/私聊归属时账号级结构事件/账本，不猜会话|platform|缺字段/账号级降级|
|notify.input_status|结构事件/账本，无历史/唤醒|platform|默认静默策略|
|bot_offline / client_status|账号状态/结构事件/账本，不将Bot号当私聊发送者|platform；client状态按实际后端扩展|账号隔离/缺字段|
|group_notice add/update/delete|结构事件、历史；本地当前转换未见原生公告推送|poll_diff / local_action；未来原生完整payload可共享基线|首次基线、增改删、失败/不完整快照、不重复差异|
|其他notice/sub_type/request|保真账本、命名空间结构事件、可检索脱敏详情；无可确认归属时账号级，不默认唤醒|真实来源保留|未知/缺字段/大ID/秒毫秒/畸形/超限|
|message（真实成员普通消息）|继续原消息链路；授权原始输入计数与映射，排除Bot及重复平台ID|platform|普通消息/echo/禁言保护/滚动窗口/回填|
|meta_event heartbeat/lifecycle及API echo|保留原分支，不作为业务聊天事件|platform|原路由回归|

所有context/wake类型均可配置关闭；持久账本受保留和磁盘策略约束，不宣称物理存储失败仍能可靠保存。补充资料失败不影响原始语义。当前事件enrichment为not_requested，资料刷新在后台缓存，不把未知昵称或原文编造为补充成功。

公告首次查询只建立基线，轮询和读取共享快照。本地公告成功后读取实际列表生成local_action来源差异；有完整原生notice时更新相同基线。payload不完整时不猜相等；无唯一ID的通知保留多次的取舍见README。
