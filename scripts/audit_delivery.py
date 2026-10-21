"""从固定参考源码、实际目录和已安装包生成覆盖与共存审计文档。"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Any

ROUTES = {
    "config": "SnowLumaConfig（按业务组织，不复制旧配置）",
    "mute_group_member": "snowluma_manage / set_group_ban",
    "unmute_group_member": "snowluma_manage / set_group_ban duration=0",
    "set_group_whole_ban": "snowluma_manage / set_group_whole_ban",
    "react_to_message": "snowluma_manage / set_msg_emoji_like；snowluma_messages 查询",
    "poke_group_member": "snowluma_manage / group_poke 或 send_poke",
    "recall_message": "snowluma_manage / delete_msg（必须核实消息范围）",
    "send_share_card": "snowluma_send kind=share；框架 contact 段",
    "group_sign": "snowluma_checkin；共用手动/计划/补打记录",
    "kick_group_member": "snowluma_manage / set_group_kick",
    "set_group_name": "snowluma_manage / set_group_name",
    "set_group_card": "snowluma_manage / set_group_card",
    "set_group_special_title": "snowluma_manage / set_group_special_title",
    "send_group_notice": "snowluma_manage / _send_group_notice；共享公告基线",
    "delete_group_notice": "snowluma_manage / _del_group_notice；共享公告基线",
    "send_group_forward_msg": "snowluma_send kind=forward；框架发送器和历史",
    "set_essence_msg": "snowluma_manage / set_essence_msg",
    "delete_essence_msg": "snowluma_manage / delete_essence_msg",
    "forward_group_single_msg": "snowluma_send kind=forward（当前群，授权范围）",
    "forward_friend_single_msg": "snowluma_send kind=forward（当前私聊）",
    "send_like": "snowluma_manage / send_like（默认关闭）",
    "send_file": "snowluma_send kind=file；规范路径/大小/类型限制",
    "save_message_file": "snowluma_files / get_file 获取链接；不自动下载任意远端文件到本机",
    "get_group_member_info": "snowluma_group view=member；真实ID/昵称/名片/头衔",
    "get_group_info": "snowluma_group view=overview",
    "get_group_member_list": "snowluma_group view=member；分页搜索",
    "refresh_group_members": "snowluma_group view=member refresh=true；并发合并",
    "get_group_notice": "snowluma_notices（列表/ID详情/搜索）",
    "get_qq_face_list": "snowluma_emoji（原生/超级/收藏分别查询）",
    "get_essence_msg_list": "snowluma_messages view=essence",
    "get_group_honor_info": "snowluma_group view=honor；身份提醒仅放Bot荣誉",
    "get_group_shut_list": "snowluma_api_read / get_group_shut_list",
    "get_bot_messages": "snowluma_messages view=bot_recent；最近协议页并非完整历史",
    "face_intercept_handler": "改用显式 snowluma_send kind=face，不重写普通文本/代码/JSON，不二次解析旧标记",
    "bot_role_reminder_handler": "后台身份/荣誉缓存 + 两类Chatter真实上下文入口",
    "group_members_reminder_handler": "TTL成员索引 + 有预算的24小时活跃成员提醒，不常驻全群名单",
    "handle_group_join_request": "snowluma_approve；内部request_id绑定flag、类型和状态",
    "get_group_join_requests": "snowluma_requests；仅已到达真实请求，无法凭日志恢复历史flag",
    "catalog": "固定紧凑组件 + snowluma_api_catalog 分页发现",
    "fold": "固定紧凑组件和有预算分页，不更改其他插件工具或缓存，无跨会话展开状态",
    "sl_help": "snowluma_api_catalog（目录、参数、风险、兼容性）",
    "sl_use": "snowluma_api_catalog 分页发现；执行层每次重新授权",
    "sl_requests": "snowluma_requests / snowluma_approve",
    "sl_qzone_read": "snowluma_api_catalog + snowluma_api_read / qzone Service",
    "sl_group_file_list": "snowluma_files；目录/搜索/链接",
    "sl_events": "snowluma_status view=events/event/search；未知字段可检索",
    "sl_user_info": "snowluma_group 或 snowluma_api_read / get_stranger_info（受作用域限制）",
    "sl_msg_history": "snowluma_messages view=history/detail/bot_recent",
    "sl_call": "snowluma_api_read + snowluma_manage；凭证/审批/流式有独立边界",
    "sl_qzone_post": "snowluma_manage / publish_qzone_detail（明确白名单，默认关闭）",
    "sl_qzone_interact": "snowluma_manage / 对应qzone action；不启动新自动互动引擎",
    "sl_group_file_upload": "snowluma_send kind=file；目录上传使用已审计的同主机公开命令兼容",
    "sl_poke": "snowluma_manage / group_poke 或 friend_poke",
    "sl_reaction": "snowluma_manage / set_msg_emoji_like",
    "sl_recall": "snowluma_manage / delete_msg",
    "sl_essence": "snowluma_messages view=essence + snowluma_manage 设置/移除",
    "sl_group_ban": "snowluma_manage / set_group_ban",
    "sl_group_whole_ban": "snowluma_manage / set_group_whole_ban",
    "sl_group_kick": "snowluma_manage / set_group_kick",
    "sl_group_card": "snowluma_manage / set_group_card",
    "sl_group_name": "snowluma_manage / set_group_name",
}


def route(entry: dict[str, Any]) -> str:
    """覆盖矩阵同时说明协议与策略边界，不将受限接口写成成功覆盖。"""
    if not entry["source_declared"]:
        return "当前源码未注册；自动调用拒绝（非运行实例实测）"
    if entry["risk"] == "stream_unavailable":
        return "协议有流式注册；单请求通道不承载多帧，明确拒绝；不伪实现"
    if entry["risk"] == "blocked":
        return "保留原Expand Service给可信插件；不向LLM暴露凭证/进程/原始包"
    if entry["risk"] == "approval_only" or "flag" in entry.get("arguments", []):
        return "snowluma_requests / snowluma_approve；通用入口拒绝flag"
    if not entry.get("backend_compatible", entry["expand_compatible"]):
        return "Expand明确标记不兼容；保留目录及原Service，不假称可用"
    if entry["action"] == "send_tuwen_ark":
        return "原Expand ark_service供可信插件；Plus拒绝原始旁路消息发送，普通分享使用snowluma_send"
    if entry["action"] in {
        "send_group_msg",
        "send_private_msg",
        "send_msg",
        "send_group_forward_msg",
        "send_private_forward_msg",
        "send_forward_msg",
        "forward_group_single_msg",
        "forward_friend_single_msg",
        "upload_forward_msg",
    }:
        return "snowluma_send（正常框架链路）；通用入口拒绝消息载荷旁路"
    return (
        "snowluma_api_read"
        if entry["risk"] == "read"
        else "snowluma_manage（操作者/群/action白名单）"
    ) + (" + 公开命令兼容" if entry.get("compatibility") else " + 原Expand Service")


def generate(workspace: Path, references: Path) -> None:
    """生成可重复的源码功能矩阵和已安装包审计，不包含用户配置和原日志。"""
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads((root / "resources/catalog.json").read_text(encoding="utf-8"))
    docs = root / "docs"
    audit = [
        "# 固定版本参考审计",
        "",
        "审计日：2026-10-21。下表是源码核对；未向QQ生产对象写入。代码实现独立编写，未复制参考插件实现。目录元数据的许可见 THIRD_PARTY_NOTICES.md。",
        "",
    ]
    summary = []
    for manifest_path in sorted(references.glob("*/*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        name = manifest["name"]
        ref_dir = manifest_path.parent
        meta = json.loads(
            (references / f"{name}.meta.json").read_text(encoding="utf-8-sig")
        )
        sha = (references / f"{name}.sha").read_text(encoding="utf-8-sig").strip()
        license_files = list(ref_dir.glob("LICENSE*"))
        tests = [
            p for p in ref_dir.rglob("*.py") if "test" in p.parts or "tests" in p.parts
        ]
        license_name = manifest.get("license") or "未声明/无许可文件，不复制实现"
        audit += [
            f"## [{meta['full_name']}](https://github.com/{meta['full_name']}/tree/{sha})",
            "",
            f"版本 `{manifest.get('version')}`；commit `{sha}`；manifest许可 `{license_name}`；许可文件 {', '.join(p.name for p in license_files) or '未发现'}；Python测试/检查文件 {len(tests)} 个。未运行其独立完整测试套件；当前安装Expand的相关回归另见验证报告。",
            "",
            "|原组件|Plus去向/限制|",
            "|---|---|",
        ]
        for component in manifest.get("include", []):
            key = component["component_name"]
            if component["component_type"] == "service":
                actions = [
                    e
                    for e in catalog["actions"]
                    if e.get("service") == f"onebot_expand:service:{key}"
                ]
                destination = f"保留 `{key}` 原响应契约；{len(actions)} 项方法进入API逐项矩阵；风险策略在Plus执行层，文件路径映射服务保留为可信插件能力"
            else:
                if key not in ROUTES:
                    raise RuntimeError(f"参考组件尚未人工映射: {name}/{key}")
                destination = ROUTES[key]
            audit.append(f"|`{component['component_type']}:{key}`|{destination}|")
        audit += [
            "",
            "源码核对包括 manifest、配置声明、注册入口、动作/工具/事件实现，以及仓库可见的测试/检查文件。配置不迁移为生产授权；所有旧owner逻辑由独立操作者/群/action策略替代。",
            "",
        ]
        summary.append(
            {
                "repository": meta["full_name"],
                "commit": sha,
                "version": manifest.get("version"),
                "license": license_name,
                "license_file_present": bool(license_files),
                "test_files": len(tests),
            }
        )
    (docs / "REFERENCE_AUDIT.md").write_text("\n".join(audit) + "\n", encoding="utf-8")
    (docs / "reference_versions.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    matrix = [
        "# API 逐项覆盖矩阵",
        "",
        f"由当前Expand定义自动生成：Expand {catalog['expand_version']}，{catalog['expand_api_count']} 项主API；加入参考目录额外6项后共 {len(catalog['actions'])} 项。SnowLuma本地源码 {catalog['snowluma_source_version']}。参考full目录声明的1.14.22与本地1.14.14分开记录，未把较新目录当作当前协议支持。",
        "",
        "`源码注册`只代表本地注册名称证据，**不是运行实例已支持或真实副作用实测**。所有常用封装复用下列Service，兼容分支见备注。别名在同一行执行相同授权。参数详情以 resources/catalog.json 的arguments/required为实际Plus调用契约；native_parameters用于审计候选，不是完整TypeScript类型推断。",
        "",
        "|Action / 别名|类别|源码注册|风险|可访问路径|兼容备注|",
        "|---|---|---|---|---|---|",
    ]
    for entry in catalog["actions"]:
        aliases = ", ".join(entry["aliases"])
        note = entry.get("compatibility", "")
        matrix.append(
            f"|`{entry['action']}`{(' / ' + aliases) if aliases else ''}|{entry['category']}|{'是' if entry['source_declared'] else '未确认'}|{entry['risk']}|{route(entry)}|{note}|"
        )
    matrix += [
        "",
        "目录源码摘要：",
        "",
        f"- Expand api_defs SHA256：`{catalog['expand_defs_sha256']}`",
        f"- SnowLuma actions源码合集 SHA256：`{catalog['source_actions_sha256']}`",
        "- 生成命令：`.venv/Scripts/python.exe plugins/snowluma_plus/scripts/generate_catalog.py`。当前生成器只执行已审计的本地Expand纯定义文件，不导入其他插件运行时。",
    ]
    (docs / "API_COVERAGE.md").write_text("\n".join(matrix) + "\n", encoding="utf-8")
    consumers = [
        "# 现有消费者与共存审计",
        "",
        "以下从本地已安装包静态读取，不执行包代码，不修改现有配置。注册项只是潜在处理入口，是否启用取决于当前配置和运行生命周期。",
        "",
        "|包|版本|涉及接收/提示的源码文件|",
        "|---|---|---|",
    ]
    pattern = re.compile(
        r"ON_RECEIVED_OTHER_MESSAGE|on_received_other_message|ON_NOTICE_RECEIVED|on_notice_received|BEFORE_MESSAGE_RECEIVED|before_message_received|on_prompt_build"
    )
    for path in sorted((workspace / "plugins").glob("*.mfp")):
        with zipfile.ZipFile(path) as archive:
            manifest_name = next(
                (name for name in archive.namelist() if name.endswith("manifest.json")),
                None,
            )
            manifest = json.loads(archive.read(manifest_name)) if manifest_name else {}
            files = [
                name
                for name in archive.namelist()
                if name.endswith(".py")
                and pattern.search(
                    archive.read(name).decode("utf-8-sig", errors="replace")
                )
            ]
            consumers.append(
                f"|{path.name}|{manifest.get('version', '未知')}|{', '.join(files) or '未发现上述静态订阅关键字'}|"
            )
    consumers += [
        "",
        "- OneBot Expand：保留SelfIdInjectHandler；新notice继续携带raw_event。真实普通消息显式声明message_type，避免禁言判断因空类型漏过。",
        "- neo_default_chatter：真实user_prompt的extra插槽；公开历史钩子传递过滤系统空正文后的副本，保留其他订阅者及extra。",
        "- neo_fatum_chatter：collect_plugin_turn_contributions的on_prompt_build入口；原历史source跳过系统空正文，不改其源码，不替换其他贡献。",
        "- neo-foxzone：仍负责其既有空间自动策略；Plus只提供受控手动API，不启动空间自动点赞/评论引擎。",
        "- emoji_sender / expression_guard：保留既有媒体和文本规则；Plus原生face采用显式结构段，不解析文本标记，不扫描代码或JSON。",
        "- 参考full/extension不建议同时开启重复业务Action或计划；本工作区未安装这两个参考插件。Expand建议保留Service，将重复LLM工具按其配置关闭；Plus不自动改写用户配置或移除别人的工具。",
    ]
    (docs / "COEXISTENCE.md").write_text("\n".join(consumers) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--references", type=Path, required=True)
    args = parser.parse_args()
    generate(Path(__file__).resolve().parents[3], args.references)
    print("generated reference/API/installed-consumer audit")
