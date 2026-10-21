# 工具和Action索引

所有调用从框架绑定的真实触发消息获得账号、适配器、操作者和会话；模型不能填写operator/self_id/adapter/flag。普通本群查询可用；跨群、账号目录、申请及敏感资料需要配置的操作者。空结果、未注册、权限拒绝、网络/超时、畸形返回分别报告。

|组件|用途与参数|
|---|---|
|snowluma_group|view=overview/member/identity/honor/active；query成员检索，group_id默认本群，offset/limit分页，refresh主动刷新/历史补齐|
|snowluma_notices|query内容搜索、notice_id平台公告ID、group_id、offset/limit；返回上游原字段含发布者/时间/媒体|
|snowluma_messages|view=history/bot_recent/essence/detail/reactions/reaction_users；message_id显式前缀，query搜索，offset/limit；回应用户需要emoji_id，cursor为插件绑定的不透明游标|
|snowluma_files|当前群根目录或folder_id，file_id/busid查群链接；私聊需file_id/file_hash；query当前目录搜索，offset/limit本地分页|
|snowluma_requests|request_id为空列出已到达待办及历史，指定ID看详情；offset/limit；平台flag不返回|
|snowluma_emoji|kind=native/super/custom；query关键词或数字ID；offset/limit，refresh；native平台失败时明确标静态备用表|
|snowluma_api_catalog|query名称/中文说明/类别/参数检索，offset/limit；不展开或移除其他插件工具|
|snowluma_api_read|action和params_json；仅受控只读，目录已审计的参数，自动填当前group_id；消息字段仍需ID核验|
|snowluma_status|view=checkin/events/event/search/diagnostics；event_id查完整脱敏事件；query检索最近1000条本会话事件；诊断仅操作者|
|snowluma_manage（Action）|action、params_json、target；当前群默认填入，target=QQ/精确昵称/名片/头衔；歧义给候选，过期资料不猜目标|
|snowluma_approve（Action）|插件request_id、approve布尔、reason；内部绑定真实类型/flag/账号，CAS只提交一次；超时、进程中断标uncertain|
|snowluma_checkin（Action）|无参数，本群；共享配置时区日期记录；成功同日不重复|
|snowluma_send（Action）|kind=text/face/reply/forward/file/image/emoji/voice/video/share，content和可选message_id；框架发送、成功事实及历史一致|
|snowluma_service|可信插件通过公共Service读取diagnostics()；不是绕过授权的通用写入入口|

分页 limit 为1..50，offset非负；目录默认8项；结果总字符预算默认6000。超限返回truncated和缩小检索提示，不截成畸形JSON。缓存展示来源、刷新时间、stale/complete；历史工具当前页最多最近50条，更早记录用目录中的message_seq接口，不宣称检索了全部历史。

## 真实参数示例

以下ID均为**合成示例**，使用前替换为用户授权范围内的真实对象。真实写入必须先配置授权；本次开发没有向这些号码发送或审批。

```json
{"view":"member","query":"我","limit":10}
{"view":"active","limit":10,"refresh":true}
{"query":"维护","limit":5}
{"view":"reactions","message_id":"platform:777"}
{"view":"reaction_users","message_id":"platform:777","emoji_id":"66","limit":10}
{"query":"get_group_album_media_list","limit":1}
{"action":"get_group_album_media_list","params_json":"{\"album_id\":\"真实相册ID\",\"attach_info\":\"\"}"}
{"action":"set_group_special_title","target":"10001","params_json":"{\"special_title\":\"雪光\"}"}
{"action":"set_group_ban","target":"10001","params_json":"{\"duration\":60}"}
{"action":"_send_group_notice","params_json":"{\"content\":\"已授权的公告正文\"}"}
{"request_id":"插件返回的真实request_id","approve":false,"reason":"已授权拒绝原因"}
{"kind":"face","content":"66"}
{"kind":"reply","content":"已授权回复文本","message_id":"platform:777"}
{"kind":"forward","content":"[\"platform:777\",\"platform:778\"]"}
```

`framework:...` 只解析本会话持久映射；`platform:...` 必须经协议详情核实群归属。私聊Bot自己的消息还需本会话映射，不能仅凭sender=Bot读取另一私聊。查不到原消息时工具清晰失败；已收到的回应notice仍进入事件历史。

管理动作同时检查操作者/action/群授权和Bot当前角色。禁言为0..2592000整数秒，解禁为0；设置管理员/头衔要求群主；不能对群主或超出Bot层级的成员操作。平台仍可能在执行时拒绝，只有status=ok、retcode=0的确定响应才报告成功。

审批状态：pending、processing、approved、rejected、invalid、expired、failed、uncertain。failed不是“已拒绝”；uncertain不是“可重试”。平台缺少可靠结果查询时不提供自动再次提交入口。只知道平台历史申请不等于持有可用原始flag。

发送还要求实际 AFTER_MESSAGE_SENT 事实，拦截导致框架返回true也不会被Plus说成已发送。原生face/分享/转发展示文字只进入历史，不额外发到QQ。撤回/精华先核实消息范围；普通新消息和合并转发走框架，不走原始消息载荷旁路。
