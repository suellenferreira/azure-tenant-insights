"""
Executive HTML Report Writer.

Generates a self-contained single-file HTML report targeted at
C-Level executives and non-technical stakeholders.

Contents:
  - Risk level banner
  - KPI summary tiles
  - Advisor recommendations by WAF pillar (chart)
  - Top resource types (chart)
  - Top priority findings list
  - Strategic recommendations
  - Modernization & technology signals (clearly labeled INFERRED)
"""

import json
import logging
from collections import Counter
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def write_executive_report(scan_data: dict, output_path: str) -> None:
    """Generates the Executive HTML report and writes to output_path."""
    meta = scan_data.get("metadata", {})
    summary = scan_data.get("summary_metrics", {})
    advisor_data = scan_data.get("advisor_data", [])
    deprecated = scan_data.get("deprecated_matches", [])
    defender_data = scan_data.get("defender_data", [])
    defender_posture = scan_data.get("defender_posture", [])
    misconfig_findings = scan_data.get("misconfig_findings", [])

    scan_date = meta.get("scan_timestamp", "")[:10]
    tenant_id_raw = meta.get("tenant_id", "N/A")
    tenant_name = meta.get("tenant_name", "N/A")
    subscriptions = scan_data.get("subscriptions", [])
    # Resolve actual tenant GUID from subscription objects when metadata shows placeholder
    tenant_id = (
        tenant_id_raw
        if tenant_id_raw not in ("auto-detected", "N/A", "", None)
        else (subscriptions[0].get("tenantId") or tenant_id_raw if subscriptions else tenant_id_raw)
    )
    sub_list = ", ".join([
        f"{s.get('displayName', 'Unknown')} ({s.get('subscriptionId', 'N/A')})"
        for s in subscriptions
    ])
    sub_list = sub_list if sub_list else "N/A"

    # Compute overall risk level from critical findings count
    critical = summary.get("critical_findings_count", 0)
    if critical > 10:
        risk_level, risk_color = "HIGH", "#C00000"
    elif critical > 3:
        risk_level, risk_color = "MEDIUM", "#FFC000"
    else:
        risk_level, risk_color = "LOW", "#70AD47"

    # Chart data
    advisor_by_pillar = summary.get("advisor_by_pillar", {})
    pillar_labels = json.dumps(list(advisor_by_pillar.keys()))
    pillar_values = json.dumps(list(advisor_by_pillar.values()))

    top_types = summary.get("top_resource_types", [])[:8]
    type_labels = json.dumps([t[0].split("/")[-1].title() for t in top_types])
    type_values = json.dumps([t[1] for t in top_types])

    # Top findings: min 5 if available; up to 10 for large environments (>= 500 resources)
    _max_findings = 10 if summary.get("total_resources", 0) >= 500 else 5
    top_findings = _build_top_findings(advisor_data, misconfig_findings, defender_data, max_findings=_max_findings)

    # Strategic recommendations
    strategic_recs = _build_strategic_recommendations(
        summary, deprecated, misconfig_findings, defender_data
    )

    # Modernization signals (inferred from resource type presence)
    resources_by_type = scan_data.get("resources_by_type", {})
    modern_signals = _detect_modernization_signals(resources_by_type)

    # Regional distribution analysis
    region_summary = _analyze_regions(resources_by_type)

    # Item 0: Build collection warnings note for report footer
    collection_warnings = scan_data.get("collection_warnings", [])
    if collection_warnings:
        _warn_items = "".join(
            f'<li><strong style="text-transform:capitalize">{w.get("collector","")}:</strong> '
            f'{w.get("message","")}</li>'
            for w in collection_warnings
        )
        warnings_html = (
            f'<details style="font-size:.73rem;color:#aaa;margin-top:.6rem;text-align:left">'
            f'<summary style="cursor:pointer">&#9432; Data collection notes '
            f'({len(collection_warnings)})</summary>'
            f'<ul style="margin:.4rem 0 0 1rem;color:#999">{_warn_items}</ul>'
            f'</details>'
        )
    else:
        warnings_html = ""

    lz_exec_html = _build_lz_executive_html(resources_by_type, summary)
    defender_exec_html = _build_defender_executive_html(defender_data, resources_by_type, summary)
    defender_posture_exec_html = _build_defender_posture_executive_html(
        defender_posture, resources_by_type, subscriptions
    )
    zt_exec_html = _build_zero_trust_executive_html(misconfig_findings)
    defender_high = sum(1 for d in defender_data if d.get("severity") == "High")
    defender_total = len(defender_data)

    html = _render_html(
        scan_date=scan_date,
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        subscriptions_list=sub_list,
        summary=summary,
        risk_level=risk_level,
        risk_color=risk_color,
        top_findings=top_findings,
        pillar_labels=pillar_labels,
        pillar_values=pillar_values,
        type_labels=type_labels,
        type_values=type_values,
        strategic_recs=strategic_recs,
        modern_signals=modern_signals,
        region_summary=region_summary,
        deprecated_count=len(deprecated),
        lz_exec_html=lz_exec_html,
        defender_exec_html=defender_exec_html,
        defender_posture_exec_html=defender_posture_exec_html,
        zt_exec_html=zt_exec_html,
        defender_high=defender_high,
        defender_total=defender_total,
        warnings_html=warnings_html,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"Executive report written: {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


def _analyze_regions(resources_by_type: dict) -> dict:
    """
    Analyze regional distribution of resources.
    Returns: {
        "top_regions": List[{"region": str, "count": int, "percentage": float}],
        "region_labels": JSON array of region names,
        "region_values": JSON array of resource counts
    }
    """
    region_counts = {}
    total = 0

    for resource_list in resources_by_type.values():
        if not isinstance(resource_list, list):
            continue
        for resource in resource_list:
            if isinstance(resource, dict):
                location = resource.get("location", "").strip()
                if location and location.lower() != "global":
                    region_counts[location] = region_counts.get(location, 0) + 1
                    total += 1
                elif location.lower() == "global":
                    region_counts["global"] = region_counts.get("global", 0) + 1
                    total += 1

    # Sort by count, top 12 regions
    sorted_regions = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)[:12]
    top_regions = [
        {
            "region": r[0].replace("_", " ").title(),
            "count": r[1],
            "percentage": round((r[1] / total * 100), 1) if total > 0 else 0,
        }
        for r in sorted_regions
    ]

    region_labels = json.dumps([r["region"] for r in top_regions])
    region_values = json.dumps([r["count"] for r in top_regions])

    return {
        "top_regions": top_regions,
        "region_labels": region_labels,
        "region_values": region_values,
        "total_regions": len(region_counts),
    }


def _build_top_findings(advisor_data, misconfig_findings, defender_data, max_findings: int = 5) -> List[dict]:
    findings = []
    for rec in [r for r in advisor_data if r.get("impact") == "High"][:max_findings]:
        findings.append({
            "severity": "High",
            "pillar": rec.get("wafPillar", ""),
            "title": rec.get("shortDescription", "")[:100],
            "source": "Azure Advisor",
        })
    for f in [x for x in misconfig_findings if x.get("severity") in ("Critical", "High")][:max_findings]:
        findings.append({
            "severity": f.get("severity"),
            "pillar": f.get("wafPillar", ""),
            "title": f.get("title", ""),
            "source": "Configuration Assessment",
        })
    for a in [x for x in defender_data if x.get("severity") == "High"][:max_findings]:
        findings.append({
            "severity": "High",
            "pillar": "Security",
            "title": a.get("displayName", "")[:100],
            "source": "Defender for Cloud",
        })
    return findings[:max_findings]


def _build_strategic_recommendations(summary, deprecated, misconfig_findings, defender_data) -> List[dict]:
    recs = []

    if summary.get("total_deprecated", 0) > 0:
        recs.append({
            "priority": "Critical", "area": "Modernization",
            "text": f"Retire or migrate {summary['total_deprecated']} deprecated resource(s) before their retirement dates to avoid service disruptions.",
            "action": "Review the 'Deprecated Resources' section in the Technical Report.",
        })

    if summary.get("critical_findings_count", 0) > 0:
        recs.append({
            "priority": "High", "area": "Security",
            "text": f"Address {summary['critical_findings_count']} critical security finding(s) across the environment.",
            "action": (
                "Review SecurityAssessments and MisconfigFindings in the Excel inventory. "
                "Remediate aligned with the CAF Security design area: "
                "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/design-area/security"
            ),
        })

    if summary.get("total_non_compliant_policies", 0) > 0:
        recs.append({
            "priority": "High", "area": "Governance",
            "text": f"{summary['total_non_compliant_policies']} resource(s) are non-compliant with assigned Azure Policies.",
            "action": "Review the PolicyCompliance sheet and remediate aligned with your governance framework.",
        })

    tag_pct = summary.get("tag_coverage_pct", 100)
    if tag_pct < 80:
        recs.append({
            "priority": "Medium", "area": "Operational Excellence",
            "text": f"Only {tag_pct}% of resources have tags. Poor tag coverage impacts cost allocation, ownership tracking, and incident response.",
            "action": "Define and enforce a mandatory tagging policy using Azure Policy.",
        })

    if summary.get("total_health_issues", 0) > 0:
        recs.append({
            "priority": "Medium", "area": "Reliability",
            "text": f"{summary['total_health_issues']} resource(s) currently show degraded or unavailable health status.",
            "action": "Review the ResourceHealth section and investigate affected resources immediately.",
        })

    if len(recs) < 3:
        recs.append({
            "priority": "Low", "area": "Reliability",
            "text": "Establish a regular Azure Advisor review cadence to proactively address environment health recommendations.",
            "action": "Schedule quarterly reviews of Azure Advisor across all WAF pillars.",
        })

    return recs[:6]


def _detect_modernization_signals(resources_by_type: dict) -> List[dict]:
    """
    INFERRED ASSESSMENT — not based on a discrete Azure API signal.
    Detects presence of specific modern Azure service types.
    """
    indicators = {
        "microsoft.machinelearningservices/workspaces": "Azure Machine Learning workspaces detected — AI/ML workloads present.",
        "microsoft.cognitiveservices/accounts": "Azure AI Services detected — AI capabilities in use.",
        "microsoft.search/searchservices": "Azure AI Search detected — intelligent search infrastructure present.",
        "microsoft.synapse/workspaces": "Azure Synapse Analytics detected — modern data platform in use.",
        "microsoft.databricks/workspaces": "Azure Databricks detected — advanced analytics workloads present.",
        "microsoft.containerservice/managedclusters": "AKS clusters detected — containerized workloads running.",
        "microsoft.app/containerapp": "Azure Container Apps detected — serverless container workloads present.",
        "microsoft.fabric/capacities": "Microsoft Fabric capacity detected — next-gen analytics platform.",
        "microsoft.botservice/botservices": "Azure Bot Services detected — conversational AI workloads present.",
    }

    signals = []
    for rtype, message in indicators.items():
        count = len(resources_by_type.get(rtype, []))
        if count > 0:
            signals.append({"message": message, "count": count})

    return signals


def _build_lz_executive_html(resources_by_type: dict, summary: dict) -> str:
    """Condensed Landing Zone observations for executive summary (warnings only, max 5)."""
    warnings_list = []
    if not resources_by_type.get("microsoft.management/managementgroups"):
        warnings_list.append("No Management Groups detected — hierarchical governance absent. Required for enterprise-scale policy and RBAC delegation.")
    if not resources_by_type.get("microsoft.network/virtualnetworks"):
        warnings_list.append("No Virtual Networks detected — network segmentation absent.")
    if not resources_by_type.get("microsoft.network/privateendpoints"):
        warnings_list.append("No Private Endpoints detected — PaaS services may be publicly exposed. Enable private connectivity for production workloads.")
    if not resources_by_type.get("microsoft.operationalinsights/workspaces"):
        warnings_list.append("No Log Analytics Workspaces detected — centralized logging absent. Required for compliance and operations.")
    if not resources_by_type.get("microsoft.recoveryservices/vaults"):
        warnings_list.append("No Recovery Services Vaults detected — backup and disaster recovery not configured.")
    if not resources_by_type.get("microsoft.keyvault/vaults"):
        warnings_list.append("No Key Vaults detected — secrets and certificates are not centrally managed.")
    defender_total = summary.get("total_defender_findings", 0)
    if defender_total and defender_total > 0:
        warnings_list.append(f"{defender_total} Defender for Cloud findings detected — security posture requires attention.")
    elif not summary.get("total_defender_findings"):
        warnings_list.append("Defender for Cloud data unavailable — enable Defender to gain security posture visibility.")
    tag_pct = summary.get("tag_coverage_pct", 100)
    if tag_pct < 80:
        warnings_list.append(f"Low tag coverage ({tag_pct}%) — cost allocation, ownership, and governance are impaired.")
    non_compliant = summary.get("total_non_compliant_policies", 0)
    if non_compliant > 0:
        warnings_list.append(f"{non_compliant} policy compliance violations — governance standards not fully enforced.")
    if not warnings_list:
        return '<div style="padding:.8rem;background:#e8f5e9;border-radius:8px;color:#2e7d32;font-size:.9rem">✓ No critical Landing Zone gaps detected.</div>'
    top5 = warnings_list[:5]
    items_html = "".join(
        f'<div style="display:flex;align-items:flex-start;gap:.8rem;padding:.6rem 0;border-bottom:1px solid #ffe8d6">'
        f'<span style="color:#C00000;font-size:1.1rem;flex-shrink:0">⚠</span>'
        f'<span style="font-size:.88rem;color:#333">{w}</span></div>'
        for w in top5
    )
    more = len(warnings_list) - 5
    more_note = (
        f'<p style="font-size:.8rem;color:#888;margin-top:.5rem">... and {more} more observation(s). See Technical Report for full Landing Zone analysis.</p>'
        if more > 0 else
        '<p style="font-size:.8rem;color:#888;margin-top:.5rem">See Technical Report for full Landing Zone analysis with CAF alignment details.</p>'
    )
    return f'<div style="background:#fff8f0;border-left:4px solid #FFC000;border-radius:8px;padding:1rem 1.2rem">{items_html}{more_note}</div>'


def _build_defender_posture_executive_html(
    posture_plans: list, resources_by_type: dict, subscriptions: list
) -> str:
    """Defender for Cloud plan-posture executive summary: enablement tiles + narrative."""
    if not posture_plans:
        return ('<div style="background:#f8f8f8;border-radius:8px;padding:1rem 1.2rem;color:#666;font-size:.9rem">'
                'Defender plan posture not available. Ensure the scanning account has at least '
                '<strong>Reader</strong> RBAC (Microsoft.Security/pricings/read) to collect plan enablement.</div>')

    from collectors.defender_posture import build_servers_resource_coverage
    from collectors.defender_pricing import compute_coverage_gap, total_gap_monthly_cost, pricing_source_label

    enabled_plans = sum(1 for p in posture_plans if p.get("enabled"))
    total_plans = len(posture_plans)
    free_plans = total_plans - enabled_plans
    subs_count = len({p.get("subscriptionId", "") for p in posture_plans})

    server_rows = build_servers_resource_coverage(posture_plans, resources_by_type)
    servers_total = len(server_rows)
    servers_covered = sum(1 for r in server_rows if r.get("covered"))
    servers_uncovered = servers_total - servers_covered

    # B2 — coverage gap & cost to protect
    gap_rows = compute_coverage_gap(resources_by_type, posture_plans)
    gap_total_units = sum(r["total_units"] for r in gap_rows)
    gap_unprotected = sum(r["unprotected_units"] for r in gap_rows)
    gap_cost = total_gap_monthly_cost(gap_rows)
    gap_line = ""
    if gap_total_units > 0:
        price_src = pricing_source_label(gap_rows)
        gap_line = (
            f'<p style="font-size:.85rem;color:#555;margin-bottom:.4rem">'
            f'\U0001f4b0 <strong>Coverage gap:</strong> {gap_unprotected:,} of {gap_total_units:,} '
            f'billable units unprotected \u2014 est. <strong>${gap_cost:,.2f}/mo</strong> to close '
            f'(prices: {price_src}; usage-based plans excluded).</p>'
        )

    # Identify the most relevant disabled plans (by friendly name)
    disabled_names = sorted({
        p.get("planDisplayName", "")
        for p in posture_plans if not p.get("enabled")
    })
    disabled_str = ", ".join(disabled_names[:6]) or "None"

    cov_color = "#70AD47" if servers_uncovered == 0 and servers_total > 0 else (
        "#C00000" if servers_uncovered > 0 else "#FFC000")
    if free_plans == 0:
        posture_text = "All discovered Defender plans are enabled across the scanned subscriptions — strong baseline coverage."
    elif enabled_plans == 0:
        posture_text = "No Defender plans are enabled. The environment lacks workload threat protection — prioritise enablement of high-value plans."
    else:
        posture_text = (f"{enabled_plans} of {total_plans} Defender plans are enabled. "
                        f"Review the disabled plans to close coverage gaps on critical workloads.")

    servers_line = ""
    if servers_total > 0:
        servers_line = (
            f'<p style="font-size:.85rem;color:#555;margin-bottom:.4rem">'
            f'<strong>Defender for Servers (per-resource):</strong> '
            f'{servers_covered}/{servers_total} VMs / VMSS / Arc Machines covered'
            + (f' \u2014 <span style="color:#C00000;font-weight:600">{servers_uncovered} not covered</span>.' if servers_uncovered else '.')
            + '</p>'
        )

    return (
        f'<div style="display:grid;grid-template-columns:auto 1fr;gap:1.5rem;align-items:start">'
        f'<div style="display:flex;flex-direction:column;gap:.8rem">'
        f'<div style="background:#e8f5e9;border-radius:12px;padding:1rem 1.5rem;text-align:center;min-width:120px">'
        f'<div style="font-size:2.2rem;font-weight:700;color:#388E3C">{enabled_plans}</div>'
        f'<div style="font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;color:#888">Plans Enabled</div></div>'
        f'<div style="background:#fde8e8;border-radius:12px;padding:.8rem 1.5rem;text-align:center">'
        f'<div style="font-size:1.6rem;font-weight:700;color:#C00000">{free_plans}</div>'
        f'<div style="font-size:.75rem;text-transform:uppercase;color:#888">Plans Off</div></div>'
        f'<div style="background:{cov_color};color:#fff;border-radius:12px;padding:.8rem 1.5rem;text-align:center">'
        f'<div style="font-size:1.6rem;font-weight:700">{servers_covered}/{servers_total}</div>'
        f'<div style="font-size:.75rem;text-transform:uppercase;opacity:.9">Servers Covered</div></div>'
        f'</div>'
        f'<div>'
        f'<p style="font-size:.92rem;color:#333;margin-bottom:.6rem">'
        f'<strong>{enabled_plans}/{total_plans} Defender plans enabled</strong> across {subs_count} subscription(s). {posture_text}</p>'
        f'{servers_line}'
        f'{gap_line}'
        f'<p style="font-size:.85rem;color:#555;margin-bottom:.4rem">'
        f'<strong>Disabled plans:</strong> {disabled_str}</p>'
        f'<p style="font-size:.8rem;color:#888;margin-top:.6rem">'
        f'VMs / VMSS / Arc are evaluated per-resource; other workloads at subscription scope '
        f'(per-resource detail via the assessments section). Plan posture requires only <strong>Reader</strong> RBAC. '
        f'See the Technical Report for the full plan-by-subscription breakdown.</p>'
        f'</div></div>'
    )


def _build_defender_executive_html(defender_data: list, resources_by_type: dict, summary: dict) -> str:
    """Defender for Cloud executive summary block: KPI tiles + narrative + cost estimate."""
    from collections import Counter
    total = len(defender_data)
    if total == 0:
        return ('<div style="background:#f8f8f8;border-radius:8px;padding:1rem 1.2rem;color:#666;font-size:.9rem">'
                'No Defender for Cloud security assessments were returned. This typically means one of: '
                '<strong>(a)</strong> all assessed resources are healthy, '
                '<strong>(b)</strong> Microsoft Defender for Cloud plans are not enabled (see the '
                '<em>Plan Posture</em> section above), or '
                '<strong>(c)</strong> the scanning account lacks the <strong>Security Reader</strong> RBAC role '
                'required to read assessments. Plan posture above is collected with <strong>Reader</strong> and is unaffected.</div>')
    sev_counts = Counter(d.get("severity", "Unknown") for d in defender_data)
    high = sev_counts.get("High", 0)
    medium = sev_counts.get("Medium", 0)
    low = sev_counts.get("Low", 0)
    cat_counts = Counter(d.get("category", "Unknown") for d in defender_data)
    top_cats = sorted(cat_counts.items(), key=lambda x: -x[1])[:3]
    top_cats_str = ", ".join(f"{c[0]} ({c[1]})" for c in top_cats) or "N/A"
    vms = (len(resources_by_type.get("microsoft.compute/virtualmachines", []))
           + len(resources_by_type.get("microsoft.hybridcompute/machines", [])))
    storage = len(resources_by_type.get("microsoft.storage/storageaccounts", []))
    aks = len(resources_by_type.get("microsoft.containerservice/managedclusters", []))
    p1_est = round(vms * 4.95 + storage * 10.00 + aks * 7.00, 2)
    p2_est = round(vms * 13.95 + storage * 10.00 + aks * 7.00, 2)
    cost_note = ""
    if (vms + storage + aks) > 0:
        cost_note = (
            f'<p style="font-size:.85rem;color:#555;margin-top:.6rem">'
            f'\U0001f4b0 <strong>Estimated monthly cost if all Defender plans enabled:</strong> '
            f'P1 ~<strong>${p1_est:,.2f}</strong> / P2 ~<strong>${p2_est:,.2f}</strong> '
            f'({vms} VMs, {storage} storage accounts, {aks} AKS clusters — public list pricing). '
            f'See Excel <em>DefenderCostEstimate</em> sheet and Technical Report for full breakdown.</p>'
        )
    sev_color = "#C00000" if high > 0 else ("#FFC000" if medium > 0 else "#70AD47")
    if high > 0:
        posture_text = "High-severity findings indicate immediate risk exposure and must be prioritized for remediation."
    elif medium > 0:
        posture_text = "No high-severity findings. Medium findings should be reviewed and remediated on a planned schedule."
    else:
        posture_text = "Findings are low severity — continue monitoring and plan remediation on a regular schedule."
    return (
        f'<div style="display:grid;grid-template-columns:auto 1fr;gap:1.5rem;align-items:start">'
        f'<div style="display:flex;flex-direction:column;gap:.8rem">'
        f'<div style="background:{sev_color};color:#fff;border-radius:12px;padding:1rem 1.5rem;text-align:center;min-width:120px">'
        f'<div style="font-size:2.2rem;font-weight:700">{high}</div>'
        f'<div style="font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;opacity:.9">High Severity</div></div>'
        f'<div style="background:#fff3cd;border-radius:12px;padding:.8rem 1.5rem;text-align:center">'
        f'<div style="font-size:1.6rem;font-weight:700;color:#B8860B">{medium}</div>'
        f'<div style="font-size:.75rem;text-transform:uppercase;color:#888">Medium</div></div>'
        f'<div style="background:#e8f5e9;border-radius:12px;padding:.8rem 1.5rem;text-align:center">'
        f'<div style="font-size:1.6rem;font-weight:700;color:#388E3C">{low}</div>'
        f'<div style="font-size:.75rem;text-transform:uppercase;color:#888">Low</div></div>'
        f'</div>'
        f'<div>'
        f'<p style="font-size:.92rem;color:#333;margin-bottom:.6rem">'
        f'<strong>{total} security assessments</strong> require attention. {posture_text}</p>'
        f'<p style="font-size:.85rem;color:#555;margin-bottom:.4rem">'
        f'<strong>Top affected categories:</strong> {top_cats_str}</p>'
        f'{cost_note}'
        f'<p style="font-size:.8rem;color:#888;margin-top:.6rem">'
        f'See the Technical Report for full severity × category breakdown and remediation guidance. '
        f'Findings align with the <a href="https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/design-area/security" '
        f'target="_blank" style="color:#2E86AB">CAF Security design area</a>.</p>'
        f'</div></div>'
    )


def _build_zero_trust_executive_html(misconfig_findings: list) -> str:
    """Condensed Zero Trust summary for executive report."""
    principle_rules = {
        "Verify Explicitly": {"STG-001", "STG-003", "APP-001", "APP-002", "APP-003", "SQL-002", "REDIS-001", "REDIS-002"},
        "Use Least Privilege": {"KV-001", "KV-002", "AKS-001"},
        "Assume Breach": {"STG-002", "STG-004", "SQL-001", "KV-003", "COSMOS-001", "REDIS-003", "PG-001", "MYSQL-001"},
    }
    grouped = {k: [] for k in principle_rules}
    for finding in misconfig_findings:
        rid = finding.get("ruleId", "")
        for principle, rules in principle_rules.items():
            if rid in rules:
                grouped[principle].append(finding)
                break

    cards = ""
    total = 0
    for principle in ["Verify Explicitly", "Use Least Privilege", "Assume Breach"]:
        findings = grouped[principle]
        total += len(findings)
        sev = Counter((f.get("severity") or "Unknown") for f in findings)
        sev_txt = ", ".join(
            f"{s}: {sev.get(s, 0):,}" for s in ["Critical", "High", "Medium", "Low"] if sev.get(s, 0) > 0
        ) or "No findings"
        cards += (
            '<div style="background:#f8fbff;border:1px solid #dbe7f3;border-radius:10px;padding:.9rem 1rem">'
            f'<div style="font-weight:700;color:#1F4E79;font-size:.9rem">{principle}</div>'
            f'<div style="font-size:1.55rem;font-weight:700;color:#1F4E79;line-height:1.2">{len(findings):,}</div>'
            f'<div style="font-size:.78rem;color:#666">{sev_txt}</div>'
            '</div>'
        )

    return (
        f'<div style="font-size:.85rem;color:#555;margin-bottom:.7rem">'
        f'Zero Trust mapping from misconfiguration findings. Total mapped findings: <strong>{total:,}</strong>.</div>'
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:.8rem">'
        f'{cards}'
        '</div>'
    )


def _render_html(
    scan_date, tenant_id, tenant_name, subscriptions_list, summary, risk_level, risk_color,
    top_findings, pillar_labels, pillar_values,
    type_labels, type_values, strategic_recs, modern_signals, region_summary, deprecated_count,
    lz_exec_html="", defender_exec_html="", defender_posture_exec_html="", zt_exec_html="",
    defender_high=0, defender_total=0,
    warnings_html="",
) -> str:
    SEV_COLORS = {"Critical": "#C00000", "High": "#FF4444", "Medium": "#FFC000", "Low": "#70AD47"}
    PRI_COLORS = {"Critical": "#C00000", "High": "#FF4444", "Medium": "#FFC000", "Low": "#70AD47"}

    findings_html = "".join(
        f"""<div class="finding-card">
            <span class="badge" style="background:{SEV_COLORS.get(f.get('severity',''),'#999')}">{f.get('severity','')}</span>
            <span class="badge badge-pillar">{f.get('pillar','')}</span>
            <p class="finding-title">{f.get('title','')}</p>
            <small class="finding-source">{f.get('source','')}</small>
        </div>"""
        for f in top_findings
    ) or '<p class="no-data">No critical findings detected. Environment appears healthy.</p>'

    recs_html = "".join(
        f"""<div class="rec-card">
            <div class="rec-header">
                <span class="badge" style="background:{PRI_COLORS.get(r.get('priority',''),'#999')}">{r.get('priority','')}</span>
                <span class="rec-area">{r.get('area','')}</span>
            </div>
            <p class="rec-text">{r.get('text','')}</p>
            <p class="rec-action"><strong>Action:</strong> {r.get('action','')}</p>
        </div>"""
        for r in strategic_recs
    )

    signals_html = "".join(
        f"""<div class="signal-item">
            <span class="signal-count">{s['count']}</span>
            <span class="signal-msg">{s['message']}</span>
        </div>"""
        for s in modern_signals[:8]
    ) or '<p class="no-data">No specific modernization signals detected.</p>'

    dep_alert = (
        f'<div class="alert-critical">⚠ <strong>Deprecated Resources Detected:</strong> '
        f'{deprecated_count} resource(s) are using retired or retiring Azure services. '
        f'Immediate action required to prevent service disruption.</div>'
        if deprecated_count > 0 else ""
    )

    kpi = summary
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Azure Tenant Insights — Executive Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:#f0f4f8;color:#1a1a2e}}
.header{{background:linear-gradient(135deg,#1F4E79 0%,#2E86AB 100%);color:#fff;padding:2rem 3rem}}
.header h1{{font-size:2rem;font-weight:700;margin-bottom:.4rem}}
.header .sub{{font-size:.95rem;opacity:.85}}
.meta-bar{{background:#1a3a5c;color:#a8c6e0;padding:.5rem 3rem;font-size:.82rem;display:flex;gap:2rem;flex-wrap:wrap}}
.container{{max-width:1400px;margin:0 auto;padding:2rem 3rem}}
.risk-banner{{padding:1rem 1.5rem;border-radius:10px;text-align:center;font-size:1.1rem;font-weight:700;color:#fff;margin:1rem 0;background:{risk_color}}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:1.2rem;margin:1.5rem 0}}
.kpi-card{{background:#fff;border-radius:12px;padding:1.5rem;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.08);border-top:4px solid #2E86AB}}
.kpi-card.warn{{border-top-color:#FFC000}}.kpi-card.crit{{border-top-color:#C00000}}.kpi-card.ok{{border-top-color:#70AD47}}
.kpi-val{{font-size:2.4rem;font-weight:700;color:#1F4E79;line-height:1}}
.kpi-lbl{{font-size:.8rem;color:#666;margin-top:.4rem;font-weight:500;text-transform:uppercase;letter-spacing:.05em}}
.section{{background:#fff;border-radius:12px;padding:1.8rem;margin:1.5rem 0;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
.section h2{{font-size:1.25rem;color:#1F4E79;border-bottom:2px solid #e8f0f7;padding-bottom:.7rem;margin-bottom:1.2rem}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem}}
.chart-box{{position:relative;height:260px}}
.finding-card{{border-left:4px solid #ddd;padding:.8rem 1rem;margin:.5rem 0;background:#fafafa;border-radius:0 8px 8px 0}}
.finding-title{{margin:.4rem 0;font-size:.92rem}}
.finding-source{{color:#888;font-size:.78rem}}
.badge{{display:inline-block;padding:.15rem .55rem;border-radius:10px;color:#fff;font-size:.73rem;font-weight:600;margin-right:.3rem}}
.badge-pillar{{background:#2E86AB!important}}
.rec-card{{border:1px solid #e0e8f0;border-radius:10px;padding:1.2rem;margin:.8rem 0;background:#fafcff}}
.rec-header{{display:flex;align-items:center;gap:.7rem;margin-bottom:.5rem}}
.rec-area{{font-weight:700;color:#1F4E79;font-size:.92rem}}
.rec-text{{color:#333;font-size:.92rem;margin-bottom:.4rem}}
.rec-action{{color:#555;font-size:.85rem}}
.signal-item{{display:flex;align-items:center;gap:1rem;padding:.6rem 0;border-bottom:1px solid #eee}}
.signal-count{{background:#1F4E79;color:#fff;border-radius:50%;width:36px;height:36px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.88rem;flex-shrink:0}}
.signal-msg{{font-size:.88rem;color:#333}}
.alert-critical{{background:#fde8e8;border-left:4px solid #C00000;color:#7b0000;padding:1rem 1.2rem;border-radius:8px;margin:.8rem 0}}
.no-data{{color:#888;font-style:italic;padding:.5rem 0}}
.footer{{text-align:center;padding:2rem;color:#888;font-size:.82rem}}
.report-badge{{background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.4);padding:.25rem 1rem;border-radius:20px;font-size:.82rem;display:inline-block;margin-top:.5rem}}
@media(max-width:768px){{.two-col{{grid-template-columns:1fr}}.kpi-grid{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>
<div class="header">
  <h1>Azure Tenant Insights</h1>
  <div class="sub">Executive Summary Report</div>
  <div class="report-badge">Confidential — For Stakeholder Review</div>
</div>
<div class="meta-bar">
  <span>📅 Scan Date: <strong>{scan_date}</strong></span>
  <span>🏢 Tenant: <strong>{tenant_name}</strong> ({tenant_id})</span>
  <span>📋 Subscriptions: <strong>{subscriptions_list}</strong></span>
  <span>⚙ Generated by: <strong>Azure Tenant Insights v1.0.0</strong></span>
</div>
<div class="container">
  {dep_alert}
  <div class="risk-banner">Overall Environment Risk Level: {risk_level}</div>

  <div class="kpi-grid">
    <div class="kpi-card"><div class="kpi-val">{kpi.get('total_resources',0):,}</div><div class="kpi-lbl">Total Resources</div></div>
    <div class="kpi-card"><div class="kpi-val">{kpi.get('total_subscriptions',0)}</div><div class="kpi-lbl">Subscriptions</div></div>
    <div class="kpi-card"><div class="kpi-val">{kpi.get('total_resource_types',0)}</div><div class="kpi-lbl">Resource Types</div></div>
    <div class="kpi-card"><div class="kpi-val">{kpi.get('total_regions',0)}</div><div class="kpi-lbl">Active Regions</div></div>
    <div class="kpi-card warn"><div class="kpi-val">{kpi.get('total_advisor_recommendations',0)}</div><div class="kpi-lbl">Advisor Recommendations</div></div>
    <div class="kpi-card {'crit' if kpi.get('critical_findings_count',0)>0 else 'ok'}"><div class="kpi-val">{kpi.get('critical_findings_count',0)}</div><div class="kpi-lbl">Critical Findings</div></div>
    <div class="kpi-card {'crit' if kpi.get('total_deprecated',0)>0 else 'ok'}"><div class="kpi-val">{kpi.get('total_deprecated',0)}</div><div class="kpi-lbl">Deprecated Resources</div></div>
    <div class="kpi-card {'warn' if kpi.get('tag_coverage_pct',100)<80 else 'ok'}"><div class="kpi-val">{kpi.get('tag_coverage_pct',0)}%</div><div class="kpi-lbl">Tag Coverage</div></div>
    <div class="kpi-card {'crit' if defender_high>0 else 'ok'}"><div class="kpi-val">{defender_high}</div><div class="kpi-lbl">Defender High</div></div>
    <div class="kpi-card {'warn' if defender_total>0 else 'ok'}"><div class="kpi-val">{defender_total}</div><div class="kpi-lbl">Defender Findings</div></div>
  </div>

  <div class="two-col">
    <div class="section"><h2>Advisor Recommendations by WAF Pillar</h2><div class="chart-box"><canvas id="pillarChart"></canvas></div></div>
    <div class="section"><h2>Top Resource Types</h2><div class="chart-box"><canvas id="typeChart"></canvas></div></div>
  </div>

  <div class="section"><h2>🌍 Active Regions Distribution</h2><div class="chart-box" style="height:250px"><canvas id="regionChart"></canvas></div></div>

  <div class="section"><h2>Top Priority Findings</h2>{findings_html}</div>
  <div class="section"><h2>Strategic Recommendations</h2>{recs_html}</div>
  <div class="section">
    <h2>🏗 Landing Zone Observations
      <small style="font-size:.72rem;color:#888;font-weight:normal;margin-left:.5rem">(Condensed — top action items. See Technical Report for full analysis.)</small>
    </h2>
    <p style="font-size:.82rem;color:#666;margin-bottom:.8rem">Key infrastructure gaps identified against the Azure Cloud Adoption Framework landing zone design areas. Warnings only — positive observations are available in the Technical Report.</p>
    {lz_exec_html}
  </div>

  <div class="section">
    <h2>� Defender for Cloud — Plan Posture</h2>
    <p style="font-size:.82rem;color:#666;margin-bottom:.8rem">Defender plan enablement per subscription (<strong>Microsoft.Security/pricings</strong>). VMs / VMSS / Arc are evaluated per-resource; other workloads at subscription scope. Requires only <strong>Reader</strong> RBAC.</p>
    {defender_posture_exec_html}
  </div>

  <div class="section">
    <h2>�🔒 Defender for Cloud — Executive Summary</h2>
    <p style="font-size:.82rem;color:#666;margin-bottom:.8rem">Microsoft Defender for Cloud security posture. Requires <strong>Security Reader</strong> RBAC on SecurityResources.</p>
    {defender_exec_html}
  </div>

    <div class="section">
        <h2>🛡 Zero Trust Security Posture — Executive Summary</h2>
        <p style="font-size:.82rem;color:#666;margin-bottom:.8rem">Findings grouped by Zero Trust principles: Verify Explicitly, Use Least Privilege, and Assume Breach.</p>
        {zt_exec_html}
    </div>

  <div class="section">
    <h2>Technology & Modernization Signals
      <small style="font-size:.72rem;color:#888;font-weight:normal;margin-left:.5rem">(Inferred from resource types detected — not an authoritative API signal)</small>
    </h2>
    {signals_html}
  </div>
</div>
<div class="footer">
  Azure Tenant Insights v1.0.0 &mdash; Executive Report &mdash; {scan_date}<br>
  <small>Data sourced exclusively from Azure Resource Graph, Azure Advisor, and official Azure APIs. All findings should be validated against your organizational context.</small>
  {warnings_html}
  <hr style="border:none;border-top:1px solid #333;margin:.8rem 0">
  <strong style="color:#ccc;font-size:.78rem">References</strong>
  <ul style="list-style:none;padding:0;margin:.4rem 0;font-size:.73rem;color:#888">
    <li><a href="https://learn.microsoft.com/en-us/azure/governance/resource-graph/overview" target="_blank" style="color:#aaa;">Azure Resource Graph — Microsoft Learn</a></li>
    <li><a href="https://learn.microsoft.com/en-us/azure/advisor/advisor-overview" target="_blank" style="color:#aaa;">Azure Advisor — Microsoft Learn</a></li>
    <li><a href="https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/design-area/security" target="_blank" style="color:#aaa;">CAF Security design area — Cloud Adoption Framework | Microsoft Learn</a></li>
    <li><a href="https://learn.microsoft.com/en-us/azure/well-architected/" target="_blank" style="color:#aaa;">Azure Well-Architected Framework — Microsoft Learn</a></li>
    <li><a href="https://learn.microsoft.com/en-us/azure/defender-for-cloud/defender-for-cloud-introduction" target="_blank" style="color:#aaa;">Microsoft Defender for Cloud — Microsoft Learn</a></li>
  </ul>
</div>
<script>
const pillarCtx=document.getElementById('pillarChart')?.getContext('2d');
if(pillarCtx){{new Chart(pillarCtx,{{type:'doughnut',data:{{labels:{pillar_labels},datasets:[{{data:{pillar_values},backgroundColor:['#1F4E79','#2E86AB','#70AD47','#FFC000','#C00000','#7F7F7F'],borderWidth:2,borderColor:'#fff'}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'right',labels:{{font:{{size:11}}}}}}}}}}}})}};
const typeCtx=document.getElementById('typeChart')?.getContext('2d');
if(typeCtx){{new Chart(typeCtx,{{type:'bar',data:{{labels:{type_labels},datasets:[{{label:'Count',data:{type_values},backgroundColor:'#2E86AB',borderRadius:4}}]}},options:{{responsive:true,maintainAspectRatio:false,indexAxis:'y',plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{display:false}}}},y:{{grid:{{display:false}}}}}}}}}})}};
const regionCtx=document.getElementById('regionChart')?.getContext('2d');
if(regionCtx){{new Chart(regionCtx,{{type:'bar',data:{{labels:{region_summary['region_labels']},datasets:[{{label:'Resources',data:{region_summary['region_values']},backgroundColor:'#70AD47',borderRadius:4}}]}},options:{{responsive:true,maintainAspectRatio:false,indexAxis:'y',plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{display:false}}}},y:{{grid:{{display:false}}}}}}}}}})}};
</script>
</body></html>"""
