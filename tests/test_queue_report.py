import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from models.queue_report import (
    DEFAULT_QUEUE_API_BASE_URLS,
    QUEUE_HEADERS,
    QueueItem,
    QueueMetrics,
    QueueMetricsReport,
    QueueServerMetrics,
    build_queue_headers,
    build_queue_metrics_from_payload,
    build_queue_metrics_report,
    build_queue_metrics_url,
    parse_queue_size,
)


class QueueReportTest(unittest.TestCase):
    def test_queue_headers(self):
        self.assertEqual(QUEUE_HEADERS["X-Forwarded-For"], "127.0.0.1")
        self.assertEqual(
            QUEUE_HEADERS["User-Agent"],
            "Apifox/1.0.0 (https://apifox.com)",
        )
        self.assertEqual(QUEUE_HEADERS["Accept"], "*/*")
        self.assertEqual(QUEUE_HEADERS["Connection"], "keep-alive")

    def test_default_queue_api_base_urls(self):
        self.assertEqual(
            DEFAULT_QUEUE_API_BASE_URLS,
            (
                "http://43.98.192.252:8991",
                "http://154.217.241.177:8991",
            ),
        )

    def test_build_queue_metrics_url(self):
        self.assertEqual(
            build_queue_metrics_url("http://127.0.0.1:8991/"),
            "http://127.0.0.1:8991/queue-metrics",
        )

    def test_build_queue_headers_sets_host(self):
        self.assertEqual(
            build_queue_headers("http://43.98.192.252:8991")["Host"],
            "43.98.192.252:8991",
        )

    def test_parse_queue_size(self):
        self.assertEqual(parse_queue_size("12292"), 12292)
        self.assertEqual(parse_queue_size(397), 397)
        self.assertEqual(parse_queue_size(None), 0)
        self.assertEqual(parse_queue_size("bad"), 0)

    def test_build_queue_metrics_from_payload(self):
        payload = {
            "success": True,
            "data": {
                "taskQueue": {
                    "key": "proxy:queue:headed",
                    "size": 12292,
                },
                "eventQueue": {
                    "key": "proxy:event:queue",
                    "size": 397,
                },
            },
        }

        metrics = build_queue_metrics_from_payload(payload)

        self.assertEqual(
            metrics,
            QueueMetrics(
                task_queue=QueueItem(
                    name="任务队列",
                    key="proxy:queue:headed",
                    size=12292,
                ),
                event_queue=QueueItem(
                    name="事件队列",
                    key="proxy:event:queue",
                    size=397,
                ),
                total=12689,
            ),
        )

    def test_build_queue_metrics_rejects_failed_payload(self):
        with self.assertRaises(RuntimeError):
            build_queue_metrics_from_payload({"success": False})

    def test_build_queue_metrics_rejects_bad_data(self):
        with self.assertRaises(RuntimeError):
            build_queue_metrics_from_payload({"success": True, "data": []})

    def test_build_queue_metrics_report(self):
        first_metrics = QueueMetrics(
            task_queue=QueueItem("任务队列", "proxy:queue:headed", 1),
            event_queue=QueueItem("事件队列", "proxy:event:queue", 2),
            total=3,
        )
        second_metrics = QueueMetrics(
            task_queue=QueueItem("任务队列", "proxy:queue:headed", 4),
            event_queue=QueueItem("事件队列", "proxy:event:queue", 5),
            total=9,
        )

        with patch(
            "models.queue_report.build_queue_metrics",
            new=AsyncMock(side_effect=[first_metrics, second_metrics]),
        ):
            report = asyncio.run(
                build_queue_metrics_report(
                    (
                        "http://43.98.192.252:8991",
                        "http://154.217.241.177:8991",
                    )
                )
            )

        self.assertEqual(
            report,
            QueueMetricsReport(
                servers=(
                    QueueServerMetrics(
                        name="服务器1",
                        base_url="http://43.98.192.252:8991",
                        metrics=first_metrics,
                    ),
                    QueueServerMetrics(
                        name="服务器2",
                        base_url="http://154.217.241.177:8991",
                        metrics=second_metrics,
                    ),
                ),
                total=12,
            ),
        )


if __name__ == "__main__":
    unittest.main()
