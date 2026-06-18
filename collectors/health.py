"""
Resource Health events collector via Resource Graph HealthResources table.

Returns resources with Degraded, Unavailable, or Unknown availability state.

API Reference:
  https://learn.microsoft.com/en-us/azure/service-health/resource-health-overview
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

UNHEALTHY_STATES = ["Degraded", "Unavailable", "Unknown"]


def collect_health(
    credential,
    subscription_ids: List[str],
    throttle_delay: float = 1.0,
    cloud: str = "AzurePublicCloud",
) -> List[Dict[str, Any]]:
    """
    Collects resource health events for resources in non-healthy states.

    Only returns resources where availabilityState is in UNHEALTHY_STATES.
    Healthy resources are excluded to keep the output actionable.
    """
    from collectors.resource_graph import query_resource_graph

    states_str = ", ".join(f"'{s}'" for s in UNHEALTHY_STATES)

    query = f"""
    HealthResources
    | where type == 'microsoft.resourcehealth/availabilitystatuses'
    | where properties.availabilityState in ({states_str})
    | project
        id,
        name,
        subscriptionId,
        resourceGroup,
        location,
        properties
    | extend
        availabilityState  = tostring(properties.availabilityState),
        summary            = tostring(properties.summary),
        reasonType         = tostring(properties.reasonType),
        occurredTime       = tostring(properties.occurredTime),
        reasonChronicity   = tostring(properties.reasonChronicity)
    | project-away properties
    """

    try:
        results = query_resource_graph(
            credential=credential,
            query=query,
            subscription_ids=subscription_ids,
            throttle_delay=throttle_delay,
        )
        logger.debug(f"Health: {len(results)} non-healthy resources found")
        return results
    except Exception as e:
        logger.warning(f"Could not collect Resource Health data: {e}")
        return []
