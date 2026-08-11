"""
Resiliency posture assessment helpers.

This module computes evidence-based resiliency signals from already collected scan
artifacts (resource inventory + summary metrics). It is intentionally non-prescriptive
and uses confidence indicators to avoid over-interpretation.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List


def _all_resources(resources_by_type: Dict[str, list]) -> List[dict]:
    rows: List[dict] = []
    for items in resources_by_type.values():
        if isinstance(items, list):
            rows.extend(r for r in items if isinstance(r, dict))
    return rows


def _safe_lower(value: Any) -> str:
    return str(value or "").strip().lower()


def _get_nested(d: dict, path: Iterable[str], default: Any = None) -> Any:
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def _location_of(r: dict) -> str:
    loc = str(r.get("location", "") or "").strip()
    return loc


def _zone_signal(r: dict) -> bool:
    # Direct zones field from ARM/ARG
    zones = r.get("zones")
    if isinstance(zones, list) and zones:
        return True

    props = r.get("properties") if isinstance(r.get("properties"), dict) else {}

    # Common zone redundancy flags
    if bool(props.get("zoneRedundant")):
        return True
    if bool(props.get("isZoneRedundant")):
        return True
    if bool(props.get("zoneReplicationEnabled")):
        return True

    # Fallback checks in nested structures
    if bool(_get_nested(props, ["availabilityZone"], False)):
        return True

    sku = r.get("sku") if isinstance(r.get("sku"), dict) else {}
    sku_name = _safe_lower(sku.get("name"))
    sku_tier = _safe_lower(sku.get("tier"))

    # Zone-resilient storage hints and zonal hints
    if any(token in sku_name for token in ("zrs", "gzrs", "zone")):
        return True
    if any(token in sku_tier for token in ("zrs", "gzrs", "zone")):
        return True

    return False


def _replication_signal(r: dict) -> bool:
    props = r.get("properties") if isinstance(r.get("properties"), dict) else {}

    # Explicit flags commonly present across services
    explicit_flags = (
        "geoRedundant",
        "geoReplicationEnabled",
        "crossRegionRestore",
        "replicationEnabled",
        "isReplicationEnabled",
        "secondaryRegionEnabled",
        "activeGeoReplicationEnabled",
    )
    if any(bool(props.get(k)) for k in explicit_flags):
        return True

    # Presence of secondary/paired region fields
    field_hints = (
        "secondaryLocation",
        "secondaryRegion",
        "pairedRegion",
        "failoverLocation",
        "partnerRegion",
    )
    if any(_safe_lower(props.get(k)) for k in field_hints):
        return True

    # Non-empty replication arrays
    list_hints = (
        "replicationPolicies",
        "replicationLinks",
        "geoReplicationStats",
        "failoverPolicies",
    )
    for k in list_hints:
        val = props.get(k)
        if isinstance(val, list) and len(val) > 0:
            return True

    # Storage redundancy SKU hints (GRS/RA-GRS/GZRS/RA-GZRS)
    sku = r.get("sku") if isinstance(r.get("sku"), dict) else {}
    sku_name = _safe_lower(sku.get("name"))
    if any(token in sku_name for token in ("grs", "ragrs", "gzrs", "ragzrs")):
        return True

    return False


def _resource_dimensions(resources: List[dict]) -> Dict[str, Dict[str, int]]:
    """Aggregate service-model, business-pillar, and technical-category counts for the environment."""
    from processors.classifier import classify_resource_type

    dimensions = {"service_model": defaultdict(int), "business_pillar": defaultdict(int), "technical_category": defaultdict(int)}
    for resource in resources:
        resource_type = str(resource.get("type", "") or "").lower()
        classified = classify_resource_type(resource_type)
        dimensions["service_model"][classified.get("service_model", "Other")] += 1
        dimensions["business_pillar"][classified.get("business_pillar", "Other")] += 1
        dimensions["technical_category"][classified.get("technical_category", "Other")] += 1
    return {name: dict(values) for name, values in dimensions.items()}


def _regional_rows(resources: List[dict]) -> List[dict]:
    """Build region distribution rows with service-model and pillar context."""
    from processors.classifier import classify_resource_type

    grouped: Dict[str, Dict[str, Any]] = {}
    for resource in resources:
        region = _location_of(resource)
        if not region or _safe_lower(region) == "global":
            continue
        item = grouped.setdefault(region, {
            "region": region,
            "resources": 0,
            "subscriptions": set(),
            "service_models": defaultdict(int),
            "business_pillars": defaultdict(int),
        })
        item["resources"] += 1
        if resource.get("subscriptionId"):
            item["subscriptions"].add(resource.get("subscriptionId"))
        classified = classify_resource_type(str(resource.get("type", "") or "").lower())
        item["service_models"][classified.get("service_model", "Other")] += 1
        item["business_pillars"][classified.get("business_pillar", "Other")] += 1
        if "technical_categories" not in item:
            item["technical_categories"] = defaultdict(int)
        item["technical_categories"][classified.get("technical_category", "Other")] += 1

    rows = []
    total = sum(item["resources"] for item in grouped.values())
    for item in sorted(grouped.values(), key=lambda x: -x["resources"]):
        rows.append({
            "region": item["region"],
            "resources": item["resources"],
            "percentage": round(item["resources"] / total * 100, 1) if total else 0,
            "subscriptions": len(item["subscriptions"]),
            "service_models": dict(sorted(item["service_models"].items(), key=lambda x: -x[1])),
            "business_pillars": dict(sorted(item["business_pillars"].items(), key=lambda x: -x[1])),
            "technical_categories": dict(sorted(item.get("technical_categories", {}).items(), key=lambda x: -x[1])),
        })
    return rows


def _zone_type_details(resources: List[dict]) -> List[dict]:
    counts: Dict[str, int] = defaultdict(int)
    for resource in resources:
        if _zone_signal(resource):
            resource_type = str(resource.get("type", "") or "unknown").lower()
            counts[resource_type] += 1
    return [
        {"type": t, "count": c}
        for t, c in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    ]


def _zone_resource_details(resources: List[dict]) -> List[dict]:
    details = []
    for resource in resources:
        if not _zone_signal(resource):
            continue
        props = resource.get("properties") if isinstance(resource.get("properties"), dict) else {}
        zones = resource.get("zones")
        if not isinstance(zones, list) or not zones:
            zones = props.get("zones")
        if isinstance(zones, list) and zones:
            zones_text = ", ".join(str(zone) for zone in zones)
        else:
            zones_text = "Detected by zone property"
        details.append({
            "type": str(resource.get("type", "") or "unknown").lower(),
            "name": resource.get("name") or resource.get("id", "").rsplit("/", 1)[-1],
            "id": resource.get("id", ""),
            "region": _location_of(resource),
            "zones": zones_text,
            "subscription_id": resource.get("subscriptionId", ""),
            "resource_group": resource.get("resourceGroup", ""),
        })
    return sorted(details, key=lambda x: (x["region"], x["type"], x["name"]))


def _multi_region_type_details(resources: List[dict]) -> List[dict]:
    by_type_regions: Dict[str, set] = defaultdict(set)
    by_type_count: Dict[str, int] = defaultdict(int)
    for resource in resources:
        region = _location_of(resource)
        if not region or _safe_lower(region) == "global":
            continue
        resource_type = str(resource.get("type", "") or "unknown").lower()
        by_type_regions[resource_type].add(region)
        by_type_count[resource_type] += 1

    details = []
    for resource_type, regions in by_type_regions.items():
        if len(regions) > 1:
            details.append({
                "type": resource_type,
                "resource_count": by_type_count[resource_type],
                "region_count": len(regions),
            })
    return sorted(details, key=lambda x: (-x["region_count"], -x["resource_count"], x["type"]))


def _top_type_summary(details: List[dict], *, limit: int = 10, mode: str = "count") -> str:
    top = details[:limit]
    if not top:
        return "—"
    if mode == "multi_region":
        return ", ".join(
            f"{item['type']} (regions:{item['region_count']}, resources:{item['resource_count']})"
            for item in top
        )
    return ", ".join(f"{item['type']} ({item['count']})" for item in top)


def _evidence_item(
    *, status: str, detected: int | None, scope: str, limitation: str,
    evaluated: int | None = None, coverage: int | None = None,
    top_resource_types: str = "—", resource_type_details: List[dict] | None = None,
    resource_details: List[dict] | None = None,
) -> dict:
    return {
        "status": status,
        "detected": detected,
        "evaluated_resources": evaluated,
        "coverage_pct": coverage,
        "scope": scope,
        "limitation": limitation,
        "top_resource_types": top_resource_types,
        "resource_type_details": resource_type_details or [],
        "resource_details": resource_details or [],
    }


# Scoring functions removed — model is now factual only (no inference)


def _build_subscription_rows(
    resources_by_type: Dict[str, list],
    resources_by_subscription: Dict[str, int],
) -> List[dict]:
    from processors.classifier import classify_resource_type

    by_sub_resources: Dict[str, List[dict]] = defaultdict(list)
    for rows in resources_by_type.values():
        if not isinstance(rows, list):
            continue
        for r in rows:
            if isinstance(r, dict):
                sid = str(r.get("subscriptionId", "") or "")
                if sid:
                    by_sub_resources[sid].append(r)

    out: List[dict] = []
    for sid, total in sorted(resources_by_subscription.items(), key=lambda x: x[0]):
        sub_rows = by_sub_resources.get(sid, [])
        loc_rows = [r for r in sub_rows if _location_of(r) and _safe_lower(_location_of(r)) != "global"]
        region_counts: Dict[str, int] = defaultdict(int)
        for r in loc_rows:
            region_counts[_location_of(r)] += 1

        region_count = len(region_counts)
        max_region_count = max(region_counts.values()) if region_counts else 0
        single_region_exposure_pct = round((max_region_count / len(loc_rows)) * 100, 1) if loc_rows else 0.0

        zone_hits = sum(1 for r in loc_rows if _zone_signal(r))

        service_models: Dict[str, int] = defaultdict(int)
        business_pillars: Dict[str, int] = defaultdict(int)
        for r in sub_rows:
            classified = classify_resource_type(str(r.get("type", "") or "").lower())
            service_models[classified.get("service_model", "Other")] += 1
            business_pillars[classified.get("business_pillar", "Other")] += 1

        technical_categories: Dict[str, int] = defaultdict(int)
        for r in sub_rows:
            classified = classify_resource_type(str(r.get("type", "") or "").lower())
            technical_categories[classified.get("technical_category", "Other")] += 1
        
        row = {
            "subscription_id": sid,
            "resources": int(total or 0),
            "regions": int(region_count),
            "single_region_exposure_pct": single_region_exposure_pct,
            "zone_signal_count": int(zone_hits),
            "service_model_distribution": dict(sorted(service_models.items(), key=lambda x: -x[1])),
            "business_pillar_distribution": dict(sorted(business_pillars.items(), key=lambda x: -x[1])),
            "technical_category_distribution": dict(sorted(technical_categories.items(), key=lambda x: -x[1])),
        }
        out.append(row)
    return out


def build_resiliency_assessment(scan_data: Dict[str, Any]) -> Dict[str, Any]:
    resources_by_type = scan_data.get("resources_by_type", {}) or {}
    summary = scan_data.get("summary_metrics", {}) or {}

    all_rows = _all_resources(resources_by_type)
    loc_rows = [r for r in all_rows if _location_of(r) and _safe_lower(_location_of(r)) != "global"]

    region_counts: Dict[str, int] = defaultdict(int)
    for r in loc_rows:
        region_counts[_location_of(r)] += 1

    region_count = len(region_counts)
    max_region_count = max(region_counts.values()) if region_counts else 0
    single_region_exposure_pct = round((max_region_count / len(loc_rows)) * 100, 1) if loc_rows else 0.0

    zone_hits = sum(1 for r in loc_rows if _zone_signal(r))
    zone_resource_details = _zone_resource_details(loc_rows)

    per_subscription = _build_subscription_rows(
        resources_by_type=resources_by_type,
        resources_by_subscription=summary.get("resources_by_subscription", {}) or {},
    )

    dimensions = _resource_dimensions(all_rows)
    regional_rows = _regional_rows(loc_rows)
    sub_count = int(summary.get("total_subscriptions", 0) or len(scan_data.get("subscriptions", [])) or 0)
    evidence = {
        "multi_region": _evidence_item(
            status="Distributed" if region_count > 1 else "Single-region concentration",
            detected=region_count,
            evaluated=len(loc_rows),
            scope=f"{len(loc_rows):,} regional resources",
            limitation="Observed region count and concentration. Does not confirm multi-region failover or redundancy configuration.",
        ),
        "zone": _evidence_item(
            status="No recognized evidence" if not zone_hits else "Evidence detected",
            detected=zone_hits,
            evaluated=len(loc_rows),
            scope=f"{len(loc_rows):,} regional resources",
            limitation="Detected from resource properties (zones, zoneRedundant, SKU hints). Internal zone configuration may not be visible.",
        ),
    }
    overall_status = "Distributed" if region_count > 1 else "Concentrated"

    return {
        "available": True,
        "environment": {
            "total_resources": len(all_rows),
            "regional_resources": len(loc_rows),
            "subscriptions": sub_count,
            "regions": region_count,
            "region_distribution": regional_rows,
            "service_model_distribution": dimensions["service_model"],
            "business_pillar_distribution": dimensions["business_pillar"],
            "technical_category_distribution": dimensions["technical_category"],
            "zone_resource_details": zone_resource_details,
        },
        "evidence": evidence,
        "summary": {
            "overall_status": overall_status,
            "region_count": region_count,
            "single_region_exposure_pct": single_region_exposure_pct,
            "zone_signal_count": zone_hits,
            "evaluated_resources": len(loc_rows),
            "total_resources": len(all_rows),
        },
        "subscriptions": per_subscription,
        "notes": {
            "scope_boundary": (
                "Workload-level backup protection validation is outside the scope of this view."
            ),
            "zone_metric": (
                "Multi-zone detected count is resource-level (number of resources with recognized zone properties). "
                "Internal configuration may not be visible from inventory."
            ),
            "interpretation": (
                "Reflects resource properties observed in Azure Resource Graph. Not a formal resiliency certification or operational validation."
            ),
        },
    }
