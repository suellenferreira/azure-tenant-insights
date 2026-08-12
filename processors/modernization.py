"""
Cloud Modernization & Opportunity assessment (INFERRED).

Turns the collected inventory + classifier taxonomy into per-dimension
maturity/adoption scores (0-100) with a confidence level, supporting evidence,
and a deterministic (non-AI) narrative. It is intentionally NON-prescriptive:
it surfaces *signals* and *opportunity indicators*, never deterministic
recommendations. No extra Azure calls — everything comes from ``scan_data``.

Config: ``config/modernization_signals.yaml`` (dimensions, scoring method,
confidence, thresholds, framework references, narrative templates).

Scoring methods:
  - proportion : modern / (modern + legacy) * 100
  - presence   : (# signal families present / total families) * 100
  - security   : Defender coverage % blended with misconfiguration density
  - governance : tag coverage %, policy compliance %, Management Group structure
  - footprint  : Microsoft vs Third-party publisher split (CONTEXT only)
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "modernization_signals.yaml"
)
_CONFIG: Optional[dict] = None


def load_config() -> dict:
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG
    cfg: dict = {}
    try:
        import yaml

        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception as e:  # noqa: BLE001 - degrade gracefully
        logger.warning(f"Could not load modernization signals config: {e}")
    cfg.setdefault("score_bands", [
        {"max": 33, "level": "Low", "color": "#C00000", "label": "High opportunity"},
        {"max": 66, "level": "Intermediate", "color": "#C55A11", "label": "Intermediate"},
        {"max": 100, "level": "High", "color": "#2E7D32", "label": "Mature adoption"},
    ])
    cfg.setdefault("dimensions", [])
    cfg.setdefault("inferred_label", "INFERRED — signals derived from resource inventory.")
    _CONFIG = cfg
    return cfg


# ── low-level counting helpers ────────────────────────────────────────────
def _norm(t: str) -> str:
    return (t or "").lower()


def _matches_kind(resource: dict, kind: Optional[str], exclude_kind: Optional[str]) -> bool:
    k = _norm(resource.get("kind"))
    if kind and _norm(kind) not in k:
        return False
    if exclude_kind and _norm(exclude_kind) in k:
        return False
    return True


def _count_types(rbt: dict, types: List[str], kind: Optional[str] = None,
                 exclude_kind: Optional[str] = None) -> int:
    total = 0
    for t in types or []:
        tl = _norm(t)
        if tl.endswith("/*"):  # namespace wildcard
            prefix = tl[:-1]
            for key, resources in rbt.items():
                if key.startswith(prefix):
                    total += sum(1 for r in resources if _matches_kind(r, kind, exclude_kind))
        else:
            for r in rbt.get(tl, []):
                if _matches_kind(r, kind, exclude_kind):
                    total += 1
    return total


def _spec_types(spec) -> tuple:
    """Normalize a family/type spec (list OR {types, kind, exclude_kind})."""
    if isinstance(spec, dict):
        return (spec.get("types", []), spec.get("kind"), spec.get("exclude_kind"))
    if isinstance(spec, list):
        return (spec, None, None)
    if isinstance(spec, str):
        return ([spec], None, None)
    return ([], None, None)


# ── scoring methods ───────────────────────────────────────────────────────
def _score_proportion(dim: dict, rbt: dict) -> Dict[str, Any]:
    modern = _count_types(rbt, dim.get("modern_types", []))
    legacy = _count_types(rbt, dim.get("legacy_types", []))
    denom = modern + legacy
    if denom == 0:
        return {"score": None, "evidence": {"modern": 0, "legacy": 0},
                "placeholders": {"modern_pct": 0, "legacy_pct": 0}, "no_data": True}
    score = round(100 * modern / denom)
    return {"score": score, "evidence": {"modern": modern, "legacy": legacy, "total": denom},
            "placeholders": {"modern_pct": score, "legacy_pct": 100 - score}, "no_data": False}


def _score_presence(dim: dict, rbt: dict) -> Dict[str, Any]:
    families = dim.get("families", {}) or {}
    total = len(families)
    present = 0
    detail: Dict[str, int] = {}
    for fam, spec in families.items():
        types, kind, exclude_kind = _spec_types(spec)
        cnt = _count_types(rbt, types, kind, exclude_kind)
        detail[fam] = cnt
        if cnt > 0:
            present += 1
    score = round(100 * present / total) if total else 0
    no_data = present == 0
    return {"score": score, "evidence": {"families": detail, "present": present, "total": total},
            "placeholders": {"families_present": present, "families_total": total},
            "no_data": no_data}


def _defender_coverage(scan_data: dict) -> Optional[int]:
    posture = scan_data.get("defender_posture", []) or []
    if not posture:
        return None
    total = len(posture)
    standard = sum(1 for p in posture if str(p.get("pricingTier", "")).lower() == "standard")
    return round(100 * standard / total) if total else None


def _total_resources(rbt: dict) -> int:
    return sum(len(v) for v in rbt.values())


def _score_security(dim: dict, rbt: dict, scan_data: dict) -> Dict[str, Any]:
    coverage = _defender_coverage(scan_data)
    misconfig = scan_data.get("misconfig_findings", []) or []
    high = sum(1 for m in misconfig if str(m.get("severity", "")).lower() == "high")
    total_res = max(_total_resources(rbt), 1)
    density = min(100.0, 100.0 * high / total_res)
    penalty = min(40, round(density))
    if coverage is None:
        base, no_data = 50, True
    else:
        base, no_data = coverage, False
    score = max(0, base - penalty)
    breadth = {}
    for fam, spec in (dim.get("signal_types", {}) or {}).items():
        types, kind, exclude_kind = _spec_types(spec)
        breadth[fam] = _count_types(rbt, types, kind, exclude_kind)
    return {"score": score,
            "evidence": {"defender_coverage_pct": coverage, "high_misconfig": high,
                         "breadth": breadth},
            "placeholders": {"coverage_pct": coverage if coverage is not None else 0},
            "no_data": no_data}


def _tag_coverage(scan_data: dict, rbt: dict) -> Optional[int]:
    metrics = scan_data.get("summary_metrics", {}) or {}
    for key in ("tag_coverage_pct", "tag_coverage", "tagged_pct"):
        if isinstance(metrics.get(key), (int, float)):
            return round(metrics[key])
    # Fallback: compute from resources that carry any tag.
    total = _total_resources(rbt)
    if total == 0:
        return None
    tagged = sum(1 for resources in rbt.values() for r in resources if (r.get("tags") or {}))
    return round(100 * tagged / total)


def _score_governance(dim: dict, rbt: dict, scan_data: dict) -> Dict[str, Any]:
    components: List[int] = []
    tag_pct = _tag_coverage(scan_data, rbt)
    if tag_pct is not None:
        components.append(tag_pct)

    policy = scan_data.get("policy_data", []) or []
    total_res = max(_total_resources(rbt), 1)
    if policy:
        noncompliant = len(policy)
        compliance_pct = max(0, round(100 - min(100, 100 * noncompliant / total_res)))
        components.append(compliance_pct)
    else:
        compliance_pct = None

    org = scan_data.get("management_groups")
    if org and org.get("management_groups"):
        mg_count = len(org["management_groups"])
        mg_score = 100 if mg_count > 1 else 55
    else:
        mg_count = 0
        mg_score = 20
    components.append(mg_score)

    score = round(sum(components) / len(components)) if components else 0
    return {"score": score,
            "evidence": {"tag_pct": tag_pct, "compliance_pct": compliance_pct,
                         "mg_count": mg_count},
            "placeholders": {"tag_pct": tag_pct if tag_pct is not None else 0,
                             "compliance_pct": compliance_pct if compliance_pct is not None else 0},
            "no_data": tag_pct is None and not policy and mg_count == 0}


def _score_footprint(dim: dict, rbt: dict) -> Dict[str, Any]:
    from processors.classifier import classify_resource_type
    ms = tp = 0
    for rtype, resources in rbt.items():
        pub = classify_resource_type(rtype).get("publisher", "Microsoft")
        n = len(resources)
        if str(pub).lower().startswith("microsoft"):
            ms += n
        else:
            tp += n
    total = ms + tp
    third_pct = round(100 * tp / total) if total else 0
    native_pct = 100 - third_pct
    return {"score": native_pct,  # heatmap shows Azure-native share
            "evidence": {"microsoft": ms, "third_party": tp, "third_party_pct": third_pct},
            "placeholders": {"third_party_pct": third_pct}, "no_data": total == 0}


# ── narrative & band helpers ──────────────────────────────────────────────
def _band(score: Optional[int], bands: List[dict]) -> dict:
    if score is None:
        return {"level": "N/A", "color": "#9AA0A6", "label": "Insufficient data"}
    for b in bands:
        if score <= b["max"]:
            return b
    return bands[-1]


class _SafeDict(dict):
    def __missing__(self, key):  # leave unknown placeholders untouched
        return "{" + key + "}"


def _render_narrative(dim: dict, level: str, placeholders: dict) -> str:
    narr = dim.get("narrative", {}) or {}
    if dim.get("context_only"):
        template = narr.get("context", "")
    else:
        template = narr.get(level, "")
    try:
        return template.format_map(_SafeDict(placeholders))
    except Exception:  # noqa: BLE001
        return template


_METHODS = {"proportion", "presence", "security", "governance", "footprint"}


def build_modernization_assessment(scan_data: dict) -> Dict[str, Any]:
    """Build the per-dimension modernization assessment. See module docstring."""
    cfg = load_config()
    rbt = scan_data.get("resources_by_type", {}) or {}
    bands = cfg["score_bands"]

    results: List[Dict[str, Any]] = []
    for dim in cfg.get("dimensions", []):
        method = dim.get("method")
        if method == "proportion":
            r = _score_proportion(dim, rbt)
        elif method == "presence":
            r = _score_presence(dim, rbt)
        elif method == "security":
            r = _score_security(dim, rbt, scan_data)
        elif method == "governance":
            r = _score_governance(dim, rbt, scan_data)
        elif method == "footprint":
            r = _score_footprint(dim, rbt)
        else:
            logger.warning(f"Unknown modernization method '{method}' for {dim.get('id')}")
            continue

        score = r["score"]
        band = _band(score, bands)
        level = band["level"]
        confidence = dim.get("confidence", "Medium")
        if r.get("no_data"):
            confidence = "Low"
        context_only = bool(dim.get("context_only"))
        opportunity = (
            not context_only and score is not None
            and score < int(dim.get("opportunity_below", 50))
        )
        results.append({
            "id": dim.get("id"),
            "name": dim.get("name"),
            "method": method,
            "score": score,
            "level": level,
            "color": band["color"],
            "confidence": confidence,
            "context_only": context_only,
            "opportunity": opportunity,
            "narrative": _render_narrative(dim, level, r.get("placeholders", {})),
            "evidence": r.get("evidence", {}),
            "framework_refs": dim.get("framework_refs", []),
        })

    summary = _build_summary(results, rbt)
    return {
        "available": _total_resources(rbt) > 0 and bool(results),
        "inferred_label": cfg.get("inferred_label"),
        "score_bands": bands,
        "dimensions": results,
        "summary": summary,
    }


def _as_is(rbt: dict) -> Dict[str, Any]:
    """As-Is snapshot: Service Model + Business Pillar distribution and the
    (neutral) third-party footprint, all from the classifier taxonomy."""
    from processors.classifier import classify_resource_type
    sm: Dict[str, int] = {}
    bp: Dict[str, int] = {}
    ms = tp = 0
    tc: Dict[str, int] = {}
    for rtype, resources in rbt.items():
        c = classify_resource_type(rtype)
        n = len(resources)
        sm[c.get("service_model", "Other")] = sm.get(c.get("service_model", "Other"), 0) + n
        bp[c.get("business_pillar", "Other")] = bp.get(c.get("business_pillar", "Other"), 0) + n
        tc[c.get("technical_category", "Other")] = tc.get(c.get("technical_category", "Other"), 0) + n
        if str(c.get("publisher", "Microsoft")).lower().startswith("microsoft"):
            ms += n
        else:
            tp += n
    total = sum(sm.values()) or 1
    sm_pct = {k: round(100 * v / total) for k, v in sm.items()}
    bp_pct = {k: round(100 * v / total) for k, v in bp.items()}
    tc_pct = {k: round(100 * v / total) for k, v in tc.items()}
    tp_total = ms + tp
    third_pct = round(100 * tp / tp_total) if tp_total else 0
    return {
        "service_model": {"counts": sm, "pct": sm_pct},
        "business_pillar": {"counts": bp, "pct": bp_pct},
        "technical_category": {"counts": tc, "pct": tc_pct},
        "third_party_pct": third_pct, "total_resources": total,
        "iaas_pct": sm_pct.get("IaaS", 0), "paas_pct": sm_pct.get("PaaS", 0),
    }


def _build_summary(results: List[dict], rbt: dict) -> Dict[str, Any]:
    asis = _as_is(rbt)
    opportunities = [d for d in results if d["opportunity"]]
    opportunities.sort(key=lambda d: (d["score"] if d["score"] is not None else 999))
    top_opportunities = [
        {"id": d["id"], "name": d["name"], "score": d["score"], "confidence": d["confidence"]}
        for d in opportunities[:5]
    ]
    quick_wins = [
        {"id": d["id"], "name": d["name"], "score": d["score"]}
        for d in opportunities if d["confidence"] == "High" and (d["score"] or 0) >= 34
    ][:5]

    # Overall modernization readiness = average score of confident, non-context dims.
    scored = [d["score"] for d in results
              if not d["context_only"] and d["score"] is not None and d["confidence"] != "Low"]
    readiness = round(sum(scored) / len(scored)) if scored else None

    parts = [f"IaaS {asis['iaas_pct']}% / PaaS {asis['paas_pct']}% of the estate"]
    if top_opportunities:
        names = ", ".join(o["name"] for o in top_opportunities[:3])
        parts.append(f"top modernization opportunities: {names}")
    high_adoption = [d["name"] for d in results
                     if not d["context_only"] and d["level"] == "High"]
    if high_adoption:
        parts.append(f"mature adoption in {', '.join(high_adoption[:3])}")
    narrative = "; ".join(parts) + "."

    return {
        "service_model": {"counts": asis["service_model"]["counts"],
                          "pct": asis["service_model"]["pct"],
                          "iaas_pct": asis["iaas_pct"], "paas_pct": asis["paas_pct"]},
        "business_pillar": asis["business_pillar"],
        "third_party_pct": asis["third_party_pct"],
        "as_is": asis,
        "iaas_pct": asis["iaas_pct"], "paas_pct": asis["paas_pct"],
        "readiness": readiness,
        "top_opportunities": top_opportunities, "quick_wins": quick_wins,
        "narrative": narrative,
    }
