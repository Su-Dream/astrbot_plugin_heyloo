import asyncio

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

try:
    from .models.click_report import (
        PLUGIN_NAME,
        build_click_overview,
        build_click_report,
        get_plugin_data_dir,
        parse_click_pattern,
    )
    from .models.queue_report import build_queue_metrics
except ImportError:  # pragma: no cover - 兼容 AstrBot 以脚本方式加载插件
    from models.click_report import (
        PLUGIN_NAME,
        build_click_overview,
        build_click_report,
        get_plugin_data_dir,
        parse_click_pattern,
    )
    from models.queue_report import build_queue_metrics


BASE_IMAGE_OPTIONS = {"type": "png", "full_page": True}


OVERVIEW_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    body {
      margin: 0;
      background: #ffffff;
      color: #1f2937;
      font-family: Arial, "Microsoft YaHei", sans-serif;
    }
  </style>
</head>
<body>
<div style="width: 596px; background: #fff; border: 1px solid #e5e7eb;">
  <div style="background: #e8efff; color: #2563eb; font-size: 16px; font-weight: 700; padding: 12px 8px;">
    代理访问统计通知
  </div>
  <div style="padding: 14px 8px 12px;">
    <div style="font-size: 14px; line-height: 1.7;">
      <div><strong>统计周期：</strong>{{ period_start }} ~ {{ period_end }}</div>
      <div><strong>总数：</strong>{{ total }}</div>
    </div>
    <div style="height: 1px; background: #e5e7eb; margin: 16px 0 14px;"></div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; row-gap: 12px; column-gap: 32px; font-size: 14px;">
      <div>
        <div style="font-weight: 700; margin-bottom: 4px;">代理访问成功数</div>
        <div>{{ success }}</div>
      </div>
      <div>
        <div style="font-weight: 700; margin-bottom: 4px;">成功率</div>
        <div>{{ success_rate }}</div>
      </div>
      <div>
        <div style="font-weight: 700; margin-bottom: 4px;">代理访问失败数</div>
        <div>{{ fail }}</div>
      </div>
      <div>
        <div style="font-weight: 700; margin-bottom: 4px;">失败率</div>
        <div>{{ fail_rate }}</div>
      </div>
    </div>
    <div style="color: #6b7280; font-size: 13px; margin-top: 20px;">
      数据来源：event_log 表 click-success / click-fail / click-fail-domain 统计结果
    </div>
  </div>
</div>
</body>
</html>
"""


QUEUE_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    body {
      margin: 0;
      background: #ffffff;
      color: #1f2937;
      font-family: Arial, "Microsoft YaHei", sans-serif;
    }
  </style>
</head>
<body>
<div style="width: 596px; background: #fff; border: 1px solid #e5e7eb;">
  <div style="background: #e8efff; color: #2563eb; font-size: 16px; font-weight: 700; padding: 12px 8px;">
    当前队列统计通知
  </div>
  <div style="padding: 14px 8px 12px;">
    <div style="font-size: 14px; line-height: 1.7;">
      <div><strong>总队列数：</strong>{{ total }}</div>
    </div>
    <div style="height: 1px; background: #e5e7eb; margin: 16px 0 14px;"></div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; row-gap: 12px; column-gap: 32px; font-size: 14px;">
      <div>
        <div style="font-weight: 700; margin-bottom: 4px;">任务队列数量</div>
        <div>{{ task_queue_size }}</div>
      </div>
      <div>
        <div style="font-weight: 700; margin-bottom: 4px;">任务队列 Key</div>
        <div>{{ task_queue_key }}</div>
      </div>
      <div>
        <div style="font-weight: 700; margin-bottom: 4px;">事件队列数量</div>
        <div>{{ event_queue_size }}</div>
      </div>
      <div>
        <div style="font-weight: 700; margin-bottom: 4px;">事件队列 Key</div>
        <div>{{ event_queue_key }}</div>
      </div>
    </div>
    <div style="color: #6b7280; font-size: 13px; margin-top: 20px;">
      数据来源：queue-metrics 当前队列指标
    </div>
  </div>
</div>
</body>
</html>
"""


@register("HeylooBot", "raphitaria", "海络云运营查询插件", "1.1")
class HeylooBotPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self._query_lock = asyncio.Lock()
        self._data_dir = get_plugin_data_dir(PLUGIN_NAME)

    async def initialize(self):
        """插件初始化时准备数据目录。"""
        self._data_dir.mkdir(parents=True, exist_ok=True)

    async def render_image(self, template: str, data: dict[str, object]) -> str:
        """使用 AstrBot HTML 渲染能力生成图片 URL。"""
        return await self.html_render(template, data, options=BASE_IMAGE_OPTIONS)

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

    @filter.command("昨日点击总览")
    async def yesterday_clicks_overview(self, event: AstrMessageEvent):
        """查询昨日点击成功和失败总览，并以图片形式回复。"""
        yield event.plain_result("查询中")

        try:
            async with self._query_lock:
                overview = await build_click_overview()
                image_url = await self.render_image(
                    OVERVIEW_TEMPLATE,
                    {
                        "period_start": overview.period_start,
                        "period_end": overview.period_end,
                        "total": overview.total,
                        "success": overview.success,
                        "fail": overview.fail,
                        "success_rate": overview.success_rate,
                        "fail_rate": overview.fail_rate,
                    },
                )
        except Exception as exc:
            logger.exception(f"昨日点击总览查询失败: {exc}")
            yield event.plain_result(f"查询失败：{exc}")
            return

        yield event.image_result(image_url)

    @filter.command("当前队列")
    async def current_queue(self, event: AstrMessageEvent):
        """查询当前任务队列和事件队列，并以图片形式回复。"""
        yield event.plain_result("查询中")

        try:
            metrics = await build_queue_metrics()
            image_url = await self.render_image(
                QUEUE_TEMPLATE,
                {
                    "total": metrics.total,
                    "task_queue_key": metrics.task_queue.key,
                    "task_queue_size": metrics.task_queue.size,
                    "event_queue_key": metrics.event_queue.key,
                    "event_queue_size": metrics.event_queue.size,
                },
            )
        except Exception as exc:
            logger.exception(f"当前队列查询失败: {exc}")
            yield event.plain_result(f"查询失败：{exc}")
            return

        yield event.image_result(image_url)

    async def terminate(self):
        """插件卸载时无需额外清理持久化数据。"""
