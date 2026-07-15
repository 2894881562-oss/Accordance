import unittest
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

import web.app as app_module
import web.history_store as history_store


def make_request(peer, headers=None, scheme="http"):
    raw_headers = [
        (name.lower().encode("ascii"), value.encode("ascii"))
        for name, value in (headers or {}).items()
    ]
    return Request({
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": scheme,
        "path": "/api/test",
        "raw_path": b"/api/test",
        "query_string": b"",
        "headers": raw_headers,
        "client": (peer, 12345),
        "server": ("testserver", 80),
    })


class WebAppBoundaryTests(unittest.TestCase):
    def setUp(self):
        app_module._rate_bucket.clear()

    def tearDown(self):
        app_module._rate_bucket.clear()

    def test_untrusted_peer_cannot_spoof_forwarded_headers(self):
        request = make_request("203.0.113.10", {
            "x-forwarded-for": "198.51.100.9",
            "x-forwarded-proto": "https",
        })
        self.assertEqual(app_module._client_ip(request), "203.0.113.10")
        self.assertFalse(app_module._is_https_request(request))

    def test_loopback_proxy_can_supply_forwarded_headers(self):
        request = make_request("127.0.0.1", {
            "x-forwarded-for": "198.51.100.9",
            "x-forwarded-proto": "https",
        })
        self.assertEqual(app_module._client_ip(request), "198.51.100.9")
        self.assertTrue(app_module._is_https_request(request))

    def test_ip_limit_survives_header_and_device_rotation(self):
        with patch.object(app_module, "RATE_LIMIT_PER_CLIENT", 10), patch.object(
            app_module, "RATE_LIMIT_PER_IP", 2
        ):
            for index in range(2):
                request = make_request(
                    "203.0.113.30",
                    {"x-forwarded-for": f"198.51.100.{index + 1}"},
                )
                app_module._rate_limit(request, f"device-{index}")
            with self.assertRaises(HTTPException) as raised:
                app_module._rate_limit(
                    make_request(
                        "203.0.113.30",
                        {"x-forwarded-for": "198.51.100.99"},
                    ),
                    "device-rotated",
                )
        self.assertEqual(raised.exception.status_code, 429)

    def test_health_reports_optional_history_degradation(self):
        with patch.object(app_module, "history_storage_status", return_value="ready"):
            self.assertEqual(
                app_module.health(),
                {"status": "ok", "history": "ready"},
            )
        with patch.object(app_module, "history_storage_status", return_value="disabled"):
            self.assertEqual(
                app_module.health(),
                {"status": "ok", "history": "disabled"},
            )
        with patch.object(app_module, "history_storage_status", return_value="degraded"):
            self.assertEqual(
                app_module.health(),
                {"status": "degraded", "history": "degraded"},
            )

    def test_history_storage_status_is_read_only(self):
        with patch.object(history_store, "HISTORY_DISABLED", True):
            self.assertEqual(history_store.history_storage_status(), "disabled")
        with patch.object(history_store, "HISTORY_DISABLED", False), patch.object(
            history_store, "web_data_dir", return_value=str(history_store.__file__)
        ):
            self.assertEqual(history_store.history_storage_status(), "degraded")
        with patch.object(history_store, "HISTORY_DISABLED", False), patch.object(
            history_store, "web_data_dir", return_value=str(history_store.os.path.dirname(__file__))
        ):
            self.assertEqual(history_store.history_storage_status(), "ready")


if __name__ == "__main__":
    unittest.main()
