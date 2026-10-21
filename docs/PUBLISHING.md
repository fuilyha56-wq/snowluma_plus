# 市场发布

用户要求完成后使用开发工具发布到市场。本机已安装命令为mpdt（mdpt为字母次序误写），已查看mpdt --help及market publish --help。

已配置的GitHub身份为fuilyha56-wq，目标独立仓库snowluma_plus；配置中的市场服务通过健康检查，发布前未发现同名插件。所有工具文件输出和独立Git仓库限制在本插件内；不修改MPDT全局配置。令牌仅交给工具用于既有认证，不写入文档或交付包。

发布命令：

```powershell
mpdt plugin check plugins/snowluma_plus
mpdt plugin build plugins/snowluma_plus --with-docs --output dist
mpdt market publish plugins/snowluma_plus --owner fuilyha56-wq --repo snowluma_plus --with-docs --output dist
```

.mfpignore及.gitignore明确排除测试工作目录、数据库、日志、真实配置、缓存及dist。发布前核验归档条目及源码一致性。最终发布状态、市场版本、GitHub Release和包SHA256以dist/publication.json回执为准；未拿到服务器回执前不声称上架成功。
