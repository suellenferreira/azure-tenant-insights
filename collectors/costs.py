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
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

COST_MGMT_API = "https://management.azure.com"
COST_MGMT_API_VERSION = "2023-11-01"


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
            if e.response is not None and e.response.status_code in (401, 403):
                logger.warning(
                    f"Unauthorized to read costs for subscription {sub_id}. "
                    "Ensure 'Cost Management Reader' RBAC is assigned."
                )
            else:
                logger.warning(f"Could not collect costs for subscription {sub_id}: {e}")
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

    body = {
        "type": "ActualCost",
        "timeframe": "Custom",
        "timePeriod": {"from": start_date, "to": end_date},
        "dataset": {
            "granularity": "None",
            "aggregation": {
                "totalCost": {"name": "Cost", "function": "Sum"}
            },
            "grouping": [
                {"type": "Dimension", "name": "ResourceGroupName"},
                {"type": "Dimension", "name": "ServiceName"},
                {"type": "Dimension", "name": "Currency"},
            ],
        },
    }

    resp = requests.post(url, headers=headers, json=body, timeout=60)
    resp.raise_for_status()

    data = resp.json()
    columns = [col["name"] for col in data.get("properties", {}).get("columns", [])]
    rows = data.get("properties", {}).get("rows", [])

    results = []
    for row in rows:
        record = dict(zip(columns, row))
        record["subscriptionId"] = subscription_id
        results.append(record)

    return results
