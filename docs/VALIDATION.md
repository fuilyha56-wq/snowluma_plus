# 验证记录（2026-10-21）

当前修订为仅插件内兼容方案；宿主/Adapter/Chatter源码已恢复。旧宿主补丁方案的结果不计入本次验收。

## 已执行

- 当前源码完整离线回归：**93 passed, 1 warning in 63.16s**。真实核心、PluginManager源码及MFP加载、公共Expand Service、两个Chatter及协议替身；非真实QQ。包括当前已安装WebUI纯Schema解析器对7分组/48字段中文名的核验及实际文件发送链路。
- ruff check --no-cache plugins/snowluma_plus：通过。
- Python compileall，仅插件目录：通过。
- 四处兼容函数指纹与未修改宿主实现一致；已有包装冲突、重绑、关闭和卸载恢复均有测试。
- MPDT静态检查0错误；分类调整为单一tool，标签齐全。其对星号展开组件列表/带注解configs有AST误报；实际源码和MFP均注册16项（15业务组件及1配置组件），并能调用Service后卸载。

Windows默认受限环境的asyncio进程不能正常退出；自动审批额度曾导致一次未执行。额度重置后，已获准在允许本地唤醒套接字的环境完成上述离线测试。此阻塞已解决。

最终测试有1条async_lru跨pytest事件循环自动清理缓存警告。较早分组运行还出现过websockets.legacy弃用警告；均为依赖提示。

源码和MPDT构建.mfp均已通过实际PluginManager加载、组件注册、公共Service调用与卸载，MFP从独立临时解压目录导入。平台写入未测，未将离线通过表述为真实QQ验收通过。发布回执在本插件dist/publication.json另行保存。

## 测试范围

测试使用真实核心事件总线、receiver、MessageConverter、MessageSender、StreamManager、SQLite、PluginManager、组件/Service注册和两个现有Chatter构建入口；协议边界替身，不连接真实QQ。

覆盖原消息缺失的表情回应、成员/头衔/精华/文件、未知notice、好友/群申请、名单、队列满、重启、会话顺序、异步Sink实际确认、多账号流隔离、禁言、缓存损坏与并发、近24小时统计、公告初始基线/不完整/权限变化、并发审批/失效/超时、打卡跨日和不确定结果、文件越界、参数预算、发送被拦截不能宣称成功、原生表情/名片/转发正常发送与历史、生命周期回滚。

fixtures为按照已审计SnowLuma字段契约生成的合成事件，不是真实QQ抓包。真实日志仅用于定位原消息缺失的回归。

## 基线与范围补充

此前核心相关回归有29通过、1个既有失败：BaseAction.to_schema测试期望action:test_action，但当前核心实现是action-test_action；这在本插件改动前就存在，不修改核心修复该问题。最终93项插件测试与该基线分开统计。

本次原先触及的11个插件外文件已逐字节恢复到审计基线，哈希记录见HOST_RESTORE_AUDIT.json；外部新增示例和raw_events文件已移入本插件或移除。Expand已有用户修改保持原状。

## 可复现命令

从工作区执行（需环境允许本地asyncio事件循环）：

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONDONTWRITEBYTECODE='1'
.venv\Scripts\python.exe -m pytest -p pytest_asyncio.plugin -p no:cacheprovider -o addopts='' --basetemp=plugins/snowluma_plus/.test-run plugins/snowluma_plus/tests -q
ruff check plugins/snowluma_plus
.venv\Scripts\python.exe plugins/snowluma_plus/scripts/build_package.py
```

生产验收建议在明确测试群/账号上依次核对只读诊断、非唤醒notice入流/上下文、单次发送/回应、申请待办授权审批、手动与计划打卡同日去重、公告基线/增改删、Bot禁言阻断、重载重绑与卸载恢复。没有测试对象授权时不自动产生这些真实副作用。
