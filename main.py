import asyncio

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

try:
    from .models.click_report import (
        build_click_count_report,
        build_click_overview,
        build_yesterday_click_count_report,
        parse_click_query_args,
        parse_yesterday_click_url,
    )
    from .models.image_options import (
        OVERVIEW_IMAGE_HEIGHT,
        QUEUE_IMAGE_HEIGHT,
        build_image_options,
    )
    from .models.plugin_config import (
        get_event_api_base_url,
        is_image_response_enabled,
        require_configured_url,
    )
    from .models.queue_report import build_queue_metrics_report
    from .models.response_text import format_click_overview_text, format_queue_metrics_text
except ImportError:  # pragma: no cover - 兼容 AstrBot 以脚本方式加载插件
    from models.click_report import (
        build_click_count_report,
        build_click_overview,
        build_yesterday_click_count_report,
        parse_click_query_args,
        parse_yesterday_click_url,
    )
    from models.image_options import (
        OVERVIEW_IMAGE_HEIGHT,
        QUEUE_IMAGE_HEIGHT,
        build_image_options,
    )
    from models.plugin_config import (
        get_event_api_base_url,
        is_image_response_enabled,
        require_configured_url,
    )
    from models.queue_report import build_queue_metrics_report
    from models.response_text import format_click_overview_text, format_queue_metrics_text


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
    <div style="display: grid; grid-template-columns: 1fr 1fr; row-gap: 12px; column-gap: 24px; font-size: 14px;">
      <div>
        <div style="font-weight: 700; margin-bottom: 4px;">{{ server_1_name }}</div>
        <div style="color: #6b7280; font-size: 12px; word-break: break-all;">{{ server_1_url }}</div>
      </div>
      <div>
        <div style="font-weight: 700; margin-bottom: 4px;">队列总数</div>
        <div>{{ server_1_total }}</div>
      </div>
      <div>
        <div style="font-weight: 700; margin-bottom: 4px;">事件队列数量</div>
        <div>{{ server_1_event_queue_size }}</div>
        <div style="color: #6b7280; font-size: 12px; word-break: break-all;">{{ server_1_event_queue_key }}</div>
      </div>
      <div>
        <div style="font-weight: 700; margin-bottom: 4px;">任务队列数量</div>
        <div>{{ server_1_task_queue_size }}</div>
        <div style="color: #6b7280; font-size: 12px; word-break: break-all;">{{ server_1_task_queue_key }}</div>
      </div>
    </div>
    <div style="height: 1px; background: #e5e7eb; margin: 14px 0;"></div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; row-gap: 12px; column-gap: 24px; font-size: 14px;">
      <div>
        <div style="font-weight: 700; margin-bottom: 4px;">{{ server_2_name }}</div>
        <div style="color: #6b7280; font-size: 12px; word-break: break-all;">{{ server_2_url }}</div>
      </div>
      <div>
        <div style="font-weight: 700; margin-bottom: 4px;">队列总数</div>
        <div>{{ server_2_total }}</div>
      </div>
      <div>
        <div style="font-weight: 700; margin-bottom: 4px;">事件队列数量</div>
        <div>{{ server_2_event_queue_size }}</div>
        <div style="color: #6b7280; font-size: 12px; word-break: break-all;">{{ server_2_event_queue_key }}</div>
      </div>
      <div>
        <div style="font-weight: 700; margin-bottom: 4px;">任务队列数量</div>
        <div>{{ server_2_task_queue_size }}</div>
        <div style="color: #6b7280; font-size: 12px; word-break: break-all;">{{ server_2_task_queue_key }}</div>
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
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self._config = config
        self._query_lock = asyncio.Lock()

    async def initialize(self):
        """插件初始化。"""

    async def render_image(
        self,
        template: str,
        data: dict[str, object],
        height: int,
    ) -> str:
        """使用 AstrBot HTML 渲染能力生成图片 URL。"""
        return await self.html_render(template, data, options=build_image_options(height))

    def image_response_enabled(self) -> bool:
        """读取当前插件配置中的图片回复开关。"""
        return is_image_response_enabled(self._config)

    def event_api_base_url(self) -> str:
        """读取打点服务器基础地址。"""
        return require_configured_url(
            get_event_api_base_url(self._config),
            "打点服务器地址",
        )

    @filter.command("昨日点击")
    async def yesterday_clicks(self, event: AstrMessageEvent):
        """查询指定短链昨日请求数和成功数。"""
        url = parse_yesterday_click_url(event.message_str)
        if not url:
            yield event.plain_result("请按格式输入：/昨日点击 ln.run/miTyN")
            return

        try:
            async with self._query_lock:
                report = await build_yesterday_click_count_report(
                    url,
                    self.event_api_base_url(),
                )
        except Exception as exc:
            logger.exception(f"昨日点击查询失败: {exc}")
            yield event.plain_result(f"查询失败：{exc}")
            return

        yield event.plain_result(
            f"{report.url} 在 {report.period_start} 到 {report.period_end} "
            f"成功 {report.success_total} 个"
        )

    @filter.command("点击查询")
    async def query_clicks(self, event: AstrMessageEvent):
        """按日期区间查询指定短链请求数和成功数。"""
        try:
            query_args = parse_click_query_args(event.message_str)
        except ValueError as exc:
            yield event.plain_result(str(exc))
            return

        try:
            async with self._query_lock:
                report = await build_click_count_report(
                    query_args.url,
                    query_args.start_date,
                    query_args.end_date,
                    self.event_api_base_url(),
                )
        except Exception as exc:
            logger.exception(f"点击查询失败: {exc}")
            yield event.plain_result(f"查询失败：{exc}")
            return

        yield event.plain_result(
            f"{report.url} 在 {report.period_start} 到 {report.period_end} "
            f"成功 {report.success_total} 个"
        )

    @filter.command("昨日点击总览")
    async def yesterday_clicks_overview(self, event: AstrMessageEvent):
        """查询昨日点击成功和失败总览，并以图片形式回复。"""
        try:
            async with self._query_lock:
                overview = await build_click_overview(self.event_api_base_url())
                if not self.image_response_enabled():
                    yield event.plain_result(format_click_overview_text(overview))
                    return

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
                    OVERVIEW_IMAGE_HEIGHT,
                )
        except Exception as exc:
            logger.exception(f"昨日点击总览查询失败: {exc}")
            yield event.plain_result(f"查询失败：{exc}")
            return

        yield event.image_result(image_url)

    @filter.command("当前队列")
    async def current_queue(self, event: AstrMessageEvent):
        """查询当前任务队列和事件队列，并以图片形式回复。"""
        try:
            report = await build_queue_metrics_report()
            if not self.image_response_enabled():
                yield event.plain_result(format_queue_metrics_text(report))
                return

            server_1, server_2 = report.servers
            image_url = await self.render_image(
                QUEUE_TEMPLATE,
                {
                    "total": report.total,
                    "server_1_name": server_1.name,
                    "server_1_url": server_1.base_url,
                    "server_1_total": server_1.metrics.total,
                    "server_1_task_queue_key": server_1.metrics.task_queue.key,
                    "server_1_task_queue_size": server_1.metrics.task_queue.size,
                    "server_1_event_queue_key": server_1.metrics.event_queue.key,
                    "server_1_event_queue_size": server_1.metrics.event_queue.size,
                    "server_2_name": server_2.name,
                    "server_2_url": server_2.base_url,
                    "server_2_total": server_2.metrics.total,
                    "server_2_task_queue_key": server_2.metrics.task_queue.key,
                    "server_2_task_queue_size": server_2.metrics.task_queue.size,
                    "server_2_event_queue_key": server_2.metrics.event_queue.key,
                    "server_2_event_queue_size": server_2.metrics.event_queue.size,
                },
                QUEUE_IMAGE_HEIGHT,
            )
        except Exception as exc:
            logger.exception(f"当前队列查询失败: {exc}")
            yield event.plain_result(f"查询失败：{exc}")
            return

        yield event.image_result(image_url)

    async def terminate(self):
        """插件卸载时无需额外清理持久化数据。"""
