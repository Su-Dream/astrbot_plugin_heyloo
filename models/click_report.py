from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta


PLUGIN_NAME = "HeylooBot"
QUERY_API_PATH = "/api/query"
REQUEST_TIMEOUT_SECONDS = 300
DOWNLOAD_RETRY_TIMES = 2
DOWNLOAD_RETRY_INTERVAL_SECONDS = 2
OVERVIEW_SQL = "SELECT action, COUNT(*) AS count FROM event_log WHERE action IN ( 'click-success', 'click-fail', 'click-fail-domain' ) AND created_at >= DATE_SUB(CURDATE(), INTERVAL 1 DAY) AND created_at < CURDATE() GROUP BY action ORDER BY count DESC;"
REQUEST_HEADERS = {
    "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Connection": "keep-alive",
}
DATE_FORMAT = "%Y-%m-%d"


@dataclass(frozen=True)
class ClickQueryArgs:
    url: str
    start_date: date
    end_date: date


@dataclass(frozen=True)
class ClickCountReport:
    url: str
    period_start: str
    period_end: str
    request_total: int
    success_total: int


@dataclass(frozen=True)
class ClickOverview:
    period_start: str
    period_end: str
    total: int
    success: int
    fail: int
    success_rate: str
    fail_rate: str


def parse_command_args(message: str, command: str) -> str:
    """从命令消息中提取参数文本。"""
    text = message.strip()
    for prefix in (f"/{command}", command):
        if text == prefix:
            return ""

        if text.startswith(prefix + " "):
            return text[len(prefix) :].strip()

    return text


def parse_yesterday_click_url(message: str) -> str:
    """从 /昨日点击 命令中提取 URL。"""
    return parse_command_args(message, "昨日点击")


def parse_query_date(value: str) -> date:
    """解析 YYYY-MM-DD 日期参数。"""
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except ValueError as exc:
        raise ValueError("日期格式应为 YYYY-MM-DD") from exc


def parse_click_query_args(message: str) -> ClickQueryArgs:
    """从 /点击查询 命令中解析 URL 和日期区间。"""
    args_text = parse_command_args(message, "点击查询")
    parts = args_text.split()
    if len(parts) != 3:
        raise ValueError("请按格式输入：/点击查询 ln.run/miTyN 2026-07-01 2026-07-02")

    url, start_text, end_text = parts
    start_date = parse_query_date(start_text)
    end_date = parse_query_date(end_text)
    if start_date >= end_date:
        raise ValueError("截止时间必须晚于起始时间")

    return ClickQueryArgs(url=url, start_date=start_date, end_date=end_date)


def parse_count(value: object) -> int:
    """将接口返回的字符串或数字计数安全转换为整数。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def build_click_overview_from_payload(
    payload: dict[str, object],
    query_date: date,
) -> ClickOverview:
    """解析总览接口响应，生成图片模板所需的数据。"""
    if not payload.get("success", False):
        message = payload.get("message", "查询失败")
        raise RuntimeError(str(message))

    data = payload.get("data", {})
    rows = data.get("rows", []) if isinstance(data, dict) else []
    if not isinstance(rows, list):
        raise RuntimeError("总览接口返回数据格式错误")

    action_counts: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue

        action = str(row.get("action", ""))
        action_counts[action] = parse_count(row.get("count", 0))

    success = action_counts.get("click-success", 0)
    fail = action_counts.get("click-fail", 0) + action_counts.get(
        "click-fail-domain",
        0,
    )
    total = sum(action_counts.values())
    success_rate = (success / total * 100) if total else 0
    fail_rate = (fail / total * 100) if total else 0
    target_date = query_date - timedelta(days=1)

    return ClickOverview(
        period_start=f"{target_date.isoformat()} 00:00:00",
        period_end=f"{query_date.isoformat()} 00:00:00",
        total=total,
        success=success,
        fail=fail,
        success_rate=f"{success_rate:.2f}%",
        fail_rate=f"{fail_rate:.2f}%",
    )


def build_click_counts_from_payload(payload: dict[str, object]) -> tuple[int, int]:
    """解析点击请求数和成功数接口响应。"""
    if not payload.get("success", False):
        message = payload.get("message", "查询失败")
        raise RuntimeError(str(message))

    data = payload.get("data", {})
    rows = data.get("rows", []) if isinstance(data, dict) else []
    if not isinstance(rows, list):
        raise RuntimeError("点击查询接口返回数据格式错误")

    action_counts: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue

        action = str(row.get("action", ""))
        action_counts[action] = parse_count(row.get("total", 0))

    return (
        action_counts.get("click-request", 0),
        action_counts.get("click-success", 0),
    )


def build_query_api_url(event_api_base_url: str) -> str:
    """拼接打点查询接口地址。"""
    return f"{event_api_base_url.rstrip('/')}{QUERY_API_PATH}"


def format_day_start(day: date) -> str:
    """格式化查询边界时间。"""
    return f"{day.isoformat()} 00:00:00"


def escape_sql_literal(value: str) -> str:
    """转义 SQL 字符串字面量中的单引号。"""
    return value.replace("'", "''")


def build_click_count_sql(url: str, start_date: date, end_date: date) -> str:
    """构造指定 URL 在日期区间内的请求数和成功数 SQL。"""
    period_start = format_day_start(start_date)
    period_end = format_day_start(end_date)
    escaped_url = escape_sql_literal(url)
    return (
        "SELECT action, COUNT(*) AS total FROM event_log "
        f"WHERE event_time >= '{period_start}' "
        f"AND event_time < '{period_end}' "
        "AND action IN ('click-request', 'click-success') "
        f"AND params LIKE '%{escaped_url}%' "
        "GROUP BY action ORDER BY action;"
    )


async def fetch_query_json(sql: str, event_api_base_url: str) -> dict[str, object]:
    """调用查询接口并返回 JSON 响应。"""
    try:
        import aiohttp
    except ImportError as exc:
        raise RuntimeError("缺少 aiohttp 依赖，请先安装 requirements.txt") from exc

    errors: list[str] = []
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    payload = {"sql": sql}
    api_url = build_query_api_url(event_api_base_url)

    for attempt in range(1, DOWNLOAD_RETRY_TIMES + 1):
        try:
            async with aiohttp.ClientSession(
                timeout=timeout,
                headers=REQUEST_HEADERS,
            ) as session:
                async with session.post(api_url, json=payload) as response:
                    response.raise_for_status()
                    text = await response.text()
                    parsed = json.loads(text)
                    if not isinstance(parsed, dict):
                        raise RuntimeError("接口返回数据格式错误")

                    return parsed
        except Exception as exc:
            errors.append(f"aiohttp第{attempt}次失败：{exc}")
            if attempt < DOWNLOAD_RETRY_TIMES:
                await asyncio.sleep(DOWNLOAD_RETRY_INTERVAL_SECONDS)

    raise RuntimeError("接口查询失败：" + "；".join(errors))


async def build_click_count_report(
    url: str,
    start_date: date,
    end_date: date,
    event_api_base_url: str,
) -> ClickCountReport:
    """查询指定 URL 在日期区间内的请求数和成功数。"""
    payload = await fetch_query_json(
        build_click_count_sql(url, start_date, end_date),
        event_api_base_url,
    )
    request_total, success_total = build_click_counts_from_payload(payload)
    return ClickCountReport(
        url=url,
        period_start=format_day_start(start_date),
        period_end=format_day_start(end_date),
        request_total=request_total,
        success_total=success_total,
    )


async def build_yesterday_click_count_report(
    url: str,
    event_api_base_url: str,
) -> ClickCountReport:
    """查询指定 URL 昨日 0 点到今日 0 点的请求数和成功数。"""
    end_date = date.today()
    start_date = end_date - timedelta(days=1)
    return await build_click_count_report(url, start_date, end_date, event_api_base_url)


async def build_click_overview(event_api_base_url: str) -> ClickOverview:
    """查询昨日点击总览并整理为图片模板数据。"""
    payload = await fetch_query_json(OVERVIEW_SQL, event_api_base_url)
    return build_click_overview_from_payload(payload, date.today())
