"""从已审计公共契约生成显式签名，运行时不搜索接口、不拼模型JSON。"""

from __future__ import annotations

import ast
import json
import keyword
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 这些接口由手工业务组件提供更强的语义/分页/消息范围/正常发送契约。
BUSINESS = {
    "get_group_info": "snowluma_group_info",
    "get_group_member_info": "snowluma_find_member / snowluma_bot_identity",
    "get_group_member_list": "snowluma_find_member",
    "get_group_honor_info": "snowluma_group_honor",
    "_get_group_notice": "snowluma_list_notices",
    "get_essence_msg_list": "snowluma_list_essence",
    "get_group_msg_history": "snowluma_message_history",
    "get_friend_msg_history": "snowluma_message_history",
    "get_msg": "snowluma_message_detail",
    "get_msg_emoji_likes": "snowluma_message_reactions",
    "fetch_emoji_like": "snowluma_reaction_users",
    "fetch_sys_faces": "snowluma_find_face",
    "search_sys_faces": "snowluma_find_face",
    "fetch_custom_face_detail": "snowluma_emoji(kind=custom)",
    "fetch_super_face_id": "snowluma_emoji(kind=super)",
    "get_group_root_files": "snowluma_list_files",
    "get_group_files_by_folder": "snowluma_list_files",
    "get_group_file_url": "snowluma_file_url",
    "get_private_file_url": "snowluma_file_url",
    "send_like": "snowluma_profile_like",
    "group_poke": "snowluma_poke",
    "friend_poke": "snowluma_poke",
    "send_poke": "snowluma_poke",
    "set_msg_emoji_like": "snowluma_react_message",
    "delete_msg": "snowluma_recall_message",
    "set_group_sign": "snowluma_checkin",
    "set_group_ban": "snowluma_mute_member / snowluma_unmute_member",
    "set_group_whole_ban": "snowluma_whole_group_mute",
    "set_group_kick": "snowluma_kick_member",
    "set_group_card": "snowluma_set_member_card",
    "set_group_special_title": "snowluma_set_member_title",
    "set_group_name": "snowluma_rename_group",
    "_send_group_notice": "snowluma_publish_notice",
    "_del_group_notice": "snowluma_delete_notice",
    "set_essence_msg": "snowluma_set_essence",
    "delete_essence_msg": "snowluma_remove_essence",
}
for name in ("send_group_msg", "send_private_msg", "send_msg"):
    BUSINESS[name] = (
        "snowluma_send_text / snowluma_send_face / snowluma_reply_message / 媒体发送组件"
    )
for name in (
    "send_forward_msg",
    "send_group_forward_msg",
    "send_private_forward_msg",
    "forward_friend_single_msg",
    "forward_group_single_msg",
    "upload_forward_msg",
):
    BUSINESS[name] = "snowluma_forward_messages（框架正常发送）"
# 该接口构造原始转发/图文消息，受控框架发送不支持其专有图文协议。
BUSINESS["send_tuwen_ark"] = "可信Expand Service；模型不旁路框架发送图文转发"
BUSINESS["send_flash_msg"] = (
    "可信Expand Service；SnowLuma只返回占位message_id=0，无法确认正常消息发送与撤回"
)

LABELS = {
    "user_id": "目标QQ号，完整数字字符串",
    "group_id": "目标群号，空为当前群；跨群需授权",
    "message_id": "消息ID，支持平台ID及framework:前缀",
    "times": "次数",
    "count": "条数",
    "limit": "返回条数",
    "offset": "分页偏移",
    "page": "页码",
    "page_size": "每页条数",
    "no_cache": "是否绕过缓存",
    "refresh": "是否刷新",
    "file_id": "平台文件ID",
    "folder_id": "目录ID",
    "file": "文件来源，须通过本地允许目录及同主机检查",
    "file_path": "本机文件绝对路径，须授权",
    "name": "名称",
    "content": "内容",
    "text": "文字",
    "title": "标题",
    "duration": "持续秒数",
    "enable": "是否启用",
    "type": "类型",
    "album_id": "群相册ID",
    "album_name": "群相册名称",
    "emoji_id": "真实表情ID",
    "uin": "目标QQ号",
    "status": "平台状态编号",
    "group_name": "群名称",
    "file_hash": "平台文件哈希",
    "busid": "平台文件业务编号",
    "url": "来源网址，受外发来源策略约束",
}


def defaults(entry: dict) -> dict:
    """读取当前本地公共Service参数默认值；只解析AST，不导入其他插件。"""
    path = ROOT.parents[1] / entry.get("file", "")
    if not path.is_file():
        return {}
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == entry.get("method"):
            result = {}
            for argument, default in zip(
                node.args.args[-len(node.args.defaults) :], node.args.defaults
            ):
                try:
                    result[argument.arg] = ast.literal_eval(default)
                except (ValueError, TypeError):
                    result[argument.arg] = None
            return result
    return {}


def annotation(name: str, value: str) -> str:
    if name.endswith("_id") or name in {"uin", "qq"}:
        return "str"
    return {"int | str": "str", "list[dict]": "list[dict[str, Any]]"}.get(value, value)


def generate() -> None:
    catalog = json.loads((ROOT / "resources/catalog.json").read_text(encoding="utf-8"))[
        "actions"
    ]
    source = '''"""生成的直接业务组件；由generate_business_tools.py维护，业务实现独立编写。"""
from __future__ import annotations
from typing import Annotated, Any
from .typed import TypedRead, TypedWrite

'''
    classes, routes = [], []
    for entry in catalog:
        action = entry["action"]
        supported = entry["source_declared"] and entry.get(
            "backend_compatible", entry["expand_compatible"]
        )
        if not supported or entry["risk"] not in {"read", "write"}:
            routes.append(
                {
                    "action": action,
                    "route": entry["risk"] if supported else "当前审计源码未确认支持",
                    "generated": False,
                }
            )
            continue
        if action in BUSINESS:
            routes.append(
                {"action": action, "route": BUSINESS[action], "generated": False}
            )
            continue
        name = "snowluma_" + action.lstrip("_")
        cls = "Api" + "".join(part.title() for part in action.split("_") if part)
        classes.append(cls)
        default_values = defaults(entry)
        arguments = sorted(
            entry["arguments"],
            key=lambda key: key not in entry["required"] or key == "group_id",
        )
        signatures, expressions = [], []
        for key in arguments:
            variable = key + "_" if keyword.iskeyword(key) else key
            kind = annotation(key, entry["params"].get(key, "str"))
            required = key in entry["required"] and key != "group_id"
            default = "" if key == "group_id" else default_values.get(key)
            if kind == "str" and default is not None:
                default = str(default)
            if not required and default is None:
                kind += " | None"
            hint = LABELS.get(key, "接口参数：" + key)
            signatures.append(
                f"{variable}: Annotated[{kind}, {hint!r}]"
                + ("" if required else " = " + repr(default))
            )
            expressions.append(f"{key!r}: {variable}")
        description = (
            "直接" + entry["description"] + "。直接填写参数即可，无需查询API目录。"
        )
        if entry["risk"] == "write":
            description += "需相应动作/群/操作者授权，保留真实执行审计。"
        source += f"\nclass {cls}({'TypedRead' if entry['risk'] == 'read' else 'TypedWrite'}):\n"
        source += f"    name = {name!r}\n    description = {description!r}\n    api_action = {action!r}\n"
        source += (
            "    async def execute(self"
            + (", *, " + ", ".join(signatures) if signatures else "")
            + ") -> tuple[bool, str | dict]:\n"
        )
        source += f"        return await self.call({{{', '.join(expressions)}}})\n\n"
        routes.append(
            {
                "action": action,
                "route": name,
                "generated": True,
                "parameters": arguments,
            }
        )
    source += "\nGENERATED_COMPONENTS = [" + ", ".join(classes) + "]\n"
    (ROOT / "generated.py").write_text(source, encoding="utf-8")
    (ROOT / "resources/business_routes.json").write_text(
        json.dumps(routes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    docs = [
        "# 直接业务工具覆盖",
        "",
        "所有可确认且允许开放的接口都有直接参数组件或专用业务路径。模型不用填写action或params_json。保留的目录仅作低频资料说明。",
        "",
        "|接口|直接入口/限制|",
        "|---|---|",
    ]
    docs += [f"|`{row['action']}`|{row['route']}|" for row in routes]
    (ROOT / "docs/DIRECT_TOOLS.md").write_text("\n".join(docs) + "\n", encoding="utf-8")
    print(f"Generated {len(classes)} typed components; documented {len(routes)} routes")


if __name__ == "__main__":
    generate()
