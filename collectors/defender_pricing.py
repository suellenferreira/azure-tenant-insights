"""
Microsoft Defender for Cloud — pricing & coverage-gap estimator (item B2).

Single source of truth for:
  - The mapping of each Defender plan (pricings API plan name) to the Azure
    Resource Graph resource types it protects.
  - Public list unit prices per plan (USD / unit / month).
  - The coverage-GAP computation: cross-references the resource inventory with
    the real plan posture (collectors/defender_posture.py) to estimate how many
    billable units are NOT yet protected, and the monthly cost to protect them.

IMPORTANT CAVEATS (documented for the reader):
  - Prices are PUBLIC LIST pricing. EA/MCA/CSP discounts, free tiers, and
    included units are NOT reflected.
  - Counts are inferred from Resource Graph (one billable unit per resource).
    Dynamic plans (Storage transactions, Cosmos RU/s, APIM calls) are billed by
    usage, not by resource count — for those the figure is a rough proxy.
  - Coverage is derived at the SUBSCRIPTION level from the pricings API
    (pricingTier == Standard). Per-resource overrides (VM-level) are not
    reflected in the gap math.

Pricing reference (public): https://azure.microsoft.com/pricing/details/defender-for-cloud/
Pricings API reference: https://learn.microsoft.com/en-us/rest/api/defenderforcloud/pricings/list
Live retail pricing: https://prices.azure.com/api/retail/prices (public, no auth)
"""

import json
import logging
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("collectors.defender_pricing")

# Azure Retail Prices API — public, unauthenticated. Used to refresh the
# hardcoded list prices below at scan time so estimates track Microsoft's
# current published pricing instead of going stale.
RETAIL_PRICES_ENDPOINT = "https://prices.azure.com/api/retail/prices"
RETAIL_API_VERSION = "2023-01-01-preview"
DEFENDER_SERVICE_NAME = "Microsoft Defender for Cloud"
HOURS_PER_MONTH = 730  # Azure's standard billing-hours-per-month convention.
DEFAULT_PRICE_REGION = "eastus"
_PRICE_FETCH_TIMEOUT = 25  # seconds (whole paged fetch is bounded by max pages)
_MAX_PRICE_PAGES = 25

# Process-level cache so report writers don't each hit the network. Holds the
# result of the first fetch attempt (including an empty dict on failure) so we
# only try once per run.
_LIVE_PRICE_CACHE: Optional[Dict[str, Dict[str, Any]]] = None

# Maps each Defender plan to the Retail Prices API meter that represents its
# per-unit list price. 'unit' is the billing unit to normalise to monthly
# ('hour' -> x730, 'month' -> x1). Trial/legacy meters are filtered out by name.
# productNames listed are matched case-sensitively against the API response.
RETAIL_METER_MAP: Dict[str, Dict[str, Any]] = {
    "virtualmachines": {
        "productNames": ["Microsoft Defender for Servers"],
        "primary": {"skuName": "Standard P1", "meterName": "Standard P1 Node", "unit": "hour"},
        "p2": {"skuName": "Standard P2", "meterName": "Standard P2 Node", "unit": "hour"},
    },
    "storageaccounts": {
        "productNames": ["Microsoft Defender for Storage"],
        "primary": {"skuName": "Standard", "meterName": "Standard Node", "unit": "hour"},
    },
    "appservices": {
        "productNames": ["Microsoft Defender for App Service"],
        "primary": {"skuName": "Standard", "meterName": "Standard Node", "unit": "hour"},
    },
    "keyvaults": {
        "productNames": ["Microsoft Defender for Key Vault"],
        "primary": {"skuName": "Per node Std", "meterName": "Per node Std Node", "unit": "hour"},
    },
    "sqlservers": {
        "productNames": ["Microsoft Defender for SQL"],
        "primary": {"skuName": "Standard", "meterName": "Standard Node", "unit": "month"},
    },
    "opensourcerelationaldatabases": {
        "productNames": [
            "Microsoft Defender for PostgreSQL",
            "Microsoft Defender for MySQL",
            "Microsoft Defender for MariaDB",
        ],
        "primary": {"skuName": "Standard", "meterName": "Standard Node", "unit": "month"},
    },
    "containers": {
        "productNames": ["Microsoft Defender for Containers"],
        "primary": {"skuName": "Standard vCore", "meterName": "Standard vCore vCore Pack", "unit": "hour"},
    },
    # cosmosdbs is intentionally absent: it is usage-based (per 100 RU/s) and
    # has no flat per-resource list price to estimate.
}


def _normalise_monthly(retail_price: float, unit: str) -> float:
    """Convert a raw retail price to a USD/unit/month figure."""
    if unit == "hour":
        return round(retail_price * HOURS_PER_MONTH, 2)
    return round(retail_price, 2)


def _match_meter(item: Dict[str, Any], selector: Dict[str, Any]) -> bool:
    """True if a Retail Prices API item matches a plan selector (no trials)."""
    sku = str(item.get("skuName", ""))
    meter = str(item.get("meterName", ""))
    if "Trial" in sku or "Trial" in meter:
        return False
    return sku == selector["skuName"] and meter == selector["meterName"]


def fetch_live_prices(
    region: str = DEFAULT_PRICE_REGION,
    currency: str = "USD",
    timeout: int = _PRICE_FETCH_TIMEOUT,
) -> Dict[str, Dict[str, Any]]:
    """
    Query the public Azure Retail Prices API for current Defender plan list
    prices and return a map keyed by pricings-API plan name (lowercased):

        { plan_key: {"price": float|None, "price_p2": float|None,
                     "asof": ISO8601 str, "region": str} }

    Returns an empty dict on any network/parse failure (caller falls back to the
    hardcoded PLAN_PRICING values). No authentication is required.
    """
    flt = (
        f"serviceName eq '{DEFENDER_SERVICE_NAME}' "
        f"and armRegionName eq '{region}' "
        f"and priceType eq 'Consumption'"
    )
    params = {
        "api-version": RETAIL_API_VERSION,
        "$filter": flt,
        "currencyCode": currency,
    }
    url = f"{RETAIL_PRICES_ENDPOINT}?{urllib.parse.urlencode(params)}"

    found: Dict[str, Dict[str, float]] = {}
    pages = 0
    try:
        while url and pages < _MAX_PRICE_PAGES:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (fixed https host)
                payload = json.loads(resp.read().decode("utf-8"))
            for item in payload.get("Items", []):
                product = str(item.get("productName", ""))
                price = item.get("retailPrice")
                if price is None:
                    continue
                for plan_key, mapping in RETAIL_METER_MAP.items():
                    if product not in mapping["productNames"]:
                        continue
                    bucket = found.setdefault(plan_key, {})
                    if _match_meter(item, mapping["primary"]) and "price" not in bucket:
                        bucket["price"] = _normalise_monthly(price, mapping["primary"]["unit"])
                    p2 = mapping.get("p2")
                    if p2 and _match_meter(item, p2) and "price_p2" not in bucket:
                        bucket["price_p2"] = _normalise_monthly(price, p2["unit"])
            url = payload.get("NextPageLink") or ""
            pages += 1
    except Exception as exc:  # network, timeout, JSON, etc. — degrade gracefully
        logger.warning(
            "Live Defender pricing fetch failed (%s); using built-in list prices.",
            exc,
        )
        return {}

    if not found:
        logger.warning(
            "Live Defender pricing returned no matching meters for region '%s'; "
            "using built-in list prices.",
            region,
        )
        return {}

    asof = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result: Dict[str, Dict[str, Any]] = {}
    for plan_key, bucket in found.items():
        result[plan_key] = {
            "price": bucket.get("price"),
            "price_p2": bucket.get("price_p2"),
            "asof": asof,
            "region": region,
        }
    logger.info(
        "Live Defender pricing loaded for %d plan(s) from Azure Retail Prices API (region %s).",
        len(result),
        region,
    )
    return result


def get_effective_prices(
    use_live: bool = True,
    region: str = DEFAULT_PRICE_REGION,
    currency: str = "USD",
) -> Dict[str, Dict[str, Any]]:
    """
    Return live prices (cached for the process). On the first call this hits the
    Retail Prices API once; subsequent calls reuse the cached result. Returns {}
    when live pricing is disabled or unavailable, signalling fallback to the
    hardcoded list prices.
    """
    global _LIVE_PRICE_CACHE
    if not use_live:
        return {}
    if _LIVE_PRICE_CACHE is None:
        _LIVE_PRICE_CACHE = fetch_live_prices(region=region, currency=currency)
    return _LIVE_PRICE_CACHE



# Per-plan configuration. Keys are the pricings API plan names (lowercased).
# resource_types are Azure Resource Graph 'type' values (lowercased).
# price = P1 / standard public list price per unit per month (USD).
# price_p2 = optional higher tier (currently only Defender for Servers P2).
# exclude_function_kind: when True, skips microsoft.web/sites of kind 'function*'.
PLAN_PRICING: Dict[str, Dict[str, Any]] = {
    "virtualmachines": {
        "display": "Defender for Servers",
        "unit": "VM / VMSS / Arc Machine",
        "resource_types": [
            "microsoft.compute/virtualmachines",
            "microsoft.compute/virtualmachinescalesets",
            "microsoft.hybridcompute/machines",
        ],
        "price": 4.95,
        "price_p2": 13.95,
        "notes": "P1: foundational + Defender XDR. P2: full vuln mgmt + JIT access.",
    },
    "storageaccounts": {
        "display": "Defender for Storage",
        "unit": "Storage Account",
        "resource_types": ["microsoft.storage/storageaccounts"],
        "price": 10.00,
        "price_p2": None,
        "notes": "Malware scanning + sensitive data discovery. Usage-based add-ons not included.",
    },
    "appservices": {
        "display": "Defender for App Service",
        "unit": "App Service Instance",
        "resource_types": ["microsoft.web/sites"],
        "exclude_function_kind": True,
        "price": 14.60,
        "price_p2": None,
        "notes": "Threat detection for web apps and APIs. Function apps excluded.",
    },
    "keyvaults": {
        "display": "Defender for Key Vault",
        "unit": "Key Vault",
        "resource_types": ["microsoft.keyvault/vaults"],
        "price": 2.00,
        "price_p2": None,
        "notes": "Est. ~$0.02/10K ops; ~$2/vault/mo at moderate use.",
    },
    "sqlservers": {
        "display": "Defender for SQL (Azure)",
        "unit": "SQL Server / MI",
        "resource_types": [
            "microsoft.sql/servers",
            "microsoft.sql/managedinstances",
        ],
        "price": 15.00,
        "price_p2": None,
        "notes": "Est. $0.015/vCore/hr; ~$15/server at ~4 vCores avg.",
    },
    "opensourcerelationaldatabases": {
        "display": "Defender for Open-Source Relational DBs",
        "unit": "DB Server",
        "resource_types": [
            "microsoft.dbforpostgresql/flexibleservers",
            "microsoft.dbforpostgresql/servers",
            "microsoft.dbformysql/flexibleservers",
            "microsoft.dbformysql/servers",
            "microsoft.dbformariadb/servers",
        ],
        "price": 15.00,
        "price_p2": None,
        "notes": "PostgreSQL / MySQL / MariaDB. Est. ~$15/server/mo.",
    },
    "containers": {
        "display": "Defender for Containers",
        "unit": "Cluster (vCore est.)",
        "resource_types": [
            "microsoft.containerservice/managedclusters",
            "microsoft.kubernetes/connectedclusters",
        ],
        "price": 7.00,
        "price_p2": None,
        "notes": "$7/vCore/mo estimate; actual cost varies by cluster size.",
    },
    "cosmosdbs": {
        "display": "Defender for Cosmos DB",
        "unit": "Cosmos DB Account",
        "resource_types": ["microsoft.documentdb/databaseaccounts"],
        "price": None,  # usage-based (per 100 RU/s) — count shown, cost not estimated
        "price_p2": None,
        "notes": "Billed per 100 RU/s/hr — usage-based; per-account cost not estimated.",
    },
}


def _count_by_subscription(
    plan_key: str,
    cfg: Dict[str, Any],
    resources_by_type: Dict[str, List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Return the list of billable resources for a plan as {subscriptionId} dicts."""
    exclude_function = cfg.get("exclude_function_kind", False)
    units: List[Dict[str, Any]] = []
    for rtype in cfg["resource_types"]:
        for r in resources_by_type.get(rtype, []):
            if not isinstance(r, dict):
                continue
            if exclude_function and "function" in str(r.get("kind", "")).lower():
                continue
            units.append({"subscriptionId": r.get("subscriptionId", "")})
    return units


def compute_coverage_gap(
    resources_by_type: Dict[str, List[Dict[str, Any]]],
    posture_plans: List[Dict[str, Any]],
    live_prices: Optional[Dict[str, Dict[str, Any]]] = None,
    use_live: bool = True,
    region: str = DEFAULT_PRICE_REGION,
) -> List[Dict[str, Any]]:
    """
    Cross-references the inventory with the real plan posture to estimate the
    coverage gap and the monthly cost to close it.

    Unit prices are fetched live from the public Azure Retail Prices API
    (cached per process) so estimates track Microsoft's current published
    pricing; the hardcoded PLAN_PRICING values are used only as a fallback when
    a live price is unavailable. Pass ``live_prices`` to inject a price map
    explicitly, or ``use_live=False`` to force the built-in fallback (e.g. tests,
    offline runs).

    Returns a list of per-plan dicts:
        plan_key, plan, unit, total_units, protected_units, unprotected_units,
        price (P1/unit/mo or None), gap_monthly_cost (price × unprotected or None),
        priceable (bool), price_source ("live"|"fallback"), price_asof (str|None),
        notes.

    Plans with zero billable units in the inventory are omitted.
    Requires posture_plans; without it, protection cannot be determined and an
    empty list is returned.
    """
    if not posture_plans:
        return []

    if live_prices is None:
        live_prices = get_effective_prices(use_live=use_live, region=region)
    live_prices = live_prices or {}

    # Build: plan_key -> set of subscription IDs where the plan is enabled.
    enabled_subs: Dict[str, set] = {}
    for p in posture_plans:
        key = (p.get("plan") or "").lower()
        if p.get("enabled"):
            enabled_subs.setdefault(key, set()).add(p.get("subscriptionId") or "")

    rows: List[Dict[str, Any]] = []
    for plan_key, cfg in PLAN_PRICING.items():
        units = _count_by_subscription(plan_key, cfg, resources_by_type)
        total = len(units)
        if total == 0:
            continue
        enabled_set = enabled_subs.get(plan_key, set())
        protected = sum(1 for u in units if u["subscriptionId"] in enabled_set)
        unprotected = total - protected

        live_entry = live_prices.get(plan_key) or {}
        live_price = live_entry.get("price")
        if live_price is not None:
            price = live_price
            price_source = "live"
            price_asof = live_entry.get("asof")
        else:
            price = cfg.get("price")
            price_source = "fallback"
            price_asof = None

        priceable = price is not None
        gap_cost = round(unprotected * price, 2) if priceable else None
        rows.append({
            "plan_key": plan_key,
            "plan": cfg["display"],
            "unit": cfg["unit"],
            "total_units": total,
            "protected_units": protected,
            "unprotected_units": unprotected,
            "price": price,
            "gap_monthly_cost": gap_cost,
            "priceable": priceable,
            "price_source": price_source,
            "price_asof": price_asof,
            "notes": cfg["notes"],
        })

    # Order: largest gap cost first, then largest unprotected count.
    rows.sort(key=lambda r: (-(r["gap_monthly_cost"] or 0), -r["unprotected_units"]))
    return rows


def pricing_source_label(gap_rows: List[Dict[str, Any]]) -> str:
    """
    Human-readable summary of where the unit prices came from, for report
    captions. Makes the fallback case explicit so readers know whether the
    figures are current or last-known static values.
    Examples:
      "live from the Azure Retail Prices API (2025-01-15)"
      "built-in list prices (offline fallback — live Azure Retail Prices API "
      "unavailable; figures are last-known public list pricing and may be outdated)"
      "mixed — live from the Azure Retail Prices API (2025-01-15) where available, "
      "built-in list prices otherwise"
    """
    sources = {r.get("price_source") for r in gap_rows if r.get("priceable")}
    if sources == {"live"}:
        asof = next((r.get("price_asof") for r in gap_rows if r.get("price_asof")), None)
        date = (asof or "")[:10]
        return f"live from the Azure Retail Prices API{' (' + date + ')' if date else ''}"
    if sources == {"fallback"} or not sources:
        return (
            "built-in list prices (offline fallback — live Azure Retail Prices API "
            "unavailable; figures are last-known public list pricing and may be outdated)"
        )
    asof = next((r.get("price_asof") for r in gap_rows if r.get("price_asof")), None)
    date = (asof or "")[:10]
    return (
        f"mixed — live from the Azure Retail Prices API{' (' + date + ')' if date else ''} "
        f"where available, built-in list prices otherwise"
    )


def total_gap_monthly_cost(gap_rows: List[Dict[str, Any]]) -> float:
    """Sum of the monthly cost to close the gap across all priceable plans."""
    return round(sum(r["gap_monthly_cost"] or 0.0 for r in gap_rows), 2)
