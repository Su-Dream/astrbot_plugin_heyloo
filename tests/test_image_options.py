import unittest

from models.image_options import (
    IMAGE_QUALITY,
    IMAGE_WIDTH,
    QUEUE_IMAGE_HEIGHT,
    build_image_options,
)


class ImageOptionsTest(unittest.TestCase):
    def test_build_image_options_crops_card_and_uses_quality_95(self):
        options = build_image_options(QUEUE_IMAGE_HEIGHT)

        self.assertEqual(options["type"], "jpeg")
        self.assertEqual(options["quality"], IMAGE_QUALITY)
        self.assertEqual(options["quality"], 95)
        self.assertEqual(
            options["clip"],
            {
                "x": 0,
                "y": 0,
                "width": IMAGE_WIDTH,
                "height": QUEUE_IMAGE_HEIGHT,
            },
        )
        self.assertNotIn("full_page", options)


if __name__ == "__main__":
    unittest.main()
