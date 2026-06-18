"""
Summary metrics computation.

Produces KPI aggregates used by the Executive and Technical HTML reports,
and for the Overview sheet in the Excel workbook.
"""

import logging
from collections import Counter
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def compute_summary(
    subscriptions: List[dict],
    resources_by_type: Dict[str, List[dict]],
    advisor_data: List[dict],
    policy_data: List[dict],
    health_data: List[dict],
    deprecated_matches: List[dict],
    misconfig_findings: List[dict],
    defender_data: List[dict],
) -> Dict[str, Any]:
    """
    Computes summary metrics for use across all report outputs.
    """
    total_resources = sum(len(v) for v in resources_by_type.values())

    # Resources by subscription
    sub_resource_counts: Counter = Counter()
    # Resources by region
    location_counts: Counter = Counter()
    # Tag coverage
    tagged_count = 0

    for rtype, resources in resources_by_type.items():
        for r in resources:
            sub_resource_counts[r.get("subscriptionId", "unknown")] += 1
            location_counts[r.get("location", "unknown")] += 1
            tags = r.get("tags") or {}
            if tags:
                tagged_count += 1

    tag_coverage_pct = (
        round((tagged_count / total_resources * 100), 1) if total_resources > 0 else 0.0
    )

    # Top 10 resource types by count
    type_counts = {rtype: len(resources) for rtype, resources in resources_by_type.items()}
    top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Advisor breakdowns
    advisor_by_pillar: Counter = Counter()
    advisor_by_impact: Counter = Counter()
    for rec in advisor_data:
        advisor_by_pillar[rec.get("wafPillar", "Uncategorized")] += 1
        advisor_by_impact[rec.get("impact", "Unknown")] += 1

    # Policy
    policy_by_action: Counter = Counter()
    for state in policy_data:
        policy_by_action[state.get("policyDefinitionAction", "unknown")] += 1

    # Health
    health_by_state: Counter = Counter()
    for event in health_data:
        health_by_state[event.get("availabilityState", "Unknown")] += 1

    # Defender
    defender_by_severity: Counter = Counter()
    for assessment in defender_data:
        defender_by_severity[assessment.get("severity", "Unknown")] += 1

    # Misconfigs
    misconfig_by_severity: Counter = Counter()
    misconfig_by_pillar: Counter = Counter()
    for finding in misconfig_findings:
        misconfig_by_severity[finding.get("severity", "Unknown")] += 1
        misconfig_by_pillar[finding.get("wafPillar", "Unknown")] += 1

    # Critical findings = High+Critical severity from misconfigs + Defender High
    critical_findings = sum(
        1 for f in misconfig_findings if f.get("severity") in ("High", "Critical")
    ) + sum(1 for f in defender_data if f.get("severity") == "High")

    return {
        "total_resources": total_resources,
        "total_subscriptions": len(subscriptions),
        "total_resource_types": len(resources_by_type),
        "total_regions": len(location_counts),
        "total_advisor_recommendations": len(advisor_data),
        "total_non_compliant_policies": len(policy_data),
        "total_health_issues": len(health_data),
        "total_deprecated": len(deprecated_matches),
        "total_misconfig_findings": len(misconfig_findings),
        "total_defender_findings": len(defender_data),
        "critical_findings_count": critical_findings,
        "tag_coverage_pct": tag_coverage_pct,
        "resources_by_subscription": dict(sub_resource_counts),
        "resources_by_location": dict(location_counts.most_common(20)),
        "top_resource_types": top_types,
        "type_counts": type_counts,
        "advisor_by_pillar": dict(advisor_by_pillar),
        "advisor_by_impact": dict(advisor_by_impact),
        "policy_non_compliant_by_action": dict(policy_by_action),
        "health_by_state": dict(health_by_state),
        "defender_by_severity": dict(defender_by_severity),
        "misconfig_by_severity": dict(misconfig_by_severity),
        "misconfig_by_pillar": dict(misconfig_by_pillar),
        "subscriptions_detail": subscriptions,
    }
