"""
Organization tree builder.

Turns the Management Group ancestry (from ``collectors.mgmt_groups``) plus the
scanned subscriptions into a nested Tenant → Management Groups → Subscriptions
tree, annotated with per-subscription resource counts. Degrades to a flat
Tenant → Subscriptions tree when no Management Group data is available.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _resource_counts(scan_data: dict) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for resources in scan_data.get("resources_by_type", {}).values():
        for r in resources:
            sid = r.get("subscriptionId", "")
            counts[sid] = counts.get(sid, 0) + 1
    return counts


def build_org_tree(scan_data: dict) -> Dict[str, Any]:
    """
    Build the organization tree.

    Node shape::

        {"kind": "tenant"|"mg"|"sub", "id", "label",
         "count": <int, subs only>, "children": [...]}

    A ``stats`` dict is attached to the returned root under ``_stats``.
    """
    meta = scan_data.get("metadata", {})
    tenant_name = meta.get("tenant_name") or "Tenant"
    tenant_id = meta.get("tenant_id")
    subs = scan_data.get("subscriptions", []) or []
    counts = _resource_counts(scan_data)
    org = scan_data.get("management_groups")

    def _sub_node(s: dict) -> Dict[str, Any]:
        sid = s.get("subscriptionId", "")
        return {
            "kind": "sub", "id": sid,
            "label": s.get("displayName") or sid,
            "count": counts.get(sid, 0), "children": [],
        }

    root: Dict[str, Any] = {
        "kind": "tenant", "id": meta.get("tenant_id", "tenant"),
        "label": tenant_name, "children": [],
    }

    if not org or not org.get("management_groups"):
        # Flat: all subscriptions directly under the tenant.
        root["children"] = [_sub_node(s) for s in subs]
        mg_count = 0
    else:
        mgs = org["management_groups"]
        sub_parent = org.get("sub_parent", {})
        nodes: Dict[str, Dict[str, Any]] = {
            name: {"kind": "mg", "id": name, "label": mg.get("displayName") or name,
                   "children": []}
            for name, mg in mgs.items()
        }
        # Link MG parent/child; collect roots (no parent, or parent unknown).
        roots: List[Dict[str, Any]] = []
        for name, mg in mgs.items():
            parent = mg.get("parentName")
            if parent and parent in nodes:
                nodes[parent]["children"].append(nodes[name])
            else:
                roots.append(nodes[name])
        # Attach subscriptions to their parent MG (or tenant root if unknown).
        for s in subs:
            sid = s.get("subscriptionId", "")
            parent_name = sub_parent.get(sid)
            target = nodes.get(parent_name) if parent_name else None
            (target["children"] if target else root["children"]).append(_sub_node(s))
        # A tenant-root MG usually IS the tenant; if a single root MG matches the
        # tenant (by id — Azure's root MG id equals the tenant id — or by name),
        # promote its children directly under the tenant node to avoid a
        # redundant "Tenant > Tenant" level.
        if len(roots) == 1 and (
            roots[0]["id"] == tenant_id or roots[0]["label"] == tenant_name
        ):
            root["children"].extend(roots[0]["children"])
        else:
            root["children"].extend(roots)
        mg_count = len(mgs)

    def _depth(node: dict) -> int:
        return 1 + max((_depth(c) for c in node["children"]), default=0)

    root["_stats"] = {
        "mg_count": mg_count,
        "sub_count": len(subs),
        "depth": _depth(root),
        "flat": mg_count == 0,
    }
    return root
