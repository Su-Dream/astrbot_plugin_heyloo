import unittest

from models.plugin_config import is_image_response_enabled


class DictLikeConfig:
    def __init__(self, value):
        self.value = value

    def get(self, _key, _default=True):
        return self.value


class PluginConfigTest(unittest.TestCase):
    def test_image_response_defaults_to_enabled(self):
        self.assertTrue(is_image_response_enabled(None))
        self.assertTrue(is_image_response_enabled({}))

    def test_image_response_reads_bool_value(self):
        self.assertTrue(is_image_response_enabled({"enable_image_response": True}))
        self.assertFalse(is_image_response_enabled({"enable_image_response": False}))
        self.assertFalse(is_image_response_enabled(DictLikeConfig(False)))

    def test_image_response_reads_false_string(self):
        self.assertFalse(is_image_response_enabled({"enable_image_response": "false"}))
        self.assertFalse(is_image_response_enabled({"enable_image_response": "关闭"}))


if __name__ == "__main__":
    unittest.main()
