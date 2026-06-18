"""
Azure Advisor recommendations collector via Resource Graph AdvisorResources table.

WAF pillar mapping is applied directly from the Advisor 'category' field,
which is the official mapping provided by the Azure Advisor API.

API Reference:
  https://learn.microsoft.com/en-us/azure/advisor/advisor-overview
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Official Azure Advisor category -> WAF pillar mapping
# Source: https://learn.microsoft.com/en-us/azure/advisor/advisor-overview#pillars-of-the-well-architected-framework
ADVISOR_WAF_MAPPING = {
    "HighAvailability": "Reliability",
    "Security": "Security",
    "Cost": "Cost Optimization",
    "OperationalExcellence": "Operational Excellence",
    "Performance": "Performance Efficiency",
}


def collect_advisor(
    credential,
    subscription_ids: List[str],
    throttle_delay: float = 1.0,
    cloud: str = "AzurePublicCloud",
) -> List[Dict[str, Any]]:
    """
    Collects Azure Advisor recommendations from the AdvisorResources table.

    Returns a list of recommendation dicts with WAF pillar already mapped.
    """
    from collectors.resource_graph import query_resource_graph

    query = """
    AdvisorResources
    | where type == 'microsoft.advisor/recommendations'
    | project
        id,
        name,
        subscriptionId,
        resourceGroup,
        location,
        properties
    | extend
        category             = tostring(properties.category),
        impact               = tostring(properties.impact),
        impactedField        = tostring(properties.impactedField),
        impactedValue        = tostring(properties.impactedValue),
        shortDescription     = tostring(properties.shortDescription.problem),
        solution             = tostring(properties.shortDescription.solution),
        potentialBenefits    = tostring(properties.potentialBenefits),
        learnMoreLink        = tostring(properties.learnMoreLink)
    | project-away properties
    """

    try:
        results = query_resource_graph(
            credential=credential,
            query=query,
            subscription_ids=subscription_ids,
            throttle_delay=throttle_delay,
        )
    except Exception as e:
        logger.warning(f"Could not collect Advisor recommendations: {e}")
        return []

    # Apply WAF pillar mapping
    for rec in results:
        category = rec.get("category", "")
        rec["wafPillar"] = ADVISOR_WAF_MAPPING.get(category, "Uncategorized")

    logger.debug(f"Advisor: {len(results)} recommendations collected")
    return results
