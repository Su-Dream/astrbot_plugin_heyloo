IMAGE_RESPONSE_CONFIG_KEY = "enable_image_response"
EVENT_API_BASE_URL_CONFIG_KEY = "event_api_base_url"
QUEUE_API_BASE_URL_CONFIG_KEY = "queue_api_base_url"
DEFAULT_EVENT_API_BASE_URL = "http://8.218.63.188:8181"


def is_image_response_enabled(config: object) -> bool:
    """读取是否启用图片回复配置，缺省时保持图片回复。"""
    if config is None:
        return True

    getter = getattr(config, "get", None)
    if not callable(getter):
        return True

    try:
        value = getter(IMAGE_RESPONSE_CONFIG_KEY, True)
    except TypeError:
        value = getter(IMAGE_RESPONSE_CONFIG_KEY)

    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off", "关闭"}

    return bool(value)


def get_config_value(config: object, key: str, default: str = "") -> str:
    """读取字符串配置，缺省或空白时返回默认值。"""
    if config is None:
        return default

    getter = getattr(config, "get", None)
    if not callable(getter):
        return default

    try:
        value = getter(key, default)
    except TypeError:
        value = getter(key)

    if value is None:
        return default

    text = str(value).strip()
    return text or default


def normalize_base_url(url: str) -> str:
    """去掉基础 URL 末尾斜杠，方便拼接接口路径。"""
    return url.strip().rstrip("/")


def get_event_api_base_url(config: object) -> str:
    """读取打点服务器基础地址。"""
    return normalize_base_url(
        get_config_value(
            config,
            EVENT_API_BASE_URL_CONFIG_KEY,
            DEFAULT_EVENT_API_BASE_URL,
        )
    )


def get_queue_api_base_url(config: object) -> str:
    """读取队列服务器基础地址。"""
    return normalize_base_url(get_config_value(config, QUEUE_API_BASE_URL_CONFIG_KEY))


def require_configured_url(url: str, label: str) -> str:
    """确保服务器地址已经配置。"""
    if not url:
        raise RuntimeError(f"请先在插件配置中填写{label}")

    return url
