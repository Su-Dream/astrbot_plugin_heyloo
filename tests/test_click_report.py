import asyncio
import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from models.click_report import (
    OVERVIEW_SQL,
    build_click_count_report,
    build_click_count_sql,
    build_click_counts_from_payload,
    build_click_overview_from_payload,
    build_query_api_url,
    build_yesterday_click_count_report,
    parse_click_query_args,
    parse_yesterday_click_url,
)


EVENT_API_BASE_URL = "http://127.0.0.1:8181"


class ClickReportTest(unittest.TestCase):
    def test_parse_yesterday_click_url(self):
        self.assertEqual(parse_yesterday_click_url("/昨日点击 ln.run/miTyN"), "ln.run/miTyN")
        self.assertEqual(parse_yesterday_click_url("昨日点击 ln.run/miTyN"), "ln.run/miTyN")
        self.assertEqual(parse_yesterday_click_url("ln.run/miTyN"), "ln.run/miTyN")
        self.assertEqual(parse_yesterday_click_url("/昨日点击总览"), "/昨日点击总览")

    def test_parse_click_query_args(self):
        args = parse_click_query_args("/点击查询 ln.run/9dEX9 2026-07-01 2026-07-02")

        self.assertEqual(args.url, "ln.run/9dEX9")
        self.assertEqual(args.start_date, date(2026, 7, 1))
        self.assertEqual(args.end_date, date(2026, 7, 2))

    def test_parse_click_query_args_rejects_bad_args(self):
        with self.assertRaises(ValueError):
            parse_click_query_args("/点击查询 ln.run/9dEX9 2026-07-01")

        with self.assertRaises(ValueError):
            parse_click_query_args("/点击查询 ln.run/9dEX9 2026/07/01 2026-07-02")

        with self.assertRaises(ValueError):
            parse_click_query_args("/点击查询 ln.run/9dEX9 2026-07-02 2026-07-01")

    def test_sql_has_no_newline(self):
        self.assertNotIn("\n", OVERVIEW_SQL)
        self.assertNotIn("\r", OVERVIEW_SQL)
        query_sql = build_click_count_sql(
            "ln.run/9dEX9",
            date(2026, 7, 1),
            date(2026, 7, 2),
        )
        self.assertNotIn("\n", query_sql)
        self.assertNotIn("\r", query_sql)

    def test_build_click_count_sql(self):
        self.assertEqual(
            build_click_count_sql(
                "ln.run/9dEX9",
                date(2026, 7, 1),
                date(2026, 7, 2),
            ),
            "SELECT action, COUNT(*) AS total FROM event_log "
            "WHERE event_time >= '2026-07-01 00:00:00' "
            "AND event_time < '2026-07-02 00:00:00' "
            "AND action IN ('click-request', 'click-success') "
            "AND params LIKE '%ln.run/9dEX9%' "
            "GROUP BY action ORDER BY action;",
        )

    def test_build_click_count_sql_escapes_single_quote(self):
        self.assertIn(
            "AND params LIKE '%ln.run/it''s%'",
            build_click_count_sql(
                "ln.run/it's",
                date(2026, 7, 1),
                date(2026, 7, 2),
            ),
        )

    def test_build_query_api_url(self):
        self.assertEqual(
            build_query_api_url("http://127.0.0.1:8181/"),
            "http://127.0.0.1:8181/api/query",
        )

    def test_build_click_counts_from_payload(self):
        payload = {
            "success": True,
            "data": {
                "rows": [
                    {"action": "click-request", "total": "82"},
                    {"action": "click-success", "total": "87"},
                ]
            },
            "message": "查询成功",
        }

        self.assertEqual(build_click_counts_from_payload(payload), (82, 87))

    def test_build_click_counts_from_payload_defaults_missing_actions_to_zero(self):
        payload = {
            "success": True,
            "data": {"rows": [{"action": "click-success", "total": "87"}]},
            "message": "查询成功",
        }

        self.assertEqual(build_click_counts_from_payload(payload), (0, 87))

    def test_build_click_counts_from_payload_rejects_failed_payload(self):
        with self.assertRaises(RuntimeError):
            build_click_counts_from_payload({"success": False, "message": "查询失败"})

    def test_build_click_count_report(self):
        payload = {
            "success": True,
            "data": {
                "rows": [
                    {"action": "click-request", "total": "82"},
                    {"action": "click-success", "total": "87"},
                ]
            },
            "message": "查询成功",
        }

        with patch("models.click_report.fetch_query_json", new=AsyncMock(return_value=payload)):
            report = asyncio.run(
                build_click_count_report(
                    "ln.run/9dEX9",
                    date(2026, 7, 1),
                    date(2026, 7, 2),
                    EVENT_API_BASE_URL,
                )
            )

        self.assertEqual(report.url, "ln.run/9dEX9")
        self.assertEqual(report.period_start, "2026-07-01 00:00:00")
        self.assertEqual(report.period_end, "2026-07-02 00:00:00")
        self.assertEqual(report.request_total, 82)
        self.assertEqual(report.success_total, 87)

    def test_build_yesterday_click_count_report(self):
        payload = {
            "success": True,
            "data": {
                "rows": [
                    {"action": "click-request", "total": "82"},
                    {"action": "click-success", "total": "87"},
                ]
            },
            "message": "查询成功",
        }

        with (
            patch("models.click_report.date") as date_mock,
            patch("models.click_report.fetch_query_json", new=AsyncMock(return_value=payload)),
        ):
            date_mock.today.return_value = date(2026, 7, 2)
            date_mock.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            report = asyncio.run(
                build_yesterday_click_count_report("ln.run/9dEX9", EVENT_API_BASE_URL)
            )

        self.assertEqual(report.period_start, "2026-07-01 00:00:00")
        self.assertEqual(report.period_end, "2026-07-02 00:00:00")
        self.assertEqual(report.request_total, 82)
        self.assertEqual(report.success_total, 87)

    def test_build_click_overview_from_payload(self):
        payload = {
            "success": True,
            "data": {
                "rows": [
                    {"action": "click-success", "count": "43920"},
                    {"action": "click-fail", "count": "15568"},
                    {"action": "click-fail-domain", "count": "12"},
                ]
            },
            "message": "查询成功",
        }

        overview = build_click_overview_from_payload(payload, date(2026, 6, 17))

        self.assertEqual(overview.period_start, "2026-06-16 00:00:00")
        self.assertEqual(overview.period_end, "2026-06-17 00:00:00")
        self.assertEqual(overview.total, 59500)
        self.assertEqual(overview.success, 43920)
        self.assertEqual(overview.fail, 15580)
        self.assertEqual(overview.success_rate, "73.82%")
        self.assertEqual(overview.fail_rate, "26.18%")

    def test_build_click_overview_rejects_failed_payload(self):
        with self.assertRaises(RuntimeError):
            build_click_overview_from_payload(
                {"success": False, "message": "查询失败"},
                date(2026, 6, 17),
            )


if __name__ == "__main__":
    unittest.main()
