from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Optional
import unittest
from unittest.mock import MagicMock, patch

from collectors.resource_graph import (
    DEFAULT_429_RETRY_DELAY,
    MAX_429_RETRIES,
    MAX_429_RETRY_DELAY,
    _retry_after_seconds,
    query_resource_graph,
)


class ThrottledError(Exception):
    def __init__(self, retry_after: Optional[str] = None) -> None:
        super().__init__("(TooManyRequests) 429")
        headers = {} if retry_after is None else {"Retry-After": retry_after}
        self.response = SimpleNamespace(status_code=429, headers=headers)


class ResourceGraphRetryTests(unittest.TestCase):
    def test_retry_after_uses_seconds_fallback_and_cap(self) -> None:
        now = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)

        self.assertEqual(_retry_after_seconds(ThrottledError("45"), now=now), 45)
        self.assertEqual(
            _retry_after_seconds(ThrottledError("999"), now=now),
            MAX_429_RETRY_DELAY,
        )
        self.assertEqual(
            _retry_after_seconds(ThrottledError("invalid"), now=now),
            DEFAULT_429_RETRY_DELAY,
        )
        self.assertEqual(
            _retry_after_seconds(ThrottledError(), now=now),
            DEFAULT_429_RETRY_DELAY,
        )

    def test_retry_after_accepts_http_date(self) -> None:
        now = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)
        error = ThrottledError("Wed, 19 Aug 2026 12:01:00 GMT")

        self.assertEqual(_retry_after_seconds(error, now=now), 60)

    def test_query_stops_after_five_429_retries(self) -> None:
        client = MagicMock()
        client.resources.side_effect = ThrottledError("1")

        with patch(
            "azure.mgmt.resourcegraph.ResourceGraphClient", return_value=client
        ):
            with patch("collectors.resource_graph.time.sleep") as sleep:
                results = query_resource_graph(object(), "Resources", ["sub-1"])

        self.assertEqual(results, [])
        self.assertEqual(client.resources.call_count, MAX_429_RETRIES + 1)
        self.assertEqual(sleep.call_count, MAX_429_RETRIES)
        sleep.assert_called_with(1)

    def test_query_preserves_completed_pages_when_retries_are_exhausted(self) -> None:
        first_page = SimpleNamespace(data=[{"id": "one"}], skip_token="next")
        client = MagicMock()
        client.resources.side_effect = [first_page] + [
            ThrottledError("1") for _ in range(MAX_429_RETRIES + 1)
        ]

        with patch(
            "azure.mgmt.resourcegraph.ResourceGraphClient", return_value=client
        ):
            with patch("collectors.resource_graph.time.sleep"):
                results = query_resource_graph(
                    object(), "Resources", ["sub-1"], throttle_delay=0
                )

        self.assertEqual(results, [{"id": "one"}])


if __name__ == "__main__":
    unittest.main()