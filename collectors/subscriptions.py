"""
Subscription discovery module.

Enumerates accessible Azure subscriptions using the Subscription REST API.
Supports filtering by explicit subscription IDs or Management Group scope.

API Reference:
  https://learn.microsoft.com/en-us/rest/api/resources/subscriptions
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def get_subscriptions(
    credential,
    subscription_ids: Optional[List[str]] = None,
    management_group: Optional[str] = None,
    cloud: str = "AzurePublicCloud",
) -> List[dict]:
    """
    Returns a list of subscription dicts the credential has read access to.

    Behavior:
      - No filters: returns ALL accessible enabled subscriptions.
      - subscription_ids provided: filters to those IDs only.
      - management_group provided: returns only subscriptions under that MG.
    """
    from azure.mgmt.subscription import SubscriptionClient

    sub_client = SubscriptionClient(credential)
    all_subs: List[dict] = []

    try:
        for sub in sub_client.subscriptions.list():
            if str(sub.state).lower() in ("enabled", "warned"):
                # Newer SDK models do not expose tenant_id on Subscription.
                tenant_id = getattr(sub, "tenant_id", None)
                all_subs.append(
                    {
                        "subscriptionId": sub.subscription_id,
                        "displayName": sub.display_name,
                        "state": str(sub.state),
                        "tenantId": tenant_id,
                    }
                )
    except Exception as e:
        logger.warning(f"Could not enumerate subscriptions: {e}")
        logger.warning(
            "Ensure the account has at least 'Reader' on subscriptions."
        )

    # Management Group filter
    if management_group:
        mg_sub_ids = _get_subs_in_management_group(credential, management_group)
        all_subs = [s for s in all_subs if s["subscriptionId"] in mg_sub_ids]

    # Explicit subscription ID filter
    if subscription_ids:
        sub_id_set = set(subscription_ids)
        found_ids = {s["subscriptionId"] for s in all_subs}
        for missing_id in sub_id_set - found_ids:
            logger.warning(
                f"Subscription '{missing_id}' not found or not accessible "
                f"— verify the ID and your RBAC permissions."
            )
        all_subs = [s for s in all_subs if s["subscriptionId"] in sub_id_set]

    logger.info(f"Discovered {len(all_subs)} accessible subscription(s)")
    return all_subs


def _get_subs_in_management_group(credential, management_group_id: str) -> set:
    """Returns the set of subscription IDs under a Management Group via Resource Graph."""
    try:
        from azure.mgmt.resourcegraph import ResourceGraphClient
        from azure.mgmt.resourcegraph.models import QueryRequest

        client = ResourceGraphClient(credential)
        query = QueryRequest(
            query="""
            ResourceContainers
            | where type == 'microsoft.resources/subscriptions'
            | project subscriptionId
            """,
            management_groups=[management_group_id],
        )
        result = client.resources(query)
        return {r["subscriptionId"] for r in (result.data or [])}
    except Exception as e:
        logger.warning(f"Could not enumerate subscriptions in Management Group '{management_group_id}': {e}")
        return set()
