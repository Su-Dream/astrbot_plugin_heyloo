import unittest

from models.queue_report import (
    QueueItem,
    QueueMetrics,
    build_queue_metrics_from_payload,
    parse_queue_size,
)


class QueueReportTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
