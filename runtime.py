"""原始回调、持久重放、有界受管理 worker 及生命周期。"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from src.app.plugin_system.api import (
    adapter_api,
    event_api,
    message_api,
    prompt_api,
    stream_api,
)
from src.app.plugin_system.api.log_api import get_logger
from src.kernel.concurrency import get_task_manager

from .compat import ActionBinding, AdapterBinding
from .business import Business
from .config import SnowLumaConfig
from .gateway import BusinessError, Gateway, response_data
from .models import (
    LABELS,
    Scope,
    UnifiedEvent,
    describe,
    identifier,
    json_text,
    normalize,
    timestamp,
)
from .store import Ledger

logger = get_logger("snowluma_plus")
OWNER = "snowluma_plus:raw_v1"


class Runtime:
    """插件拥有的唯一运行状态，不依赖 Service 实例为单例。"""

    def __init__(self, config: SnowLumaConfig, path: Path | None = None) -> None:
        """资源仅在 start 中启用，导入插件不产生连接或任务。"""
        self.config = config
        self.ledger = Ledger(path or Path("data/snowluma_plus/ledger.sqlite3"))
        self.gateway = Gateway(config, self.ledger)
        self.business = Business(self.gateway, self.ledger)
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=config.events.queue_size)
        self.bound: dict[str, Any] = {}
        self.bindings: dict[str, AdapterBinding] = {}
        self.action_binding = ActionBinding()
        self.callbacks: dict[str, Any] = {}
        self.accounts: dict[str, str] = {}
        self.tasks: list[Any] = []
        self.running = False
        self.counters: Counter[str] = Counter()
        self.scopes: dict[str, Scope] = {}
        self.last_poll: dict[str, float] = {}
        self.last_checkin: dict[str, float] = {}
        self.reminder_streams: set[str] = set()
        self.delivery_acks: dict[str, asyncio.Event] = {}
        self.backend_state: dict[str, Any] = {}
        self.last_backend_probe: dict[str, float] = {}
        self.identity_rotation = 0

    def remember_scope(self, key: str, scope: Scope) -> None:
        """有限路由缓存，近期会话优先，持久数据保持隔离。"""
        self.scopes.pop(key, None)
        self.scopes[key] = scope
        while len(self.scopes) > self.config.members.max_scopes:
            self.scopes.pop(next(iter(self.scopes)))

    async def start(self) -> None:
        """幂等启动；部分失败由 stop 回滚句柄和任务。"""
        if self.running:
            return
        self.config.validate_runtime()
        await self.ledger.open()
        self.running = True
        try:
            await self.bind()
            manager = get_task_manager()
            for name, factory in (
                ("worker", self.worker),
                ("lifecycle", self.supervise),
                ("automation", self.automate),
            ):
                coro = factory()
                try:
                    info = manager.create_task(
                        coro,
                        name=f"snowluma_plus:{name}",
                        daemon=True,
                        group_name="snowluma_plus",
                    )
                except BaseException:
                    coro.close()
                    raise
                self.tasks.append(info)
        except BaseException:
            await self.stop()
            raise

    async def stop(self) -> None:
        """注销所有绑定，取消并等待自己的任务，不清理其他插件资源。"""
        self.running = False
        for binding in self.bindings.values():
            if not binding.close():
                self.counters["compat_restore_conflict"] += 1
        self.bindings.clear()
        if not self.action_binding.close():
            self.counters["compat_restore_conflict"] += 1
        self.bound.clear()
        self.callbacks.clear()
        manager = get_task_manager()
        futures = []
        for info in self.tasks:
            manager.cancel_task(info.task_id)
            task = getattr(info, "task", None)
            if task is not None:
                futures.append(task)
        if futures:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*futures, return_exceptions=True), timeout=5
                )
            except asyncio.TimeoutError:
                self.counters["shutdown_timeout"] += 1
        self.tasks.clear()
        for stream_id in self.reminder_streams:
            prompt_api.delete_stream_reminder(
                stream_id, "actor", "snowluma_plus_identity"
            )
        self.reminder_streams.clear()
        await self.ledger.close()

    async def bind(self) -> None:
        """插件内兼容层；实例更换恢复旧句柄后重新核验并绑定。"""
        self.action_binding.install()
        active = adapter_api.get_all_adapters()
        for signature, old in tuple(self.bound.items()):
            if active.get(signature) is not old:
                if not self.bindings.pop(signature).close():
                    self.counters["compat_restore_conflict"] += 1
                self.bound.pop(signature, None)
                self.callbacks.pop(signature, None)
        for signature in self.config.plugin.adapters:
            adapter = active.get(signature)
            if adapter is None:
                continue
            binding = self.bindings.get(signature)
            if binding is None:
                info = await adapter.get_bot_info()
                self.accounts[signature] = identifier(info.get("bot_id"))
                binding = AdapterBinding(adapter, signature, self.accounts[signature])
                try:
                    binding.install()
                except Exception as exc:
                    self.counters["unsupported_adapter"] += 1
                    logger.error(f"SnowLuma兼容入口未安装：{type(exc).__name__}: {exc}")
                    continue
                self.bindings[signature] = binding
                self.bound[signature] = adapter
                self.counters["bound"] += 1
            else:
                binding.install()  # 校验所有权，不能悄悄覆盖后安装的包装器。
            if not self.config.plugin.capture:
                binding.hooks.unregister(OWNER)
                self.callbacks.pop(signature, None)
                continue
            if signature in self.callbacks:
                continue

            async def callback(
                raw: dict[str, Any], sign: str = signature
            ) -> dict[str, Any]:
                return await self.capture(sign, raw)

            binding.hooks.register(OWNER, callback)
            self.callbacks[signature] = callback

    async def capture(self, signature: str, raw: dict[str, Any]) -> dict[str, Any]:
        """接收循环只校验、落盘和唤醒，无平台查询。"""
        if not self.running or not self.config.plugin.capture:
            return {"status": "unhandled"}
        post_type = raw.get("post_type")
        account = identifier(raw.get("self_id")) or self.accounts.get(signature, "")
        if not account:
            self.counters["missing_account"] += 1
            return {"status": "failed", "reason": "missing_account"}
        self.accounts[signature] = account
        if post_type in {"message", "message_sent"}:
            if post_type == "message":
                scope = Scope(
                    account,
                    signature,
                    identifier(raw.get("group_id")),
                    identifier(
                        raw.get("user_id") or (raw.get("sender") or {}).get("user_id")
                    ),
                )
                platform_id = identifier(raw.get("message_id"))
                occurred = timestamp(raw.get("time"), time.time())
                if scope.group and self.config.members.enabled:
                    await self.ledger.activity(
                        scope,
                        platform_id,
                        scope.user,
                        occurred,
                    )
                if platform_id:
                    await self.ledger.write(
                        "INSERT OR IGNORE INTO mappings(scope,framework_id,platform_id,at) VALUES(?,?,?,?)",
                        (scope.key, platform_id, platform_id, occurred),
                    )
            return {"status": "unhandled"}
        if post_type not in {"notice", "request"}:
            return {"status": "unhandled"}
        encoded = json_text(raw)
        if len(encoded.encode()) > self.config.events.max_event_bytes:
            self.counters["event_oversize"] += 1
            return {"status": "failed", "reason": "event_oversize"}
        storage_bytes = sum(
            path.stat().st_size
            for path in (self.ledger.path, Path(str(self.ledger.path) + "-wal"))
            if path.exists()
        )
        if storage_bytes > self.config.events.max_database_mb * 1048576:
            self.counters["storage_limit"] += 1
            return {"status": "failed", "reason": "storage_limit"}
        event = normalize(raw, signature, account)
        if (
            post_type == "request"
            and event.scope.group
            and event.scope.group not in self.config.access.approval_groups
        ):
            # 未授权请求保留事件，审批状态不向管理会话广播。
            self.counters["request_scope_unapproved"] += 1
        try:
            inserted = await self.ledger.accept(event)
        except Exception:
            self.counters["storage_failure"] += 1
            logger.error("原始事件持久化失败，交由适配器保真降级（未输出原始资料）")
            return {"status": "failed", "reason": "storage_failure"}
        self.counters["accepted" if inserted else "duplicate"] += 1
        if inserted:
            try:
                self.queue.put_nowait(event.event_id)
            except asyncio.QueueFull:
                self.counters["queue_full_recoverable"] += 1
        return {"status": "handled", "event_id": event.event_id}

    async def worker(self) -> None:
        """一个顺序消费者保障会话顺序；网络请求有总超时。"""
        while self.running:
            try:
                if not self.config.plugin.capture:
                    await asyncio.sleep(1)
                    continue
                probe = await event_api.publish_event(
                    "snowluma_plus:consumer_probe", {"ready": False}
                )
                if not (probe.get("params") or {}).get("ready"):
                    self.counters["consumer_not_ready"] += 1
                    await asyncio.sleep(0.25)
                    continue
                rows = await self.ledger.pending()
                for row in rows:
                    try:
                        await asyncio.wait_for(self.deliver(row), timeout=45)
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        self.counters[f"delivery_error:{type(exc).__name__}"] += 1
                        reason = (
                            str(exc)
                            if isinstance(exc, BusinessError)
                            else type(exc).__name__
                        )
                        await self.ledger.failed(
                            row, reason, self.config.events.delivery_retries
                        )
                while not self.queue.empty():
                    self.queue.get_nowait()
                    self.queue.task_done()
                if not rows:
                    try:
                        await asyncio.wait_for(self.queue.get(), timeout=1)
                        self.queue.task_done()
                    except asyncio.TimeoutError:
                        pass
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.counters[f"worker_recovered:{type(exc).__name__}"] += 1
                await asyncio.sleep(1)

    async def deliver(self, row: dict[str, Any]) -> None:
        """账本 -> 命名空间事件 -> 真实适配器 CoreSink -> receiver。"""
        raw = json.loads(row["raw"])
        event = normalize(raw, row["adapter"], row["account"], row["source"])
        event.event_id, event.received_at = row["id"], row["received"]
        adapter = self.bound.get(row["adapter"])
        if adapter is None:
            raise BusinessError("adapter_unbound")
        if adapter.raw_event_context().get("account") != event.scope.account:
            raise BusinessError("account_changed_before_delivery")
        if not adapter.allows_raw_event(raw):
            await self.ledger.finish(event.event_id, "ignored", "policy_revoked")
            self.counters["policy_revoked"] += 1
            return
        if event.scope.group:
            self.remember_scope(event.scope.key, event.scope)
            if (
                event.kind
                in {"group_increase", "group_decrease", "group_card", "group_admin"}
                or event.type_key == "notify.title"
            ):
                await self.ledger.write(
                    "UPDATE snapshots SET complete=0 WHERE scope=? AND kind IN ('members','identity')",
                    (event.scope.key,),
                )
            if event.kind == "group_notice" and event.source == "platform":
                await self.business.observe_notice(event.scope, raw)
        self.counters["parsed"] += 1
        if raw.get("post_type") == "notice" and event.type_key not in LABELS:
            self.counters["unknown_type"] += 1
        if event.type_key in self.config.events.disabled_types:
            await self.ledger.finish(event.event_id, "ignored", "configured_disabled")
            return
        await event_api.publish_event("snowluma_plus:event", {"event": event.public()})
        if raw.get("post_type") == "request":
            await self.request_notifications(event, adapter)
        elif event.scope.group or event.scope.user:
            if event.kind in {
                "group_ban",
                "group_whole_ban",
                "group_whole_ban_status",
            } or (
                event.type_key in self.config.events.context_types
                or event.type_key in self.config.events.wake_types
            ):
                await self.send_to_core(event, adapter)
            else:
                self.counters["record_only"] += 1
        else:
            self.counters["account_event"] += 1
        await self.ledger.finish(event.event_id, "delivered")

    async def request_notifications(self, event: UnifiedEvent, adapter: Any) -> None:
        """只投递配置的管理私聊；不将申请者当作管理员，也不自动发送 QQ 消息。"""
        if (
            event.scope.group
            and event.scope.group not in self.config.access.approval_groups
        ):
            return
        for user in self.config.access.management_users:
            raw = {
                "post_type": "notice",
                "user_id": user,
                "self_id": event.scope.account,
            }
            if not adapter.allows_raw_event(raw):
                self.counters["management_filtered"] += 1
                continue
            await self.send_to_core(event, adapter, management_user=user)
        if self.config.access.approval_mode == "auto":
            try:
                await self.business.approve(
                    event.scope, "", event.event_id, True, automatic=True
                )
            except BusinessError:
                self.counters["automatic_request_not_eligible"] += 1

    def envelope(
        self, event: UnifiedEvent, management_user: str = ""
    ) -> dict[str, Any]:
        """保留 self_id/raw_event 给 Expand 禁言保护，LLM 只消费脱敏资料。"""
        text = describe(event, self.config.events.text_budget)
        if event.data.get("post_type") == "request":
            text = (
                f"[审批待办 request_id={event.event_id}；请使用待办工具核对权限和状态]\n"
                + text
            )
        info: dict[str, Any] = {
            "platform": event.scope.platform,
            "message_id": f"snowluma:{event.event_id}"
            + (f":{management_user}" if management_user else ""),
            "message_type": "notice",
            "time": event.occurred_at,
            "extra": {
                "self_id": event.scope.account,
                "snowluma_plus": event.public(),
                "system_event": True,
                "group_id": "" if management_user else event.scope.group,
                "snowluma_text": text,
                "management_user": management_user,
                "snowluma_state_only": event.data.get("post_type") != "request"
                and event.type_key not in self.config.events.context_types
                and event.type_key not in self.config.events.wake_types,
            },
        }
        if event.scope.group and not management_user:
            info["group_info"] = {
                "platform": "qq",
                "group_id": event.scope.group,
                "group_name": "",
            }
            info["user_info"] = {
                "platform": "qq",
                "user_id": "system:snowluma",
                "user_nickname": "平台事件",
            }
        else:
            info["user_info"] = {
                "platform": "qq",
                "user_id": "system:snowluma:" + event.scope.account,
                "user_nickname": "平台事件",
            }
        segment: dict[str, Any] = {"type": "text", "data": text}
        if event.kind in {"group_ban", "group_whole_ban", "group_whole_ban_status"}:
            whole = event.kind != "group_ban" or str(event.data.get("user_id")) == "0"
            enabled = (
                event.subtype == "ban"
                if event.kind == "group_ban"
                else str(event.data.get("enable")).lower()
                in {"true", "1", "on", "enable", "yes"}
            )
            info["extra"]["notice_type"] = (
                ("group_whole_ban" if enabled else "group_whole_lift_ban")
                if whole
                else ("group_ban" if enabled else "group_lift_ban")
            )
            segment = {
                "type": "notify",
                "data": {
                    "duration": event.data.get("duration", 0),
                    "banned_user_info" if enabled else "lifted_user_info": {
                        "user_id": identifier(event.data.get("user_id"))
                    },
                },
            }
        return {
            "direction": "incoming",
            "message_info": info,
            "message_segment": segment,
            "raw_message": event.public(),
            "raw_event": dict(event.data),
        }

    def acknowledge(self, message_id: str) -> None:
        """消费者在实际历史入库后确认；不是 Sink 派发回执。"""
        ack = self.delivery_acks.get(message_id)
        if ack is not None:
            ack.set()

    async def send_to_core(
        self, event: UnifiedEvent, adapter: Any, management_user: str = ""
    ) -> None:
        """等待实际入流证据，覆盖 CoreSink 异步派发和消费者缺失。"""
        from src.core.models.stream import ChatStream

        envelope = self.envelope(event, management_user)
        mid = envelope["message_info"]["message_id"]
        route = Scope(
            event.scope.account,
            event.scope.adapter,
            "" if management_user else event.scope.group,
            management_user or event.scope.user,
        )
        stream_id = (
            route.stream_id
            if self.config.plugin.isolate_streams
            else ChatStream.generate_stream_id(
                platform=route.platform, group_id=route.group
            )
            if route.group
            else ChatStream.generate_stream_id(
                platform=route.platform, user_id=route.user
            )
        )
        ack = asyncio.Event()
        self.delivery_acks[mid] = ack
        try:
            await adapter.core_sink.send(envelope)
            async with asyncio.timeout(self.config.events.delivery_timeout_seconds):
                while not ack.is_set():
                    stream = await stream_api.get_stream(stream_id)
                    if stream is not None:
                        messages = [
                            *stream.context.history_messages,
                            *stream.context.unread_messages,
                            *stream.context.message_cache,
                        ]
                        if any(item.message_id == mid for item in messages):
                            ack.set()
                            break
                    await asyncio.sleep(0.02)
            await self.ledger.write(
                "UPDATE events SET framework=1 WHERE id=?", (event.event_id,)
            )
        except asyncio.TimeoutError as exc:
            raise BusinessError("consumer_delivery_timeout") from exc
        finally:
            self.delivery_acks.pop(mid, None)

    async def supervise(self) -> None:
        """重绑更换的适配器；常规保留清理不影响接收循环。"""
        last_prune = 0.0
        while self.running:
            try:
                await self.bind()
                for signature, adapter in tuple(self.bound.items()):
                    if (
                        adapter.raw_event_context().get("connected")
                        and time.time() - self.last_backend_probe.get(signature, 0)
                        > 300
                    ):
                        self.last_backend_probe[signature] = time.time()
                        try:
                            scope = Scope(self.accounts.get(signature, ""), signature)
                            response = await asyncio.wait_for(
                                self.gateway.raw_call(scope, "get_version_info", {}),
                                timeout=5,
                            )
                            self.backend_state[signature] = {
                                "status": "ok",
                                "version": response_data(response),
                                "checked_at": time.time(),
                            }
                        except Exception as exc:
                            self.backend_state[signature] = {
                                "status": "unavailable",
                                "error": type(exc).__name__,
                                "checked_at": time.time(),
                            }
                if time.monotonic() - last_prune > 300:
                    await self.ledger.prune(self.config.events.retention_days)
                    for key, values in tuple(self.gateway.rate.items()):
                        if not values or values[-1] < time.monotonic() - 60:
                            self.gateway.rate.pop(key, None)
                    last_prune = time.monotonic()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.counters[f"lifecycle_error:{type(exc).__name__}"] += 1
            await asyncio.sleep(2)

    async def automate(self) -> None:
        """单个受管理调度器，群间有界并发；每项独立捕获失败。"""
        while self.running:
            # 受配置/已接收范围约束，网络调用另有全局 semaphore。
            observed = {
                scope.key: scope for scope in self.scopes.values() if scope.group
            }
            unique: dict[str, Scope] = {}
            for signature in tuple(self.bound):
                account = self.accounts.get(signature, "")
                if not account:
                    continue
                for group in set(
                    self.config.announcements.groups + self.config.checkin.groups
                ):
                    scope = Scope(account, signature, group)
                    unique[scope.key] = scope
            background = [scope for key, scope in observed.items() if key not in unique]
            if background:
                start = self.identity_rotation % len(background)
                rotated = background[start:] + background[:start]
                unique.update({scope.key: scope for scope in rotated[:50]})
                self.identity_rotation = (start + 50) % len(background)
            jobs = [self.automate_group(scope) for scope in unique.values()]
            if jobs:
                # 协议并发由 Gateway semaphore 限制，任务数来自配置白名单而非事件流。
                results = await asyncio.gather(*jobs, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        self.counters[f"automation_error:{type(result).__name__}"] += 1
            await asyncio.sleep(30)

    async def automate_group(self, scope: Scope) -> None:
        """轮询与打卡独立节奏，不因某群失败阻止其他群。"""
        now = time.time()
        if (
            scope.group in self.config.announcements.groups
            and now - self.last_poll.get(scope.key, 0)
            >= self.config.announcements.interval_seconds
        ):
            self.last_poll[scope.key] = now
            try:
                await self.business.notices(scope, emit=True)
            except BusinessError:
                self.counters["announcement_poll_failed"] += 1
        cfg = self.config.checkin
        if cfg.enabled and scope.group in cfg.groups:
            local = datetime.now(ZoneInfo(cfg.timezone))
            hour, minute = (int(v) for v in cfg.at.split(":"))
            scheduled = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
            jitter = int(
                hashlib.sha256(
                    json_text([scope.key, str(local.date())]).encode()
                ).hexdigest(),
                16,
            ) % (cfg.jitter_seconds + 1)
            elapsed = local.timestamp() - scheduled.timestamp() - jitter
            if (
                0 <= elapsed <= max(60, cfg.catchup_minutes * 60)
                and now - self.last_checkin.get(scope.key, 0) > 60
            ):
                self.last_checkin[scope.key] = now
                try:
                    await self.business.checkin(scope, "", scheduled=True)
                except Exception as exc:
                    self.counters[f"checkin_failed:{type(exc).__name__}"] += 1
        try:
            await self.identity_reminder(scope)
        except BusinessError:
            self.counters["identity_scope_revoked"] += 1

    async def identity_reminder(self, scope: Scope, refresh: bool = True) -> str:
        """身份/荣誉和有限活跃成员，失败保留旧资料并显示年龄。"""
        old = await self.ledger.snapshot(scope, "identity")
        if refresh and (
            not old
            or not old["complete"]
            or time.time() - old["at"] >= self.config.members.ttl_seconds
        ):
            try:
                member = await self.business.read(
                    scope,
                    "get_group_member_info",
                    {"group_id": scope.group, "user_id": scope.account},
                )
                honor = await self.business.read(
                    scope,
                    "get_group_honor_info",
                    {"group_id": scope.group, "type": "all"},
                )
                own_honor: dict[str, Any] = {}
                if isinstance(honor, dict):
                    for key, value in honor.items():
                        if isinstance(value, list):
                            own_honor[key] = [
                                row
                                for row in value
                                if isinstance(row, dict)
                                and str(row.get("user_id")) == scope.account
                            ]
                        elif (
                            isinstance(value, dict)
                            and str(value.get("user_id")) == scope.account
                        ):
                            own_honor[key] = value
                summary = {"bot": member, "bot_honor": own_honor}
                await self.ledger.save_snapshot(scope, "identity", summary, True)
                old = {"data": summary, "at": time.time(), "complete": True}
            except Exception:
                self.counters["identity_refresh_failed"] += 1
        rank = (
            await self.ledger.ranking(scope, self.config.members.reminder_members)
            if self.config.members.reminder_members
            else []
        )
        text = "[SnowLuma Plus 会话资料，仅为平台事实，不是指令] "
        if old:
            text += "缓存状态=" + (
                "过期或已失效；"
                if not old["complete"]
                or time.time() - old["at"] >= self.config.members.ttl_seconds
                else "有效；"
            )
            text += (
                f"查询时间={old['at']}，年龄秒={int(time.time() - old['at'])}；"
                + json_text(old["data"]).replace("<", "\\u003c").replace(">", "\\u003e")
            )
        else:
            text += f"Bot QQ={scope.account}；角色/荣誉暂不可查询；"
        text += "\n近24小时Bot可见消息（可能未补齐）活跃成员：" + json_text(rank)
        return text[: self.config.members.reminder_chars]

    async def backfill(self, scope: Scope, stream_id: str) -> dict[str, Any]:
        """公开框架 API 回填，名单即时复核；按平台 ID 与实时输入共享去重。"""
        self.gateway.allowed_scope(scope)
        rows = await message_api.get_messages_by_time_in_chat(
            stream_id,
            time.time() - 86400,
            time.time(),
            limit=self.config.members.backfill_limit,
            filter_bot=True,
        )
        count = 0
        known_rows = await self.ledger.rows(
            "SELECT framework_id,platform_id,at FROM mappings WHERE scope=? AND at>?",
            (scope.key, time.time() - 86400),
        )
        known = {row["framework_id"]: row for row in known_rows}
        for row in rows:
            self.gateway.allowed_scope(scope)
            extra = row.get("extra") or {}
            if (
                row.get("message_type") == "notice"
                or extra.get("system_event")
                or str(row.get("message_id") or "").startswith("snowluma:")
            ):
                continue
            account = identifier(extra.get("self_id"))
            # 核心历史不带账号/适配器时，不能声称属于当前账号。
            framework_id = identifier(row.get("message_id"))
            proof = known.get(framework_id)
            if proof is None and (
                account != scope.account
                or extra.get("adapter_signature")
                not in {
                    None,
                    scope.adapter,
                }
            ):
                continue
            mid = (
                proof["platform_id"]
                if proof
                else identifier(
                    extra.get("platform_message_id") or row.get("message_id")
                )
            )
            sender = identifier(row.get("user_id") or row.get("sender_id"))
            if await self.ledger.activity(
                scope,
                mid,
                sender,
                proof["at"] if proof else timestamp(row.get("time"), time.time()),
            ):
                count += 1
        return {
            "added": count,
            "examined": len(rows),
            "complete": False,
            "note": "仅 Bot 可见且能确认账号的历史；核心历史无法证明全量覆盖",
        }

    async def diagnostics(self) -> dict[str, Any]:
        """区分绑定、解析、框架、消费，不从警告消失推断成功。"""
        states = await self.ledger.rows(
            "SELECT state,COUNT(*) AS count FROM events GROUP BY state"
        )
        proof = await self.ledger.rows(
            "SELECT SUM(framework) AS framework,SUM(consumed) AS consumed FROM events"
        )
        requests = await self.ledger.rows(
            "SELECT state,COUNT(*) AS count FROM requests GROUP BY state"
        )
        recent = await self.ledger.rows(
            "SELECT id,adapter,account,state,error,received FROM events ORDER BY seq DESC LIMIT 10"
        )
        return {
            "running": self.running,
            "capture": self.config.plugin.capture,
            "bound": list(self.bound),
            "accounts": self.accounts,
            "adapters": {
                signature: adapter.raw_event_context()
                for signature, adapter in self.bound.items()
            },
            "backend": self.backend_state,
            "queue": {"size": self.queue.qsize(), "limit": self.queue.maxsize},
            "workers": len(self.tasks),
            "counters": dict(self.counters),
            "events": states,
            "evidence": proof,
            "requests": requests,
            "cache": await self.ledger.rows(
                "SELECT scope,kind,at,complete FROM snapshots ORDER BY at DESC LIMIT 30"
            ),
            "checkin_schedule": {
                "enabled": self.config.checkin.enabled,
                "groups": self.config.checkin.groups,
                "at": self.config.checkin.at,
                "timezone": self.config.checkin.timezone,
            },
            "activity": await self.ledger.rows(
                "SELECT scope,COUNT(*) AS messages FROM activity WHERE at>? GROUP BY scope",
                (time.time() - 86400,),
            ),
            "recent": recent,
            "database_bytes": self.ledger.path.stat().st_size
            if self.ledger.path.exists()
            else 0,
            "guarantee": "本地持久接收，框架投递至少一次；无平台唯一ID时不吞同秒合法通知",
        }
