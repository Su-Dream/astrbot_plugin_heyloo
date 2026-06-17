IMAGE_RESPONSE_CONFIG_KEY = "enable_image_response"


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
