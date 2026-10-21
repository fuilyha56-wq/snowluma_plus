# 插件内兼容、升级与卸载

全部开发文件仅位于 plugins/snowluma_plus。交付包不含宿主补丁；无需修改核心、OneBot Adapter、Expand 或 Chatter 的文件。使用既有登录账号和连接，不读取适配器私有连接配置，无第二套WebSocket或网络扫描。

## 已审计边界

核心实际 CORE_VERSION=1.3.0-alpha.1（项目pyproject另标1.3.0-alpha.0）；OneBot Adapter manifest 2.0.0（组件继承的版本字段实际0.0.1）；Expand本地1.0.22。resources/compatibility.json固定四处真实函数的SHA256，compat.py在安装前以inspect读取当前实现并核验；额外包装器即使保留原函数元数据也会被拒绝。版本号不能替代正文指纹。未知实现只报告未接管，不悄悄覆盖。

|入口|插件内处理|
|---|---|
|适配器实例 from_platform_message|echo、心跳及生命周期直接委托原方法；message附来源后仍走原转换；notice/request在转换前经同一公共配置名单校验，再落本插件账本。四态回调由raw_events.py实现|
|适配器实例 _send_platform_message|普通发送直接委托原方法；仅本插件带标记的face/contact/node经公共adapter命令补齐协议，返回PlatformSendResult，仍由核心MessageSender写历史及发布发送后事件|
|核心统一create_llm_usable_execution、ActionManager.execute_action|保存框架传入的真实触发Message到任务局部ContextVar；仅本插件BoundAction构造器使用；模型没有operator/flag参数，不猜最近发言|
|BEFORE_MESSAGE_RECEIVED / ON_MESSAGE_RECEIVED|通过公开事件补来源、守卫禁言，在分发前设置账号/适配器隔离的实际Message.stream_id，不修改核心哈希函数|
|Chatter公开历史事件及on_prompt_build|系统事件正文为空，资料保留在extra；默认Chatter历史钩子跳过它们，NFC原有实现跳过空正文；两者从公开额外资料入口接收带边界的系统事件，不包装或导入其他Chatter私有实现|

配置只通过公共config_api读取名单/开关，不改对象、不读取server/token。标准事件保留raw_event/self_id/message_type供现有Expand禁言逻辑；本插件另有账号/群隔离的持久禁言守卫，避免原守卫按群号缓存引入跨账号漏放。

## 生命周期与冲突

安装保存实例原属性（包括属性原本不存在的情况）。同一Runtime重复bind幂等；两份Runtime抢同一实例会报冲突。实例更换时先恢复旧实例，再检查新实例。已有连接重连后沿用相同入口，无新连接。每2秒检查适配器实例及句柄所有权。

卸载先禁用包装器业务行为，再仅恢复仍由本插件持有的属性；原本不存在的辅助属性删除。如果其他实现后来包裹了本插件方法，不强行覆盖对方入口，报告compat_restore_conflict；残留闭包已停用并仅委托原方法。关闭账本、取消并等待自己的三个受管理任务，不取消其他插件任务。任务启动部分失败同样回滚。

plugin.capture=false只注销本插件原始回调；已有账本暂停投递。保持来源和发送兼容能力供查询工具使用。plugin.enabled=false并重载或正常卸载会完全释放句柄。禁用隔离或卸载恢复核心旧哈希规则；不会删除旧/新聊天流。

持久状态位于框架data/snowluma_plus目录，正常卸载保留。processing重启后变为uncertain，不能盲重试副作用。移除插件文件前按框架正常卸载；无需对宿主文件应用或反向应用补丁。

## 并发事实

已安装mofox-wire的_ws_listen_loop按帧派发任务，不能仅凭on_platform_message等待转换就断言WS一定死锁。原始回调仍禁止平台查询，只做校验、SQLite落盘和唤醒；worker及后台补充受管理且有预算。CoreSink.send也可能只是派发任务，投递必须等待真实聊天流证据/消费确认。
