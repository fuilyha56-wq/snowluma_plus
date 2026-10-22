# SnowLuma Plus

面向当前 Neo-Mofox / OneBot Adapter / OneBot Expand 的业务增强插件。它在 notice/request 转换前持久接收原始事件，用独立 worker 处理，并把需要的事件送入真实 receiver、聊天流和 Chatter 上下文。表情回应查不到原消息时仍保留事件，不编造原文。

实现包括：群资料/成员/头衔/身份/荣誉、滚动24小时活跃统计、公告快照与差异、持久审批、手动/定时/启动补打、精华/历史/回应用户/文件查询、受控管理与正常框架发送。新增157个直接参数组件（39个常用业务封装、118个静态生成组件），不用先查目录或填写action/params_json。**源码能力、离线框架重放、运行平台验证分别记录，不将Mock通过写成真实QQ验收。**

## 安装和启用

当前工作区已放置独立插件源码；按用户更正要求，所有实现及兼容代码仅在本插件内。没有修改宿主/其他插件源码。真实消息测试仅在用户授权的测试群完成，并已撤回测试消息；未重启生产Bot。

1. 当前宿主最低版本为 `CORE_VERSION=1.3.0-alpha.1`，未经修改的 OneBot Adapter `2.0.0`，当前本地 Expand `1.0.22`（其已有未提交修改保留）。本地 SnowLuma 源码为 `1.14.14`；运行实例实测为 `1.14.4-node`（OneBot v11），通过用户提供的本地管理接口复用既有账号核验。
2. 使用源码目录 `plugins/snowluma_plus/`，或将构建好的 `.mfp` 放进插件目录。**同一个插件只保留目录或包其中一份**。本项目包放在本插件 `dist/`，不会成为第二个顶层插件。
3. 核对 [COMPATIBILITY.md](docs/COMPATIBILITY.md)。插件内兼容层在内存绑定原始入口及发送/Action上下文缺口；精确检查审计过的函数指纹，未知升级或包装冲突会报告未接管，不修改宿主文件。
4. 按项目正常方式启动/重载插件。框架生成 `config/plugins/snowluma_plus/config.toml`。默认接管开启，当前会话日常工具/普通互动采用黑名单制；群管理、审批、文件外发独立授权，自动审批、计划打卡和公告轮询关闭。
5. 需要跨会话/敏感资料/管理操作时填写 `access.operators`。查询 `snowluma_status(view="diagnostics")`，核对绑定、连接、后端版本、队列、解析/入流/上下文构建证据。普通群查询无需操作者身份；跨会话和敏感资料另行授权。

默认 `plugin.isolate_streams=true`，用平台/账号/适配器/会话生成独立路由，真实QQ群号及发送目标不变。首次启用会建立新聊天流；原聊天历史保留，不自动迁移。需要沿用旧单账号聊天流时可显式关闭该项，但那时不提供跨账号聊天流隔离。内部缓存/审批/统计仍用复合键隔离。

## 配置原则

完整安全默认示例见 [config.example.toml](config.example.toml)。Web UI 的7个分组及52个字段均提供中文显示名称：插件设置、事件接管与账本、权限与审批、文件外发、成员资料与活跃统计、群公告同步、群打卡计划。框架自动生成中文注释；内部TOML键保持兼容。更新后重载插件并刷新配置页面即可读取新标签。

- 当前会话普通查询/互动默认黑名单制：`blocked_users`、`blocked_groups`、`blocked_actions` 分别禁用用户、群和接口，黑名单优先于显式授权；仍遵守适配器原有名单。`allow_basic_interactions=true` 允许贴/取消表情、戳请求者、给请求者主页点赞1..10次、文字/原生表情/引用、手动打卡、撤回Bot自己的消息。
- `access.operators` 是跨会话、账号敏感资料及独立授权写入的真实触发者，不固定为owner。`allowed_actions` 和 `write_groups` 分别约束动作及群；还会执行平台当前角色检查。
- `approval_mode="remind"` 默认不批准请求。申请立即成为持久待办；配置的 `management_users` 必须同时在 operators 中，且须通过适配器私聊名单。未配置管理会话时只保留待办，不猜接收者、不向申请者回发。
- `assisted` 允许授权操作者以插件 request_id 审批。`auto` 还必须同时填写申请者白名单、完整理由正则、群范围及对应审批 action。平台 flag 永不交给模型。
- `checkin.enabled=true` 之前，配置打卡群、write_groups 和 `set_group_sign` 的动作授权。普通互动开启时，当前群手动打卡无需配置上述计划白名单。手动、计划、补打共用同日状态。时区默认 Asia/Shanghai；HH:MM 严格校验；结果不确定不自动重试。
- 公告组默认空，不自动读取全账号群列表。当前源码 `_get_group_notice` 返回合并列表、无原生分页参数；工具本地分页。超出预算、缺ID、has_more/next_token/incomplete或请求失败不会覆盖完整基线，也不会误判删除。
- 本地外发默认关闭。开启需要允许根、扩展名、大小上限，以及确认协议端与本机同主机。拒绝相对路径、UNC、链接/共享卷、越界、模型base64和未经核验的远端URL。普通媒体经框架处理；源文件读取有大小上限。
- `events.context_types` 控制进入上下文的通知，`wake_types=[]` 默认不主动唤醒其他事件；`wake_bot_pokes=true` 时，目标为当前 Bot 的戳一戳会直接交给主模型并绕过普通闲聊过滤。其他成员之间的戳戳、Bot 自己产生的回声仍保持静默。输入状态、客户端状态等默认只作结构化事件/账本。

## 常用说法和工具

|用户表达|直接入口|
|---|---|
|查我的头衔|`snowluma_find_member(query="我")`|
|Bot现在是什么身份/荣誉|`snowluma_bot_identity()` / `snowluma_group_honor()`|
|看最新公告/查精华|`snowluma_list_notices(limit=5)` / `snowluma_list_essence()`|
|给这条消息点赞/取消|`snowluma_react_message(emoji="赞", remove=false/true)`，默认本次触发消息|
|戳我一下|`snowluma_poke()`|
|给我的主页点赞3次|`snowluma_profile_like(user_id="真实QQ", times=3)`|
|发消息后撤回|`snowluma_send_text(text=...)` → 用返回的ID调用 `snowluma_recall_message(message_id=...)`|
|谁给消息贴了表情|`snowluma_message_reactions(message_id=...)` → `snowluma_reaction_users(message_id=..., emoji_id=...)`|
|处理待审批|`snowluma_requests()` → `snowluma_approve(request_id, approve, reason)`|
|本群最近活跃成员|`snowluma_active_members(refresh=true)`|
|今天打卡了吗/打卡|`snowluma_checkin_status()` / `snowluma_checkin()`|
|禁言/改名片/发公告|`snowluma_mute_member(member, duration_seconds)` / `snowluma_set_member_card(member, card)` / `snowluma_publish_notice(content)`，需管理授权|

新增直接入口的参数和226项路由见 [DIRECT_TOOLS.md](docs/DIRECT_TOOLS.md)，常用封装见 [BUSINESS_TOOLS.md](docs/BUSINESS_TOOLS.md)。实际参数、消息ID规则、分页和中文示例见 [TOOLS.md](docs/TOOLS.md)。接口逐项去向见 [API_COVERAGE.md](docs/API_COVERAGE.md)，四个参考插件的逐组件对应见 [REFERENCE_AUDIT.md](docs/REFERENCE_AUDIT.md)。

## 可靠性与使用边界

SQLite WAL 先提交再确认接管；有界队列只是唤醒提示，满时从账本恢复。投递等待真实入流确认，不把 Sink 派发当作消费成功。同会话待重试头部阻止后续越序；其他群可继续处理。框架投递采用至少一次语义，历史以事件消息ID幂等入库。无平台唯一标识的相同notice不会用时间桶合并，避免吞掉合法重复操作；因此无法证明唯一性的重复notice可能保留多次。

系统事件在聊天流中保存无发言人、空正文的NOTICE记录，脱敏说明位于extra；两个Chatter通过现有prompt额外资料入口呈现带边界的平台事件。NFC跳过空正文，默认Chatter的公开历史事件钩子跳过此类记录，防止渲染成用户发言。事件资料有50条/12000字符预算。

状态和原始资料在 `data/snowluma_plus/ledger.sqlite3`，仅供宿主OS账号与可信进程使用。原始请求flag留在内部，普通工具和上下文使用脱敏结果；数据默认保留14天，pending/uncertain/失败账本不会被静默挤掉。达到磁盘软限额或写盘失败会给出计数、错误和保真降级，不伪称已可靠入库。

24小时排名只代表Bot获准接收、能够归属账号的真实成员消息；排除Bot、notice和重复消息。不按自然日归零。公开框架历史缺账号元数据时只依据本插件持久映射回填，并始终说明覆盖可能不完整。

凭证、原始包、重启/退出、危险下载和流式API不直接开放给模型。流式需要真实多帧/取消/清理通道，当前单请求入口明确拒绝；原始 Expand Service 仍保留给可信插件。QQ空间不新建自动互动引擎，继续与 neo-foxzone 共存。文本表情标记不自动改写。

## 验证、构建和回滚

离线测试命令及逐项证据见 [VALIDATION.md](docs/VALIDATION.md)。Windows受限沙箱可能阻止asyncio本地唤醒套接字；测试是否真正执行及当前修订验证状态以记录为准。离线测试的协议边界为替身；真实平台只读及授权消息闭环单独记录。

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.venv\Scripts\python.exe -m pytest -p pytest_asyncio.plugin -p no:cacheprovider -o addopts='' plugins/snowluma_plus/tests -q
ruff check plugins/snowluma_plus
.venv\Scripts\python.exe plugins/snowluma_plus/scripts/build_package.py
```

卸载会注销自己的原始处理器、取消并等待自己的worker/计划任务、关闭账本。不会改动Expand的原Service响应或删除其他插件工具。停用、内存兼容句柄恢复及升级见 [COMPATIBILITY.md](docs/COMPATIBILITY.md)，状态与证据见 [IMPLEMENTATION.md](docs/IMPLEMENTATION.md)。许可与署名见 [THIRD_PARTY_NOTICES.md](docs/THIRD_PARTY_NOTICES.md)。
