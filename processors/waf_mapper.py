"""
WAF pillar mapping for Advisor recommendations.

Groups recommendations by WAF pillar for structured reporting.
The mapping itself is applied by collectors/advisor.py using the
official Advisor API category field.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

WAF_PILLARS = [
    "Reliability",
    "Security",
    "Cost Optimization",
    "Operational Excellence",
    "Performance Efficiency",
]


def map_waf_pillars(
    advisor_data: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Groups Advisor recommendations by WAF pillar.

    Returns: { "Reliability": [...], "Security": [...], ... }
    Only pillars with at least one recommendation are included.
    """
    pillars: Dict[str, List[dict]] = {p: [] for p in WAF_PILLARS}
    pillars["Uncategorized"] = []

    for rec in advisor_data:
        pillar = rec.get("wafPillar", "Uncategorized")
        if pillar in pillars:
            pillars[pillar].append(rec)
        else:
            pillars["Uncategorized"].append(rec)

    # Return only pillars with data
    return {k: v for k, v in pillars.items() if v}
