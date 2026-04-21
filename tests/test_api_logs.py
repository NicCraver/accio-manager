import json
import tempfile
import unittest
from pathlib import Path

from accio_panel.api_logs import ApiLogStore


class ApiLogStoreTests(unittest.TestCase):
    def test_recent_includes_upstream_attempt_entries_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "api.log"
            store = ApiLogStore(log_file)
            store.record(
                {
                    "level": "error",
                    "event": "v1_messages",
                    "success": False,
                    "phase": "upstream_attempt",
                    "attempt": 1,
                    "rootRequestId": "root-request",
                    "requestId": "attempt-request",
                    "accountName": "账号1",
                    "accountId": "acc-1",
                    "model": "claude-sonnet-4-6",
                    "stream": False,
                    "message": "上游返回错误 [429]: quota exhausted",
                    "statusCode": 502,
                    "stopReason": "upstream_turn_error",
                    "inputTokens": 0,
                    "outputTokens": 0,
                    "durationMs": 123,
                }
            )
            store.record(
                {
                    "level": "info",
                    "event": "v1_messages",
                    "success": True,
                    "requestId": "final-request",
                    "rootRequestId": "root-request",
                    "accountName": "账号2",
                    "accountId": "acc-2",
                    "model": "claude-sonnet-4-6",
                    "stream": False,
                    "message": "非流式调用完成",
                    "statusCode": 200,
                    "stopReason": "end_turn",
                    "inputTokens": 7,
                    "outputTokens": 10,
                    "durationMs": 456,
                }
            )

            items = store.recent()

            self.assertEqual(len(items), 2)
            self.assertEqual(items[0]["message"], "非流式调用完成")
            self.assertEqual(items[0]["phase"], "final")
            self.assertEqual(items[0]["attempt"], 0)
            self.assertEqual(items[1]["message"], "上游返回错误 [429]: quota exhausted")
            self.assertEqual(items[1]["phase"], "upstream_attempt")
            self.assertEqual(items[1]["attempt"], 1)
            self.assertEqual(items[1]["rootRequestId"], "root-request")
            detail = json.loads(items[1]["detailJson"])
            self.assertEqual(detail["requestId"], "attempt-request")
            self.assertEqual(detail["rootRequestId"], "root-request")

    def test_dashboard_logs_table_has_phase_and_attempt_headers(self):
        template_text = Path("accio_panel/templates/dashboard.html").read_text(
            encoding="utf-8"
        )

        self.assertIn("<th>阶段</th>", template_text)
        self.assertIn("<th>尝试</th>", template_text)
