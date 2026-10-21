# 许可和来源

SnowLuma Plus 原创业务实现按 AGPL-3.0-only 发布，完整文本见插件根目录 LICENSE。作者为 SnowLuma Plus contributors。

- 当前本地 `onebot_expand` 由 Lycoris / fuilyha56-wq 维护，manifest 为 AGPL-3.0。`resources/catalog.json` 的220项接口说明、参数和别名由当前用户工作区的 `api_defs.py` 及公共Service签名生成；保留本署名及AGPL许可。未复制其业务实现；运行时仅经公共Service/适配器API调用。
- `resources/reference_extra_apis.json` 的6项协议目录事实来源于 Aemeath / xianshu-virtuous 的 `snowluma_full`，commit `6c3482c3806aa0228e5233eb25cb1a0616634a32`，MIT；该许可完整文本见 `resources/snowluma_full_MIT_LICENSE.txt`。
- `resources/faces.json` 从本工作区 Neo-Mofox OneBot Adapter 的 QQ_FACE 静态映射生成。它是静态备用目录，不代表运行实例已支持全部表情。
- Windpicker-owo/napcat_extension 当前manifest无license字段且仓库未发现LICENSE；不复制实现。
- tt-P607/snowluma_extension manifest声明AGPL-3.0，当前下载源码无LICENSE文件；只审计功能和配置，不复制实现。
- 本地 `E:/SnowLuma` 使用 SnowLuma Source-Available Non-Commercial License 1.0。仅核对协议字段、action注册和返回形状，未复制其实现或打包其源码。

版本、源码引用、对应组件和差异见 REFERENCE_AUDIT.md 和 API_COVERAGE.md。参考不表示这些项目为本插件背书。
