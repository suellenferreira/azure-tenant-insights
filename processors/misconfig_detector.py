"""
Known misconfiguration detector.

Evaluates collected resources against rules defined in
config/misconfiguration_rules.yaml.

All rules are based EXCLUSIVELY on official Microsoft Azure documentation.
No inferred or assumed rules are included.
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

RULES_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "misconfiguration_rules.yaml"
)


def load_rules() -> List[dict]:
    """Loads misconfiguration detection rules from YAML config."""
    try:
        import yaml

        with open(RULES_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data.get("rules", [])
    except FileNotFoundError:
        logger.warning(f"Misconfiguration rules config not found at {RULES_CONFIG_PATH}")
        return []
    except Exception as e:
        logger.warning(f"Could not load misconfiguration rules: {e}")
        return []


def detect_misconfigurations(
    resources_by_type: Dict[str, List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """
    Evaluates resources against all loaded misconfiguration rules.

    Returns a list of finding dicts for each resource that violates a rule.
    """
    rules = load_rules()
    if not rules:
        return []

    findings: List[Dict[str, Any]] = []

    for rule in rules:
        rule_id = rule.get("id", "UNKNOWN")
        resource_type = rule.get("resource_type", "").lower()
        condition_path = rule.get("condition_path", "")
        expected_value = rule.get("expected_value")
        operator = rule.get("operator", "equals")
        severity = rule.get("severity", "Medium")
        title = rule.get("title", "")
        description = rule.get("description", "")
        waf_pillar = rule.get("waf_pillar", "Security")
        documentation_url = rule.get("documentation_url", "")

        resources = resources_by_type.get(resource_type, [])
        if not resources:
            continue

        for resource in resources:
            actual_value = _get_nested(resource, condition_path)

            if _is_violated(actual_value, expected_value, operator):
                findings.append(
                    {
                        "ruleId": rule_id,
                        "title": title,
                        "description": description,
                        "severity": severity,
                        "wafPillar": waf_pillar,
                        "resourceId": resource.get("id", ""),
                        "resourceName": resource.get("name", ""),
                        "resourceType": resource_type,
                        "subscriptionId": resource.get("subscriptionId", ""),
                        "resourceGroup": resource.get("resourceGroup", ""),
                        "location": resource.get("location", ""),
                        "actualValue": str(actual_value) if actual_value is not None else "not set",
                        "expectedValue": str(expected_value),
                        "documentationUrl": documentation_url,
                    }
                )

    logger.debug(f"Misconfiguration check: {len(findings)} finding(s)")
    return findings


def _get_nested(obj: dict, path: str) -> Optional[Any]:
    """Retrieves a nested value using a dot-separated path string."""
    parts = path.split(".")
    current = obj
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _is_violated(actual: Any, expected: Any, operator: str) -> bool:
    """
    Returns True if the condition is VIOLATED (misconfiguration detected).

    Operators:
      equals       -> violation if actual != expected
      not_equals   -> violation if actual == expected (bad value present)
      equals_true  -> violation if actual is not True/true
      equals_false -> violation if actual is not False/false
      is_null      -> violation if actual is not None (field should be absent)
      is_not_null  -> violation if actual is None (field should be present)
      contains     -> violation if expected NOT in str(actual)
      not_contains -> violation if expected IN str(actual)
    """
    if operator == "equals":
        return actual != expected

    if operator == "not_equals":
        return actual == expected

    if operator == "equals_true":
        return actual not in (True, "true", "True", "yes", "Yes")

    if operator == "equals_false":
        return actual not in (False, "false", "False", "no", "No")

    if operator == "is_null":
        return actual is not None

    if operator == "is_not_null":
        return actual is None

    if operator == "contains":
        return str(expected) not in str(actual or "")

    if operator == "not_contains":
        return str(expected) in str(actual or "")

    # Unknown operator — do not raise a false positive
    logger.warning(f"Unknown operator '{operator}' in misconfiguration rule")
    return False
