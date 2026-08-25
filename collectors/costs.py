"""
Azure Cost Management data collector.

Uses the Cost Management REST API to retrieve cost data grouped by
resource group and service for the current billing month.

Required RBAC: 'Cost Management Reader' or 'Billing Reader'.
This is optional — the tool degrades gracefully if unauthorized.

API Reference:
  https://learn.microsoft.com/en-us/rest/api/cost-management/query
"""

import logging
import math
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

COST_MGMT_API = "https://management.azure.com"
COST_MGMT_API_VERSION = "2023-11-01"
MAX_COST_RETRIES = 6
DEFAULT_RETRY_DELAY = 2
MAX_RETRY_DELAY = 120
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class RetryBudget:
    """Shared retry counter across primary and fallback cost queries."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.used = 0

    @property
    def remaining(self) -> int:
        return max(self.limit - self.used, 0)

    @property
    def exhausted(self) -> bool:
        return self.used >= self.limit

    def consume(self) -> None:
        self.used += 1


def _retry_delay_seconds(
    response: requests.Response,
    retry_number: int,
    now: Optional[datetime] = None,
) -> int:
    """Return a bounded Retry-After value or exponential fallback."""
    retry_after = response.headers.get("Retry-After")
    delay: Optional[float] = None
    if retry_after:
        try:
            delay = float(retry_after)
        except (TypeError, ValueError):
            try:
                retry_at = parsedate_to_datetime(str(retry_after))
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                delay = (retry_at - (now or datetime.now(timezone.utc))).total_seconds()
            except (TypeError, ValueError, OverflowError):
                delay = None
    if delay is None or delay < 0:
        delay = DEFAULT_RETRY_DELAY * (2 ** (retry_number - 1))
    return min(math.ceil(delay), MAX_RETRY_DELAY)


def _azure_error_details(response: requests.Response) -> Tuple[str, str, str]:
    """Extract non-sensitive Azure error details and request correlation ID."""
    error_code = "Unknown"
    error_message = response.reason or "No service error message returned."
    try:
        payload = response.json()
        error = payload.get("error", payload) if isinstance(payload, dict) else {}
        if isinstance(error, dict):
            error_code = str(error.get("code") or error_code)
            error_message = str(error.get("message") or error_message)
    except (ValueError, TypeError):
        pass
    request_id = (
        response.headers.get("x-ms-request-id")
        or response.headers.get("x-ms-correlation-request-id")
        or response.headers.get("x-ms-client-request-id")
        or "not returned"
    )
    return error_code, " ".join(error_message.split())[:500], request_id


def _cost_error_guidance(status_code: int) -> str:
    if status_code == 400:
        return (
            "The request was rejected and was not retried. Review the Azure error above. "
            "Common causes include an unsupported subscription/billing offer, unavailable "
            "cost data for the requested period, or a Cost Management query/API limitation. "
            "A permission problem normally returns 401 or 403."
        )
    if status_code in (401, 403):
        return (
            "Access was denied for this Cost Management request, but the response does not "
            "identify a missing role. Verify the signed-in identity, tenant, token, queried "
            "scope, and the Cost Management or billing permissions required by the applicable "
            "agreement. Cost Management Reader at subscription scope is common, but billing "
            "scopes, organizational restrictions, deny assignments, or delegated access may "
            "require different remediation."
        )
    if status_code == 429:
        return (
            "Cost Management throttled the request. The retry budget was exhausted; wait before "
            "running ATI again, reduce the number/frequency of scans, or use --skip-costs."
        )
    return (
        "Azure Cost Management remained unavailable after bounded retries. Retry later or use "
        "--skip-costs; the remaining ATI collectors and reports are still valid."
    )


def _format_cost_http_error(
    subscription_id: str,
    error: requests.exceptions.HTTPError,
) -> str:
    response = error.response
    if response is None:
        return f"Cost collection failed for subscription {subscription_id}: {error}"
    error_code, error_message, request_id = _azure_error_details(response)
    attempts = getattr(error, "ati_attempts", 1)
    return (
        f"Cost collection failed for subscription {subscription_id}. HTTP {response.status_code}; "
        f"Azure error: {error_code}: {error_message}; attempts: {attempts}; "
        f"request ID: {request_id}. Action: {_cost_error_guidance(response.status_code)}"
    )


def collect_costs(
    credential,
    subscription_ids: List[str],
    cloud: str = "AzurePublicCloud",
) -> List[Dict[str, Any]]:
    """
    Collects cost data for each subscription for the current billing month.
    Groups by resource group and service name.

    Returns a flat list of cost records across all subscriptions.
    """
    token = credential.get_token("https://management.azure.com/.default")
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json",
    }

    today = datetime.now(timezone.utc)
    start_of_month = today.replace(day=1).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    all_costs: List[Dict[str, Any]] = []

    for sub_id in subscription_ids:
        try:
            costs = _get_subscription_costs(sub_id, headers, start_of_month, end_date)
            all_costs.extend(costs)
            logger.debug(f"Costs: {len(costs)} records for subscription {sub_id}")
        except requests.exceptions.HTTPError as e:
            logger.warning(_format_cost_http_error(sub_id, e))
        except Exception as e:
            logger.warning(f"Cost data unavailable for subscription {sub_id}: {e}")

    return all_costs


def _get_subscription_costs(
    subscription_id: str,
    headers: dict,
    start_date: str,
    end_date: str,
) -> List[Dict[str, Any]]:
    """Fetches cost data grouped by ResourceGroup and ServiceName."""
    url = (
        f"{COST_MGMT_API}/subscriptions/{subscription_id}"
        f"/providers/Microsoft.CostManagement/query"
        f"?api-version={COST_MGMT_API_VERSION}"
    )

    grouping_with_currency = [
        {"type": "Dimension", "name": "ResourceGroupName"},
        {"type": "Dimension", "name": "ServiceName"},
        {"type": "Dimension", "name": "Currency"},
    ]
    grouping_without_currency = [
        {"type": "Dimension", "name": "ResourceGroupName"},
        {"type": "Dimension", "name": "ServiceName"},
    ]

    body = {
        "type": "ActualCost",
        "timeframe": "Custom",
        "timePeriod": {"from": start_date, "to": end_date},
        "dataset": {
            "granularity": "None",
            "aggregation": {
                "totalCost": {"name": "Cost", "function": "Sum"}
            },
            "grouping": grouping_with_currency,
        },
    }

    # Shared retry budget between primary and fallback queries
    budget = RetryBudget(MAX_COST_RETRIES)

    results = _execute_cost_query(url, headers, body, subscription_id, budget)
    if results is not None:
        return results

    if budget.exhausted:
        return []

    # Fallback: Currency dimension not supported for this billing model
    logger.info(
        "Retrying cost query for subscription %s without Currency dimension.",
        subscription_id,
    )
    body["dataset"]["grouping"] = grouping_without_currency
    results = _execute_cost_query(url, headers, body, subscription_id, budget)
    if results is not None:
        for record in results:
            record.setdefault("Currency", "")
        return results

    return []


def _execute_cost_query(
    url: str,
    headers: dict,
    body: dict,
    subscription_id: str,
    budget: RetryBudget,
) -> Optional[List[Dict[str, Any]]]:
    """POST the cost query with bounded retries. Returns None on non-transient 400."""
    attempts = 0
    while True:
        attempts += 1
        resp = requests.post(url, headers=headers, json=body, timeout=60)
        if resp.status_code not in TRANSIENT_STATUS_CODES:
            break
        if budget.exhausted:
            break
        budget.consume()
        delay = _retry_delay_seconds(resp, budget.used)
        request_id = (
            resp.headers.get("x-ms-request-id")
            or resp.headers.get("x-ms-correlation-request-id")
            or "not returned"
        )
        logger.info(
            "Cost Management transient HTTP %d for subscription %s; retry %d/%d in %d "
            "second(s) (request ID: %s).",
            resp.status_code,
            subscription_id,
            budget.used,
            budget.limit,
            delay,
            request_id,
        )
        time.sleep(delay)

    if resp.status_code == 400 and "Invalid dataset grouping" in (resp.text or ""):
        return None

    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as error:
        error.ati_attempts = budget.used + 1
        raise

    data = resp.json()
    columns = [col["name"] for col in data.get("properties", {}).get("columns", [])]
    rows = data.get("properties", {}).get("rows", [])

    results = []
    for row in rows:
        record = dict(zip(columns, row))
        record["subscriptionId"] = subscription_id
        results.append(record)

    return results
