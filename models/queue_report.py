from __future__ import annotations

import asyncio
from dataclasses import dataclass


QUEUE_METRICS_URL = "http://43.98.192.252:8991/queue-metrics"
QUEUE_TIMEOUT_SECONDS = 30
QUEUE_RETRY_TIMES = 2
QUEUE_RETRY_INTERVAL_SECONDS = 1


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


async def fetch_queue_metrics_payload() -> dict[str, object]:
    """调用队列指标接口并返回 JSON 响应。"""
    try:
        import aiohttp
    except ImportError as exc:
        raise RuntimeError("缺少 aiohttp 依赖，请先安装 requirements.txt") from exc

    errors: list[str] = []
    timeout = aiohttp.ClientTimeout(total=QUEUE_TIMEOUT_SECONDS)

    for attempt in range(1, QUEUE_RETRY_TIMES + 1):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(QUEUE_METRICS_URL) as response:
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


async def build_queue_metrics() -> QueueMetrics:
    """查询当前队列指标并整理为图片模板数据。"""
    payload = await fetch_queue_metrics_payload()
    return build_queue_metrics_from_payload(payload)
