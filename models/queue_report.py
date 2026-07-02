from __future__ import annotations

import asyncio
from dataclasses import dataclass
from urllib.parse import urlparse


QUEUE_METRICS_PATH = "/queue-metrics"
QUEUE_TIMEOUT_SECONDS = 30
QUEUE_RETRY_TIMES = 2
QUEUE_RETRY_INTERVAL_SECONDS = 1
DEFAULT_QUEUE_API_BASE_URLS = (
    "http://43.98.192.252:8991",
    "http://154.217.241.177:8991",
)
QUEUE_HEADERS = {
    "X-Forwarded-For": "127.0.0.1",
    "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
    "Accept": "*/*",
    "Connection": "keep-alive",
}


@dataclass(frozen=True)
class QueueItem:
    name: str
    key: str
    size: int


@dataclass(frozen=True)
class QueueMetrics:
    task_queue: QueueItem
    event_queue: QueueItem
    total: int


@dataclass(frozen=True)
class QueueServerMetrics:
    name: str
    base_url: str
    metrics: QueueMetrics


@dataclass(frozen=True)
class QueueMetricsReport:
    servers: tuple[QueueServerMetrics, ...]
    total: int


def parse_queue_size(value: object) -> int:
    """将队列长度安全转换为整数。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def parse_queue_item(payload: object, name: str) -> QueueItem:
    """解析单个队列指标，缺失字段时给出安全默认值。"""
    if not isinstance(payload, dict):
        return QueueItem(name=name, key="", size=0)

    return QueueItem(
        name=name,
        key=str(payload.get("key", "")),
        size=parse_queue_size(payload.get("size", 0)),
    )


def build_queue_metrics_from_payload(payload: dict[str, object]) -> QueueMetrics:
    """解析队列指标接口响应，生成图片模板所需数据。"""
    if not payload.get("success", False):
        raise RuntimeError("队列指标接口返回失败")

    data = payload.get("data", {})
    if not isinstance(data, dict):
        raise RuntimeError("队列指标接口返回数据格式错误")

    task_queue = parse_queue_item(data.get("taskQueue", {}), "任务队列")
    event_queue = parse_queue_item(data.get("eventQueue", {}), "事件队列")

    return QueueMetrics(
        task_queue=task_queue,
        event_queue=event_queue,
        total=task_queue.size + event_queue.size,
    )


def build_queue_metrics_url(queue_api_base_url: str) -> str:
    """拼接队列指标接口地址。"""
    return f"{queue_api_base_url.rstrip('/')}{QUEUE_METRICS_PATH}"


def build_queue_headers(queue_api_base_url: str) -> dict[str, str]:
    """生成队列接口请求头，Host 与目标服务器保持一致。"""
    headers = dict(QUEUE_HEADERS)
    host = urlparse(queue_api_base_url).netloc
    if host:
        headers["Host"] = host

    return headers


async def fetch_queue_metrics_payload(queue_api_base_url: str) -> dict[str, object]:
    """调用队列指标接口并返回 JSON 响应。"""
    try:
        import aiohttp
    except ImportError as exc:
        raise RuntimeError("缺少 aiohttp 依赖，请先安装 requirements.txt") from exc

    errors: list[str] = []
    timeout = aiohttp.ClientTimeout(total=QUEUE_TIMEOUT_SECONDS)
    metrics_url = build_queue_metrics_url(queue_api_base_url)
    headers = build_queue_headers(queue_api_base_url)

    for attempt in range(1, QUEUE_RETRY_TIMES + 1):
        try:
            async with aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
            ) as session:
                async with session.get(metrics_url) as response:
                    response.raise_for_status()
                    payload = await response.json()
                    if not isinstance(payload, dict):
                        raise RuntimeError("队列指标接口返回数据格式错误")

                    return payload
        except Exception as exc:
            errors.append(f"aiohttp第{attempt}次失败：{exc}")
            if attempt < QUEUE_RETRY_TIMES:
                await asyncio.sleep(QUEUE_RETRY_INTERVAL_SECONDS)

    raise RuntimeError("队列指标查询失败：" + "；".join(errors))


async def build_queue_metrics(queue_api_base_url: str) -> QueueMetrics:
    """查询当前队列指标并整理为图片模板数据。"""
    payload = await fetch_queue_metrics_payload(queue_api_base_url)
    return build_queue_metrics_from_payload(payload)


async def build_queue_metrics_report(
    queue_api_base_urls: tuple[str, ...] = DEFAULT_QUEUE_API_BASE_URLS,
) -> QueueMetricsReport:
    """查询多台队列服务器指标并汇总。"""
    metrics_list = await asyncio.gather(
        *(build_queue_metrics(base_url) for base_url in queue_api_base_urls)
    )
    servers = tuple(
        QueueServerMetrics(
            name=f"服务器{index}",
            base_url=base_url,
            metrics=metrics,
        )
        for index, (base_url, metrics) in enumerate(
            zip(queue_api_base_urls, metrics_list),
            start=1,
        )
    )

    return QueueMetricsReport(
        servers=servers,
        total=sum(server.metrics.total for server in servers),
    )
