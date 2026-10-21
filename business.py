"""成员索引、公告快照、审批和每日打卡的持久业务状态。"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .gateway import BusinessError, Gateway, UncertainError, response_data
from .models import Scope, identifier, json_text, normalize, redact
from .store import Ledger


class Business:
    """并发刷新合并，副作用 CAS，首次轮询只建立基线。"""

    def __init__(self, gateway: Gateway, ledger: Ledger) -> None:
        """所有状态按 scope 隔离。"""
        self.gateway, self.ledger = gateway, ledger
        self.config = gateway.config
        self.locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def read(self, scope: Scope, action: str, params: dict[str, Any]) -> Any:
        """后台只读能力，仍核验名单和目录风险。"""
        return response_data(
            await self.gateway.call(scope, "", action, params, trusted=True)
        )

    async def members(self, scope: Scope, refresh: bool = False) -> dict[str, Any]:
        """TTL 和双重检查合并刷新；失败保留旧值并标记 stale。"""
        if not scope.group:
            raise BusinessError("成员索引需要群会话")
        self.gateway.allowed_scope(scope)
        requested_at = time.time()
        async with self.locks[f"members:{scope.key}"]:
            old = await self.ledger.snapshot(scope, "members")
            if (
                old
                and old["complete"]
                and (
                    (
                        not refresh
                        and time.time() - old["at"] < self.config.members.ttl_seconds
                    )
                    or old["at"] >= requested_at
                )
            ):
                return {**old, "stale": False, "source": "platform_cache"}
            try:
                data = await self.read(
                    scope, "get_group_member_list", {"group_id": scope.group}
                )
                if not isinstance(data, list) or not all(
                    isinstance(row, dict) and row.get("user_id") is not None
                    for row in data
                ):
                    raise BusinessError("成员列表响应畸形，不覆盖旧索引")
                await self.ledger.save_snapshot(scope, "members", data, True)
                return {
                    "data": data,
                    "at": time.time(),
                    "complete": True,
                    "stale": False,
                    "source": "platform",
                }
            except Exception as exc:
                if old and isinstance(old.get("data"), list):
                    return {
                        **old,
                        "stale": True,
                        "error": type(exc).__name__,
                        "source": "platform_cache",
                    }
                raise BusinessError(
                    f"成员索引尚无资料，刷新失败：{type(exc).__name__}"
                ) from exc

    async def resolve_member(self, scope: Scope, target: str, operator: str) -> str:
        """真实 ID 优先；昵称/名片/头衔完全匹配有歧义时列候选。"""
        if target in {"我", "自己", "me", ""}:
            if not operator:
                raise BusinessError("当前调用没有真实触发者")
            return operator
        if target.isdecimal():
            return target
        snapshot = await self.members(scope)
        if snapshot.get("stale") or not snapshot.get("complete"):
            raise BusinessError(
                "成员索引过期或不完整，不能可靠解析昵称；请使用QQ号或主动刷新"
            )
        matches = [
            m
            for m in snapshot["data"]
            if target
            in {
                str(m.get(k) or "")
                for k in ("nickname", "card", "title", "special_title")
            }
        ]
        if len(matches) != 1:
            candidates = [
                {k: m.get(k) for k in ("user_id", "nickname", "card", "title", "role")}
                for m in matches[:10]
            ]
            raise BusinessError(
                f"成员匹配{'歧义' if matches else '为空'}；请提供QQ号；候选={json_text(candidates)}"
            )
        return identifier(matches[0]["user_id"])

    async def notices(
        self,
        scope: Scope,
        *,
        emit: bool = True,
        source: str = "poll_diff",
        reset: bool = False,
    ) -> dict[str, Any]:
        """共享读取/轮询快照；失败和不完整分页绝不误报删除。"""
        if not scope.group:
            raise BusinessError("公告需要群会话")
        self.gateway.allowed_scope(scope)
        async with self.locks[f"notices:{scope.key}"]:
            old = await self.ledger.snapshot(scope, "notices")
            data = await self.read(
                scope, "_get_group_notice", {"group_id": scope.group}
            )
            # 当前源码 _get_group_notice 无分页参数；后端返回完整列表。
            rows = (
                data
                if isinstance(data, list)
                else data.get("notices")
                if isinstance(data, dict)
                else None
            )
            if not isinstance(rows, list) or not all(
                isinstance(item, dict) for item in rows
            ):
                raise BusinessError("公告响应没有可靠列表，旧基线保持不变")
            normalized = {
                str(item.get("notice_id") or item.get("id") or item.get("fid")): item
                for item in rows
                if item.get("notice_id") or item.get("id") or item.get("fid")
            }
            complete = (
                len(normalized) == len(rows)
                and len(rows) <= self.config.announcements.max_items
                and not (
                    isinstance(data, dict)
                    and (
                        data.get("has_more")
                        or data.get("next_token")
                        or data.get("incomplete")
                    )
                )
            )
            if not complete:
                return {
                    "data": rows,
                    "complete": False,
                    "at": time.time(),
                    "source": "platform",
                    "note": "列表缺 ID 或分页未完成，未覆盖基线，未生成删除事件",
                }
            before = (
                old["data"]
                if old
                and old["complete"]
                and isinstance(old["data"], dict)
                and not reset
                else None
            )
            if before is None:
                try:
                    role = (await self.gateway.bot_role(scope)).get("role")
                except (BusinessError, asyncio.TimeoutError):
                    role = None
                await self.ledger.save_snapshot(
                    scope, "notice_authority", {"role": role}, bool(role)
                )
            elif set(before) - set(normalized):
                authority = await self.ledger.snapshot(scope, "notice_authority")
                try:
                    current_role = (await self.gateway.bot_role(scope)).get("role")
                except (BusinessError, asyncio.TimeoutError):
                    current_role = None
                if (
                    not authority
                    or not isinstance(authority.get("data"), dict)
                    or not current_role
                    or authority["data"].get("role") != current_role
                ):
                    return {
                        "data": rows,
                        "complete": False,
                        "source": "platform",
                        "at": time.time(),
                        "note": "角色/权限变化或未知，暂停删除差异并保留旧基线；授权操作者可用rebaseline重建",
                    }
            if before is not None and emit:
                for key in sorted(set(before) | set(normalized)):
                    previous, current = before.get(key), normalized.get(key)
                    if previous == current:
                        continue
                    change = (
                        "add"
                        if previous is None
                        else "delete"
                        if current is None
                        else "update"
                    )
                    # 状态内容指纹用于合并读取/轮询/本地写入后的相同快照。
                    signature = hashlib.sha256(
                        json_text([scope.key, key, previous, current]).encode()
                    ).hexdigest()
                    raw = {
                        "post_type": "notice",
                        "notice_type": "group_notice",
                        "sub_type": change,
                        "group_id": scope.group,
                        "self_id": scope.account,
                        "notice_id": key,
                        "event_id": f"notice-diff:{signature}",
                        "notice": current or previous,
                        "time": time.time(),
                    }
                    await self.ledger.accept(
                        normalize(raw, scope.adapter, scope.account, source)
                    )
            await self.ledger.save_snapshot(scope, "notices", normalized, True)
            return {
                "data": list(normalized.values()),
                "complete": True,
                "at": time.time(),
                "source": "platform",
                "baseline": before is None,
            }

    async def observe_notice(self, scope: Scope, raw: dict[str, Any]) -> None:
        """完整原生公告与轮询共享基线；字段不足时不猜内容、也不误删。"""
        notice_id = identifier(raw.get("notice_id") or raw.get("fid"))
        if not notice_id:
            return
        async with self.locks[f"notices:{scope.key}"]:
            old = await self.ledger.snapshot(scope, "notices")
            if not old or not old["complete"]:
                return
            data = dict(old["data"])
            if raw.get("sub_type") in {"delete", "remove"}:
                data.pop(notice_id, None)
            elif isinstance(raw.get("notice"), dict):
                data[notice_id] = raw["notice"]
            else:
                return
            await self.ledger.save_snapshot(scope, "notices", data, True)

    async def request_list(
        self,
        scope: Scope,
        operator: str,
        offset: int = 0,
        limit: int = 10,
        request_id: str = "",
    ) -> list[dict[str, Any]]:
        """申请详情与历史只对授权操作者开放；flag 永不返回。"""
        self.gateway.allowed_scope(scope, operator)
        if operator not in self.config.access.operators:
            raise BusinessError("审批资料仅供 access.operators 中的操作者查看")
        await self.ledger.write(
            "UPDATE requests SET state='expired',updated=? WHERE state='pending' AND received<?",
            (time.time(), time.time() - self.config.access.requests_ttl_hours * 3600),
        )
        sql = "SELECT r.id AS request_id,r.kind,r.subtype,r.group_id,r.applicant,r.comment,r.received,r.state,r.result,r.updated,e.raw AS request_raw FROM requests r JOIN events e ON r.id=e.id WHERE r.account=? AND r.adapter=?"
        args: tuple[Any, ...] = (scope.account, scope.adapter)
        if request_id:
            sql += " AND r.id=?"
            args += (request_id,)
        sql += " ORDER BY r.received DESC LIMIT ? OFFSET ?"
        rows = await self.ledger.rows(sql, (*args, limit, offset))
        for row in rows:
            raw = json.loads(row.pop("request_raw"))
            row["invited_id"] = identifier(raw.get("invited_id"))
            row["raw_ref"] = f"ledger:{row['request_id']}"
        return redact(rows)

    async def approve(
        self,
        scope: Scope,
        operator: str,
        request_id: str,
        approve: bool,
        reason: str = "",
        *,
        automatic: bool = False,
    ) -> dict[str, Any]:
        """服务端绑定 flag/类型；CAS 保证并发一次提交，超时不自动再次提交。"""
        self.gateway.allowed_scope(scope, operator if not automatic else "")
        if self.config.access.approval_mode == "remind" or (
            not automatic and operator not in self.config.access.operators
        ):
            raise BusinessError("审批当前仅提醒或操作者未获授权")
        rows = await self.ledger.rows(
            "SELECT r.*,e.raw FROM requests r JOIN events e ON r.id=e.id WHERE r.id=? AND r.account=? AND r.adapter=?",
            (request_id, scope.account, scope.adapter),
        )
        if not rows:
            raise BusinessError("待办不存在；请求未到达时不能从日志生成申请")
        row = rows[0]
        target = Scope(scope.account, scope.adapter, row["group_id"], row["applicant"])
        self.gateway.allowed_scope(target, row["applicant"])
        action = (
            "set_group_add_request"
            if row["kind"] == "group"
            else "set_friend_add_request"
        )
        if action not in self.config.access.allowed_actions:
            raise BusinessError("审批 action 未被明确授权")
        if row["kind"] == "group":
            if row["group_id"] not in self.config.access.approval_groups or row[
                "subtype"
            ] not in {"add", "invite"}:
                raise BusinessError("群申请范围/子类型未授权或不支持")
            invited = identifier(json.loads(row["raw"]).get("invited_id"))
            if row["subtype"] == "add" or (invited and invited != scope.account):
                bot = await self.gateway.bot_role(target)
                if bot.get("role") not in {"admin", "owner"}:
                    raise BusinessError("Bot 没有处理本群申请的平台权限")
        if automatic and (
            self.config.access.approval_mode != "auto"
            or row["applicant"] not in self.config.access.auto_applicants
            or not re.fullmatch(self.config.access.auto_reason_pattern, row["comment"])
        ):
            raise BusinessError("申请不满足明确的自动审批规则")
        if row["received"] < time.time() - self.config.access.requests_ttl_hours * 3600:
            await self.ledger.write(
                "UPDATE requests SET state='expired',updated=? WHERE id=? AND state='pending'",
                (time.time(), request_id),
            )
            raise BusinessError("本地待办已过期，请通过平台核实")
        if (
            await self.ledger.write(
                "UPDATE requests SET state='processing',updated=? WHERE id=? AND state='pending'",
                (time.time(), request_id),
            )
            != 1
        ):
            raise BusinessError(f"待办不处于 pending（{row['state']}），禁止重复提交")
        params: dict[str, Any] = {"flag": row["flag"], "approve": approve}
        if row["kind"] == "group":
            params.update(sub_type=row["subtype"], reason=reason)
        else:
            params["remark"] = reason
        op = f"approval:{request_id}"
        await self.ledger.claim(
            op, target, action, operator or "configured_auto_rule", "local_action"
        )
        try:
            response = await self.gateway.raw_call(target, action, params)
            response_data(response)
            state = "approved" if approve else "rejected"
        except (asyncio.TimeoutError, asyncio.CancelledError):
            await self.ledger.write(
                "UPDATE requests SET state='uncertain',result='超时/取消，不自动再次提交',updated=? WHERE id=?",
                (time.time(), request_id),
            )
            await self.ledger.operation_result(op, "uncertain", "超时/取消；需平台核实")
            raise
        except Exception as exc:
            # 明确的过期/已处理协议错误归入 invalid，其余失败不冒充成功。
            text = str(exc).replace(row["flag"], "[已隐藏]")
            state = (
                "invalid"
                if any(
                    word in text.lower()
                    for word in ("expired", "already", "已处理", "过期", "失效")
                )
                else "failed"
                if isinstance(exc, BusinessError)
                and not isinstance(exc, UncertainError)
                else "uncertain"
            )
            await self.ledger.write(
                "UPDATE requests SET state=?,result=?,updated=? WHERE id=?",
                (state, text[:500], time.time(), request_id),
            )
            await self.ledger.operation_result(op, state, text[:500])
            if text != str(exc):
                raise type(exc)(text) from exc
            raise
        await self.ledger.write(
            "UPDATE requests SET state=?,result=?,updated=? WHERE id=?",
            (state, json_text(redact(response)), time.time(), request_id),
        )
        await self.ledger.operation_result(op, "success", response)
        return {"request_id": request_id, "state": state, "source": "protocol_response"}

    async def checkin(
        self,
        scope: Scope,
        operator: str,
        *,
        scheduled: bool = False,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """日期、账号、群共用操作键；明确失败可有限重试，uncertain 不重试。"""
        config = self.config.checkin
        if not scope.group or scope.group not in config.groups:
            raise BusinessError("群未在 checkin.groups 白名单")
        self.gateway.authorize(
            scope,
            operator,
            "set_group_sign",
            True,
            {"group_id": scope.group},
            trusted=scheduled,
        )
        day = (
            (now or datetime.now(ZoneInfo(config.timezone)))
            .astimezone(ZoneInfo(config.timezone))
            .date()
            .isoformat()
        )
        operation_id = (
            "checkin:"
            + hashlib.sha256(json_text([scope.key, day]).encode()).hexdigest()
        )
        if not await self.ledger.claim(
            operation_id,
            scope,
            "set_group_sign",
            operator or "scheduler",
            "scheduled" if scheduled else "manual",
            retries=config.retries,
        ):
            rows = await self.ledger.rows(
                "SELECT state,result,at,attempts FROM operations WHERE id=?",
                (operation_id,),
            )
            return {"date": day, "submitted": False, **rows[0]}
        try:
            response = await self.gateway.raw_call(
                scope, "set_group_sign", {"group_id": scope.group}
            )
            if response_data(response) is False:
                raise UncertainError(
                    "打卡响应status成功但data=false，需核实实际日期状态"
                )
            completed_day = (
                (now or datetime.now(ZoneInfo(config.timezone)))
                .astimezone(ZoneInfo(config.timezone))
                .date()
                .isoformat()
            )
            if completed_day != day:
                next_id = (
                    "checkin:"
                    + hashlib.sha256(
                        json_text([scope.key, completed_day]).encode()
                    ).hexdigest()
                )
                if await self.ledger.claim(
                    next_id,
                    scope,
                    "set_group_sign",
                    operator or "scheduler",
                    "midnight_guard",
                ):
                    await self.ledger.operation_result(
                        next_id, "uncertain", "在途请求跨越午夜，实际打卡归属日期待核实"
                    )
                raise UncertainError(
                    "打卡请求跨越配置时区午夜，两个日期均待核实，禁止自动重复提交"
                )
        except (asyncio.TimeoutError, asyncio.CancelledError):
            await self.ledger.operation_result(
                operation_id,
                "uncertain",
                "API 超时或取消，需核实今日签到列表，禁止自动再次提交",
            )
            raise
        except Exception as exc:
            await self.ledger.operation_result(
                operation_id,
                "failed"
                if isinstance(exc, BusinessError)
                and not isinstance(exc, UncertainError)
                else "uncertain",
                type(exc).__name__,
            )
            raise
        await self.ledger.operation_result(operation_id, "success", response)
        return {
            "date": day,
            "state": "success",
            "submitted": True,
            "source": "protocol_response",
        }
