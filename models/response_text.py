from __future__ import annotations

from .click_report import ClickOverview
from .queue_report import QueueMetrics


def format_click_overview_text(overview: ClickOverview) -> str:
    """格式化昨日点击总览纯文本回复。"""
    return "\n".join(
        [
            "代理访问统计通知",
            f"统计周期：{overview.period_start} ~ {overview.period_end}",
            f"总数：{overview.total}",
            f"代理访问成功数：{overview.success}",
            f"成功率：{overview.success_rate}",
            f"代理访问失败数：{overview.fail}",
            f"失败率：{overview.fail_rate}",
            "数据来源：event_log 表 click-success / click-fail / click-fail-domain 统计结果",
        ]
    )


def format_queue_metrics_text(metrics: QueueMetrics) -> str:
    """格式化当前队列纯文本回复。"""
    return "\n".join(
        [
            "当前队列统计通知",
            f"总队列数：{metrics.total}",
            f"任务队列数量：{metrics.task_queue.size}",
            f"任务队列 Key：{metrics.task_queue.key}",
            f"事件队列数量：{metrics.event_queue.size}",
            f"事件队列 Key：{metrics.event_queue.key}",
            "数据来源：queue-metrics 当前队列指标",
        ]
    )
