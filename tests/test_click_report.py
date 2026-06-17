import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from click_report import QUERY_SQL, ClickCounts, count_click_records, parse_click_pattern


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
