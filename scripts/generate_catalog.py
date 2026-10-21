"""从已审计的 Expand 定义及 SnowLuma 注册源码生成可追溯静态目录。

只在维护/构建时运行；插件运行时不导入其他插件源码。
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import runpy
from pathlib import Path
from typing import Any


def native_parameters(text: str) -> dict[str, dict[str, Any]]:
    """提取声明式 action 的顶层参数名作为审计证据，不执行上游源码。"""
    matches = list(
        re.finditer(
            r"\b(defineAction|groupAction|groupUserAction|streamAction)\(\s*\{", text
        )
    )
    result: dict[str, dict[str, Any]] = {}
    for index, match in enumerate(matches):
        chunk = text[
            match.end() : matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        ]
        name = re.search(r"\bname\s*:\s*('([^']+)'|\"([^\"]+)\"|\[([^\]]+)\])", chunk)
        if not name:
            continue
        names = re.findall(r"['\"]([^'\"]+)['\"]", name.group(1))
        section = re.search(r"\n    params:\s*\{(.*?)\n    \},", chunk, re.S)
        arguments = (
            re.findall(r"^      (\w+):", section.group(1), re.M) if section else []
        )
        required = []
        if section:
            for line in section.group(1).splitlines():
                key = re.match(r"      (\w+):", line)
                if (
                    key
                    and ".optional(" not in line
                    and ".default(" not in line
                    and "f.raw(" not in line
                ):
                    required.append(key.group(1))
        if match.group(1) in {"groupAction", "groupUserAction"}:
            arguments.insert(0, "group_id")
            required.insert(0, "group_id")
        if match.group(1) == "groupUserAction":
            arguments.insert(1, "user_id")
            required.insert(1, "user_id")
        for action in names:
            result[action] = {
                "arguments": sorted(set(arguments)),
                "required": sorted(set(required)),
            }
    return result


def generate(workspace: Path, snowluma: Path) -> dict[str, Any]:
    """生成协议元数据及公共 Service 方法映射。"""
    expand = workspace / "plugins/onebot_expand"
    definitions = runpy.run_path(str(expand / "api_defs.py"))["ALL_APIS"]
    methods: dict[str, dict[str, Any]] = {}
    for path in sorted((expand / "services").glob("*_service.py")):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
            name = next(
                (
                    n.value.value
                    for n in cls.body
                    if isinstance(n, ast.AnnAssign)
                    and isinstance(n.target, ast.Name)
                    and n.target.id == "name"
                    and isinstance(n.value, ast.Constant)
                ),
                "",
            )
            for node in (n for n in cls.body if isinstance(n, ast.AsyncFunctionDef)):
                calls = [
                    n
                    for n in ast.walk(node)
                    if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Name)
                    and n.func.id == "_call_onebot_api"
                ]
                if (
                    len(calls) == 1
                    and calls[0].args
                    and isinstance(calls[0].args[0], ast.Constant)
                ):
                    args = [a.arg for a in node.args.args if a.arg != "self"]
                    required = args[: len(args) - len(node.args.defaults)]
                    methods[str(calls[0].args[0].value)] = {
                        "service": f"onebot_expand:service:{name}",
                        "method": node.name,
                        "arguments": args,
                        "required": required,
                        "file": path.relative_to(workspace).as_posix(),
                    }
    sources = sorted((snowluma / "packages/onebot/src/actions").rglob("*.ts"))
    source_text = "\n".join(p.read_text(encoding="utf-8-sig") for p in sources)
    native = native_parameters(source_text)
    # Action declarations use normalAction/streamAction with a canonical name.
    declared = set(
        re.findall(r"(?:name|action|canonical)\s*:\s*['\"]([^'\"]+)['\"]", source_text)
    )
    declared.update(
        re.findall(
            r"(?:defineAction|normalAction|streamAction)\(\s*['\"]([^'\"]+)['\"]",
            source_text,
        )
    )
    for names in re.findall(r"name\s*:\s*\[([^\]]+)\]", source_text):
        declared.update(re.findall(r"['\"]([^'\"]+)['\"]", names))
    actions = []
    for action, definition in definitions.items():
        entry = {
            "action": action,
            "category": definition.category.value,
            "description": definition.description,
            "params": definition.params,
            "aliases": list(definition.aliases),
            "expand_compatible": definition.snowluma_compat,
            "source_declared": action in declared,
            **methods.get(action, {}),
        }
        entry["stream"] = "stream" in action
        entry["risk"] = risk(action, definition.category.value)
        if action in native:
            entry["native_parameters"] = native[action]
        if action == "fetch_emoji_like":
            entry.update(
                arguments=["message_id", "emoji_id", "count", "cursor"],
                required=["message_id", "emoji_id"],
                compatibility="公共Service缺少cookie且将emojiId写为emoji_id；Plus通过公开适配器命令最小兼容，cursor为分页游标，非账号Cookie",
                params={
                    "message_id": "int | str",
                    "emoji_id": "str",
                    "count": "int",
                    "cursor": "str",
                },
            )
        if action == "upload_image_to_qun_album":
            entry.update(
                arguments=["group_id", "file", "album_id", "album_name"],
                required=["group_id", "file", "album_id", "album_name"],
                compatibility="公共Service缺少SnowLuma必填album_name；Plus通过公开适配器命令补齐，不修改Expand响应契约",
            )
            entry["params"] = {**entry["params"], "album_name": "str"}
        if action in {"upload_group_file", "upload_private_file"}:
            entry["compatibility"] = (
                "使用公开适配器命令发送已核验同主机的规范路径，避免Expand PathMapper在检查之后重映射为未核验远端路径；普通聊天文件优先snowluma_send"
            )
            entry["params"] = {
                "file_path": "str",
                **{
                    key: value
                    for key, value in entry["params"].items()
                    if key != "file"
                },
            }
        actions.append(entry)
    extras_path = (
        Path(__file__).resolve().parents[1] / "resources/reference_extra_apis.json"
    )
    if extras_path.exists():
        extra_catalog = json.loads(extras_path.read_text(encoding="utf-8"))
        existing = {entry["action"] for entry in actions} | {
            alias for entry in actions for alias in entry["aliases"]
        }
        for item in extra_catalog["actions"]:
            action = item["name"]
            if action in existing:
                continue
            arguments = [param["name"] for param in item["params"]]
            actions.append(
                {
                    "action": action,
                    "category": item["category"],
                    "description": item["summary"],
                    "params": {arg: "参照协议文档" for arg in arguments},
                    "aliases": item["aliases"],
                    "source_declared": action in declared,
                    "expand_compatible": False,
                    "backend_compatible": action in declared,
                    "arguments": arguments,
                    "required": [
                        param["name"]
                        for param in item["params"]
                        if param.get("required")
                    ],
                    "stream": item["stream"],
                    "risk": "stream_unavailable"
                    if item["stream"]
                    else risk(action, item["category"]),
                    "compatibility": "参考目录版本1.14.22；当前本地源码1.14.14必须另行确认注册。Expand无Service时才使用公开适配器命令。",
                    "reference": "snowluma_full/assets/sl_catalog.json",
                }
            )
    metadata = {
        "schema": 1,
        "expand_version": json.loads(
            (expand / "manifest.json").read_text(encoding="utf-8-sig")
        )["version"],
        "expand_api_count": len(definitions),
        "expand_defs_sha256": hashlib.sha256(
            (expand / "api_defs.py").read_bytes()
        ).hexdigest(),
        "snowluma_source_version": json.loads(
            (snowluma / "package.json").read_text(encoding="utf-8-sig")
        )["version"],
        "source_actions_sha256": hashlib.sha256(source_text.encode()).hexdigest(),
        "actions": actions,
    }
    output = Path(__file__).resolve().parents[1] / "resources/catalog.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return metadata


def risk(action: str, category: str) -> str:
    """保守分类；授权白名单仍不能放开凭证/原始包/进程/流式操作。"""
    if (
        any(
            word in action
            for word in (
                "cookie",
                "token",
                "credentials",
                "csrf",
                "restart",
                "clean_cache",
                "send_pb",
                "packet",
                "skey",
            )
        )
        or category == "cred"
    ):
        return "blocked"
    if "stream" in action:
        return "stream_unavailable"
    if action in {"set_friend_add_request", "set_group_add_request"}:
        return "approval_only"
    if action.startswith(
        ("get_", "fetch_", "can_", "check_", "query_", "ocr_")
    ) or action in {"_get_group_notice", "get_group_msg_history"}:
        return "read"
    return "write"


if __name__ == "__main__":
    result = generate(Path(__file__).resolve().parents[3], Path("E:/SnowLuma"))
    print(
        f"generated {len(result['actions'])} actions; {sum('service' in a for a in result['actions'])} public Service mappings"
    )
