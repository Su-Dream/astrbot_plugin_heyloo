import unittest

from models.plugin_config import (
    get_event_api_base_url,
    get_queue_api_base_url,
    is_image_response_enabled,
    require_configured_url,
)


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

    def test_server_base_urls_are_read_and_normalized(self):
        config = {
            "event_api_base_url": " http://127.0.0.1:8181/ ",
            "queue_api_base_url": " http://127.0.0.1:8991/ ",
        }

        self.assertEqual(get_event_api_base_url(config), "http://127.0.0.1:8181")
        self.assertEqual(get_queue_api_base_url(config), "http://127.0.0.1:8991")

    def test_server_base_urls_default_to_empty(self):
        self.assertEqual(get_event_api_base_url({}), "http://8.218.63.188:8181")
        self.assertEqual(get_queue_api_base_url({}), "")

    def test_require_configured_url(self):
        self.assertEqual(
            require_configured_url("http://127.0.0.1:8181", "打点服务器地址"),
            "http://127.0.0.1:8181",
        )
        with self.assertRaises(RuntimeError):
            require_configured_url("", "打点服务器地址")


if __name__ == "__main__":
    unittest.main()
