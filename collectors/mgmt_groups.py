"""
Management Group hierarchy collector.

The Management Group tree is reconstructed from each subscription's
``managementGroupAncestorsChain`` (exposed by Azure Resource Graph on the
``resourcecontainers`` table), ordered nearest-parent → tenant-root. This needs
no extra permissions or SDK beyond the Resource Graph access already used by the
rest of the tool, and works with whatever subscription scope was requested.

Returns ``None`` when no ancestry data is available (e.g. flat tenant or missing
permissions); callers should then degrade to a flat Tenant → Subscriptions view.

API reference:
  https://learn.microsoft.com/en-us/azure/governance/resource-graph/reference/supported-tables-resources
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_GUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)


def get_management_group_tree(
    credential,
    subscription_ids: List[str],
    throttle_delay: float = 1.0,
    tenant_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Build a Management Group hierarchy from subscription ancestry chains.

    Returns::

        {
          "management_groups": { name: {name, displayName, parentName} },
          "sub_parent": { subscriptionId: parent_mg_name_or_None },
        }

    or ``None`` when no ancestry information is available.
    """
    from collectors.resource_graph import query_resource_graph

    query = """
    resourcecontainers
    | where type == 'microsoft.resources/subscriptions'
    | project subscriptionId,
              subName = tostring(properties.displayName),
              mgChain = properties.managementGroupAncestorsChain
    """

    try:
        rows = query_resource_graph(
            credential=credential,
            query=query,
            subscription_ids=subscription_ids,
            throttle_delay=throttle_delay,
            caller="mgmt_groups",
        )
    except Exception as e:  # noqa: BLE001 - degrade gracefully
        logger.warning(f"Could not query Management Group ancestry: {e}")
        return None

    mgs: Dict[str, Dict[str, Any]] = {}
    sub_parent: Dict[str, Optional[str]] = {}
    any_chain = False

    for r in rows:
        sub_id = r.get("subscriptionId", "")
        if not sub_id:
            continue
        chain = r.get("mgChain") or []
        if not isinstance(chain, list) or not chain:
            sub_parent[sub_id] = None
            continue
        any_chain = True
        sub_parent[sub_id] = chain[0].get("name")
        for i, node in enumerate(chain):
            if not isinstance(node, dict):
                continue
            name = node.get("name")
            if not name:
                continue
            disp = node.get("displayName") or name
            parent = chain[i + 1].get("name") if i + 1 < len(chain) else None
            existing = mgs.get(name)
            if existing is None:
                mgs[name] = {"name": name, "displayName": disp, "parentName": parent}
            elif parent and not existing.get("parentName"):
                existing["parentName"] = parent

    if not any_chain:
        logger.info("No Management Group ancestry found; org view will be flat.")
        return None

    # Relabel the tenant-root MG (whose display name is often just its GUID id).
    for mg in mgs.values():
        if mg["parentName"] is None and tenant_name and (
            mg["displayName"] == mg["name"] or _GUID_RE.match(str(mg["displayName"]))
        ):
            mg["displayName"] = tenant_name

    logger.info(f"Management Groups discovered: {len(mgs)}")
    return {"management_groups": mgs, "sub_parent": sub_parent}
