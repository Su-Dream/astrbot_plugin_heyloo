import asyncio

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

try:
    from .click_report import (
        PLUGIN_NAME,
        build_click_report,
        get_plugin_data_dir,
        parse_click_pattern,
    )
except ImportError:  # pragma: no cover - 兼容 AstrBot 以脚本方式加载插件
    from click_report import (
        PLUGIN_NAME,
        build_click_report,
        get_plugin_data_dir,
        parse_click_pattern,
    )


@register("HeylooBot", "raphitaria", "海络云运营查询插件", "1.1")
class HeylooBotPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self._query_lock = asyncio.Lock()
        self._data_dir = get_plugin_data_dir(PLUGIN_NAME)

    async def initialize(self):
        """插件初始化时准备数据目录。"""
        self._data_dir.mkdir(parents=True, exist_ok=True)

    @filter.command("昨日点击")
    async def yesterday_clicks(self, event: AstrMessageEvent):
        """查询指定短链昨日成功和失败点击明细。"""
        pattern = parse_click_pattern(event.message_str)
        if not pattern:
            yield event.plain_result("请按格式输入：/昨日点击 ln.run/miTyN")
            return

        yield event.plain_result("查询中")

        try:
            async with self._query_lock:
                report = await build_click_report(pattern, self._data_dir)
        except Exception as exc:
            logger.exception(f"昨日点击查询失败: {exc}")
            yield event.plain_result(f"查询失败：{exc}")
            return

        summary = (
            f"查找到{pattern}成功点击{report.counts.success}个,"
            f"失败点击{report.counts.fail}个;点击明细如下"
        )
        yield event.chain_result(
            [
                Comp.Plain(summary),
                Comp.File(file=str(report.record_csv), name="record.csv"),
            ]
        )

    async def terminate(self):
        """插件卸载时无需额外清理持久化数据。"""
