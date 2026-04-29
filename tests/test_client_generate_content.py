import unittest
from unittest.mock import Mock
from urllib.parse import parse_qs, unquote, urlparse

from accio_panel.client import AccioClient
from accio_panel.config import Settings
from accio_panel.models import Account


class ClientBuildLoginUrlTests(unittest.TestCase):
    def test_build_login_url_embeds_login_trace_id_and_ttid_like_desktop(self):
        client = AccioClient(Settings())
        url = client.build_login_url(
            "http://127.0.0.1:4097/auth/callback",
            state="fixedstate",
            ttid="ttid_a1496e61d3e948a39374b460a5acd0dd",
            login_trace_id="login_8515120529314d38ac9bad3337c839b7",
        )
        self.assertTrue(url.startswith("https://www.accio.com/login?"))
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        self.assertEqual(qs["state"], ["fixedstate"])
        self.assertEqual(qs["ttid"], ["ttid_a1496e61d3e948a39374b460a5acd0dd"])
        return_url = unquote(qs["return_url"][0])
        self.assertIn(
            "login_trace_id=login_8515120529314d38ac9bad3337c839b7", return_url
        )
        self.assertTrue(return_url.startswith("http://127.0.0.1:4097/auth/callback"))

    def test_build_login_url_does_not_duplicate_login_trace_id(self):
        client = AccioClient(Settings())
        url = client.build_login_url(
            "http://127.0.0.1:4097/auth/callback?login_trace_id=login_keep",
            state="s",
            ttid="ttid_one",
        )
        qs = parse_qs(urlparse(url).query)
        return_url = unquote(qs["return_url"][0])
        self.assertEqual(return_url.count("login_trace_id"), 1)
        self.assertIn("login_keep", return_url)

    def test_build_login_url_uses_configurable_login_host(self):
        settings = Settings(login_base_url="https://www.accio-ai.com")
        client = AccioClient(settings)
        url = client.build_login_url(
            "http://127.0.0.1:4097/auth/callback",
            state="s",
            ttid="ttid_x",
            login_trace_id="login_y",
        )
        self.assertTrue(url.startswith("https://www.accio-ai.com/login?"))


class ClientGenerateContentTests(unittest.TestCase):
    def test_generate_content_uses_reqtxt_headers(self):
        client = AccioClient(Settings())
        client._session.post = Mock()
        account = Account(
            id="acc-1",
            name="账号1",
            access_token="token-1",
            refresh_token="refresh-1",
            utdid="utdid-1",
        )

        client.generate_content(account, {"model": "claude-sonnet-4-6"})

        _, kwargs = client._session.post.call_args
        headers = kwargs["headers"]
        self.assertEqual(headers["content-type"], "application/json")
        self.assertEqual(headers["accept"], "text/event-stream")
        self.assertEqual(headers["x-utdid"], "utdid-1")
        self.assertEqual(headers["utdid"], "utdid-1")
        self.assertEqual(headers["x-app-version"], Settings().version)
        self.assertEqual(headers["x-os"], "win32")
        self.assertEqual(headers["appKey"], "35298846")
        self.assertEqual(headers["user-agent"], "node")
        self.assertEqual(headers["accept-language"], "*")
        self.assertEqual(headers["sec-fetch-mode"], "cors")

    def test_generate_content_sets_x_cna_from_cookie_without_cookie_header(self):
        client = AccioClient(Settings())
        client._session.post = Mock()
        account = Account(
            id="acc-1",
            name="账号1",
            access_token="token-1",
            refresh_token="refresh-1",
            utdid="utdid-1",
            cookie="cna=abc123; session=x",
        )

        client.generate_content(account, {"model": "claude-sonnet-4-6"})

        _, kwargs = client._session.post.call_args
        headers = kwargs["headers"]
        self.assertEqual(headers["x-cna"], "abc123")
        self.assertNotIn("Cookie", headers)


if __name__ == "__main__":
    unittest.main()
