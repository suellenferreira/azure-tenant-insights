"""
Azure Policy compliance state collector via Resource Graph PolicyResources table.

Returns only NON-COMPLIANT resources to keep output focused on actionable items.

API Reference:
  https://learn.microsoft.com/en-us/azure/governance/policy/concepts/policy-compliance-states
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def collect_policy(
    credential,
    subscription_ids: List[str],
    throttle_delay: float = 1.0,
    cloud: str = "AzurePublicCloud",
) -> List[Dict[str, Any]]:
    """
    Collects non-compliant policy states from the PolicyResources table.

    Returns list of non-compliant resource policy state records.
    Gracefully returns empty list if PolicyResources table is inaccessible.
    """
    from collectors.resource_graph import query_resource_graph

    query = """
    PolicyResources
    | where type == 'microsoft.policyinsights/policystates'
    | where properties.complianceState == 'NonCompliant'
    | project
        id,
        subscriptionId,
        resourceGroup,
        properties
    | extend
        resourceId               = tostring(properties.resourceId),
        resourceType             = tostring(properties.resourceType),
        policyAssignmentName     = tostring(properties.policyAssignmentName),
        policyDefinitionName     = tostring(properties.policyDefinitionName),
        policyDefinitionAction   = tostring(properties.policyDefinitionAction),
        policyDefinitionCategory = tostring(properties.policyDefinitionCategory),
        complianceState          = tostring(properties.complianceState),
        stateWeight              = tolong(properties.stateWeight)
    | project-away properties
    | order by stateWeight desc
    """

    try:
        results = query_resource_graph(
            credential=credential,
            query=query,
            subscription_ids=subscription_ids,
            throttle_delay=throttle_delay,
        )
        logger.debug(f"Policy: {len(results)} non-compliant records collected")
        return results
    except Exception as e:
        logger.warning(f"Could not collect Policy compliance data: {e}")
        logger.warning(
            "Ensure the account has 'Reader' RBAC and the "
            "Microsoft.PolicyInsights provider is registered in all subscriptions."
        )
        return []
