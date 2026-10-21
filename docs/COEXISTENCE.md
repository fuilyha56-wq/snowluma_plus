# 现有消费者与共存审计

以下从本地已安装包静态读取，不执行包代码，不修改现有配置。注册项只是潜在处理入口，是否启用取决于当前配置和运行生命周期。

|包|版本|涉及接收/提示的源码文件|
|---|---|---|
|expression_guard-1.1.0.mfp|1.1.0|未发现上述静态订阅关键字|
|mofox_docs-1.1.1.mfp|1.1.1|未发现上述静态订阅关键字|
|mute_guard-1.0.4.mfp|1.0.4|components/event_handler.py, plugin.py|
|neo-mofox-webui-1.0.26.mfp|1.0.26|未发现上述静态订阅关键字|
|onebot_webqq-3.0.0 (1).mfp|3.0.0|未发现上述静态订阅关键字|
|tavern_preset_regex-2.5.7.mfp|2.5.7|未发现上述静态订阅关键字|

- OneBot Expand：保留SelfIdInjectHandler；新notice继续携带raw_event。真实普通消息显式声明message_type，避免禁言判断因空类型漏过。
- neo_default_chatter：真实user_prompt的extra插槽；公开历史钩子传递过滤系统空正文后的副本，保留其他订阅者及extra。
- neo_fatum_chatter：collect_plugin_turn_contributions的on_prompt_build入口；原历史source跳过系统空正文，不改其源码，不替换其他贡献。
- neo-foxzone：仍负责其既有空间自动策略；Plus只提供受控手动API，不启动空间自动点赞/评论引擎。
- emoji_sender / expression_guard：保留既有媒体和文本规则；Plus原生face采用显式结构段，不解析文本标记，不扫描代码或JSON。
- 参考full/extension不建议同时开启重复业务Action或计划；本工作区未安装这两个参考插件。Expand建议保留Service，将重复LLM工具按其配置关闭；Plus不自动改写用户配置或移除别人的工具。
