import asyncio
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

from click_report import (
    QUERY_SQL,
    ClickCounts,
    build_click_report,
    count_click_records,
    is_request_cache_current,
    parse_click_pattern,
    write_request_cache_meta,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT_DIR / "scripts" / "extract_url_records.py"


class ClickReportTest(unittest.TestCase):
    def test_parse_click_pattern(self):
        self.assertEqual(parse_click_pattern("/昨日点击 ln.run/miTyN"), "ln.run/miTyN")
        self.assertEqual(parse_click_pattern("昨日点击 ln.run/miTyN"), "ln.run/miTyN")
        self.assertEqual(parse_click_pattern("ln.run/miTyN"), "ln.run/miTyN")

    def test_query_sql_has_no_newline(self):
        self.assertNotIn("\n", QUERY_SQL)
        self.assertNotIn("\r", QUERY_SQL)

    def test_request_cache_only_reuses_same_query_date(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            request_path = temp_path / "request.json"
            meta_path = temp_path / "request_meta.json"
            query_date = date(2026, 6, 17)

            request_path.write_text('{"data":{"rows":[]}}', encoding="utf-8")
            write_request_cache_meta(meta_path, query_date)

            self.assertTrue(
                is_request_cache_current(request_path, meta_path, query_date)
            )
            self.assertFalse(
                is_request_cache_current(
                    request_path,
                    meta_path,
                    date(2026, 6, 18),
                )
            )

    def test_request_cache_rejects_incomplete_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            request_path = temp_path / "request.json"
            meta_path = temp_path / "request_meta.json"
            query_date = date(2026, 6, 17)

            request_path.write_text('{"data":{"rows":[}', encoding="utf-8")
            write_request_cache_meta(meta_path, query_date)

            self.assertFalse(
                is_request_cache_current(request_path, meta_path, query_date)
            )

    def test_build_click_report_reuses_same_day_request_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            request_path = temp_path / "request.json"
            request_path.write_text('{"data":{"rows":[]}}', encoding="utf-8")
            write_request_cache_meta(temp_path / "request_meta.json", date.today())

            async def fake_extract(_pattern, _input_path, output_path):
                with output_path.open("w", encoding="utf-8-sig", newline="") as file:
                    writer = csv.DictWriter(file, fieldnames=["动作"])
                    writer.writeheader()

            with (
                patch("click_report.fetch_event_log", new=AsyncMock()) as fetch_mock,
                patch("click_report.run_extract_script", new=fake_extract),
            ):
                report = asyncio.run(build_click_report("ln.run/miTyN", temp_path))

            fetch_mock.assert_not_awaited()
            self.assertEqual(report.record_csv, temp_path / "record.csv")

    def test_build_click_report_refreshes_next_day_request_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            request_path = temp_path / "request.json"
            request_path.write_text('{"data":{"rows":[]}}', encoding="utf-8")
            write_request_cache_meta(
                temp_path / "request_meta.json",
                date(2026, 6, 17),
            )

            async def fake_fetch(output_path):
                output_path.write_text('{"data":{"rows":[]}}', encoding="utf-8")

            async def fake_extract(_pattern, _input_path, output_path):
                with output_path.open("w", encoding="utf-8-sig", newline="") as file:
                    writer = csv.DictWriter(file, fieldnames=["动作"])
                    writer.writeheader()

            fetch_mock = AsyncMock(side_effect=fake_fetch)
            with (
                patch("click_report.date") as date_mock,
                patch("click_report.fetch_event_log", new=fetch_mock),
                patch("click_report.run_extract_script", new=fake_extract),
            ):
                date_mock.today.return_value = date(2026, 6, 18)
                date_mock.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
                asyncio.run(build_click_report("ln.run/miTyN", temp_path))

            fetch_mock.assert_awaited_once_with(request_path)

    def test_count_click_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "record.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=["动作"])
                writer.writeheader()
                writer.writerows(
                    [
                        {"动作": "click-success"},
                        {"动作": "click-fail"},
                        {"动作": "click-success"},
                    ]
                )

            self.assertEqual(
                count_click_records(csv_path),
                ClickCounts(success=2, fail=1),
            )

    def test_extract_script_filters_url_pattern(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "request.json"
            output_path = temp_path / "record.csv"
            payload = {
                "data": {
                    "rows": [
                        {
                            "id": 1,
                            "event_time": "2026-06-16 10:00:00",
                            "action": "click-success",
                            "params": json.dumps({"url": "https://ln.run/miTyN"}),
                        },
                        {
                            "id": 2,
                            "event_time": "2026-06-16 11:00:00",
                            "action": "click-fail",
                            "params": {"requestUrl": "ln.run/miTyN", "status": "timeout"},
                        },
                        {
                            "id": 3,
                            "event_time": "2026-06-16 12:00:00",
                            "action": "click-success",
                            "params": {"url": "https://ln.run/other"},
                        },
                    ]
                }
            }
            input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "ln.run/miTyN",
                    "-i",
                    str(input_path),
                    "-o",
                    str(output_path),
                ],
                capture_output=True,
                check=False,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(count_click_records(output_path), ClickCounts(success=1, fail=1))


if __name__ == "__main__":
    unittest.main()
