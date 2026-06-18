"""
Microsoft Defender for Cloud assessments collector via Resource Graph SecurityResources table.

Returns unhealthy assessments only (status != Healthy).

Required RBAC: 'Security Reader' on the subscription(s).
This is a higher privilege than Reader — gracefully returns empty list if unauthorized.

API Reference:
  https://learn.microsoft.com/en-us/azure/defender-for-cloud/secure-score-security-controls
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def collect_defender(
    credential,
    subscription_ids: List[str],
    throttle_delay: float = 1.0,
    cloud: str = "AzurePublicCloud",
) -> List[Dict[str, Any]]:
    """
    Collects Defender for Cloud (CSPM) security assessments.

    Returns assessments where status.code is not 'Healthy'.
    Sorted by severity (High > Medium > Low).
    """
    from collectors.resource_graph import query_resource_graph

    query = """
    SecurityResources
    | where type == 'microsoft.security/assessments'
    | where properties.status.code != 'Healthy'
    | project
        id,
        name,
        subscriptionId,
        resourceGroup,
        properties
    | extend
        parentResourceId       = tostring(split(id, '/providers/Microsoft.Security/assessments')[0]),
        displayName            = tostring(properties.displayName),
        statusCode             = tostring(properties.status.code),
        statusCause            = tostring(properties.status.cause),
        statusDescription      = tostring(properties.status.description),
        severity               = tostring(properties.metadata.severity),
        categoryRaw            = tostring(properties.metadata.category),
        assessmentType         = tostring(properties.metadata.assessmentType),
        remediationDescription = tostring(properties.metadata.remediationDescription),
        implementationEffort   = tostring(properties.metadata.implementationEffort),
        resourceDetailsRaw     = tostring(properties.resourceDetails.id)
    | extend
        resourceDetails        = iif(isempty(resourceDetailsRaw), parentResourceId, resourceDetailsRaw),
        category               = iif(isempty(categoryRaw), iif(isempty(assessmentType), 'Unknown', assessmentType), categoryRaw)
    | project-away properties
    | order by severity asc
    """

    try:
        results = query_resource_graph(
            credential=credential,
            query=query,
            subscription_ids=subscription_ids,
            throttle_delay=throttle_delay,
            caller="defender",
        )
        logger.debug(f"Defender: {len(results)} unhealthy assessments collected")
        return results
    except Exception as e:
        logger.warning(f"Could not collect Defender for Cloud assessments: {e}")
        logger.warning(
            "Ensure the account has 'Security Reader' RBAC and "
            "Microsoft Defender for Cloud is enabled on the subscriptions."
        )
        return []
