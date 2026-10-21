"""独立 SQLite WAL 账本；队列只是提示，审批和副作用状态先落盘。"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import aiosqlite

from .models import Scope, UnifiedEvent, json_text, redact

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
 seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
 scope TEXT NOT NULL, adapter TEXT NOT NULL, account TEXT NOT NULL,
 raw TEXT NOT NULL, source TEXT NOT NULL, received REAL NOT NULL,
 state TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
 next_at REAL NOT NULL DEFAULT 0, error TEXT NOT NULL DEFAULT '', delivered REAL,
 framework INTEGER NOT NULL DEFAULT 0, consumed INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS events_pending ON events(state, next_at, seq);
CREATE TABLE IF NOT EXISTS requests (
 id TEXT PRIMARY KEY REFERENCES events(id), scope TEXT NOT NULL, account TEXT NOT NULL,
 adapter TEXT NOT NULL, kind TEXT NOT NULL, subtype TEXT NOT NULL, group_id TEXT NOT NULL,
 applicant TEXT NOT NULL, flag TEXT NOT NULL, comment TEXT NOT NULL, received REAL NOT NULL,
 state TEXT NOT NULL, result TEXT NOT NULL DEFAULT '', updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS activity (
 scope TEXT NOT NULL, message_id TEXT NOT NULL, user_id TEXT NOT NULL, at REAL NOT NULL,
 PRIMARY KEY(scope,message_id)
);
CREATE INDEX IF NOT EXISTS activity_window ON activity(scope,at);
CREATE TABLE IF NOT EXISTS mappings (
 scope TEXT NOT NULL, framework_id TEXT NOT NULL, platform_id TEXT NOT NULL,
 at REAL NOT NULL, PRIMARY KEY(scope,framework_id)
);
CREATE TABLE IF NOT EXISTS snapshots (
 scope TEXT NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL, at REAL NOT NULL,
 complete INTEGER NOT NULL, PRIMARY KEY(scope,kind)
);
CREATE TABLE IF NOT EXISTS operations (
 id TEXT PRIMARY KEY, scope TEXT NOT NULL, kind TEXT NOT NULL, operator TEXT NOT NULL,
 source TEXT NOT NULL, state TEXT NOT NULL, result TEXT NOT NULL, at REAL NOT NULL,
 attempts INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
PRAGMA user_version=1;
"""


class Ledger:
    """同进程串行事务，跨进程用 SQLite 唯一键/CAS 防重复。"""

    def __init__(self, path: Path) -> None:
        """只保存明确的数据路径，延迟建立连接。"""
        self.path = path
        self.db: aiosqlite.Connection | None = None
        self.lock = asyncio.Lock()

    async def open(self) -> None:
        """初始化；恢复中断审批/打卡为 uncertain，事件继续重放。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = await aiosqlite.connect(self.path)
        self.db.row_factory = aiosqlite.Row
        async with self.db.execute("PRAGMA user_version") as cursor:
            version = (await cursor.fetchone())[0]
        if version > 1:
            await self.db.close()
            self.db = None
            raise RuntimeError(
                f"事件账本版本 {version} 高于本插件支持版本1；拒绝覆盖，请升级插件或恢复备份"
            )
        await self.db.execute("PRAGMA journal_mode=WAL")
        await self.db.execute("PRAGMA synchronous=FULL")
        await self.db.execute("PRAGMA busy_timeout=3000")
        await self.db.executescript(SCHEMA)
        await self.db.execute(
            "UPDATE requests SET state='uncertain',result='进程在提交期间中断，禁止自动再次提交' WHERE state='processing'"
        )
        await self.db.execute(
            "UPDATE operations SET state='uncertain',result='进程中断，需核实协议端结果' WHERE state='processing'"
        )
        await self.db.commit()

    def connection(self) -> aiosqlite.Connection:
        """要求已打开的连接。"""
        if self.db is None:
            raise RuntimeError("事件账本尚未打开或已关闭")
        return self.db

    async def close(self) -> None:
        """有界生命周期调用方负责停 worker 后关闭。"""
        async with self.lock:
            if self.db is not None:
                await self.db.close()
                self.db = None

    async def rows(
        self, sql: str, params: tuple[Any, ...] = ()
    ) -> list[dict[str, Any]]:
        """参数化只读查询。"""
        async with self.lock:
            async with self.connection().execute(sql, params) as cur:
                return [dict(row) for row in await cur.fetchall()]

    async def write(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        """提交一个状态变更，返回 CAS 影响行数。"""
        async with self.lock:
            db = self.connection()
            try:
                cur = await db.execute(sql, params)
                await db.commit()
                return cur.rowcount
            except BaseException:
                await db.rollback()
                raise

    async def accept(self, event: UnifiedEvent) -> bool:
        """事件和审批在同一事务内落盘；重复返回 False。"""
        async with self.lock:
            db = self.connection()
            try:
                cur = await db.execute(
                    "INSERT OR IGNORE INTO events(id,scope,adapter,account,raw,source,received) VALUES(?,?,?,?,?,?,?)",
                    (
                        event.event_id,
                        event.scope.key,
                        event.scope.adapter,
                        event.scope.account,
                        json_text(event.data),
                        event.source,
                        event.received_at,
                    ),
                )
                inserted = cur.rowcount == 1
                raw = event.data
                if (
                    inserted
                    and event.scope.group
                    and raw.get("notice_type")
                    in {"group_ban", "group_whole_ban", "group_whole_ban_status"}
                ):
                    async with db.execute(
                        "SELECT data FROM snapshots WHERE scope=? AND kind='mute'",
                        (event.scope.key,),
                    ) as cursor:
                        old = await cursor.fetchone()
                    try:
                        mute = (
                            json.loads(old[0]) if old else {"until": 0, "whole": False}
                        )
                        if not isinstance(mute, dict):
                            raise ValueError("invalid_mute_snapshot")
                    except (ValueError, TypeError):
                        mute = {"until": 0, "whole": False, "unknown_snapshot": True}
                    target = str(raw.get("user_id") or "0")
                    if raw.get("notice_type") != "group_ban":
                        mute["whole"] = str(raw.get("enable")).lower() in {
                            "true",
                            "1",
                            "on",
                            "enable",
                            "yes",
                        }
                    elif target == "0":
                        mute["whole"] = raw.get("sub_type") == "ban"
                    elif target == event.scope.account:
                        if raw.get("sub_type") == "lift_ban":
                            mute["until"] = 0
                            mute.pop("unknown_duration", None)
                        else:
                            try:
                                duration = max(0, float(raw.get("duration", 0)))
                                mute["until"] = event.occurred_at + duration
                                mute.pop("unknown_duration", None)
                            except (TypeError, ValueError):
                                mute["unknown_duration"] = True
                    await db.execute(
                        "INSERT INTO snapshots(scope,kind,data,at,complete) VALUES(?,'mute',?,?,1) ON CONFLICT(scope,kind) DO UPDATE SET data=excluded.data,at=excluded.at,complete=1",
                        (event.scope.key, json_text(mute), event.received_at),
                    )
                if inserted and event.data.get("post_type") == "request":
                    valid = bool(
                        event.data.get("flag")
                        and event.scope.user
                        and event.kind in {"friend", "group"}
                    )
                    if event.kind == "group":
                        valid = (
                            valid
                            and bool(event.scope.group)
                            and event.subtype in {"add", "invite"}
                        )
                    state = "pending" if valid else "invalid"
                    await db.execute(
                        "INSERT INTO requests(id,scope,account,adapter,kind,subtype,group_id,applicant,flag,comment,received,state,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            event.event_id,
                            event.scope.key,
                            event.scope.account,
                            event.scope.adapter,
                            event.kind,
                            event.subtype,
                            event.scope.group,
                            event.scope.user,
                            str(event.data.get("flag") or ""),
                            str(event.data.get("comment") or ""),
                            event.received_at,
                            state,
                            event.received_at,
                        ),
                    )
                await db.commit()
                return inserted
            except BaseException:
                await db.rollback()
                raise

    async def pending(self, limit: int = 25) -> list[dict[str, Any]]:
        """读取按到达顺序可重放的事件。"""
        return await self.rows(
            "SELECT e.* FROM events e WHERE e.state='pending' AND e.next_at<=? AND NOT EXISTS (SELECT 1 FROM events earlier WHERE earlier.scope=e.scope AND earlier.state='pending' AND earlier.seq<e.seq) ORDER BY e.seq LIMIT ?",
            (time.time(), limit),
        )

    async def finish(self, event_id: str, state: str, error: str = "") -> None:
        """记录投递、策略忽略或失败原因；不删除原始事件。"""
        await self.write(
            "UPDATE events SET state=?,error=?,delivered=? WHERE id=?",
            (state, error, time.time(), event_id),
        )

    async def failed(self, row: dict[str, Any], error: str, retries: int) -> None:
        """投递有限重试；终止后仍可人工查账和重放。"""
        attempt = row["attempts"] + 1
        await self.write(
            "UPDATE events SET state=?,attempts=?,error=?,next_at=? WHERE id=?",
            (
                "failed" if attempt >= retries else "pending",
                attempt,
                error[:300],
                time.time() + min(60, 2**attempt),
                row["id"],
            ),
        )

    async def activity(
        self, scope: Scope, message_id: str, user: str, at: float
    ) -> bool:
        """实时/历史共用真实平台 ID，拒绝 Bot、缺 ID、窗口外和明显未来数据。"""
        now = time.time()
        if (
            not message_id
            or not user
            or user == scope.account
            or not now - 86400 < at <= now + 5
        ):
            return False
        return (
            await self.write(
                "INSERT OR IGNORE INTO activity(scope,message_id,user_id,at) VALUES(?,?,?,?)",
                (scope.key, message_id, user, at),
            )
            == 1
        )

    async def ranking(
        self, scope: Scope, limit: int = 10, offset: int = 0
    ) -> list[dict[str, Any]]:
        """滚动窗口，不按自然日清零。"""
        return await self.rows(
            "SELECT user_id,COUNT(*) AS messages,MAX(at) AS last_at FROM activity WHERE scope=? AND at>? AND at<=? GROUP BY user_id ORDER BY messages DESC,user_id LIMIT ? OFFSET ?",
            (scope.key, time.time() - 86400, time.time() + 5, limit, offset),
        )

    async def snapshot(self, scope: Scope, kind: str) -> dict[str, Any] | None:
        """读取最后可用快照及完整性。"""
        rows = await self.rows(
            "SELECT * FROM snapshots WHERE scope=? AND kind=?", (scope.key, kind)
        )
        if not rows:
            return None
        result = rows[0]
        try:
            result["data"] = json.loads(result["data"])
        except (ValueError, TypeError):
            result.update(data=None, complete=0, error="snapshot_invalid_json")
        return result

    async def save_snapshot(
        self, scope: Scope, kind: str, data: Any, complete: bool
    ) -> None:
        """只有调用方确认的有效快照才能覆盖旧资料。"""
        await self.write(
            "INSERT INTO snapshots(scope,kind,data,at,complete) VALUES(?,?,?,?,?) ON CONFLICT(scope,kind) DO UPDATE SET data=excluded.data,at=excluded.at,complete=excluded.complete",
            (scope.key, kind, json_text(data), time.time(), int(complete)),
        )

    async def claim(
        self,
        operation_id: str,
        scope: Scope,
        kind: str,
        operator: str,
        source: str,
        retries: int = 0,
    ) -> bool:
        """提交前落 processing；唯一键阻止并发和重启二次副作用。"""
        async with self.lock:
            db = self.connection()
            try:
                cur = await db.execute(
                    "INSERT OR IGNORE INTO operations(id,scope,kind,operator,source,state,result,at) VALUES(?,?,?,?,?,'processing','',?)",
                    (operation_id, scope.key, kind, operator, source, time.time()),
                )
                claimed = cur.rowcount == 1
                if not claimed and retries:
                    cur = await db.execute(
                        "UPDATE operations SET state='processing',attempts=attempts+1,at=? WHERE id=? AND state='failed' AND attempts<=?",
                        (time.time(), operation_id, retries),
                    )
                    claimed = cur.rowcount == 1
                await db.commit()
                return claimed
            except BaseException:
                await db.rollback()
                raise

    async def operation_result(
        self, operation_id: str, state: str, result: Any
    ) -> None:
        """审计内部结果；对外查询必须再脱敏。"""
        await self.write(
            "UPDATE operations SET state=?,result=?,at=? WHERE id=?",
            (state, json_text(redact(result)), time.time(), operation_id),
        )

    async def prune(self, days: int) -> None:
        """清理终态，待办和失败事件不静默挤掉；健康指标可见占用。"""
        cutoff = time.time() - days * 86400
        await self.write(
            "DELETE FROM events WHERE received<? AND state IN ('delivered','ignored') AND id NOT IN (SELECT id FROM requests)",
            (cutoff,),
        )
        await self.write(
            "DELETE FROM requests WHERE updated<? AND state NOT IN ('pending','processing','uncertain')",
            (cutoff,),
        )
        await self.write("DELETE FROM activity WHERE at<=?", (time.time() - 86400,))
        await self.write("DELETE FROM mappings WHERE at<?", (cutoff,))
        await self.write("DELETE FROM snapshots WHERE at<? AND kind!='mute'", (cutoff,))
        await self.write(
            "DELETE FROM operations WHERE at<? AND state NOT IN ('processing','uncertain')",
            (cutoff,),
        )
        await self.write(
            "DELETE FROM meta WHERE key LIKE 'reaction-cursor:%' AND json_extract(value,'$.expires')<?",
            (time.time(),),
        )
        async with self.lock:
            await self.connection().execute("PRAGMA wal_checkpoint(PASSIVE)")
