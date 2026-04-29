from __future__ import annotations

import unittest

from accio_panel.desktop_credentials import DesktopCredentials


class DesktopCredentialsTests(unittest.TestCase):
    def test_to_account_payload_uses_stable_desktop_account_id(self) -> None:
        credentials = DesktopCredentials(
            access_token="access-token",
            refresh_token="refresh-token",
            expires_at=1_779_415_721,
            cookie="cookie=value",
            utdid="desktop-utdid",
            user_id="7083353518",
            user_name="quan hong li",
        )

        payload = credentials.to_account_payload()

        self.assertEqual(payload["id"], "desktop-7083353518")
        self.assertEqual(payload["name"], "桌面端-quan hong li")
        self.assertEqual(payload["utdid"], "desktop-utdid")
        self.assertEqual(payload["accessToken"], "access-token")
        self.assertEqual(payload["refreshToken"], "refresh-token")
        self.assertEqual(payload["expiresAt"], 1_779_415_721)

    def test_to_account_payload_keeps_optional_identity_fields_empty(self) -> None:
        credentials = DesktopCredentials(
            access_token="access-token",
            refresh_token="refresh-token",
            expires_at=None,
            cookie=None,
            utdid="desktop-utdid",
        )

        payload = credentials.to_account_payload()

        self.assertNotIn("id", payload)
        self.assertNotIn("name", payload)
        self.assertEqual(payload["utdid"], "desktop-utdid")


if __name__ == "__main__":
    unittest.main()
