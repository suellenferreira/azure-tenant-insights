"""
Security posture overlay builder.

Indexes already-collected security signals by resource id and subscription id so
the draw.io writer can color-code nodes by severity and render a Security Posture
summary page. No extra Azure calls — consumes:

  - ``misconfig_findings``  (rule-based, per resource, with severity + Zero Trust)
  - ``defender_data``       (unhealthy Defender assessments, per resource)
  - ``policy_data``         (non-compliant resources; no native severity)
  - ``defender_posture``    (Defender plan enablement per subscription)

Severity model and Zero Trust mapping are config-driven via
``config/security_overlay.yaml``. Returns ``available=False`` when no security
data is present, so the overlay can be skipped cleanly.
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "security_overlay.yaml"
)
_CONFIG: Optional[dict] = None

_DEFAULTS: Dict[str, Any] = {
    "severity_colors": {"High": "#C00000", "Medium": "#C55A11",
                        "Low": "#BF8F00", "OK": "#2E7D32"},
    "severity_rank": {"High": 3, "Medium": 2, "Low": 1},
    "policy_default_severity": "Medium",
    "zero_trust": {},
}


def load_config() -> dict:
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG
    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in _DEFAULTS.items()}
    try:
        import yaml

        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        cfg.update(loaded)
    except Exception as e:  # noqa: BLE001 - degrade to defaults
        logger.warning(f"Could not load security overlay config: {e}")
    _CONFIG = cfg
    return cfg


def _norm_sev(value: Any) -> Optional[str]:
    s = str(value or "").strip().lower()
    return {"high": "High", "medium": "Medium", "moderate": "Medium",
            "low": "Low"}.get(s)


def build_security_overlay(scan_data: dict) -> Dict[str, Any]:
    """Build the per-resource and per-subscription security posture index."""
    cfg = load_config()
    rank = cfg["severity_rank"]
    default_sev = cfg.get("policy_default_severity", "Medium")

    # rule id -> Zero Trust principle
    zt_of: Dict[str, str] = {}
    for principle, rules in (cfg.get("zero_trust") or {}).items():
        for rid in rules or []:
            zt_of[str(rid)] = principle

    misconfig = scan_data.get("misconfig_findings", []) or []
    defender = scan_data.get("defender_data", []) or []
    policy = scan_data.get("policy_data", []) or []
    posture = scan_data.get("defender_posture", []) or []

    available = bool(misconfig or defender or policy or posture)

    by_resource: Dict[str, Dict[str, Any]] = {}

    def _add(rid: str, severity: Optional[str], source: str, title: str,
             sub: str, zt: Optional[str] = None) -> None:
        if not rid or not severity:
            return
        key = rid.lower()
        entry = by_resource.setdefault(
            key, {"risk": None, "subscriptionId": sub, "findings": []})
        entry["findings"].append(
            {"source": source, "severity": severity, "title": title, "zt": zt})
        if entry["risk"] is None or rank.get(severity, 0) > rank.get(entry["risk"], 0):
            entry["risk"] = severity

    for f in misconfig:
        _add(f.get("resourceId", ""), _norm_sev(f.get("severity")), "misconfig",
             f.get("title", f.get("ruleId", "")), f.get("subscriptionId", ""),
             zt_of.get(f.get("ruleId", "")))
    for f in defender:
        _add(f.get("resourceDetails", "") or f.get("id", ""),
             _norm_sev(f.get("severity")), "defender",
             f.get("displayName", ""), f.get("subscriptionId", ""))
    for f in policy:
        _add(f.get("resourceId", ""), _norm_sev(default_sev), "policy",
             f"Non-compliant: {f.get('resourceType', '')}", f.get("subscriptionId", ""))

    # ── Per-subscription posture ──
    posture_by_sub: Dict[str, Dict[str, int]] = {}
    for p in posture:
        sid = p.get("subscriptionId", "")
        d = posture_by_sub.setdefault(sid, {"standard": 0, "total": 0})
        d["total"] += 1
        if str(p.get("pricingTier", "")).lower() == "standard":
            d["standard"] += 1

    by_subscription: Dict[str, Dict[str, Any]] = {}
    sub_ids = {s.get("subscriptionId", "") for s in scan_data.get("subscriptions", [])}
    sub_ids |= {e["subscriptionId"] for e in by_resource.values() if e["subscriptionId"]}
    sub_ids |= set(posture_by_sub)
    for sid in sub_ids:
        if not sid:
            continue
        counts = {"High": 0, "Medium": 0, "Low": 0}
        zt_counts: Dict[str, int] = {}
        for e in by_resource.values():
            if e["subscriptionId"] != sid:
                continue
            if e["risk"] in counts:
                counts[e["risk"]] += 1
            for fnd in e["findings"]:
                if fnd["zt"]:
                    zt_counts[fnd["zt"]] = zt_counts.get(fnd["zt"], 0) + 1
        risk = ("High" if counts["High"] else "Medium" if counts["Medium"]
                else "Low" if counts["Low"] else "OK")
        pd = posture_by_sub.get(sid, {"standard": 0, "total": 0})
        coverage = round(100 * pd["standard"] / pd["total"]) if pd["total"] else None
        by_subscription[sid] = {
            "risk": risk, "counts": counts, "zt": zt_counts,
            "defender_standard": pd["standard"], "defender_total": pd["total"],
            "defender_coverage_pct": coverage,
        }

    return {
        "available": available,
        "by_resource": by_resource,
        "by_subscription": by_subscription,
        "severity_colors": cfg["severity_colors"],
        "stats": {
            "resources_with_findings": len(by_resource),
            "high": sum(1 for e in by_resource.values() if e["risk"] == "High"),
            "medium": sum(1 for e in by_resource.values() if e["risk"] == "Medium"),
            "low": sum(1 for e in by_resource.values() if e["risk"] == "Low"),
        },
    }
