from __future__ import annotations

import asyncio
import csv
import sys
from dataclasses import dataclass
from pathlib import Path


PLUGIN_NAME = "HeylooBot"
API_URL = "http://8.218.63.188:8181/api/query"
REQUEST_TIMEOUT_SECONDS = 300
SCRIPT_TIMEOUT_SECONDS = 120
QUERY_SQL = "SELECT * FROM event_log WHERE action IN ('click-success', 'click-fail') AND event_time >= DATE_SUB(CURDATE(), INTERVAL 1 DAY) AND event_time < CURDATE() ORDER BY event_time DESC;"
REQUEST_HEADERS = {
    "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Host": "8.218.63.188:8181",
    "Connection": "keep-alive",
}
SCRIPT_PATH = Path(__file__).resolve().parent / "scripts" / "extract_url_records.py"


@dataclass(frozen=True)
class ClickCounts:
    success: int = 0
    fail: int = 0


@dataclass(frozen=True)
class ClickReport:
    pattern: str
    request_json: Path
    record_csv: Path
    counts: ClickCounts


def get_plugin_data_dir(plugin_name: str = PLUGIN_NAME) -> Path:
    """返回 AstrBot 规范插件数据目录，测试环境缺少 AstrBot 时回退到本地 data。"""
    try:
        from astrbot.core.utils.astrbot_path import get_astrbot_data_path

        data_root = Path(get_astrbot_data_path())
    except Exception:
        data_root = Path(__file__).resolve().parent / "data"

    return data_root / "plugin_data" / plugin_name


def parse_click_pattern(message: str) -> str:
    """从 /昨日点击 命令中提取 URL 片段。"""
    text = message.strip()
    for prefix in ("/昨日点击", "昨日点击"):
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


async def fetch_event_log(output_path: Path) -> None:
    """调用查询接口并以流式写入保存原始 JSON，避免大响应占用过多内存。"""
    try:
        import aiohttp
    except ImportError as exc:
        raise RuntimeError("缺少 aiohttp 依赖，请先安装 requirements.txt") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    payload = {"sql": QUERY_SQL}

    async with aiohttp.ClientSession(timeout=timeout, headers=REQUEST_HEADERS) as session:
        async with session.post(API_URL, json=payload) as response:
            response.raise_for_status()
            with output_path.open("wb") as file:
                async for chunk in response.content.iter_chunked(1024 * 1024):
                    file.write(chunk)


async def run_extract_script(
    pattern: str,
    input_path: Path,
    output_path: Path,
    script_path: Path = SCRIPT_PATH,
) -> None:
    """调用现有筛选脚本生成 record.csv。"""
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(script_path),
        pattern,
        "-i",
        str(input_path),
        "-o",
        str(output_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=SCRIPT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        process.kill()
        await process.communicate()
        raise RuntimeError("筛选点击记录超时") from exc

    if process.returncode != 0:
        detail = (stderr or stdout).decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"筛选点击记录失败：{detail or '未知错误'}")


def count_click_records(csv_path: Path) -> ClickCounts:
    """统计筛选结果中的 click-success 和 click-fail 数量。"""
    success = 0
    fail = 0

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            action = row.get("动作", "").strip()
            if action == "click-success":
                success += 1
            elif action == "click-fail":
                fail += 1

    return ClickCounts(success=success, fail=fail)


async def build_click_report(pattern: str, data_dir: Path) -> ClickReport:
    """完整执行查询、保存 request.json、生成 record.csv 和统计结果。"""
    request_json = data_dir / "request.json"
    record_csv = data_dir / "record.csv"

    await fetch_event_log(request_json)
    await run_extract_script(pattern, request_json, record_csv)
    counts = count_click_records(record_csv)

    return ClickReport(
        pattern=pattern,
        request_json=request_json,
        record_csv=record_csv,
        counts=counts,
    )
