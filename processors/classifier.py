"""
Resource classification (Assessment lens).

Maps an Azure resource type to a 3-tier taxonomy plus a Publisher axis, driven by
``config/resource_classification.yaml``:

    technical_category  — Tier 1: detailed workload category
    business_pillar     — Tier 2: business pillar
    service_model       — Tier 3: IaaS | PaaS | SaaS | Hybrid | Supporting Services | Other
    publisher           — Microsoft (namespace ``microsoft.*``) or Third-party

Matching precedence: exact type -> provider namespace -> third-party/default.
"""

import logging
import os
from typing import Dict, List

logger = logging.getLogger(__name__)

CLASSIFICATION_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "resource_classification.yaml"
)

_DEFAULTS = {
    "technical_category": "Other",
    "business_pillar": "Other",
    "service_model": "Other",
}

_DEFAULT_SERVICE_MODEL_ORDER = [
    "IaaS", "PaaS", "SaaS", "Hybrid", "Supporting Services", "Other",
]

_CONFIG: dict = None  # type: ignore[assignment]


def _load_config() -> dict:
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG
    cfg: dict = {}
    try:
        import yaml

        with open(CLASSIFICATION_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning(
            f"Classification config not found at {CLASSIFICATION_CONFIG_PATH}. "
            "Resources will be classified as 'Other'."
        )
    except Exception as e:  # noqa: BLE001 - degrade gracefully
        logger.warning(f"Could not load classification config: {e}")

    cfg.setdefault("types", {})
    cfg.setdefault("namespaces", {})
    cfg.setdefault("defaults", dict(_DEFAULTS))
    cfg.setdefault("service_model_order", list(_DEFAULT_SERVICE_MODEL_ORDER))
    _CONFIG = cfg
    return _CONFIG


def service_model_order() -> List[str]:
    """Preferred display order for service-model buckets."""
    return list(_load_config().get("service_model_order") or _DEFAULT_SERVICE_MODEL_ORDER)


def classify_resource_type(resource_type: str) -> Dict[str, str]:
    """Return ``{technical_category, business_pillar, service_model, publisher}``."""
    rt = (resource_type or "").strip().lower()
    cfg = _load_config()
    defaults = cfg.get("defaults") or _DEFAULTS

    publisher = "Microsoft" if rt.startswith("microsoft.") else "Third-party"

    rule = cfg["types"].get(rt)
    if not rule:
        namespace = rt.split("/", 1)[0] if "/" in rt else rt
        rule = cfg["namespaces"].get(namespace)

    if rule:
        result = {
            "technical_category": rule.get("technical_category", defaults["technical_category"]),
            "business_pillar": rule.get("business_pillar", defaults["business_pillar"]),
            "service_model": rule.get("service_model", defaults["service_model"]),
        }
    elif publisher == "Third-party":
        result = {
            "technical_category": "Third-party",
            "business_pillar": "Third-party",
            "service_model": "Other",
        }
    else:
        result = dict(defaults)

    result["publisher"] = publisher
    return result
