"""
Microsoft Defender for Cloud — plan posture collector via Resource Graph
SecurityResources (microsoft.security/pricings) table.

Returns the per-subscription enablement status of every Defender plan
(Standard = enabled, Free = disabled), the sub-plan, the aggregate
resourcesCoverageStatus, and the enabled extensions.

ANALYSIS SEGREGATION (by official API capability):
  - VirtualMachines / VMSS / Arc Machines → per-RESOURCE coverage is supported.
    build_servers_resource_coverage() produces an individual row per server
    cross-referencing the inventory with the Defender for Servers plan tier.
  - All other workloads (Storage, SQL, Containers, Key Vault, App Service,
    APIM, Cosmos DB, etc.) → the pricings API only exposes status at the
    SUBSCRIPTION level. Per-resource posture for those must come from the more
    restrictive assessments collector (collectors/defender.py).
  This is an official limitation of the Microsoft.Security/pricings API, not
  of this tool.

Required RBAC: 'Reader' is sufficient (*/read includes
Microsoft.Security/pricings/read) — less restrictive than the 'Security Reader'
required for assessments. Gracefully returns an empty list if unauthorized.

API Reference:
  https://learn.microsoft.com/en-us/rest/api/defenderforcloud/pricings/list
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Resource types for which the pricings API supports per-resource coverage.
SERVER_RESOURCE_TYPES = (
    "microsoft.compute/virtualmachines",
    "microsoft.compute/virtualmachinescalesets",
    "microsoft.hybridcompute/machines",
)

# Defender plan name (from the pricings API) that protects the server resources above.
SERVERS_PLAN_NAME = "virtualmachines"

# Friendly display names for the raw plan names returned by the pricings API.
PLAN_DISPLAY_NAMES = {
    "virtualmachines": "Defender for Servers",
    "sqlservers": "Defender for SQL (Azure)",
    "sqlservervirtualmachines": "Defender for SQL (VMs)",
    "opensourcerelationaldatabases": "Defender for Open-Source Relational DBs",
    "cosmosdbs": "Defender for Cosmos DB",
    "appservices": "Defender for App Service",
    "storageaccounts": "Defender for Storage",
    "keyvaults": "Defender for Key Vault",
    "arm": "Defender for Resource Manager",
    "dns": "Defender for DNS",
    "containers": "Defender for Containers",
    "containerregistry": "Defender for Container Registries (legacy)",
    "kubernetesservice": "Defender for Kubernetes (legacy)",
    "cloudposture": "Defender CSPM",
    "api": "Defender for APIs",
    "aiservices": "Defender for AI Services",
}


def _plan_display_name(plan: str) -> str:
    return PLAN_DISPLAY_NAMES.get((plan or "").lower(), plan or "Unknown")


def collect_defender_posture(
    credential,
    subscription_ids: List[str],
    throttle_delay: float = 1.0,
    cloud: str = "AzurePublicCloud",
) -> List[Dict[str, Any]]:
    """
    Collects the Defender for Cloud plan posture (one record per plan per
    subscription).

    Returns a flat list of dicts with keys:
        subscriptionId, plan, planDisplayName, pricingTier, enabled (bool),
        subPlan, resourcesCoverageStatus, enablementTime,
        freeTrialRemainingTime, enabledExtensions (list[str]).
    """
    from collectors.resource_graph import query_resource_graph

    query = """
    securityresources
    | where type == 'microsoft.security/pricings'
    | project
        subscriptionId,
        plan                    = tostring(name),
        pricingTier             = tostring(properties.pricingTier),
        subPlan                 = tostring(properties.subPlan),
        resourcesCoverageStatus = tostring(properties.resourcesCoverageStatus),
        enablementTime          = tostring(properties.enablementTime),
        freeTrialRemainingTime  = tostring(properties.freeTrialRemainingTime),
        extensions              = properties.extensions
    | order by subscriptionId asc, plan asc
    """

    try:
        results = query_resource_graph(
            credential=credential,
            query=query,
            subscription_ids=subscription_ids,
            throttle_delay=throttle_delay,
            caller="defender_posture",
        )

        for r in results:
            tier = (r.get("pricingTier") or "").strip()
            r["enabled"] = tier.lower() == "standard"
            r["planDisplayName"] = _plan_display_name(r.get("plan"))
            exts = r.get("extensions") or []
            enabled_exts: List[str] = []
            if isinstance(exts, list):
                for e in exts:
                    if not isinstance(e, dict):
                        continue
                    is_enabled = str(e.get("isEnabled", "")).lower() in ("true", "1")
                    if is_enabled and e.get("name"):
                        enabled_exts.append(str(e.get("name")))
            r["enabledExtensions"] = enabled_exts
            # Drop the raw extensions blob to keep the payload light/serialisable
            r.pop("extensions", None)

        logger.debug(f"Defender posture: {len(results)} plan records collected")
        return results
    except Exception as e:
        logger.warning(f"Could not collect Defender for Cloud plan posture: {e}")
        logger.warning(
            "Ensure the account has at least 'Reader' RBAC on the subscriptions "
            "(Microsoft.Security/pricings/read)."
        )
        return []


def build_servers_resource_coverage(
    posture_plans: List[Dict[str, Any]],
    resources_by_type: Dict[str, List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """
    Builds an INDIVIDUAL (per-resource) Defender for Servers coverage list for
    VMs, VMSS and Arc Machines, cross-referencing the inventory with the
    Defender for Servers plan tier of each resource's subscription.

    Only these resource types are listed individually because the pricings API
    supports per-resource coverage exclusively for them. All other workloads
    rely on the subscription-level / assessment-based view.

    Returns a list of dicts with keys:
        name, type, subscriptionId, resourceGroup, location,
        serversPlanTier, covered (bool), coverageStatus, subPlan.
    """
    servers_tier: Dict[str, str] = {}
    servers_status: Dict[str, str] = {}
    servers_subplan: Dict[str, str] = {}
    for p in posture_plans:
        if (p.get("plan") or "").lower() == SERVERS_PLAN_NAME:
            sub = p.get("subscriptionId") or ""
            servers_tier[sub] = p.get("pricingTier") or "Unknown"
            servers_status[sub] = p.get("resourcesCoverageStatus") or ""
            servers_subplan[sub] = p.get("subPlan") or ""

    rows: List[Dict[str, Any]] = []
    for rtype in SERVER_RESOURCE_TYPES:
        for r in resources_by_type.get(rtype, []):
            if not isinstance(r, dict):
                continue
            sub = r.get("subscriptionId") or ""
            tier = servers_tier.get(sub, "Unknown")
            rows.append({
                "name": r.get("name", ""),
                "type": rtype,
                "subscriptionId": sub,
                "resourceGroup": r.get("resourceGroup", ""),
                "location": r.get("location", ""),
                "serversPlanTier": tier,
                "covered": tier.lower() == "standard",
                "coverageStatus": servers_status.get(sub, ""),
                "subPlan": servers_subplan.get(sub, ""),
            })
    return rows
