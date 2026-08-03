"""
Resource collection module — dynamic, type-agnostic approach.

Key design principle:
  Instead of one hardcoded module per resource type, this module
  dynamically discovers ALL resource types in the tenant and captures
  them generically. Type-specific enrichment (promoting nested
  properties to named columns) is additive and configured via
  config/resource_enrichment.yaml — not required for collection.

Any resource type with NO enrichment rule still appears in the
AllResources sheet with its raw 'properties' blob.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ENRICHMENT_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "resource_enrichment.yaml"
)

# Internal resource types that add noise without useful inventory value
SKIP_TYPES = frozenset(
    [
        "microsoft.resources/deployments",
        "microsoft.resources/deploymentscripts",
    ]
)


def load_enrichment_config() -> dict:
    """Loads resource enrichment rules from YAML config file."""
    try:
        import yaml

        with open(ENRICHMENT_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning(
            f"Enrichment config not found at {ENRICHMENT_CONFIG_PATH}. "
            "All resources will be collected with generic columns only."
        )
        return {}
    except Exception as e:
        logger.warning(f"Could not load enrichment config: {e}")
        return {}


def collect_resources(
    credential,
    subscription_ids: List[str],
    resource_groups: Optional[List[str]] = None,
    tag_key: Optional[str] = None,
    tag_value: Optional[str] = None,
    throttle_delay: float = 1.0,
    cloud: str = "AzurePublicCloud",
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Dynamically discovers and collects all resources grouped by type.

    Steps:
      1. Query Resource Graph for all distinct resource types (dynamic discovery)
      2. For each type: run a paginated query with standard fields
      3. Apply enrichment rules from config to promote nested properties
      4. Return dict: type_string -> list of resource dicts

    Returns: { "microsoft.compute/virtualmachines": [...], ... }
    """
    from collectors.resource_graph import get_resource_types, query_resource_graph

    enrichment_config = load_enrichment_config()

    # Build optional WHERE filter clauses
    filter_clauses = []
    if resource_groups:
        rg_list = ", ".join(f"'{rg.lower()}'" for rg in resource_groups)
        filter_clauses.append(f"tolower(resourceGroup) in ({rg_list})")
    if tag_key and tag_value:
        filter_clauses.append(f"tags['{tag_key}'] =~ '{tag_value}'")
    elif tag_key:
        filter_clauses.append(f"isnotnull(tags['{tag_key}'])")

    filter_str = (
        "| where " + " and ".join(filter_clauses) if filter_clauses else ""
    )

    logger.info("Step 1/2: Discovering resource types dynamically...")
    resource_types = get_resource_types(credential, subscription_ids, throttle_delay)
    logger.info(f"Step 2/2: Collecting {len(resource_types)} resource type(s)...")

    resources_by_type: Dict[str, List[Dict[str, Any]]] = {}

    for idx, rtype in enumerate(resource_types, 1):
        if rtype in SKIP_TYPES:
            continue

        query = f"""
        Resources
        | where type =~ '{rtype}'
        {filter_str}
        | project
            id,
            name,
            type,
            location,
            resourceGroup,
            subscriptionId,
            tenantId,
            kind,
            sku,
            tags,
            properties,
            identity,
            zones
        """

        try:
            results = query_resource_graph(
                credential=credential,
                query=query,
                subscription_ids=subscription_ids,
                throttle_delay=throttle_delay,
            )

            if results:
                enriched = _apply_enrichment(results, rtype, enrichment_config)
                resources_by_type[rtype] = enriched
                logger.debug(
                    f"  [{idx}/{len(resource_types)}] {rtype}: {len(results)} resource(s)"
                )

        except Exception as e:
            logger.warning(f"  [{idx}/{len(resource_types)}] Could not collect '{rtype}': {e}")

        time.sleep(throttle_delay)

    return resources_by_type


def _apply_enrichment(
    resources: List[dict],
    resource_type: str,
    enrichment_config: dict,
) -> List[dict]:
    """
    Applies type-specific enrichment rules to promote nested properties
    to top-level columns prefixed with 'enriched_'.

    Resources without enrichment rules are returned unchanged.
    """
    type_config = enrichment_config.get("resource_types", {}).get(resource_type, {})
    promoted_fields = type_config.get("promoted_fields", [])

    if not promoted_fields:
        return resources

    enriched = []
    for resource in resources:
        r = dict(resource)
        for field_def in promoted_fields:
            if isinstance(field_def, str):
                path = field_def
                col_name = path.replace("properties.", "").replace(".", "_")
            elif isinstance(field_def, dict):
                path = field_def.get("path", "")
                col_name = field_def.get("column", path.split(".")[-1])
            else:
                continue

            value = _get_nested(r, path)
            if value is not None:
                r[f"enriched_{col_name}"] = value

        enriched.append(r)

    return enriched


def _get_nested(obj: dict, path: str):
    """Retrieves a nested value using a dot-separated path string."""
    parts = path.split(".")
    current = obj
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current
