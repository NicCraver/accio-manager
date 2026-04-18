import unittest

from accio_panel.app_settings import PanelSettings
from accio_panel.models import Account
from accio_panel.proxy_selection import (
    UPSTREAM_QUOTA_EXHAUSTED_RECOVERY_REASON,
    _plan_next_quota_check,
)


class ProxySelectionTests(unittest.TestCase):
    def test_quota_exhausted_recovery_is_capped_when_next_billing_is_far_away(self):
        account = Account(
            id="acc-1",
            name="账号1",
            access_token="access-1",
            refresh_token="refresh-1",
            utdid="utdid-1",
            auto_disabled=True,
            next_quota_check_reason=UPSTREAM_QUOTA_EXHAUSTED_RECOVERY_REASON,
        )

        next_check_at, reason = _plan_next_quota_check(
            account,
            quota_success=True,
            next_billing_at=1_800_000,
            panel_settings=PanelSettings(),
            now_ts=1_000_000,
        )

        self.assertEqual(next_check_at, 1_001_800)
        self.assertEqual(reason, UPSTREAM_QUOTA_EXHAUSTED_RECOVERY_REASON)

    def test_quota_exhausted_recovery_keeps_near_billing_retry_time(self):
        account = Account(
            id="acc-1",
            name="账号1",
            access_token="access-1",
            refresh_token="refresh-1",
            utdid="utdid-1",
            auto_disabled=True,
            next_quota_check_reason=UPSTREAM_QUOTA_EXHAUSTED_RECOVERY_REASON,
        )

        next_check_at, reason = _plan_next_quota_check(
            account,
            quota_success=True,
            next_billing_at=1_000_300,
            panel_settings=PanelSettings(),
            now_ts=1_000_000,
        )

        self.assertEqual(next_check_at, 1_000_390)
        self.assertEqual(reason, UPSTREAM_QUOTA_EXHAUSTED_RECOVERY_REASON)


if __name__ == "__main__":
    unittest.main()
