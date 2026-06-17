import unittest

from models.click_report import ClickOverview
from models.queue_report import QueueItem, QueueMetrics
from models.response_text import format_click_overview_text, format_queue_metrics_text


class ResponseTextTest(unittest.TestCase):
    def test_format_click_overview_text(self):
        text = format_click_overview_text(
            ClickOverview(
                period_start="2026-06-16 00:00:00",
                period_end="2026-06-17 00:00:00",
                total=59488,
                success=43920,
                fail=15568,
                success_rate="73.83%",
                fail_rate="26.17%",
            )
        )

        self.assertIn("代理访问统计通知", text)
        self.assertIn("总数：59488", text)
        self.assertIn("成功率：73.83%", text)
        self.assertIn("失败率：26.17%", text)

    def test_format_queue_metrics_text(self):
        text = format_queue_metrics_text(
            QueueMetrics(
                task_queue=QueueItem(
                    name="任务队列",
                    key="proxy:queue:headed",
                    size=13859,
                ),
                event_queue=QueueItem(
                    name="事件队列",
                    key="proxy:event:queue",
                    size=196,
                ),
                total=14055,
            )
        )

        self.assertIn("当前队列统计通知", text)
        self.assertIn("总队列数：14055", text)
        self.assertIn("任务队列 Key：proxy:queue:headed", text)
        self.assertIn("事件队列 Key：proxy:event:queue", text)


if __name__ == "__main__":
    unittest.main()
