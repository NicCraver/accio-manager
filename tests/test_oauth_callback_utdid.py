import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from accio_panel.proxy_selection import _callback_utdid_from_params
from accio_panel.store import AccountStore


class OAuthCallbackUtdidTests(unittest.TestCase):
    def test_callback_utdid_from_params_is_case_insensitive(self) -> None:
        self.assertEqual(
            _callback_utdid_from_params({"UTDID": "from-url"}),
            "from-url",
        )
        self.assertEqual(
            _callback_utdid_from_params({"utdid": "lower"}),
            "lower",
        )
        self.assertIsNone(_callback_utdid_from_params({"other": "x"}))

    def test_upsert_from_callback_uses_explicit_utdid_for_new_account(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountStore(Path(tmp), None)
            account, created = store.upsert_from_callback(
                access_token="access-new",
                refresh_token="refresh-new",
                expires_at=None,
                cookie=None,
                utdid="browser-session-utdid",
            )
            self.assertTrue(created)
            self.assertEqual(account.utdid, "browser-session-utdid")

    def test_upsert_from_callback_prefers_explicit_over_local_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "accio_panel.store.read_local_accio_utdid_file",
                return_value="from-desktop-file",
            ):
                store = AccountStore(Path(tmp), None)
                account, created = store.upsert_from_callback(
                    access_token="access-a",
                    refresh_token="refresh-a",
                    expires_at=None,
                    cookie=None,
                    utdid="from-oauth-query",
                )
            self.assertTrue(created)
            self.assertEqual(account.utdid, "from-oauth-query")

    def test_upsert_from_callback_reads_local_file_when_no_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "accio_panel.store.read_local_accio_utdid_file",
                return_value="desktop-utdid-file",
            ):
                store = AccountStore(Path(tmp), None)
                account, created = store.upsert_from_callback(
                    access_token="access-b",
                    refresh_token="refresh-b",
                    expires_at=None,
                    cookie=None,
                )
            self.assertTrue(created)
            self.assertEqual(account.utdid, "desktop-utdid-file")

    def test_upsert_from_callback_updates_utdid_when_explicit_on_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountStore(Path(tmp), None)
            first, created = store.upsert_from_callback(
                access_token="access-c",
                refresh_token="refresh-c1",
                expires_at=None,
                cookie=None,
                utdid="old-utdid",
            )
            self.assertTrue(created)
            second, updated = store.upsert_from_callback(
                access_token="access-c",
                refresh_token="refresh-c2",
                expires_at=None,
                cookie=None,
                utdid="new-utdid",
            )
            self.assertFalse(updated)
            self.assertEqual(first.id, second.id)
            self.assertEqual(second.utdid, "new-utdid")
            self.assertEqual(second.refresh_token, "refresh-c2")

    def test_upsert_from_callback_keeps_utdid_when_update_has_no_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountStore(Path(tmp), None)
            store.upsert_from_callback(
                access_token="access-d",
                refresh_token="refresh-d1",
                expires_at=None,
                cookie=None,
                utdid="stable",
            )
            account, _ = store.upsert_from_callback(
                access_token="access-d",
                refresh_token="refresh-d2",
                expires_at=None,
                cookie=None,
                utdid=None,
            )
            self.assertEqual(account.utdid, "stable")


if __name__ == "__main__":
    unittest.main()
