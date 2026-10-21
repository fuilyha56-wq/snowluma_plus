"""SnowLuma Plus 配置；副作用默认关闭，接管和只读查询默认启用。"""

from __future__ import annotations

import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.app.plugin_system.base import BaseConfig, Field, SectionBase, config_section


class SnowLumaConfig(BaseConfig):
    """按业务组织的配置模型。"""

    name = "config"
    description = "SnowLuma Plus 事件、工具、权限及自动任务"

    @config_section("plugin", title="插件设置", tag="general")
    class PluginSection(SectionBase):
        """启用与适配器选择。"""

        enabled: bool = Field(label="启用插件", default=True, description="启用插件")
        capture: bool = Field(
            label="接管平台事件",
            default=True,
            description="接管允许接收的 notice/request；关闭后恢复旧链路",
        )
        adapters: list[str] = Field(
            label="允许接管的适配器",
            default_factory=lambda: ["onebot_adapter:adapter:onebot_adapter"],
            description="适配器签名白名单",
        )
        backend: str = Field(
            label="协议后端",
            default="snowluma",
            description="后端能力资料名；本地源码能力不代表运行实例能力",
        )
        isolate_streams: bool = Field(
            label="按账号隔离聊天流",
            default=True,
            description="按账号/适配器隔离聊天流；首次启用建立新流，保留原流历史不自动迁移",
        )

    @config_section("events", title="事件接管与账本", tag="database")
    class EventsSection(SectionBase):
        """账本和事件呈现。"""

        disabled_types: list[str] = Field(
            label="仅记录不投递的事件",
            default_factory=list,
            description="仅记录不投递的类型，例如 notify.input_status",
        )
        context_types: list[str] = Field(
            label="进入聊天上下文的事件",
            default_factory=lambda: [
                "group_msg_emoji_like",
                "notify.poke",
                "group_increase",
                "group_decrease",
                "group_admin",
                "group_card",
                "notify.title",
                "notify.group_name",
                "essence",
                "group_ban",
                "group_recall",
                "friend_recall",
                "group_upload",
                "friend_add",
                "group_notice",
            ],
            description="允许进入会话上下文的类型；默认不主动唤醒 LLM",
        )
        wake_types: list[str] = Field(
            label="允许唤醒回复的事件",
            default_factory=list,
            description="明确允许唤醒 Chatter 的类型；建议仅在测试群配置",
        )
        queue_size: int = Field(
            label="事件唤醒队列容量",
            default=128,
            ge=1,
            le=10000,
            description="有界唤醒队列；满时从持久账本恢复",
        )
        retention_days: int = Field(
            label="已完成记录保留天数",
            default=14,
            ge=1,
            le=365,
            description="已完成事件、审批、审计保留天数",
        )
        max_event_bytes: int = Field(
            label="单条事件大小上限（字节）",
            default=262144,
            ge=4096,
            le=1048576,
            description="单事件大小限制；超限保留失败指标，不冒充接管成功",
        )
        max_database_mb: int = Field(
            label="事件账本大小上限（兆字节）",
            default=256,
            ge=16,
            le=4096,
            description="账本软限额；达到后告警并拒绝接管，不静默挤掉审批",
        )
        text_budget: int = Field(
            label="单条事件上下文字符上限",
            default=1800,
            ge=200,
            le=8000,
            description="单事件上下文字符预算",
        )
        delivery_retries: int = Field(
            label="事件投递重试上限",
            default=3,
            ge=1,
            le=10,
            description="失败投递重试上限；超限留账供诊断重放",
        )
        delivery_timeout_seconds: float = Field(
            label="等待实际入流的超时（秒）",
            default=10,
            ge=0.1,
            le=120,
            description="等待核心实际入流/持久化确认的超时；超时留账重放",
        )

    @config_section("access", title="权限与审批", tag="security")
    class AccessSection(SectionBase):
        """触发者授权与平台权限分开检查。"""

        allow_basic_interactions: bool = Field(
            label="允许当前会话普通互动",
            default=True,
            description="允许真实用户在当前获准会话请求贴表情、戳自己、给自己主页点赞1至10次、普通文字/原生表情、手动打卡及撤回Bot自己消息；群管理、审批、文件仍需单独授权",
        )

        blocked_users: list[str] = Field(
            label="工具调用用户黑名单",
            default_factory=list,
            description="禁止这些QQ号调用本插件工具或动作；空为不额外禁止。仍遵守适配器名单。",
        )
        blocked_groups: list[str] = Field(
            label="工具调用群黑名单",
            default_factory=list,
            description="禁止在这些群使用本插件工具或动作；普通获准会话默认可用。",
        )
        blocked_actions: list[str] = Field(
            label="工具动作黑名单",
            default_factory=list,
            description="禁止的协议接口名称，别名与主名称等效；例如group_poke、send_like。优先于普通互动及显式授权。",
        )

        operators: list[str] = Field(
            label="授权操作者QQ号",
            default_factory=list,
            description="可跨会话查询和执行授权动作的 QQ 号；空为无操作者",
        )
        management_users: list[str] = Field(
            label="审批提醒接收者QQ号",
            default_factory=list,
            description="审批提醒私聊接收者；同时受适配器私聊名单限制",
        )
        write_groups: list[str] = Field(
            label="允许执行写入动作的群",
            default_factory=list,
            description="允许执行独立授权管理/公告/文件等动作的群白名单；普通互动另有开关",
        )
        allowed_actions: list[str] = Field(
            label="允许执行的接口名称",
            default_factory=list,
            description="独立授权写入的协议 action 精确白名单；当前会话普通互动由单独开关控制",
        )
        approval_mode: str = Field(
            label="审批处理模式",
            default="remind",
            description="仅提醒：remind；人工辅助审批：assisted；按白名单与理由规则自动审批：auto",
            hint="默认仅提醒。辅助审批仍需授权操作者，自动审批还需填写申请者与理由规则。",
        )
        approval_groups: list[str] = Field(
            label="允许接收申请的群",
            default_factory=list,
            description="可接收及处理群申请的额外范围；仍受适配器群名单限制",
        )
        auto_reason_pattern: str = Field(
            label="自动同意的申请理由规则",
            default="",
            description="自动同意理由的完整正则；auto 模式必须同时配置申请者白名单",
        )
        auto_applicants: list[str] = Field(
            label="允许自动同意的申请者QQ号",
            default_factory=list,
            description="自动同意申请者 QQ 白名单；不以等级作为唯一判断",
        )
        requests_ttl_hours: int = Field(
            label="审批待办有效期（小时）",
            default=72,
            ge=1,
            le=720,
            description="本地待办过期时间，不表示平台 flag 一定有效",
        )
        result_chars: int = Field(
            label="工具结果字符上限",
            default=6000,
            ge=500,
            le=20000,
            description="工具输出字符上限；原响应保存在内部审计",
        )
        calls_per_minute: int = Field(
            label="每会话每分钟调用上限",
            default=30,
            ge=1,
            le=300,
            description="每会话每分钟工具协议调用上限",
        )

    @config_section("files", title="文件外发", tag="file")
    class FilesSection(SectionBase):
        """文件外发边界；默认只允许平台文件 ID 的读取查询。"""

        allow_local_upload: bool = Field(
            label="允许本地文件外发",
            default=False,
            description="允许本地文件外发；必须确认与协议端同一文件系统",
        )
        same_host: bool = Field(
            label="确认与协议端位于同一主机",
            default=False,
            description="操作者确认 Neo-MoFox 与协议端路径解析在同一主机",
        )
        roots: list[str] = Field(
            label="允许外发的本地目录",
            default_factory=list,
            description="本地允许根目录的绝对路径",
        )
        extensions: list[str] = Field(
            label="允许外发的文件扩展名",
            default_factory=lambda: [".txt", ".pdf", ".png", ".jpg"],
            description="允许扩展名",
        )
        max_mb: int = Field(
            label="外发文件大小上限（兆字节）",
            default=10,
            ge=1,
            le=100,
            description="外发文件最大 MiB",
        )
        url_hosts: list[str] = Field(
            label="网络媒体来源域名白名单",
            default_factory=list,
            description="网络媒体来源主机精确白名单；空禁用 URL 外发，不自动下载",
        )

    @config_section("members", title="成员资料与活跃统计", tag="user")
    class MembersSection(SectionBase):
        """成员索引、可见消息统计和提示预算。"""

        max_scopes: int = Field(
            label="内存会话缓存上限",
            default=256,
            ge=16,
            le=4096,
            description="内存路由缓存条目上限；淘汰不删除持久资料",
        )

        enabled: bool = Field(
            label="启用近24小时活跃统计",
            default=True,
            description="维护允许群成员消息的滚动 24 小时统计",
        )
        ttl_seconds: int = Field(
            label="成员资料缓存时间（秒）",
            default=900,
            ge=30,
            description="资料缓存 TTL；失败保留过期资料",
        )
        reminder_members: int = Field(
            label="提醒中显示的活跃成员人数",
            default=5,
            ge=0,
            le=20,
            description="提醒中最多列出的活跃成员",
        )
        reminder_chars: int = Field(
            label="身份与荣誉提醒字符上限",
            default=1200,
            ge=200,
            le=4000,
            description="身份和荣誉提醒总字符预算",
        )
        backfill_limit: int = Field(
            label="框架历史回填条数上限",
            default=1000,
            ge=1,
            le=10000,
            description="公开框架消息 API 历史回填上限；达到上限显示不完整",
        )

    @config_section("announcements", title="群公告同步", tag="notification")
    class AnnouncementsSection(SectionBase):
        """公告快照；首次同步只建立基线。"""

        groups: list[str] = Field(
            label="自动同步公告的群",
            default_factory=list,
            description="轮询群白名单，空不自动查询",
        )
        interval_seconds: int = Field(
            label="公告同步间隔（秒）", default=1800, ge=300, description="公告轮询间隔"
        )
        max_items: int = Field(
            label="公告完整快照条数上限",
            default=500,
            ge=1,
            le=5000,
            description="当前协议无原生分页；超出此快照预算标记不完整，不生成删除差异",
        )

    @config_section("checkin", title="群打卡计划", tag="timer")
    class CheckinSection(SectionBase):
        """手动、定时、启动补打共用持久状态。"""

        enabled: bool = Field(
            label="启用定时群打卡",
            default=False,
            description="启用定时群打卡；手动也需动作授权",
        )
        groups: list[str] = Field(
            label="自动打卡的群", default_factory=list, description="打卡群白名单"
        )
        at: str = Field(
            label="每日打卡时间",
            default="08:30",
            description="本地时区的 HH:MM，严格校验",
        )
        timezone: str = Field(
            label="打卡使用的时区", default="Asia/Shanghai", description="IANA 时区"
        )
        catchup_minutes: int = Field(
            label="启动补打窗口（分钟）",
            default=120,
            ge=0,
            le=1440,
            description="启动补打窗口",
        )
        jitter_seconds: int = Field(
            label="各群打卡错峰上限（秒）",
            default=30,
            ge=0,
            le=600,
            description="每群每天固定抖动上限",
        )
        retries: int = Field(
            label="打卡明确失败后的重试上限",
            default=2,
            ge=0,
            le=5,
            description="明确失败有限重试；结果不确定不重试",
        )

    plugin: PluginSection = Field(label="插件设置", default_factory=PluginSection)
    events: EventsSection = Field(label="事件接管与账本", default_factory=EventsSection)
    access: AccessSection = Field(label="权限与审批", default_factory=AccessSection)
    files: FilesSection = Field(label="文件外发", default_factory=FilesSection)
    members: MembersSection = Field(
        label="成员资料与活跃统计", default_factory=MembersSection
    )
    announcements: AnnouncementsSection = Field(
        label="群公告同步", default_factory=AnnouncementsSection
    )
    checkin: CheckinSection = Field(label="群打卡计划", default_factory=CheckinSection)

    def validate_runtime(self) -> None:
        """加载时拒绝无效时间、时区、授权模式及自动审批规则。"""
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", self.checkin.at):
            raise ValueError("checkin.at 必须为有效 HH:MM")
        try:
            ZoneInfo(self.checkin.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(
                f"checkin.timezone 无效或缺少时区数据：{self.checkin.timezone}"
            ) from exc
        if not set(self.access.management_users).issubset(self.access.operators):
            raise ValueError(
                "管理通知接收者必须同时列入 access.operators，避免向未授权会话披露申请"
            )
        if len(self.checkin.groups) + len(self.announcements.groups) > 100:
            raise ValueError("自动任务群总配置上限为100；请分账号分实例配置")
        if self.access.approval_mode not in {"remind", "assisted", "auto"}:
            raise ValueError("access.approval_mode 必须为 remind/assisted/auto")
        if self.access.auto_reason_pattern:
            re.compile(self.access.auto_reason_pattern)
        if self.access.approval_mode == "auto" and not (
            self.access.auto_reason_pattern and self.access.auto_applicants
        ):
            raise ValueError("自动审批必须同时配置申请者白名单和理由完整正则")
