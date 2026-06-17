from __future__ import annotations

import asyncio
import csv
import json
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


PLUGIN_NAME = "HeylooBot"
API_URL = "http://8.218.63.188:8181/api/query"
REQUEST_TIMEOUT_SECONDS = 300
SCRIPT_TIMEOUT_SECONDS = 120
DOWNLOAD_RETRY_TIMES = 2
DOWNLOAD_RETRY_INTERVAL_SECONDS = 2
QUERY_SQL = "SELECT * FROM event_log WHERE action IN ('click-success', 'click-fail') AND event_time >= DATE_SUB(CURDATE(), INTERVAL 1 DAY) AND event_time < CURDATE() ORDER BY event_time DESC;"
REQUEST_HEADERS = {
    "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Host": "8.218.63.188:8181",
    "Connection": "keep-alive",
}
SCRIPT_PATH = Path(__file__).resolve().parent / "scripts" / "extract_url_records.py"
REQUEST_JSON_NAME = "request.json"
REQUEST_META_NAME = "request_meta.json"
RECORD_CSV_NAME = "record.csv"


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


def is_valid_json_file(path: Path) -> bool:
    """确认响应文件是完整 JSON，避免复用半截响应。"""
    try:
        if not path.exists() or path.stat().st_size == 0:
            return False

        with path.open("r", encoding="utf-8") as file:
            json.load(file)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False

    return True


def write_request_cache_meta(meta_path: Path, query_date: date) -> None:
    """记录 request.json 对应的查询日期，同一天内允许复用。"""
    payload = {
        "query_date": query_date.isoformat(),
        "target_date": (query_date - timedelta(days=1)).isoformat(),
        "request_file": REQUEST_JSON_NAME,
    }
    meta_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def is_request_cache_current(
    request_path: Path,
    meta_path: Path,
    query_date: date,
) -> bool:
    """判断 request.json 是否属于今天发起的昨日查询。"""
    try:
        if not is_valid_json_file(request_path):
            return False

        with meta_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError):
        return False

    return payload.get("query_date") == query_date.isoformat()


def replace_downloaded_file(temp_path: Path, output_path: Path) -> None:
    """下载完成并通过 JSON 校验后，原子替换正式缓存文件。"""
    if not is_valid_json_file(temp_path):
        raise RuntimeError("接口返回内容不是完整 JSON")

    temp_path.replace(output_path)


async def fetch_event_log(output_path: Path) -> None:
    """调用查询接口并保存原始 JSON，失败时保留旧缓存文件。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_name(f"{output_path.name}.tmp")
    errors: list[str] = []

    for attempt in range(1, DOWNLOAD_RETRY_TIMES + 1):
        try:
            await fetch_event_log_with_aiohttp(temp_path)
            replace_downloaded_file(temp_path, output_path)
            return
        except Exception as exc:
            if is_valid_json_file(temp_path):
                temp_path.replace(output_path)
                return

            errors.append(f"aiohttp第{attempt}次失败：{exc}")
            temp_path.unlink(missing_ok=True)
            if attempt < DOWNLOAD_RETRY_TIMES:
                await asyncio.sleep(DOWNLOAD_RETRY_INTERVAL_SECONDS)

    try:
        await fetch_event_log_with_curl(temp_path)
        replace_downloaded_file(temp_path, output_path)
        return
    except Exception as exc:
        if is_valid_json_file(temp_path):
            temp_path.replace(output_path)
            return

        errors.append(f"curl兜底失败：{exc}")
        temp_path.unlink(missing_ok=True)

    raise RuntimeError("接口查询失败：" + "；".join(errors))


async def fetch_event_log_with_aiohttp(output_path: Path) -> None:
    """用 aiohttp 下载响应，读到完整 JSON 后由上层替换缓存文件。"""
    try:
        import aiohttp
    except ImportError as exc:
        raise RuntimeError("缺少 aiohttp 依赖，请先安装 requirements.txt") from exc

    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    payload = {"sql": QUERY_SQL}

    async with aiohttp.ClientSession(timeout=timeout, headers=REQUEST_HEADERS) as session:
        async with session.post(API_URL, json=payload) as response:
            response.raise_for_status()
            with output_path.open("wb") as file:
                async for chunk in response.content.iter_chunked(1024 * 1024):
                    file.write(chunk)


async def fetch_event_log_with_curl(output_path: Path) -> None:
    """用 curl 兜底处理服务端提前断开或长度头不准确的响应。"""
    payload = json.dumps({"sql": QUERY_SQL}, ensure_ascii=False)
    command = [
        "curl",
        "--location",
        "--request",
        "POST",
        API_URL,
        "--max-time",
        str(REQUEST_TIMEOUT_SECONDS),
        "--connect-timeout",
        "30",
        "--silent",
        "--show-error",
        "--ignore-content-length",
        "--output",
        str(output_path),
        "--write-out",
        "%{http_code}",
    ]

    for name, value in REQUEST_HEADERS.items():
        command.extend(["--header", f"{name}: {value}"])

    command.extend(["--data-raw", payload])

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=REQUEST_TIMEOUT_SECONDS + 30,
        )
    except asyncio.TimeoutError as exc:
        process.kill()
        await process.communicate()
        raise RuntimeError("curl下载响应超时") from exc

    status_text = stdout.decode("utf-8", errors="replace").strip()
    if status_text and status_text.isdigit():
        status_code = int(status_text)
        if status_code < 200 or status_code >= 300:
            raise RuntimeError(f"接口返回HTTP {status_code}")

    if process.returncode != 0 and not is_valid_json_file(output_path):
        detail = stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(detail or f"curl退出码 {process.returncode}")


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
    data_dir.mkdir(parents=True, exist_ok=True)
    request_json = data_dir / REQUEST_JSON_NAME
    request_meta = data_dir / REQUEST_META_NAME
    record_csv = data_dir / RECORD_CSV_NAME
    query_date = date.today()

    if not is_request_cache_current(request_json, request_meta, query_date):
        await fetch_event_log(request_json)
        write_request_cache_meta(request_meta, query_date)

    await run_extract_script(pattern, request_json, record_csv)
    counts = count_click_records(record_csv)

    return ClickReport(
        pattern=pattern,
        request_json=request_json,
        record_csv=record_csv,
        counts=counts,
    )
