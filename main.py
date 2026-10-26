import re

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.message_components import File, Image, Plain, Record, Video
from astrbot.api.star import Context, Star, register

# 允许被静默丢弃的占位符。大小写不敏感，容忍首尾空白与尖括号内的空格，
# 顺带兼容常见的 slience 手滑拼写和方括号写法。
SILENCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^<\s*sil\s*ence\s*>$", re.IGNORECASE),
    re.compile(r"^<\s*slie?nce\s*>$", re.IGNORECASE),
    re.compile(r"^\[\s*silence\s*\]$", re.IGNORECASE),
)

# 带这些成分的回复一律放行，静默只针对文本
MEDIA_TYPES = (Image, Record, Video, File)


def is_silence(text: str) -> bool:
    """整条回复去掉首尾空白后是否恰好是一个静默占位符"""
    stripped = text.strip()
    if not stripped:
        return False
    return any(p.match(stripped) for p in SILENCE_PATTERNS)


@register(
    "astrbot_plugin_slience_guard",
    "神秘蓝色小女仆",
    "静默丢弃 <silence> 占位回复：不发送、不提示、不播报拦截信息",
    "v1.0.0",
)
class SilencePlugin(Star):
    """让 agent 的 <silence> 真的安静下来。

    AstrBot 核心没有 silence 机制，人设提示词里约定的 <silence> 会被原样发出。
    内容安全屏蔽词虽然能拦，但那是「整条拒收 + 播报一句英文提示」，不是静默丢弃。

    本插件挂在发送消息前的事件上：整条回复就是一个静默占位符时直接 clear_result()，
    result_decorate 阶段会因结果被清空而提前返回，消息不会被发送，也没有任何提示。
    """

    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        logger.info("[silence_guard] 已加载，静默占位符模式: %d 条", len(SILENCE_PATTERNS))

    @filter.on_decorating_result()
    async def drop_silence(self, event: AstrMessageEvent):
        """发送消息前检查：命中静默占位符就丢弃整条回复"""
        result = event.get_result()
        if result is None or not result.chain:
            return

        if any(isinstance(comp, MEDIA_TYPES) for comp in result.chain):
            return

        text = "".join(
            comp.text for comp in result.chain if isinstance(comp, Plain)
        )
        if is_silence(text):
            event.clear_result()
            logger.info("[silence_guard] 丢弃静默回复: %r", text.strip())

    @filter.command("silence_check")
    async def silence_check(self, event: AstrMessageEvent):
        """查看静默守卫是否在工作"""
        yield event.plain_result(
            "silence_guard 在跑，命中 <silence> / <slience> / [silence] 的整条回复会被静默丢弃"
        )

    async def terminate(self):
        logger.info("[silence_guard] 已卸载")
