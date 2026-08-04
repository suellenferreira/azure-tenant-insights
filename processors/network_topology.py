"""
Network topology builder — derives a VNet/subnet/peering graph from the data
already collected by the Resource Graph scan (no extra Azure calls).

Source data: ``scan_data["resources_by_type"]["microsoft.network/virtualnetworks"]``.
Each VNet's ``properties`` blob (projected by collectors/resources.py) contains:
  - ``addressSpace.addressPrefixes``       → VNet CIDRs
  - ``subnets[].name`` / ``properties.addressPrefix``  → subnets
  - ``virtualNetworkPeerings[]``           → peerings (state + remote VNet id)

The builder is fully data-driven, so any new VNet / subnet / peering is picked
up automatically. Reserved subnet names (GatewaySubnet, AzureBastionSubnet,
AzureFirewallSubnet, RouteServerSubnet) are flagged so the diagram can badge
gateways / bastions / firewalls without a separate lookup.
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

VNET_TYPE = "microsoft.network/virtualnetworks"

# Reserved subnet name → logical role (Azure-defined, case-insensitive).
_SPECIAL_SUBNETS = {
    "gatewaysubnet": "gateway",
    "azurebastionsubnet": "bastion",
    "azurefirewallsubnet": "firewall",
    "azurefirewallmanagementsubnet": "firewall",
    "routeserversubnet": "routeserver",
}


def _props(resource: Dict[str, Any]) -> Dict[str, Any]:
    """Return a resource's ``properties`` as a dict (parse if serialized)."""
    p = resource.get("properties")
    if isinstance(p, dict):
        return p
    if isinstance(p, str) and p.strip():
        try:
            parsed = json.loads(p)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}
    return {}


def _short_id(resource_id: str) -> str:
    """Last path segment of an ARM resource id (the VNet name)."""
    return (resource_id or "").rstrip("/").split("/")[-1] or "?"


def build_network_topology(scan_data: dict) -> Dict[str, Any]:
    """
    Build a normalized network-topology graph.

    Returns::

        {
          "vnets": [ {id, name, subscriptionId, resourceGroup, location,
                      address_prefixes: [str], subnets: [{name, prefix, special}]} ],
          "peerings": [ {src, dst, dst_name, state, broken, orphan} ],
          "stats": {vnet_count, subnet_count, peering_count, broken_count},
        }
    """
    vnet_resources = scan_data.get("resources_by_type", {}).get(VNET_TYPE, []) or []

    vnets: List[Dict[str, Any]] = []
    raw_peerings: List[Dict[str, Any]] = []
    subnet_count = 0

    for r in vnet_resources:
        vid = (r.get("id") or "").lower()
        if not vid:
            continue
        props = _props(r)

        prefixes = []
        addr = props.get("addressSpace") or {}
        if isinstance(addr, dict):
            prefixes = [p for p in (addr.get("addressPrefixes") or []) if p]

        subnets = []
        for sn in props.get("subnets") or []:
            if not isinstance(sn, dict):
                continue
            name = sn.get("name") or "?"
            sp = sn.get("properties") or {}
            prefix = sp.get("addressPrefix") or ", ".join(sp.get("addressPrefixes") or [])
            subnets.append({
                "name": name,
                "prefix": prefix,
                "special": _SPECIAL_SUBNETS.get(str(name).lower()),
            })
        subnet_count += len(subnets)

        vnets.append({
            "id": vid,
            "name": r.get("name") or _short_id(vid),
            "subscriptionId": r.get("subscriptionId", ""),
            "resourceGroup": r.get("resourceGroup", ""),
            "location": (r.get("location") or "").strip(),
            "address_prefixes": prefixes,
            "subnets": subnets,
        })

        for pe in props.get("virtualNetworkPeerings") or []:
            if not isinstance(pe, dict):
                continue
            pp = pe.get("properties") or {}
            remote = (pp.get("remoteVirtualNetwork") or {}).get("id", "")
            remote = (remote or "").lower()
            if not remote:
                continue
            raw_peerings.append({
                "src": vid,
                "dst": remote,
                "state": pp.get("peeringState") or "Unknown",
            })

    vnet_ids = {v["id"] for v in vnets}

    # Deduplicate bidirectional peerings into a single undirected edge.
    edges: Dict[frozenset, Dict[str, Any]] = {}
    for pe in raw_peerings:
        key = frozenset((pe["src"], pe["dst"]))
        orphan = pe["dst"] not in vnet_ids
        broken = str(pe["state"]).lower() != "connected"
        existing = edges.get(key)
        if existing:
            existing["broken"] = existing["broken"] or broken
            if broken and not str(existing["state"]).lower() == "connected":
                existing["state"] = pe["state"]
        else:
            edges[key] = {
                "src": pe["src"],
                "dst": pe["dst"],
                "dst_name": _short_id(pe["dst"]),
                "state": pe["state"],
                "broken": broken,
                "orphan": orphan,
            }

    peerings = list(edges.values())
    broken_count = sum(1 for e in peerings if e["broken"] or e["orphan"])

    return {
        "vnets": vnets,
        "peerings": peerings,
        "stats": {
            "vnet_count": len(vnets),
            "subnet_count": subnet_count,
            "peering_count": len(peerings),
            "broken_count": broken_count,
        },
    }
