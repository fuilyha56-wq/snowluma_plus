"""显式启用的真实平台测试；只允许用户指定的1094860211群。"""

import json
import os
import time
import urllib.request
from types import SimpleNamespace

import pytest

from src.app.plugin_system.api import adapter_api, stream_api
from src.core.models.message import Message
from src.core.transport.message_send import message_sender

from ..direct import React, Recall, Text
from ..models import Scope
from .conftest import ADAPTER, USER
from .test_direct_tools import execute

pytestmark = pytest.mark.skipif(
    os.environ.get("SNOWLUMA_LIVE_TEST") != "1",
    reason="真实平台测试需显式启用及管理密码",
)
BASE = "http://127.0.0.1:5099"
TEST_GROUP, BOT = "1094860211", "3693525299"


async def test_live_current_backend_and_framework_message_roundtrip(env, monkeypatch):
    """真实HTTP既有账号；实际框架执行器/发送/历史，触发者为隔离测试驱动。"""
    token = ""
    sent_ids = set()
    report = {
        "group": TEST_GROUP,
        "account": BOT,
        "transport": "existing_instance_debug_invoke",
        "trigger": "isolated_test_driver_not_production_llm",
        "results": [],
    }

    def request(path, payload=None):
        headers = {"Content-Type": "application/json", "Origin": BASE}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(
            BASE + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)

    def invoke(action, params):
        read = {
            "get_version_info",
            "get_login_info",
            "get_group_info",
            "get_group_member_info",
            "get_group_member_list",
            "_get_group_notice",
            "get_essence_msg_list",
            "get_msg",
        }
        if action not in read:
            assert action in {"send_group_msg", "set_msg_emoji_like", "delete_msg"}
            if action == "send_group_msg":
                assert str(params.get("group_id")) == TEST_GROUP
                assert "SnowLuma Plus 授权测试" in json.dumps(
                    params, ensure_ascii=False
                )
            else:
                assert str(params.get("message_id")) in sent_ids
        if params.get("group_id"):
            assert str(params["group_id"]) == TEST_GROUP
        result = request(
            "/api/debug/invoke", {"uin": BOT, "action": action, "params": params}
        )
        # WebUI返回invokeAction的协议结果，不包裹伪成功。
        assert isinstance(result, dict), type(result).__name__
        if action == "send_group_msg" and result.get("retcode") == 0:
            mid = str((result.get("data") or {}).get("message_id") or "")
            assert mid and mid != "0"
            sent_ids.add(mid)
        return result

    try:
        auth = request("/api/login", {"password": os.environ["SNOWLUMA_TEST_PASSWORD"]})
        token = auth["token"]
        accounts = request("/api/qq-list")["list"]
        assert any(str(item["uin"]) == BOT for item in accounts)
        version = invoke("get_version_info", {})
        report["runtime_version"] = version.get("data")
        for action, params in [
            ("get_login_info", {}),
            ("get_group_info", {"group_id": TEST_GROUP}),
            (
                "get_group_member_info",
                {"group_id": TEST_GROUP, "user_id": BOT, "no_cache": True},
            ),
            ("get_group_member_list", {"group_id": TEST_GROUP}),
            ("_get_group_notice", {"group_id": TEST_GROUP}),
            ("get_essence_msg_list", {"group_id": TEST_GROUP}),
        ]:
            result = invoke(action, params)
            data = result.get("data")
            report["results"].append(
                {
                    "action": action,
                    "status": result.get("status"),
                    "retcode": result.get("retcode"),
                    "shape": type(data).__name__,
                    "count": len(data) if isinstance(data, list) else None,
                }
            )
            assert result.get("retcode") == 0, action

        # 用真实账号重新绑定兼容入口，保留合成测试数据库/配置。
        env.runtime.bindings.pop(ADAPTER).close()
        env.runtime.bound.clear()
        env.adapter_config.bot.qq_id = BOT
        await env.runtime.bind()
        scope = Scope(BOT, ADAPTER, TEST_GROUP, USER)
        stream = await stream_api.get_or_create_stream(
            stream_id=scope.stream_id,
            platform="qq",
            group_id=TEST_GROUP,
            chat_type="group",
        )
        env.runtime.scopes[stream.stream_id] = scope
        env.config.access.operators = []
        env.config.access.management_users = []
        trigger = Message(
            message_id="live-isolated-trigger",
            sender_id=USER,
            stream_id=stream.stream_id,
            platform="qq",
        )

        async def protocol(scope, action, params):
            assert scope.account == BOT and scope.group == TEST_GROUP
            return invoke(action, params)

        async def send_backend(*args, **kwargs):
            return invoke("send_group_msg", args[-1])

        async def command(signature, action, params, **kwargs):
            assert signature == ADAPTER
            return invoke(action, params)

        monkeypatch.setattr(env.runtime.gateway, "raw_call", protocol)
        monkeypatch.setattr(adapter_api, "send_adapter_command", command)
        env.adapter.send_handler.send_message_to_onebot = send_backend
        sender = message_sender.MessageSender()
        sender.set_adapter_manager(SimpleNamespace(get_adapter=lambda _: env.adapter))
        monkeypatch.setattr(message_sender, "_global_message_sender", sender)
        success, result = await execute(
            env,
            Text,
            trigger,
            text="SnowLuma Plus 授权测试：发送→表情回应→撤回。" + str(int(time.time())),
        )
        assert success, result
        mid = stream.context.history_messages[-1].message_id
        assert mid in sent_ids and "platform_message_id=" + mid in result
        report["results"].append(
            {
                "action": "snowluma_send_text",
                "success": success,
                "framework_history": True,
                "after_sent": env.runtime.counters["send_confirmed"] == 1,
            }
        )
        success, result = await execute(env, React, trigger, emoji="赞", message_id=mid)
        report["results"].append(
            {"action": "snowluma_react_message", "success": success}
        )
        assert success, result
        success, result = await execute(env, Recall, trigger, message_id=mid)
        report["results"].append(
            {"action": "snowluma_recall_message", "success": success}
        )
        assert success, result
        sent_ids.remove(mid)
    finally:
        for mid in list(sent_ids):
            result = invoke("delete_msg", {"message_id": mid})
            report["results"].append(
                {"action": "cleanup_own_test_message", "retcode": result.get("retcode")}
            )
        if token:
            request("/api/logout", {})
        from pathlib import Path

        (
            Path(__file__).resolve().parents[1] / ".test-work/live-report.json"
        ).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
