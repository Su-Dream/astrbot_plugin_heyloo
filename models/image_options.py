IMAGE_WIDTH = 598
OVERVIEW_IMAGE_HEIGHT = 276
QUEUE_IMAGE_HEIGHT = 254
IMAGE_QUALITY = 95


def build_image_options(height: int) -> dict[str, object]:
    """生成 AstrBot HTML 转图片的裁剪和质量参数。"""
    return {
        "type": "jpeg",
        "quality": IMAGE_QUALITY,
        "clip": {
            "x": 0,
            "y": 0,
            "width": IMAGE_WIDTH,
            "height": height,
        },
    }
