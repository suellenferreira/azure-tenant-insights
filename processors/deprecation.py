"""
Deprecated resource detector.

Matches collected resources against config/deprecated_types.json,
which contains retirement announcements sourced exclusively from
https://azure.microsoft.com/en-us/updates/
"""

import json
import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

DEPRECATED_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "deprecated_types.json"
)


def load_deprecated_config() -> List[dict]:
    """Loads deprecated type definitions from JSON config."""
    try:
        with open(DEPRECATED_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("deprecated_types", [])
    except FileNotFoundError:
        logger.warning(f"Deprecated types config not found at {DEPRECATED_CONFIG_PATH}")
        return []
    except Exception as e:
        logger.warning(f"Could not load deprecated types config: {e}")
        return []


def detect_deprecated(
    resources_by_type: Dict[str, List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """
    Scans all collected resources against the deprecated types list.

    For entries with an optional 'sku_name' filter, only resources
    whose SKU name contains the specified value are flagged.

    Returns a list of match dicts with retirement metadata.
    """
    deprecated_config = load_deprecated_config()
    if not deprecated_config:
        return []

    matches: List[Dict[str, Any]] = []

    for dep_entry in deprecated_config:
        resource_type = dep_entry.get("type", "").lower()
        sku_filter = dep_entry.get("sku_name")  # Optional SKU-level filter

        resources = resources_by_type.get(resource_type, [])
        if not resources:
            continue

        for resource in resources:
            # Apply optional SKU filter
            if sku_filter:
                sku = resource.get("sku") or {}
                sku_name = sku.get("name", "") if isinstance(sku, dict) else str(sku)
                if sku_filter.lower() not in sku_name.lower():
                    continue

            matches.append(
                {
                    "resourceId": resource.get("id", ""),
                    "resourceName": resource.get("name", ""),
                    "resourceType": resource_type,
                    "subscriptionId": resource.get("subscriptionId", ""),
                    "resourceGroup": resource.get("resourceGroup", ""),
                    "location": resource.get("location", ""),
                    "retirementDate": dep_entry.get("retirement_date", "Unknown"),
                    "retirementAnnouncementUrl": dep_entry.get("announcement_url", ""),
                    "migrationPath": dep_entry.get("migration_path", ""),
                    "severity": dep_entry.get("severity", "Warning"),
                    "notes": dep_entry.get("notes", ""),
                    "displayName": dep_entry.get("display_name", resource_type),
                }
            )

    logger.debug(f"Deprecation check: {len(matches)} deprecated resource(s) found")
    return matches
