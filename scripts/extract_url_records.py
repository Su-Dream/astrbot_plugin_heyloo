#!/usr/bin/env python3
"""按完整URL或路径片段筛选记录并导出CSV"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path("requestlist/response.json")
DEFAULT_OUTPUT = Path("output/url_records.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按URL或路径片段匹配记录")
    parser.add_argument("pattern", help="要匹配的URL片段，例如 ln.run/VsOJ_")
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_rows(input_path: Path) -> list[dict[str, Any]]:
    with input_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]

    rows = payload.get("data", {}).get("rows", [])
    if not isinstance(rows, list):
        raise ValueError("未找到有效的数据行")

    return [row for row in rows if isinstance(row, dict)]


def parse_params(raw_params: Any) -> dict[str, Any]:
    if isinstance(raw_params, dict):
        return raw_params

    if isinstance(raw_params, str) and raw_params.strip():
        try:
            parsed = json.loads(raw_params)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            pass

    return {}


def contains_pattern(value: Any, pattern: str) -> bool:
    """递归搜索任意值中是否包含pattern"""
    if value is None:
        return False

    if isinstance(value, dict):
        return any(contains_pattern(v, pattern) for v in value.values())

    if isinstance(value, list):
        return any(contains_pattern(v, pattern) for v in value)

    return pattern.lower() in str(value).lower()


def main() -> None:
    args = parse_args()
    pattern = args.pattern.strip()
    output_rows: list[dict[str, Any]] = []

    for row in load_rows(args.input):
        raw_params = row.get("params", "")
        params = parse_params(raw_params)

        # 在整个row中搜索
        if contains_pattern(row, pattern):
            params_text = json.dumps(raw_params, ensure_ascii=False) if isinstance(raw_params, dict) else str(raw_params)

            output_rows.append({
                "记录ID": row.get("id", ""),
                "事件时间": row.get("event_time", ""),
                "动作": row.get("action", ""),
                "状态": params.get("status", ""),
                "原始URL": params.get("originalUrl", ""),
                "当前URL": params.get("url", ""),
                "请求URL": params.get("requestUrl", ""),
                "params原文": params_text,
            })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["记录ID", "事件时间", "动作", "状态", "原始URL", "当前URL", "请求URL", "params原文"]

    with args.output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"已导出 {len(output_rows)} 条包含 '{pattern}' 的记录到 {args.output}")


if __name__ == "__main__":
    main()
