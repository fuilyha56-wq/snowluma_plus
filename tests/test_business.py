"""持久审批、并发、快照、滚动统计和打卡契约。"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from ..gateway import BusinessError
from ..models import Scope, normalize
from .conftest import ACCOUNT, ADAPTER, GROUP, OPERATOR, USER, raw_notice


def ok(data=None):
    """合成成功协议响应，不代表真实平台验证。"""
    return {"status": "ok", "retcode": 0, "data": data}


@pytest.mark.parametrize(
    "request_type,subtype", [("friend", ""), ("group", "add"), ("group", "invite")]
)
async def test_concurrent_approval_once_and_flag_not_model_argument(
    env, request_type, subtype
):
    """同一申请并发只提交一次，flag/类型从服务端绑定。"""
    scope = Scope(ACCOUNT, ADAPTER, GROUP, USER)
    raw = {
        "post_type": "request",
        "request_type": request_type,
        "sub_type": subtype,
        "self_id": ACCOUNT,
        "user_id": USER,
        "flag": "internal-only",
        "comment": "测试",
    }
    if request_type == "group":
        raw["group_id"] = GROUP
    event = normalize(raw, ADAPTER, ACCOUNT)
    await env.runtime.ledger.accept(event)
    env.config.access.approval_mode = "assisted"
    action = (
        "set_group_add_request" if request_type == "group" else "set_friend_add_request"
    )
    env.config.access.allowed_actions = [action]
    calls = []

    async def backend(scope, name, params):
        """管理员查询和审批响应，审批延迟制造并发竞争。"""
        if name == "get_group_member_info":
            return ok({"role": "admin"})
        calls.append((name, params))
        await asyncio.sleep(0.01)
        return ok()

    env.runtime.gateway.raw_call = backend
    results = await asyncio.gather(
        *(
            env.runtime.business.approve(scope, OPERATOR, event.event_id, True)
            for _ in range(4)
        ),
        return_exceptions=True,
    )
    assert len(calls) == 1
    assert calls[0][1]["flag"] == "internal-only"
    assert (
        sum(isinstance(item, dict) and item["state"] == "approved" for item in results)
        == 1
    )
    rows = await env.runtime.business.request_list(scope, OPERATOR)
    assert len(rows) == 1 and "flag" not in rows[0]


async def test_approval_timeout_uncertain_and_cannot_resubmit(env):
    """超时可能已经执行，状态必须保持 uncertain，不能发第二次。"""
    scope = Scope(ACCOUNT, ADAPTER, user=USER)
    event = normalize(
        {
            "post_type": "request",
            "request_type": "friend",
            "self_id": ACCOUNT,
            "user_id": USER,
            "flag": "f",
        },
        ADAPTER,
        ACCOUNT,
    )
    await env.runtime.ledger.accept(event)
    env.config.access.approval_mode = "assisted"
    env.config.access.allowed_actions = ["set_friend_add_request"]
    backend = AsyncMock(side_effect=asyncio.TimeoutError)
    env.runtime.gateway.raw_call = backend
    with pytest.raises(asyncio.TimeoutError):
        await env.runtime.business.approve(scope, OPERATOR, event.event_id, True)
    with pytest.raises(BusinessError, match="pending"):
        await env.runtime.business.approve(scope, OPERATOR, event.event_id, True)
    assert backend.await_count == 1
    assert (await env.runtime.ledger.rows("SELECT state FROM requests"))[0][
        "state"
    ] == "uncertain"


@pytest.mark.parametrize(
    "response",
    [
        {"status": "failed", "retcode": 100, "wording": "flag expired"},
        {"status": "failed", "retcode": 1, "wording": "no permission"},
        {"status": "async", "retcode": 1},
        None,
    ],
)
async def test_approval_failure_never_success(env, response):
    """失效、无权限、异步或畸形返回不能报告成功。"""
    scope = Scope(ACCOUNT, ADAPTER, user=USER)
    event = normalize(
        {
            "post_type": "request",
            "request_type": "friend",
            "self_id": ACCOUNT,
            "user_id": USER,
            "flag": "f",
        },
        ADAPTER,
        ACCOUNT,
    )
    await env.runtime.ledger.accept(event)
    env.config.access.approval_mode = "assisted"
    env.config.access.allowed_actions = ["set_friend_add_request"]
    env.runtime.gateway.raw_call = AsyncMock(return_value=response)
    with pytest.raises(BusinessError):
        await env.runtime.business.approve(scope, OPERATOR, event.event_id, False)
    assert (await env.runtime.ledger.rows("SELECT state FROM requests"))[0][
        "state"
    ] in {"failed", "invalid", "uncertain"}


async def test_members_ttl_merge_and_stale_on_failure(env):
    """并发普通刷新只查询一次；失败保留旧索引。"""
    scope = Scope(ACCOUNT, ADAPTER, GROUP)
    backend = AsyncMock(
        return_value=ok(
            [
                {
                    "user_id": USER,
                    "nickname": "测试",
                    "card": "名片",
                    "title": "头衔",
                    "role": "member",
                }
            ]
        )
    )
    env.runtime.gateway.raw_call = backend
    values = await asyncio.gather(
        *(env.runtime.business.members(scope) for _ in range(8))
    )
    assert backend.await_count == 1 and all(
        v["data"][0]["user_id"] == USER for v in values
    )
    backend.side_effect = asyncio.TimeoutError
    stale = await env.runtime.business.members(scope, refresh=True)
    assert stale["stale"] and stale["data"][0]["card"] == "名片"
    assert await env.runtime.business.resolve_member(scope, "头衔", USER) == USER


async def test_duplicate_nicknames_return_candidates(env):
    """重名不猜 QQ。"""
    scope = Scope(ACCOUNT, ADAPTER, GROUP)
    await env.runtime.ledger.save_snapshot(
        scope,
        "members",
        [
            {"user_id": USER, "nickname": "同名"},
            {"user_id": OPERATOR, "nickname": "同名"},
        ],
        True,
    )
    with pytest.raises(BusinessError, match="歧义"):
        await env.runtime.business.resolve_member(scope, "同名", USER)


async def test_rolling_activity_duplicates_late_and_isolated(env):
    """滚动窗口去重按真实 ID，迟到消息可纳入，Bot 和窗口外排除。"""
    ledger = env.runtime.ledger
    scope = Scope(ACCOUNT, ADAPTER, GROUP)
    now = time.time()
    assert await ledger.activity(scope, "m1", USER, now - 300)
    assert not await ledger.activity(scope, "m1", USER, now - 300)
    assert await ledger.activity(scope, "late", USER, now - 86399)
    assert not await ledger.activity(scope, "old", USER, now - 86401)
    assert not await ledger.activity(scope, "self", ACCOUNT, now)
    assert not await ledger.activity(scope, "future", USER, now + 1000)
    other = Scope("other-account", ADAPTER, GROUP)
    assert await ledger.activity(other, "m1", OPERATOR, now)
    assert (await ledger.ranking(scope))[0]["messages"] == 2
    assert (await ledger.ranking(other))[0]["messages"] == 1
    await ledger.close()
    await ledger.open()
    assert (await ledger.ranking(scope))[0]["messages"] == 2


async def test_notice_baseline_diff_failed_and_partial_snapshot(env):
    """首次无播报，增改删正确，不完整/失败不能误报大量删除。"""
    scope = Scope(ACCOUNT, ADAPTER, GROUP)
    env.runtime.gateway.bot_role = AsyncMock(return_value={"role": "member"})
    backend = AsyncMock(return_value=ok([{"notice_id": "n1", "content": "旧公告"}]))
    env.runtime.gateway.raw_call = backend
    first = await env.runtime.business.notices(scope, emit=True)
    assert first["baseline"] and not await env.runtime.ledger.rows(
        "SELECT * FROM events"
    )
    backend.return_value = ok(
        [
            {"notice_id": "n1", "content": "新公告"},
            {"notice_id": "n2", "content": "新增"},
        ]
    )
    await env.runtime.business.notices(scope, emit=True)
    assert len(await env.runtime.ledger.rows("SELECT * FROM events")) == 2
    await env.runtime.business.notices(scope, emit=True)
    assert len(await env.runtime.ledger.rows("SELECT * FROM events")) == 2
    backend.return_value = ok({"notices": [], "has_more": True})
    partial = await env.runtime.business.notices(scope, emit=True)
    assert not partial["complete"]
    assert len((await env.runtime.ledger.snapshot(scope, "notices"))["data"]) == 2
    backend.side_effect = asyncio.TimeoutError
    with pytest.raises(asyncio.TimeoutError):
        await env.runtime.business.notices(scope, emit=True)
    backend.side_effect = None
    backend.return_value = ok([])
    await env.runtime.business.notices(scope, emit=True)
    assert len(await env.runtime.ledger.rows("SELECT * FROM events")) == 4


async def test_checkin_manual_scheduled_and_restart_same_day(env):
    """同一天多个入口并发共用成功记录，跨时区日期独立。"""
    scope = Scope(ACCOUNT, ADAPTER, GROUP)
    env.config.checkin.groups = [GROUP]
    env.config.access.write_groups = [GROUP]
    env.config.access.allowed_actions = ["set_group_sign"]
    backend = AsyncMock(return_value=ok())
    env.runtime.gateway.raw_call = backend
    local = datetime(2026, 10, 21, 0, 1, tzinfo=ZoneInfo("Asia/Shanghai"))
    results = await asyncio.gather(
        env.runtime.business.checkin(scope, OPERATOR, now=local),
        env.runtime.business.checkin(scope, "", scheduled=True, now=local),
    )
    assert backend.await_count == 1
    assert any(r["state"] == "success" for r in results)
    await env.runtime.ledger.close()
    await env.runtime.ledger.open()
    result = await env.runtime.business.checkin(scope, OPERATOR, now=local)
    assert result["state"] == "success" and not result["submitted"]
    assert backend.await_count == 1
    next_day = local.replace(day=22)
    await env.runtime.business.checkin(scope, OPERATOR, now=next_day)
    assert backend.await_count == 2


async def test_checkin_uncertain_not_retried_and_explicit_failure_bounded(env):
    """不确定不重试，明确失败最多配置次数。"""
    scope = Scope(ACCOUNT, ADAPTER, GROUP)
    env.config.checkin.groups = [GROUP]
    env.config.access.write_groups = [GROUP]
    env.config.access.allowed_actions = ["set_group_sign"]
    backend = AsyncMock(side_effect=asyncio.TimeoutError)
    env.runtime.gateway.raw_call = backend
    with pytest.raises(asyncio.TimeoutError):
        await env.runtime.business.checkin(scope, OPERATOR)
    assert (await env.runtime.business.checkin(scope, OPERATOR))["state"] == "uncertain"
    assert backend.await_count == 1


async def test_same_second_legitimate_notice_not_swallowed(env):
    """无平台唯一 ID 时保留完全相同的合法原始通知，不用时间桶去重。"""
    raw = raw_notice("notify", sub_type="poke", time=1_792_500_001)
    await env.adapter.on_platform_message(raw)
    await env.adapter.on_platform_message(raw)
    assert len(await env.runtime.ledger.rows("SELECT * FROM events")) == 2
