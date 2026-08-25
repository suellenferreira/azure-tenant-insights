from types import SimpleNamespace
from typing import Optional
import unittest
from unittest.mock import MagicMock, patch

import requests

from collectors.costs import MAX_COST_RETRIES, RetryBudget, _get_subscription_costs, collect_costs


def _response(status_code: int, payload: dict, headers: Optional[dict] = None) -> MagicMock:
    response = MagicMock(spec=requests.Response)
    response.status_code = status_code
    response.headers = headers or {}
    response.reason = "Bad Request" if status_code == 400 else "Too Many Requests"
    response.text = str(payload)
    response.json.return_value = payload
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=response
        )
    else:
        response.raise_for_status.return_value = None
    return response


class CostRetryTests(unittest.TestCase):
    def test_forbidden_reports_context_without_assuming_missing_role(self) -> None:
        response = _response(
            403,
            {"error": {"code": "AuthorizationFailed", "message": "Access denied."}},
            {"x-ms-request-id": "request-403"},
        )
        credential = MagicMock()
        credential.get_token.return_value = SimpleNamespace(token="token")

        with patch("collectors.costs.requests.post", return_value=response):
            with self.assertLogs("collectors.costs", level="WARNING") as logs:
                result = collect_costs(credential, ["sub-1"])

        self.assertEqual(result, [])
        message = logs.output[-1]
        self.assertIn("HTTP 403", message)
        self.assertIn("does not identify a missing role", message)
        self.assertIn("identity, tenant, token, queried scope", message)
        self.assertIn("Cost Management Reader at subscription scope is common", message)
        self.assertIn("may require different remediation", message)
        self.assertIn("request-403", message)

    def test_bad_request_non_grouping_is_not_retried(self) -> None:
        response = _response(
            400,
            {"error": {"code": "BadRequest", "message": "Some other bad request."}},
            {"x-ms-request-id": "request-400"},
        )
        credential = MagicMock()
        credential.get_token.return_value = SimpleNamespace(token="token")

        with patch("collectors.costs.requests.post", return_value=response) as post:
            with self.assertLogs("collectors.costs", level="WARNING") as logs:
                result = collect_costs(credential, ["sub-1"])

        self.assertEqual(result, [])
        self.assertEqual(post.call_count, 1)
        message = logs.output[-1]
        self.assertIn("HTTP 400", message)
        self.assertIn("was not retried", message)

    def test_invalid_grouping_falls_back_without_currency(self) -> None:
        grouping_rejected = MagicMock(spec=requests.Response)
        grouping_rejected.status_code = 400
        grouping_rejected.headers = {"x-ms-request-id": "request-fallback"}
        grouping_rejected.reason = "Bad Request"
        grouping_rejected.text = "Invalid dataset grouping: 'Currency'"
        grouping_rejected.json.return_value = {
            "error": {"code": "BadRequest", "message": "Invalid dataset grouping: 'Currency'"}
        }
        grouping_rejected.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=grouping_rejected
        )

        success = _response(
            200,
            {
                "properties": {
                    "columns": [{"name": "Cost"}, {"name": "ResourceGroupName"}, {"name": "ServiceName"}],
                    "rows": [[10.5, "rg-demo", "Virtual Machines"]],
                }
            },
        )
        credential = MagicMock()
        credential.get_token.return_value = SimpleNamespace(token="token")

        with patch("collectors.costs.requests.post", side_effect=[grouping_rejected, success]) as post:
            with self.assertLogs("collectors.costs", level="INFO") as logs:
                result = collect_costs(credential, ["sub-1"])

        self.assertEqual(post.call_count, 2)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Cost"], 10.5)
        self.assertEqual(result[0]["Currency"], "")
        self.assertTrue(any("without Currency" in m for m in logs.output))

    def test_rate_limit_honors_retry_after_then_succeeds(self) -> None:
        throttled = _response(
            429,
            {"error": {"code": "TooManyRequests", "message": "Slow down."}},
            {"Retry-After": "3", "x-ms-request-id": "request-429"},
        )
        success = _response(
            200,
            {
                "properties": {
                    "columns": [{"name": "Cost"}],
                    "rows": [[12.5]],
                }
            },
        )

        with patch("collectors.costs.requests.post", side_effect=[throttled, success]) as post:
            with patch("collectors.costs.time.sleep") as sleep:
                result = _get_subscription_costs("sub-1", {}, "2026-08-01", "2026-08-24")

        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(3)
        self.assertEqual(result, [{"Cost": 12.5, "subscriptionId": "sub-1"}])

    def test_rate_limit_stops_after_bounded_retries(self) -> None:
        responses = [
            _response(
                429,
                {"error": {"code": "TooManyRequests", "message": "Quota exhausted."}},
                {"Retry-After": "1", "x-ms-request-id": f"request-{attempt}"},
            )
            for attempt in range(MAX_COST_RETRIES + 1)
        ]
        credential = MagicMock()
        credential.get_token.return_value = SimpleNamespace(token="token")

        with patch("collectors.costs.requests.post", side_effect=responses) as post:
            with patch("collectors.costs.time.sleep") as sleep:
                with self.assertLogs("collectors.costs", level="WARNING") as logs:
                    result = collect_costs(credential, ["sub-1"])

        self.assertEqual(result, [])
        self.assertEqual(post.call_count, MAX_COST_RETRIES + 1)
        self.assertEqual(sleep.call_count, MAX_COST_RETRIES)
        message = logs.output[-1]
        self.assertIn("HTTP 429", message)
        self.assertIn(f"attempts: {MAX_COST_RETRIES + 1}", message)
        self.assertIn("retry budget was exhausted", message)
        self.assertIn("--skip-costs", message)

    def test_shared_budget_prevents_fallback_retries_when_exhausted(self) -> None:
        """If primary query burns all retries on 429, fallback doesn't retry again."""
        throttled = lambda: _response(
            429,
            {"error": {"code": "TooManyRequests", "message": "Slow down."}},
            {"Retry-After": "1", "x-ms-request-id": "req-shared"},
        )
        # MAX_COST_RETRIES+1 for primary (all 429), then 1 more attempt for fallback (no retries left)
        responses = [throttled() for _ in range(MAX_COST_RETRIES + 1)] + [throttled()]
        credential = MagicMock()
        credential.get_token.return_value = SimpleNamespace(token="token")

        with patch("collectors.costs.requests.post", side_effect=responses) as post:
            with patch("collectors.costs.time.sleep") as sleep:
                with self.assertLogs("collectors.costs", level="WARNING") as logs:
                    result = collect_costs(credential, ["sub-1"])

        self.assertEqual(result, [])
        # Primary: 1 initial + 8 retries = 9 calls. Fallback skipped (budget exhausted).
        self.assertEqual(post.call_count, MAX_COST_RETRIES + 1)
        self.assertEqual(sleep.call_count, MAX_COST_RETRIES)


if __name__ == "__main__":
    unittest.main()