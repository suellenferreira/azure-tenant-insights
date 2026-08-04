"""
Network *detail* builder — places resources (VMs, private endpoints, firewalls,
gateways, app gateways, load balancers, bastions, SQL MI, loose NICs) inside the
VNet subnets they belong to, for the draw.io "Network Detail" page.

All associations are derived from data already collected by the Resource Graph
scan (no extra Azure calls). Placement is config-driven via
``config/network_placement.yaml`` — adding a new resource type is a one-line
YAML change (a JSON path to its subnet id), so the diagram stays flexible for
new Azure resource types.

VMs are resolved with a two-hop join: VM -> NIC -> subnet.
NSGs are read from each VNet subnet's own ``networkSecurityGroup`` reference.
An On-Premises node is emitted per subscription that has a VPN/ExpressRoute
gateway.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

VNET_TYPE = "microsoft.network/virtualnetworks"

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "network_placement.yaml"
)
_CONFIG: Optional[dict] = None

# Reserved subnet name -> logical role (same rules as network_topology).
_SPECIAL_SUBNETS = {
    "gatewaysubnet": "gateway",
    "azurebastionsubnet": "bastion",
    "azurefirewallsubnet": "firewall",
    "azurefirewallmanagementsubnet": "firewall",
    "routeserversubnet": "routeserver",
}

_DEFAULT_CONFIG: Dict[str, Any] = {
    "aggregate_threshold": 8,
    "nic_type": "microsoft.network/networkinterfaces",
    "vm_type": "microsoft.compute/virtualmachines",
    "nic_subnet_paths": ["properties.ipConfigurations[].properties.subnet.id"],
    "nic_vm_path": "properties.virtualMachine.id",
    "resolvers": {},
    "vm_icon": "compute/Virtual_Machine.svg",
    "nic_icon": "networking/Network_Interfaces.svg",
    "nsg_icon": "networking/Network_Security_Groups.svg",
    "onprem_icon": "networking/Local_Network_Gateways.svg",
    "subnet_icon": "networking/Subnet.svg",
    "vnet_icon": "networking/Virtual_Networks.svg",
    "subscription_icon": "general/Subscriptions.svg",
}


def load_config() -> dict:
    """Load network placement config, degrading to sensible defaults."""
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG
    cfg = dict(_DEFAULT_CONFIG)
    try:
        import yaml

        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        cfg.update(loaded)
    except Exception as e:  # noqa: BLE001 - degrade gracefully
        logger.warning(f"Could not load network placement config: {e}")
    _CONFIG = cfg
    return cfg


def _props(resource: Dict[str, Any]) -> Dict[str, Any]:
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


def _iter_path(obj: Any, tokens: List[str]):
    """Yield string leaf values reached by dotted tokens; '[]' iterates a list."""
    if not tokens:
        if isinstance(obj, str) and obj:
            yield obj
        return
    tok, rest = tokens[0], tokens[1:]
    if tok.endswith("[]"):
        key = tok[:-2]
        seq = obj.get(key) if isinstance(obj, dict) else None
        if isinstance(seq, list):
            for item in seq:
                yield from _iter_path(item, rest)
    else:
        nxt = obj.get(tok) if isinstance(obj, dict) else None
        if nxt is not None:
            yield from _iter_path(nxt, rest)


def _first_by_path(resource: Dict[str, Any], path: str) -> Optional[str]:
    root = {"properties": _props(resource)}
    for val in _iter_path(root, path.split(".")):
        return val
    return None


def _all_by_paths(resource: Dict[str, Any], paths: List[str]) -> List[str]:
    root = {"properties": _props(resource)}
    out: List[str] = []
    for path in paths:
        for val in _iter_path(root, path.split(".")):
            if val:
                out.append(val)
    return out


def _short_id(resource_id: str) -> str:
    return (resource_id or "").rstrip("/").split("/")[-1] or "?"


def build_network_detail(scan_data: dict) -> Dict[str, Any]:
    """
    Build a subscription -> VNet -> subnet -> resources structure for the
    Network Detail page. See module docstring for placement rules.
    """
    cfg = load_config()
    rbt = scan_data.get("resources_by_type", {})
    resolvers: Dict[str, dict] = {k.lower(): v for k, v in cfg.get("resolvers", {}).items()}

    # ---- Subnet index: subnet_id(lower) -> subnet dict (mutable, shared) ----
    subnet_by_id: Dict[str, dict] = {}
    # subscription -> vnet_id -> vnet dict
    subs: Dict[str, Dict[str, Any]] = {}

    for r in rbt.get(VNET_TYPE, []) or []:
        vid = (r.get("id") or "").lower()
        if not vid:
            continue
        sid = r.get("subscriptionId", "")
        props = _props(r)
        prefixes = []
        addr = props.get("addressSpace") or {}
        if isinstance(addr, dict):
            prefixes = [p for p in (addr.get("addressPrefixes") or []) if p]

        vnet = {
            "id": vid,
            "name": r.get("name") or _short_id(vid),
            "subscriptionId": sid,
            "resourceGroup": r.get("resourceGroup", ""),
            "location": (r.get("location") or "").strip(),
            "address_prefixes": prefixes,
            "subnets": [],
            "has_gateway": False,
            "gateway_kinds": set(),
        }
        for sn in props.get("subnets") or []:
            if not isinstance(sn, dict):
                continue
            sp = sn.get("properties") or {}
            snid = (sn.get("id") or "").lower()
            nsg = bool((sp.get("networkSecurityGroup") or {}).get("id"))
            prefix = sp.get("addressPrefix") or ", ".join(sp.get("addressPrefixes") or [])
            subnet = {
                "id": snid,
                "name": sn.get("name") or "?",
                "prefix": prefix,
                "special": _SPECIAL_SUBNETS.get(str(sn.get("name") or "").lower()),
                "nsg": nsg,
                "groups": {},       # rtype -> {"icon": rel, "names": [..]}
                "loose_nics": 0,
            }
            vnet["subnets"].append(subnet)
            if snid:
                subnet_by_id[snid] = subnet

        subs.setdefault(sid, {"vnets": {}, "onprem": False, "gateway_kinds": set()})
        subs[sid]["vnets"][vid] = vnet

    def _place(subnet_id: Optional[str], rtype: str, icon: str, name: str) -> bool:
        if not subnet_id:
            return False
        sn = subnet_by_id.get(subnet_id.lower())
        if sn is None:
            return False
        g = sn["groups"].setdefault(rtype, {"icon": icon, "names": []})
        g["names"].append(name)
        return True

    placed = 0

    # ---- NIC join: subnet per NIC; VM -> subnet; loose NIC counts ----
    nic_type = str(cfg.get("nic_type", "")).lower()
    vm_type = str(cfg.get("vm_type", "")).lower()
    nic_subnet_paths = cfg.get("nic_subnet_paths", [])
    nic_vm_path = cfg.get("nic_vm_path", "")
    vm_subnet: Dict[str, str] = {}

    for nic in rbt.get(nic_type, []) or []:
        subnet_ids = _all_by_paths(nic, nic_subnet_paths)
        subnet_id = subnet_ids[0].lower() if subnet_ids else None
        vm_id = _first_by_path(nic, nic_vm_path) if nic_vm_path else None
        if vm_id and subnet_id:
            vm_subnet.setdefault(vm_id.lower(), subnet_id)
        elif subnet_id:
            sn = subnet_by_id.get(subnet_id)
            if sn is not None:
                sn["loose_nics"] += 1
                placed += 1

    # ---- VMs via NIC join ----
    vm_icon = cfg.get("vm_icon", "compute/Virtual_Machine.svg")
    for vm in rbt.get(vm_type, []) or []:
        vid = (vm.get("id") or "").lower()
        subnet_id = vm_subnet.get(vid)
        if _place(subnet_id, vm_type, vm_icon, vm.get("name") or _short_id(vid)):
            placed += 1

    # ---- Direct resolvers (PE, firewall, gateways, app gw, lb, bastion, SQL MI) ----
    for rtype, resolver in resolvers.items():
        paths = resolver.get("paths", [])
        icon = resolver.get("icon", "general/All_Resources.svg")
        is_onprem = bool(resolver.get("onprem"))
        gw_type_path = resolver.get("gateway_type_path")
        for r in rbt.get(rtype, []) or []:
            sid = r.get("subscriptionId", "")
            name = r.get("name") or _short_id(r.get("id", ""))
            subnet_ids = _all_by_paths(r, paths)
            done = False
            for snid in subnet_ids:
                if _place(snid, rtype, icon, name):
                    done = True
                    break
            if done:
                placed += 1
            if is_onprem and sid in subs:
                subs[sid]["onprem"] = True
                kind = (_first_by_path(r, gw_type_path) if gw_type_path else None) or "Gateway"
                subs[sid]["gateway_kinds"].add(kind)
                # mark the hosting VNet(s) so the writer can link On-Premises to it
                for snid in subnet_ids:
                    host = subnet_by_id.get((snid or "").lower())
                    if host is not None:
                        for vnet in subs[sid]["vnets"].values():
                            if host in vnet["subnets"]:
                                vnet["has_gateway"] = True
                                vnet["gateway_kinds"].add(kind)

    # ---- Assemble output ----
    sub_meta = {s.get("subscriptionId", ""): s for s in scan_data.get("subscriptions", [])}
    out_subs: List[Dict[str, Any]] = []
    total_subnets = 0
    for sid, data in subs.items():
        vnets = list(data["vnets"].values())
        if not vnets:
            continue
        for v in vnets:
            v["gateway_kinds"] = sorted(v["gateway_kinds"])
            total_subnets += len(v["subnets"])
        out_subs.append({
            "subscriptionId": sid,
            "displayName": (sub_meta.get(sid, {}).get("displayName") or sid),
            "onprem": data["onprem"],
            "gateway_kinds": sorted(data["gateway_kinds"]),
            "vnets": sorted(vnets, key=lambda v: v["name"]),
        })
    out_subs.sort(key=lambda s: s["displayName"])

    return {
        "subscriptions": out_subs,
        "icons": {
            "vm": vm_icon,
            "nic": cfg.get("nic_icon"),
            "nsg": cfg.get("nsg_icon"),
            "onprem": cfg.get("onprem_icon"),
            "subnet": cfg.get("subnet_icon"),
            "vnet": cfg.get("vnet_icon"),
            "subscription": cfg.get("subscription_icon"),
        },
        "aggregate_threshold": int(cfg.get("aggregate_threshold", 8)),
        "stats": {
            "subscription_count": len(out_subs),
            "vnet_count": sum(len(s["vnets"]) for s in out_subs),
            "subnet_count": total_subnets,
            "placed_resource_count": placed,
        },
    }
