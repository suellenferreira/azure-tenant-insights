"""
Technical HTML Report Writer.

Generates a comprehensive single-file HTML report for engineering,
architecture, security, and operations teams.

Contents (tabbed / anchored):
  - Summary KPIs + charts
  - Resource inventory by type
  - WAF pillar findings (Azure Advisor, tabbed by pillar)
  - Policy compliance violations
  - Known misconfigurations
  - Defender for Cloud assessments (optional)
  - Resource health events
  - Deprecated/retiring resources
  - Landing Zone observations (clearly labeled INFERRED)
  - Azure Arc resources (if present)
"""

import json
import logging
from collections import Counter
from typing import Any, Dict, List


def _esc(value: Any) -> str:
    """HTML-escape a value for safe inline rendering."""
    import html as _html
    return _html.escape(str(value if value is not None else ""), quote=True)

logger = logging.getLogger(__name__)

WAF_PILLARS = [
    "Reliability", "Security", "Cost Optimization",
    "Operational Excellence", "Performance Efficiency",
]
WAF_ICONS = {
    "Reliability": "🔄", "Security": "🔒",
    "Cost Optimization": "💰", "Operational Excellence": "⚙",
    "Performance Efficiency": "⚡",
}
WAF_COLORS = {
    "Reliability": "#2E86AB", "Security": "#C00000",
    "Cost Optimization": "#70AD47", "Operational Excellence": "#1F4E79",
    "Performance Efficiency": "#7030A0",
}


def write_technical_report(scan_data: dict, output_path: str) -> None:
    """Generates the Technical HTML report and writes to output_path."""
    meta = scan_data.get("metadata", {})
    summary = scan_data.get("summary_metrics", {})
    advisor_data = scan_data.get("advisor_data", [])
    policy_data = scan_data.get("policy_data", [])
    health_data = scan_data.get("health_data", [])
    deprecated = scan_data.get("deprecated_matches", [])
    misconfig_findings = scan_data.get("misconfig_findings", [])
    defender_data = scan_data.get("defender_data", [])
    defender_posture = scan_data.get("defender_posture", [])
    waf_findings = scan_data.get("waf_findings", {})
    resources_by_type = scan_data.get("resources_by_type", {})

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

    # Chart data
    resources_by_sub = summary.get("resources_by_subscription", {})
    _sub_name_map = {
        s.get("subscriptionId", ""): (s.get("displayName") or s.get("subscriptionId", ""))
        for s in subscriptions
    }
    _sub_items = list(resources_by_sub.items())[:10]
    sub_labels = json.dumps([_sub_name_map.get(k) or k for k, _ in _sub_items])
    sub_values = json.dumps([v for _, v in _sub_items])

    misconfig_sev = summary.get("misconfig_by_severity", {})
    sev_labels = json.dumps(list(misconfig_sev.keys()))
    sev_values = json.dumps(list(misconfig_sev.values()))

    # Sections
    inventory_html = _inventory_section(summary)
    waf_html = _waf_section(waf_findings)
    policy_summary_html = _policy_summary_section(policy_data)
    policy_html = _table_section(policy_data, [
        ("resourceId", "Resource"), ("resourceType", "Type"),
        ("policyAssignmentName", "Policy Assignment"),
        ("policyDefinitionAction", "Effect"),
        ("complianceState", "State"),
        ("subscriptionId", "Subscription"), ("resourceGroup", "RG"),
    ], table_id="tbl-policy")
    misconfig_html = _misconfig_table(misconfig_findings)
    health_html = _health_section(health_data)
    deprecated_html = _deprecated_table(deprecated)
    lz_html = _landing_zone_section(resources_by_type, summary)

    defender_section = _build_defender_section_html(defender_data, resources_by_type)
    posture_section = _build_defender_posture_section_html(
        defender_posture, resources_by_type, subscriptions
    )
    defender_section = posture_section + defender_section

    # Azure Arc
    arc_resources = (
        resources_by_type.get("microsoft.hybridcompute/machines", []) +
        resources_by_type.get("microsoft.hybridkubernetes/connectedclusters", [])
    )
    arc_section = ""
    if arc_resources:
        arc_counts = Counter(r.get("type", "Unknown") for r in arc_resources)
        arc_summary_rows = "".join(
            f"<tr><td>{rtype}</td><td class='num'>{count}</td></tr>"
            for rtype, count in sorted(arc_counts.items(), key=lambda x: x[0])
        )
        arc_summary_table = (
            '<div class="table-scroll" style="margin-bottom:.8rem">'
            '<table class="dtable"><thead><tr><th>Type</th><th class="num">Total</th></tr></thead>'
            f'<tbody>{arc_summary_rows}</tbody></table></div>'
        )
        arc_rows = _table_section(arc_resources, [
            ("name", "Name"), ("type", "Type"),
            ("location", "Location"), ("resourceGroup", "RG"),
            ("subscriptionId", "Subscription"),
        ])
        arc_section = f"""<div class="section" id="arc">
            <h2>🌐 Azure Arc Resources <span class="cnt">{len(arc_resources)}</span></h2>
            <p class="note">Hybrid and on-premises resources registered via Azure Arc.</p>
            {arc_summary_table}
            {arc_rows}</div>"""

    # Cloud Modernization & Opportunity (INFERRED) — detailed evidence view
    from processors.modernization import build_modernization_assessment
    modernization = build_modernization_assessment(scan_data)
    modernization_detail_html = _build_modernization_tech_html(modernization)

    # Item 3: Regional distribution analysis
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
            f'<details id="data-collection-notes" style="font-size:.73rem;color:#aaa;margin-top:.6rem;text-align:left">'
            f'<summary style="cursor:pointer">&#9432; Data Collection Notes '
            f'({len(collection_warnings)})</summary>'
            f'<ul style="margin:.4rem 0 0 1rem;color:#999">{_warn_items}</ul>'
            f'</details>'
        )
    else:
        warnings_html = (
            f'<div id="data-collection-notes" style="font-size:.73rem;color:#aaa;margin-top:.6rem">'
            f'&#9432; Data Collection Notes: no collection warnings recorded for this scan.</div>'
        )

    zerotrust_html = _zero_trust_section(misconfig_findings, resources_by_type, summary)
    html = _render_html(
        scan_date=scan_date, tenant_id=tenant_id, tenant_name=tenant_name,
        subscriptions_list=sub_list, summary=summary,
        inventory_html=inventory_html, waf_html=waf_html,
        policy_html=policy_html, policy_summary_html=policy_summary_html,
        misconfig_html=misconfig_html,
        health_html=health_html, deprecated_html=deprecated_html,
        lz_html=lz_html, defender_section=defender_section,
        zerotrust_html=zerotrust_html,
        arc_section=arc_section, modernization_detail_html=modernization_detail_html,
        region_summary=region_summary,
        sub_labels=sub_labels, sub_values=sub_values,
        sev_labels=sev_labels, sev_values=sev_values,
        has_defender=bool(defender_data) or bool(defender_posture), has_arc=bool(arc_resources),
        policy_count=len(policy_data), misconfig_count=len(misconfig_findings),
        health_count=len(health_data), deprecated_count=len(deprecated),
        advisor_count=len(advisor_data),
        warnings_html=warnings_html,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"Technical report written: {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Section builders
# ─────────────────────────────────────────────────────────────────────────────

def _table_section(data: list, columns: list, max_rows: int = 400, table_id: str = "") -> str:
    if not data:
        return '<div class="table-scroll"><p class="no-data">No records found.</p></div>'

    col_keys = [c[0] for c in columns]
    col_labels = [c[1] for c in columns]

    thead_hdr = "".join(f"<th>{lbl}</th>" for lbl in col_labels)
    tbl_id_attr = f' id="{table_id}"' if table_id else ""
    filter_row = ""
    if table_id:
        filter_inputs = "".join(
            f'<th style="padding:.2rem .4rem;background:#e8f4f8">'
            f'<input class="filter-input" data-tbl="{table_id}" placeholder="⌕ {lbl}..." '
            f'oninput="filterCol(this,\'{table_id}\',{i})"></th>'
            for i, lbl in enumerate(col_labels)
        )
        filter_row = f'<tr class="filter-row">{filter_inputs}</tr>'

    rows = ""
    for item in data[:max_rows]:
        row = "".join(
            f"<td>{str(item.get(k,''))[:200]}</td>" for k in col_keys
        )
        rows += f"<tr>{row}</tr>"

    if len(data) > max_rows:
        rows += f'<tr><td colspan="{len(columns)}" class="info-cell">... and {len(data)-max_rows} more rows — see Excel inventory for complete data.</td></tr>'

    return f"""<div class="table-scroll">
        <table class="dtable"{tbl_id_attr}><thead><tr>{thead_hdr}</tr>{filter_row}</thead><tbody>{rows}</tbody></table></div>"""


def _kpi_row_from_counter(counter: Counter, color_map: dict | None = None) -> str:
    if not counter:
        return '<p class="no-data">No data available.</p>'
    parts = []
    for key, value in counter.items():
        bg = color_map.get(key, "#2E86AB") if color_map else "#2E86AB"
        parts.append(
            f'<span style="display:inline-block;margin:.2rem .4rem .2rem 0;padding:.22rem .55rem;'
            f'background:{bg};color:#fff;border-radius:10px;font-size:.77rem;font-weight:600">'
            f'{key}: {value:,}</span>'
        )
    return "".join(parts)


def _policy_summary_section(policy_data: list) -> str:
    effect_counts = Counter((p.get("policyDefinitionAction") or "Unknown") for p in policy_data)
    type_counts = Counter((p.get("resourceType") or "Unknown") for p in policy_data)
    top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    effect_html = _kpi_row_from_counter(effect_counts)
    type_rows = "".join(
        f"<tr><td>{rtype}</td><td class='num'>{count:,}</td></tr>" for rtype, count in top_types
    ) or '<tr><td colspan="2" class="no-data">No records found.</td></tr>'

    return (
        '<details id="policy-summary" style="margin:.4rem 0 .9rem" open>'
        '<summary style="cursor:pointer;font-weight:700;color:#1F4E79">Policy Summary (by Effect and Type)</summary>'
        '<div style="margin-top:.6rem">'
        '<div style="font-size:.81rem;color:#666;margin-bottom:.25rem"><strong>Totals by Effect</strong></div>'
        f'{effect_html}'
        '<div style="font-size:.81rem;color:#666;margin:.6rem 0 .25rem"><strong>Top Resource Types</strong></div>'
        '<div class="table-scroll"><table class="dtable">'
        '<thead><tr><th>Type</th><th class="num">Count</th></tr></thead>'
        f'<tbody>{type_rows}</tbody></table></div>'
        '</div></details>'
    )


def _normalize_health_events(health_data: list) -> list:
    normalized = []
    for event in health_data:
        summary = (event.get("summary") or "").strip()
        reason_type = (event.get("reasonType") or "").strip()
        reason_chronicity = (event.get("reasonChronicity") or "").strip()
        state = (event.get("availabilityState") or "Unknown").strip()
        normalized.append({
            **event,
            "summary": summary or f"{state} status reported by Azure Resource Health.",
            "reasonType": reason_type or reason_chronicity or "Not provided",
        })
    return normalized


def _health_section(health_data: list) -> str:
    normalized = _normalize_health_events(health_data)
    return _table_section(normalized, [
        ("name", "Resource"), ("availabilityState", "State"),
        ("summary", "Summary"), ("reasonType", "Reason"),
        ("occurredTime", "Occurred"),
        ("subscriptionId", "Subscription"), ("resourceGroup", "RG"),
    ], table_id="tbl-health")


def _misconfig_table(findings: list) -> str:
    if not findings:
        return '<p class="no-data">No misconfiguration findings detected.</p>'

    _SEV_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    sorted_findings = sorted(findings, key=lambda x: _SEV_ORDER.get(x.get("severity", ""), 99))
    SEV_COLORS = {"Critical": "#C00000", "High": "#FF4444", "Medium": "#FFC000", "Low": "#FFFF99"}
    sev_counts = Counter(f.get("severity", "Unknown") for f in findings)
    sev_summary = _kpi_row_from_counter(
        Counter({k: sev_counts.get(k, 0) for k in ["Critical", "High", "Medium", "Low"] if sev_counts.get(k, 0) > 0}),
        color_map={"Critical": "#7b0000", "High": "#C00000", "Medium": "#B8860B", "Low": "#2E7D32"},
    )
    _HEADERS = ["Rule", "Severity", "Pillar", "Title", "Resource", "Type", "Subscription", "RG", "Docs"]
    filter_row = "".join(
        f'<th style="padding:.2rem .4rem;background:#e8f4f8">'
        f'<input class="filter-input" data-tbl="tbl-misconfig" placeholder="⌕ {h}..." '
        f'oninput="filterCol(this,\'tbl-misconfig\',{i})"></th>'
        for i, h in enumerate(_HEADERS)
    )
    rows = ""
    for f in sorted_findings[:400]:
        sev = f.get("severity", "")
        sev_style = (
            f'style="background:{SEV_COLORS.get(sev,"#eee")};font-weight:700;'
            f'white-space:nowrap;min-width:75px"'
        ) if sev in SEV_COLORS else ""
        rows += f"""<tr>
            <td>{f.get('ruleId','')}</td>
            <td {sev_style}>{sev}</td>
            <td>{f.get('wafPillar','')}</td>
            <td>{f.get('title','')}</td>
            <td>{f.get('resourceName','')}</td>
            <td>{f.get('resourceType','')}</td>
            <td>{f.get('subscriptionId','')}</td>
            <td>{f.get('resourceGroup','')}</td>
            <td><a href="{f.get('documentationUrl','')}" target="_blank" rel="noopener">📖</a></td>
        </tr>"""

    hdr_row = "".join(f"<th>{h}</th>" for h in _HEADERS)
    return f"""<div style="margin:.3rem 0 .7rem"><strong style="font-size:.82rem;color:#1F4E79">Totals by Severity:</strong> {sev_summary}</div>
    <div class="table-scroll"><table class="dtable" id="tbl-misconfig">
        <thead><tr>{hdr_row}</tr><tr class="filter-row">{filter_row}</tr></thead>
        <tbody>{rows}</tbody></table></div>"""


def _deprecated_table(deprecated: list) -> str:
    if not deprecated:
        return '<p class="no-data">No deprecated resources detected.</p>'

    _SEV_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Warning": 3, "Low": 4}
    sorted_dep = sorted(deprecated, key=lambda x: _SEV_ORDER.get(x.get("severity", ""), 99))
    _HEADERS = ["Resource", "Type", "Retirement Date", "Severity", "Subscription", "RG", "Why Listed", "Migration"]
    filter_row = "".join(
        f'<th style="padding:.2rem .4rem;background:#e8f4f8">'
        f'<input class="filter-input" data-tbl="tbl-deprecated" placeholder="⌕ {h}..." '
        f'oninput="filterCol(this,\'tbl-deprecated\',{i})"></th>'
        for i, h in enumerate(_HEADERS)
    )
    rows = ""
    for m in sorted_dep:
        rows += f"""<tr>
            <td>{m.get('resourceName','')}</td>
            <td>{m.get('resourceType','')}</td>
            <td style="font-weight:700;color:#C00000;white-space:nowrap">{m.get('retirementDate','')}</td>
            <td>{m.get('severity','')}</td>
            <td>{m.get('subscriptionId','')}</td>
            <td>{m.get('resourceGroup','')}</td>
            <td>{m.get('notes','')}</td>
            <td><a href="{m.get('migrationPath','')}" target="_blank" rel="noopener">Migration Guide →</a></td>
        </tr>"""

    hdr_row = "".join(f"<th>{h}</th>" for h in _HEADERS)
    return f"""<div class="table-scroll"><table class="dtable" id="tbl-deprecated">
        <thead><tr>{hdr_row}</tr><tr class="filter-row">{filter_row}</tr></thead>
        <tbody>{rows}</tbody></table></div>"""


def _inventory_section(summary: dict) -> str:
    type_counts = summary.get("type_counts", {})
    rows = ""
    for rtype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        display = rtype.split("/")[-1].replace("-", " ").title()
        rows += f"<tr><td>{display}</td><td class='mono'>{rtype}</td><td class='num'>{count:,}</td></tr>"

    _HEADERS = ["Resource Type", "Full Type", "Count"]
    filter_row = "".join(
        f'<th style="padding:.2rem .4rem;background:#e8f4f8">'
        f'<input class="filter-input" data-tbl="tbl-inventory" placeholder="⌕ {h}..." '
        f'oninput="filterCol(this,\'tbl-inventory\',{i})"></th>'
        for i, h in enumerate(_HEADERS)
    )
    hdr_row = "".join(f"<th>{h}</th>" for h in _HEADERS)
    return f"""<div class="table-scroll"><table class="dtable" id="tbl-inventory">
        <thead><tr>{hdr_row}</tr><tr class="filter-row">{filter_row}</tr></thead>
        <tbody>{rows}</tbody></table></div>"""


# Max WAF rows rendered into the HTML DOM per pillar; the remainder is available in
# the Excel export. Rendered rows are revealed progressively (see data-paginate below).
_WAF_MAX_ROWS = 300


def _waf_section(waf_findings: dict) -> str:
    tabs = '<div class="tab-bar">'
    contents = ""

    for pillar in WAF_PILLARS:
        recs = waf_findings.get(pillar, [])
        count = len(recs)
        icon = WAF_ICONS.get(pillar, "")
        color = WAF_COLORS.get(pillar, "#2E86AB")
        impact_counts = Counter((r.get("impact") or "Unknown") for r in recs)
        impacts_txt = (
            f"High: {impact_counts.get('High', 0):,}, "
            f"Medium: {impact_counts.get('Medium', 0):,}, "
            f"Low: {impact_counts.get('Low', 0):,}"
        )

        tabs += (
            f'<button class="tab-btn" id="tb-{pillar}" '
            f'onclick="showPillar(\'{pillar}\')" '
            f'style="--tc:{color}">'
            f'{icon} {pillar} <span class="tc">{count}</span></button>'
        )

        _IMPACT_ORDER = {"High": 0, "Medium": 1, "Low": 2}
        sorted_recs = sorted(recs, key=lambda x: _IMPACT_ORDER.get(x.get("impact", ""), 99))
        waf_tid = f"tbl-waf-{pillar.replace(' ', '-')}"
        waf_filter_row = (
            f'<tr class="filter-row">'
            f'<th style="padding:.2rem .4rem;background:#e8f4f8"><input class="filter-input" data-tbl="{waf_tid}" placeholder="⌕ Impact..." oninput="filterCol(this,\'{waf_tid}\',0)"></th>'
            f'<th style="padding:.2rem .4rem;background:#e8f4f8"><input class="filter-input" data-tbl="{waf_tid}" placeholder="⌕ Type..." oninput="filterCol(this,\'{waf_tid}\',1)"></th>'
            f'<th style="padding:.2rem .4rem;background:#e8f4f8"><input class="filter-input" data-tbl="{waf_tid}" placeholder="⌕ Resource..." oninput="filterCol(this,\'{waf_tid}\',2)"></th>'
            f'<th style="padding:.2rem .4rem;background:#e8f4f8"><input class="filter-input" data-tbl="{waf_tid}" placeholder="⌕ Recommendation..." oninput="filterCol(this,\'{waf_tid}\',3)"></th>'
            f'<th style="padding:.2rem .4rem;background:#e8f4f8"><input class="filter-input" data-tbl="{waf_tid}" placeholder="⌕ Subscription..." oninput="filterCol(this,\'{waf_tid}\',4)"></th>'
            f'<th style="padding:.2rem .4rem;background:#e8f4f8"><input class="filter-input" data-tbl="{waf_tid}" placeholder="⌕ RG..." oninput="filterCol(this,\'{waf_tid}\',5)"></th>'
            f'</tr>'
        )
        rows = ""
        if sorted_recs:
            for rec in sorted_recs[:_WAF_MAX_ROWS]:
                impact = rec.get("impact", "")
                ic = {"High": "#C00000", "Medium": "#FFC000", "Low": "#70AD47"}.get(impact, "#ccc")
                rows += (
                    f'<tr><td><span style="background:{ic};color:#fff;padding:.1rem .4rem;'
                    f'border-radius:8px;font-size:.72rem;font-weight:700;white-space:nowrap">{impact}</span></td>'
                    f'<td>{rec.get("impactedField","")}</td>'
                    f'<td>{str(rec.get("impactedValue",""))[:80]}</td>'
                    f'<td>{rec.get("shortDescription","")[:120]}</td>'
                    f'<td>{rec.get("subscriptionId","")}</td>'
                    f'<td>{rec.get("resourceGroup","")}</td></tr>'
                )
            if len(sorted_recs) > _WAF_MAX_ROWS:
                rows += (
                    f'<tr class="pg-note"><td colspan="6" style="text-align:center;color:#888;font-style:italic;padding:.55rem;background:#fbfbfb">'
                    f'\u2139 Showing the first {_WAF_MAX_ROWS:,} of {len(sorted_recs):,} {pillar} recommendations. '
                    f'For the complete list, use the <strong>Excel export</strong> (AllResources / per-type sheets).</td></tr>'
                )
        else:
            rows = f'<tr><td colspan="6" class="no-data">No {pillar} recommendations found.</td></tr>'

        contents += (
            f'<div id="waf-{pillar}" class="tab-content" style="display:none">'
            f'<div class="pillar-hdr" style="border-left:5px solid {color}">'
            f'<strong style="color:{color}">{icon} {pillar}</strong>'
            f' — {count} Azure Advisor recommendation(s) '
            f'<span style="margin-left:.5rem;color:#555;font-size:.79rem">({impacts_txt})</span></div>'
            f'<div class="table-scroll"><table class="dtable" id="{waf_tid}" data-paginate="30" data-page-step="30">'
            f'<thead><tr><th>Impact</th><th>Resource Type</th><th>Resource</th>'
            f'<th>Recommendation</th><th>Subscription</th><th>RG</th></tr>'
            f'{waf_filter_row}</thead>'
            f'<tbody>{rows}</tbody></table></div></div>'
        )

    tabs += '</div>'
    return tabs + contents


# CAF Security Design reference used across security observations below:
_CAF_SECURITY_URL = (
    "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/"
    "ready/landing-zone/design-area/security"
)


def _landing_zone_section(resources_by_type: dict, summary: dict) -> str:
    """
    Generate Landing Zone observations with Cloud Adoption Framework (CAF) alignment.

    Evaluates infrastructure against 5 CAF pillars:
    - Security: Identity, access, network security
      Reference: https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/design-area/security
    - Cost Management: Resource optimization, tagging, governance
    - Operational Excellence: Monitoring, automation, compliance
    - Performance Efficiency: Scalability, resource sizing
    - Reliability: Redundancy, backup, availability
    """
    obs = []

    # ── GOVERNANCE & STRUCTURE ──
    mg = resources_by_type.get("microsoft.management/managementgroups", [])
    if mg:
        obs.append(("info", f"✓ Management Group hierarchy detected ({len(mg)} groups). Enterprise governance structure is in place."))
    else:
        obs.append(("warn", "⚠ No Management Groups detected. Consider implementing a hierarchical structure for policy and RBAC delegation per CAF governance model."))

    # ── IDENTITY & ACCESS (CAF Security Pillar) ──
    entra_ids = len(resources_by_type.get("microsoft.aad/applications", [])) + len(resources_by_type.get("microsoft.aad/servicePrincipals", []))
    if entra_ids > 0:
        obs.append(("info", f'✓ {entra_ids} Entra ID identities detected. Validate conditional access policies and MFA enforcement per '
                           f'<a href="{_CAF_SECURITY_URL}" target="_blank">CAF Security design area</a> — Identity &amp; Access Management.'))
    else:
        obs.append(("warn", f'⚠ Minimal Entra ID configuration detected. Ensure strong authentication and identity governance align with '
                           f'<a href="{_CAF_SECURITY_URL}" target="_blank">CAF Security design area</a> — Identity &amp; Access Management.'))

    # ── NETWORK SECURITY (CAF Security Pillar) ──
    vnets = len(resources_by_type.get("microsoft.network/virtualnetworks", []))
    nsgs = len(resources_by_type.get("microsoft.network/networksecuritygroups", []))
    if vnets:
        obs.append(("info", f'✓ {vnets} VNet(s) with {nsgs} NSGs detected. Validate network segmentation and micro-segmentation against '
                           f'<a href="{_CAF_SECURITY_URL}" target="_blank">CAF Security design area</a> — Network topology &amp; connectivity.'))
    else:
        obs.append(("warn", f'⚠ No Virtual Networks detected. If using IaaS workloads, implement proper network segmentation per '
                           f'<a href="{_CAF_SECURITY_URL}" target="_blank">CAF Security design area</a> — Network topology &amp; connectivity.'))

    # ── PRIVATE CONNECTIVITY (CAF Security + Network Design) ──
    pdns = len(resources_by_type.get("microsoft.network/privatednszones", []))
    priveps = len(resources_by_type.get("microsoft.network/privateendpoints", []))
    if pdns or priveps:
        obs.append(("info", f'✓ Private endpoints ({priveps}) and DNS zones ({pdns}) configured. Private connectivity aligns with '
                           f'<a href="{_CAF_SECURITY_URL}" target="_blank">CAF Security design area</a> — Network isolation &amp; private access.'))
    else:
        obs.append(("warn", f'⚠ No private endpoints or DNS zones detected. For PaaS services, enable private endpoints with private DNS per '
                           f'<a href="{_CAF_SECURITY_URL}" target="_blank">CAF Security design area</a> — Network isolation &amp; private access.'))

    # ── LOGGING & MONITORING (CAF Operational Excellence) ──
    law = len(resources_by_type.get("microsoft.operationalinsights/workspaces", []))
    app_insights = len(resources_by_type.get("microsoft.insights/components", []))
    if law > 0:
        obs.append(("info", f"✓ {law} Log Analytics Workspace(s) configured. Verify centralized vs. federated logging aligns with your Landing Zone operational model (CAF operational excellence)."))
    else:
        obs.append(("warn", "⚠ No Log Analytics Workspaces detected. Implement centralized logging for auditing, compliance, and operational insights per CAF operational excellence pillar."))

    if app_insights > 0:
        obs.append(("info", f"✓ {app_insights} Application Insights instance(s) active. Monitor application performance and diagnostics per CAF observability recommendations."))

    # ── BACKUP & DISASTER RECOVERY (CAF Reliability Pillar) ──
    backup_vaults = len(resources_by_type.get("microsoft.recoveryservices/vaults", []))
    if backup_vaults > 0:
        obs.append(("info", f"✓ {backup_vaults} Recovery Services Vault(s) configured. Ensure backup/restore strategy aligns with RPO/RTO targets (CAF reliability pillar)."))
    else:
        obs.append(("warn", "⚠ No Recovery Services Vaults detected. For critical workloads, implement backup and disaster recovery per CAF reliability design principles."))

    # ── KEY VAULT & SECRETS MANAGEMENT (CAF Security) ──
    kv = len(resources_by_type.get("microsoft.keyvault/vaults", []))
    if kv > 0:
        obs.append(("info", f'✓ {kv} Key Vault(s) configured. Validate key/secret rotation and RBAC policies per '
                           f'<a href="{_CAF_SECURITY_URL}" target="_blank">CAF Security design area</a> — Encryption &amp; secrets management.'))
    else:
        obs.append(("warn", f'⚠ No Key Vaults detected. Implement centralized secrets management for credentials, certificates, and keys per '
                           f'<a href="{_CAF_SECURITY_URL}" target="_blank">CAF Security design area</a> — Encryption &amp; secrets management.'))

    # ── DEFENDER FOR CLOUD (CAF Security & Compliance) ──
    if summary.get("total_defender_findings", 0) > 0:
        obs.append(("warn", f'⚠ {summary.get("total_defender_findings", 0)} Defender for Cloud findings detected. Address recommendations per '
                           f'<a href="{_CAF_SECURITY_URL}" target="_blank">CAF Security design area</a> — Security posture &amp; compliance.'))
    elif not summary.get("total_defender_findings"):
        obs.append(("warn", f'⚠ Defender for Cloud data unavailable. Enable Defender and review posture per '
                           f'<a href="{_CAF_SECURITY_URL}" target="_blank">CAF Security design area</a> — Security posture &amp; compliance.'))
    else:
        obs.append(("info", f'✓ No critical Defender findings. Continue monitoring per '
                           f'<a href="{_CAF_SECURITY_URL}" target="_blank">CAF Security design area</a> — Security posture &amp; compliance.'))

    # ── COST MANAGEMENT & TAGGING (CAF Cost Management Pillar) ──
    tag_pct = summary.get("tag_coverage_pct", 0)
    if tag_pct >= 80:
        obs.append(("info", f"✓ High tag coverage ({tag_pct}%). Tagging strategy supports cost allocation, chargeback, and governance (CAF cost management pillar)."))
    elif tag_pct >= 60:
        obs.append(("warn", f"⚠ Moderate tag coverage ({tag_pct}%). Increase mandatory tagging for environment, owner, cost center via Azure Policy to enable CAF cost chargeback model."))
    else:
        obs.append(("warn", f"⚠ Low tag coverage ({tag_pct}%). Without consistent tagging, cost allocation, ownership tracking, and governance are impaired. Enforce via Azure Policy (CAF cost management)."))

    # ── POLICY COMPLIANCE (CAF Governance) ──
    non_compliant = summary.get("total_non_compliant_policies", 0)
    if non_compliant > 0:
        obs.append(("warn", f"⚠ {non_compliant} Policy compliance violations detected. Remediate to align with organizational governance standards and CAF governance policies."))
    else:
        obs.append(("info", "✓ Policy compliance healthy. Continue enforcing via Azure Policy for consistent governance across the Landing Zone."))

    # ── DEPRECATED RESOURCES (CAF Operational Excellence) ──
    deprecated = summary.get("total_deprecated", 0)
    if deprecated > 0:
        obs.append(("warn", f"⚠ {deprecated} deprecated or retiring resources detected. Plan migrations to supported alternatives to maintain supportability (CAF operational excellence)."))

    # ── HEALTH & AVAILABILITY (CAF Reliability) ──
    health_issues = summary.get("total_health_issues", 0)
    if health_issues > 0:
        obs.append(("warn", f"⚠ {health_issues} resource health issues detected. Investigate degraded resources and plan remediation to maintain SLA targets (CAF reliability pillar)."))
    else:
        obs.append(("info", "✓ No critical health issues. Monitor resource health regularly for early problem detection."))

    # ── CAF SECURITY REFERENCE BLOCK ──
    caf_ref_block = (
        f'<div style="margin-top:1.2rem;padding:.8rem 1rem;background:#f0f4f8;border-left:4px solid #2E86AB;'
        f'border-radius:4px;font-size:.85rem;color:#333;">'
        f'<strong>📖 Reference — CAF Security Design Area:</strong> '
        f'<a href="{_CAF_SECURITY_URL}" target="_blank" style="color:#2E86AB;">'
        f'Security design in Azure — Cloud Adoption Framework | Microsoft Learn</a><br>'
        f'<span style="color:#666;">Covers: identity &amp; access, network topology, encryption, '
        f'security posture, compliance, and governance controls for Azure Landing Zones.</span>'
        f'</div>'
    )

    legend_block = (
        '<div style="margin:.2rem 0 .8rem;padding:.6rem .8rem;background:#f8faff;border-radius:8px;font-size:.8rem;color:#445">'
        '<strong>Legend:</strong> '
        '<span style="display:inline-block;margin-left:.4rem;background:#fff8e1;border-left:4px solid #FFC000;padding:.15rem .45rem;border-radius:4px">'
        'Yellow = Attention required / gap observed</span> '
        '<span style="display:inline-block;margin-left:.35rem;background:#e8f4f8;border-left:4px solid #2E86AB;padding:.15rem .45rem;border-radius:4px">'
        'Blue = Informational / good practice detected</span>'
        '</div>'
    )

    return (
        legend_block + "".join(
            f'<div class="obs obs-{t}"> {m}</div>'
            for t, m in obs
        )
        + caf_ref_block
    )


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


def _detect_modernization_signals(resources_by_type: dict) -> List[dict]:
    """
    Infer modernization & technology adoption signals from resource types present.
    INFERRED ASSESSMENT — not based on a discrete Azure API signal.

    Resource types are the official Azure Resource Provider namespaces as
    enumerated by Azure Resource Graph. References:
      - Azure resource providers: https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/resource-providers-and-types
      - Azure AI Foundry (ML/workspaces): https://learn.microsoft.com/en-us/azure/machine-learning/
      - Microsoft Fabric capacities: https://learn.microsoft.com/en-us/fabric/admin/capacity-settings
      - Cosmos DB: https://learn.microsoft.com/en-us/azure/cosmos-db/
      - SQL Managed Instance: https://learn.microsoft.com/en-us/azure/azure-sql/managed-instance/
      - PostgreSQL/MySQL Flexible Server: https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/
      - Azure Cache for Redis: https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/
    """
    signals = []

    # Each entry: (display_name, [resource_types_lowercase], message)
    # Resource types match exactly what Azure Resource Graph returns in the 'type' field.
    signal_patterns = [
        (
            "AI/ML & Azure AI Foundry",
            [
                "microsoft.cognitiveservices/accounts",        # Azure AI Services, OpenAI, Speech, Vision…
                "microsoft.machinelearningservices/workspaces", # Azure ML + AI Foundry hubs/projects (same RP)
                "microsoft.botservice/botservices",             # Azure Bot Service
            ],
            "AI/ML & Azure AI Foundry resources detected (Cognitive Services, Azure ML, AI Foundry)",
        ),
        (
            "Microsoft Fabric",
            [
                "microsoft.fabric/capacities",  # Microsoft Fabric F-SKU capacity
            ],
            "Microsoft Fabric capacity detected — unified analytics platform",
        ),
        (
            "Containerization",
            [
                "microsoft.containerregistry/registries",       # Azure Container Registry
                "microsoft.containerservice/managedclusters",   # Azure Kubernetes Service (AKS)
                "microsoft.app/containerapps",                  # Azure Container Apps
                "microsoft.containerinstance/containergroups",  # Azure Container Instances
            ],
            "Container platforms in use (ACR, AKS, Container Apps, Container Instances)",
        ),
        (
            "Serverless & Integration",
            [
                "microsoft.logic/workflows",        # Azure Logic Apps
                "microsoft.eventgrid/namespaces",   # Azure Event Grid (namespaces tier)
                "microsoft.eventgrid/topics",       # Azure Event Grid (topics)
            ],
            "Serverless & integration workloads detected (Logic Apps, Event Grid)",
        ),
        (
            "Data & Analytics Platform",
            [
                "microsoft.databricks/workspaces",        # Azure Databricks
                "microsoft.synapse/workspaces",            # Azure Synapse Analytics
                "microsoft.datafactory/factories",         # Azure Data Factory
                "microsoft.datalakestore/accounts",        # Azure Data Lake Store Gen1
                "microsoft.analysisservices/servers",      # Azure Analysis Services
            ],
            "Modern data & analytics platform (Databricks, Synapse, Data Factory)",
        ),
        (
            "Real-time Streaming",
            [
                "microsoft.eventhub/namespaces",            # Azure Event Hubs
                "microsoft.streamanalytics/streamingjobs",  # Azure Stream Analytics
                "microsoft.kusto/clusters",                 # Azure Data Explorer (Kusto)
            ],
            "Event streaming infrastructure (Event Hubs, Stream Analytics, Data Explorer)",
        ),
        (
            "Modern PaaS Databases",
            [
                "microsoft.documentdb/databaseaccounts",       # Azure Cosmos DB (all APIs)
                "microsoft.sql/managedinstances",              # Azure SQL Managed Instance
                "microsoft.dbforpostgresql/flexibleservers",   # Azure Database for PostgreSQL Flexible Server
                "microsoft.dbformysql/flexibleservers",        # Azure Database for MySQL Flexible Server
                "microsoft.cache/redis",                       # Azure Cache for Redis
                "microsoft.cache/redisenterprise",             # Azure Cache for Redis Enterprise
            ],
            "Modern PaaS databases detected (Cosmos DB, SQL MI, PostgreSQL/MySQL Flexible, Redis)",
        ),
        (
            "API & Integration Platform",
            [
                "microsoft.apimanagement/service",   # Azure API Management
                "microsoft.apicenter/services",      # Azure API Center
                "microsoft.servicebus/namespaces",   # Azure Service Bus
            ],
            "API & integration platform (API Management, API Center, Service Bus)",
        ),
    ]

    for _name, resource_types, message in signal_patterns:
        count = sum(
            len(resources_by_type.get(rt, []))
            for rt in resource_types
        )
        if count > 0:
            signals.append({"message": message, "count": count})

    return signals


def _zero_trust_section(misconfig_findings: list, resources_by_type: dict, summary: dict) -> str:
    """
    Build Zero Trust security posture analysis section (Option B — dedicated section).
    Groups misconfiguration findings by Zero Trust principle.
    References:
    - https://learn.microsoft.com/en-us/azure/security/fundamentals/zero-trust
    - https://learn.microsoft.com/en-us/azure/security/fundamentals/overview
    - https://learn.microsoft.com/en-us/azure/security/fundamentals/end-to-end
    """
    _ZT = {
        "Verify Explicitly": {
            "rules": {"STG-001", "STG-003", "APP-001", "APP-002", "APP-003", "SQL-002", "REDIS-001", "REDIS-002"},
            "desc": ("Every request must be authenticated, authorized, and validated. "
                     "These findings indicate resources accepting unencrypted or weakly-authenticated connections."),
            "icon": "\U0001f510", "color": "#1F4E79", "bg": "#e8f0fe",
        },
        "Use Least Privilege": {
            "rules": {"KV-001", "KV-002", "AKS-001"},
            "desc": ("Limit access with just-in-time and just-enough-access controls. "
                     "These findings indicate missing RBAC or data protection controls."),
            "icon": "\U0001f511", "color": "#7030A0", "bg": "#f3e8ff",
        },
        "Assume Breach": {
            "rules": {"STG-002", "STG-004", "SQL-001", "KV-003", "COSMOS-001", "REDIS-003", "PG-001", "MYSQL-001"},
            "desc": ("Minimize blast radius — segment access and reduce public exposure. "
                     "These findings indicate resources exposed to the public internet."),
            "icon": "\U0001f3f9", "color": "#C00000", "bg": "#fde8e8",
        },
    }

    grouped: dict = {p: [] for p in _ZT}
    for f in misconfig_findings:
        rid = f.get("ruleId", "")
        for principle, cfg in _ZT.items():
            if rid in cfg["rules"]:
                grouped[principle].append(f)
                break

    tiles = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:1rem;margin:1rem 0">'
    for principle, cfg in _ZT.items():
        findings = grouped[principle]
        count = len(findings)
        color = cfg["color"]
        bg = cfg["bg"]
        sev_counts = Counter((f.get("severity") or "Unknown") for f in findings)
        sev_badges = _kpi_row_from_counter(
            Counter({k: sev_counts.get(k, 0) for k in ["Critical", "High", "Medium", "Low"] if sev_counts.get(k, 0) > 0}),
            color_map={"Critical": "#7b0000", "High": "#C00000", "Medium": "#B8860B", "Low": "#2E7D32"},
        )
        grouped_counts = Counter(
            (
                (f.get("severity") or "Unknown"),
                (f.get("resourceType") or "Unknown"),
                (f.get("title") or "Unknown"),
            )
            for f in findings
        )
        top_groups = sorted(grouped_counts.items(), key=lambda x: x[1], reverse=True)
        summary_rows = "".join(
            f'<li style="font-size:.77rem;padding:.18rem 0;border-bottom:1px solid rgba(0,0,0,.05)">'
            f'<span style="color:{color};font-weight:700">{key[0]}</span> - '
            f'{key[1].split("/")[-1]} - {key[2]}: <strong>{val:,}</strong></li>'
            for key, val in top_groups[:5]
        )
        details_rows = "".join(
            f'<tr><td>{key[0]}</td><td>{key[1]}</td><td>{key[2]}</td><td class="num">{val:,}</td></tr>'
            for key, val in top_groups
        ) or '<tr><td colspan="4" class="no-data">No detailed findings.</td></tr>'
        detail_id = f'zt-{principle.lower().replace(" ", "-")}'
        if not findings:
            summary_rows = '<li style="font-size:.78rem;color:#70AD47;padding:.25rem 0">\u2713 No findings for this principle</li>'
            details_rows = '<tr><td colspan="4" class="no-data">No detailed findings.</td></tr>'
        tiles += (
            f'<div style="background:{bg};border-radius:10px;padding:1.2rem;border-top:4px solid {color}">'
            f'<div style="display:flex;align-items:center;gap:.6rem;margin-bottom:.6rem">'
            f'<span style="font-size:1.4rem">{cfg["icon"]}</span>'
            f'<div><div style="font-weight:700;color:{color};font-size:.93rem">{principle}</div>'
            f'<div style="font-size:.74rem;color:#555;line-height:1.4">{cfg["desc"]}</div></div></div>'
            f'<div style="text-align:center;background:rgba(0,0,0,.05);border-radius:6px;padding:.4rem;margin-bottom:.7rem">'
            f'<span style="font-size:1.7rem;font-weight:700;color:{color}">{count}</span>'
            f'<span style="font-size:.73rem;color:#666;display:block">Findings</span></div>'
            f'<div style="margin-bottom:.4rem"><strong style="font-size:.78rem">By Severity:</strong> {sev_badges}</div>'
            f'<ul style="list-style:none;padding:0;margin:0">{summary_rows}</ul>'
            f'<details style="margin-top:.45rem" id="{detail_id}">'
            f'<summary style="cursor:pointer;font-size:.78rem;color:{color}">Show detailed table</summary>'
            f'<div class="table-scroll" style="margin-top:.45rem"><table class="dtable">'
            f'<thead><tr><th>Severity</th><th>Resource Type</th><th>Finding</th><th class="num">Count</th></tr></thead>'
            f'<tbody>{details_rows}</tbody></table></div></details></div>'
        )
    tiles += '</div>'

    public_ips = len(resources_by_type.get("microsoft.network/publicipaddresses", []))
    private_eps = len(resources_by_type.get("microsoft.network/privateendpoints", []))
    private_dns = len(resources_by_type.get("microsoft.network/privatednszones", []))
    exp_msg = (
        "\u26a0 Public IPs outnumber private endpoints \u2014 review each association for Zero Trust compliance."
        if public_ips > private_eps
        else "\u2713 Private endpoints \u2265 public IPs \u2014 good network isolation posture."
    )
    exp_color = "#C00000" if public_ips > private_eps else "#70AD47"
    public_ip_rows = "".join(
        f'<tr><td>{r.get("name", "")}</td><td>{r.get("type", "")}</td><td>{r.get("location", "")}</td>'
        f'<td>{(r.get("sku") or {}).get("name", "") if isinstance(r.get("sku"), dict) else r.get("sku", "")}</td>'
        f'<td>{r.get("subscriptionId", "")}</td><td>{r.get("resourceGroup", "")}</td></tr>'
        for r in resources_by_type.get("microsoft.network/publicipaddresses", [])[:200]
    )
    pe_rows = "".join(
        f'<tr><td>{r.get("name", "")}</td><td>{r.get("type", "")}</td><td>{r.get("location", "")}</td>'
        f'<td>{r.get("subscriptionId", "")}</td><td>{r.get("resourceGroup", "")}</td></tr>'
        for r in resources_by_type.get("microsoft.network/privateendpoints", [])[:200]
    )
    network_evidence = (
        '<details style="margin-top:.55rem">'
        '<summary style="cursor:pointer;font-size:.79rem;color:#1F4E79">Show network exposure evidence</summary>'
        '<div style="margin-top:.5rem">'
        '<div style="font-size:.78rem;color:#666;margin-bottom:.25rem"><strong>Public IP resources</strong></div>'
        '<div class="table-scroll"><table class="dtable"><thead><tr><th>Name</th><th>Type</th><th>Location</th><th>SKU</th><th>Subscription</th><th>RG</th></tr></thead>'
        f'<tbody>{public_ip_rows or "<tr><td colspan=\"6\" class=\"no-data\">No public IP resources found.</td></tr>"}</tbody></table></div>'
        '<div style="font-size:.78rem;color:#666;margin:.55rem 0 .25rem"><strong>Private Endpoint resources</strong></div>'
        '<div class="table-scroll"><table class="dtable"><thead><tr><th>Name</th><th>Type</th><th>Location</th><th>Subscription</th><th>RG</th></tr></thead>'
        f'<tbody>{pe_rows or "<tr><td colspan=\"5\" class=\"no-data\">No private endpoint resources found.</td></tr>"}</tbody></table></div>'
        '</div></details>'
    )

    network_block = (
        f'<div style="margin-top:1rem;padding:.8rem 1rem;background:#f8faff;border-radius:8px;border-left:4px solid #2E86AB">'
        f'<strong style="color:#1F4E79;font-size:.88rem">Network Exposure Indicators</strong>'
        f'<div style="display:flex;flex-wrap:wrap;gap:1.2rem;margin-top:.4rem">'
        f'<span style="font-size:.82rem">\U0001f310 <strong>{public_ips}</strong> Public IP Addresses</span>'
        f'<span style="font-size:.82rem">\U0001f512 <strong>{private_eps}</strong> Private Endpoints</span>'
        f'<span style="font-size:.82rem">\U0001f4e1 <strong>{private_dns}</strong> Private DNS Zones</span>'
        f'</div>'
        f'<p style="font-size:.78rem;color:{exp_color};margin-top:.4rem">{exp_msg}</p>'
        f'{network_evidence}'
        f'</div>'
    )

    ref_block = (
        f'<div style="margin-top:1rem;padding:.7rem 1rem;background:#f0f4f8;border-left:4px solid #1F4E79;'
        f'border-radius:4px;font-size:.8rem">'
        f'<strong>\U0001f4d6 Official References:</strong> '
        f'<a href="https://learn.microsoft.com/en-us/azure/security/fundamentals/zero-trust" target="_blank" style="color:#2E86AB">Zero Trust security in Azure</a> \u00b7 '
        f'<a href="https://learn.microsoft.com/en-us/azure/security/fundamentals/overview" target="_blank" style="color:#2E86AB">Introduction to Azure security</a> \u00b7 '
        f'<a href="https://learn.microsoft.com/en-us/azure/security/fundamentals/end-to-end" target="_blank" style="color:#2E86AB">End-to-end security in Azure</a>'
        f'</div>'
    )

    total_zt = sum(len(v) for v in grouped.values())
    return (
        f'<div class="section" id="zerotrust">'
        f'<h2>\U0001f6e1 Zero Trust Security Posture <span class="cnt">{total_zt} findings</span></h2>'
        f'<p class="note">Misconfiguration findings mapped to Zero Trust principles. Zero Trust assumes no implicit trust \u2014 '
        f'every access request must be verified, least-privilege enforced, and breach containment planned. '
        f'<a href="https://learn.microsoft.com/en-us/azure/security/fundamentals/zero-trust" target="_blank">Learn more \u2192</a></p>'
        f'{tiles}'
        f'{network_block}'
        f'{ref_block}'
        f'</div>'
    )


def _compute_defender_cost_estimate(resources_by_type: dict) -> list:
    """Compute Defender for Cloud cost estimates (public list pricing × resource counts).
    NOTE: EA/MCA/CSP discounts not included.
    """
    vms = (
        len(resources_by_type.get("microsoft.compute/virtualmachines", []))
        + len(resources_by_type.get("microsoft.hybridcompute/machines", []))
    )
    storage = len(resources_by_type.get("microsoft.storage/storageaccounts", []))
    aks = len(resources_by_type.get("microsoft.containerservice/managedclusters", []))
    app_services = len([
        r for r in resources_by_type.get("microsoft.web/sites", [])
        if "function" not in r.get("kind", "").lower()
    ])
    key_vaults = len(resources_by_type.get("microsoft.keyvault/vaults", []))
    sql = (
        len(resources_by_type.get("microsoft.sql/servers", []))
        + len(resources_by_type.get("microsoft.sql/managedinstances", []))
    )
    rows = []
    if vms > 0:
        rows.append({"plan": "Defender for Servers", "unit": "VM / Arc Machine",
                     "count": vms, "p1_price": 4.95, "p1_total": round(vms * 4.95, 2),
                     "p2_price": 13.95, "p2_total": round(vms * 13.95, 2),
                     "notes": "P1: foundational. P2: full vuln mgmt + JIT access."})
    if storage > 0:
        rows.append({"plan": "Defender for Storage", "unit": "Storage Account",
                     "count": storage, "p1_price": 10.00, "p1_total": round(storage * 10.00, 2),
                     "p2_price": None, "p2_total": None,
                     "notes": "Malware scanning + sensitive data discovery."})
    if aks > 0:
        rows.append({"plan": "Defender for Containers", "unit": "AKS Cluster (est.)",
                     "count": aks, "p1_price": 7.00, "p1_total": round(aks * 7.00, 2),
                     "p2_price": None, "p2_total": None,
                     "notes": "$7/vCore/mo estimate; varies by cluster size."})
    if app_services > 0:
        rows.append({"plan": "Defender for App Service", "unit": "App Service Instance",
                     "count": app_services, "p1_price": 14.60, "p1_total": round(app_services * 14.60, 2),
                     "p2_price": None, "p2_total": None,
                     "notes": "Threat detection for web apps and APIs."})
    if key_vaults > 0:
        rows.append({"plan": "Defender for Key Vault", "unit": "Key Vault",
                     "count": key_vaults, "p1_price": 2.00, "p1_total": round(key_vaults * 2.00, 2),
                     "p2_price": None, "p2_total": None,
                     "notes": "Est. ~$0.02/10K ops; $2/vault/mo at moderate use."})
    if sql > 0:
        rows.append({"plan": "Defender for SQL", "unit": "SQL Server / MI",
                     "count": sql, "p1_price": 15.00, "p1_total": round(sql * 15.00, 2),
                     "p2_price": None, "p2_total": None,
                     "notes": "Est. $0.015/vCore/hr; $15/server at ~4 vCores avg."})
    return rows


def _build_defender_posture_section_html(
    posture_plans: list, resources_by_type: dict, subscriptions: list
) -> str:
    """
    Build the Defender for Cloud plan-posture section.

    Segregation:
      - VMs / VMSS / Arc Machines  -> individual per-resource coverage table.
      - All other workloads        -> subscription-level plan status; per-resource
        detail relies on the (more restrictive) assessments section.
    """
    if not posture_plans:
        return ""

    from collectors.defender_posture import build_servers_resource_coverage

    sub_names = {
        s.get("subscriptionId", ""): s.get("displayName", "Unknown")
        for s in (subscriptions or [])
    }

    enabled_plans = sum(1 for p in posture_plans if p.get("enabled"))
    free_plans = len(posture_plans) - enabled_plans
    subs_with_plans = len({p.get("subscriptionId", "") for p in posture_plans})

    # ── Per-resource coverage for VMs/VMSS/Arc (individual analysis) ──
    server_rows = build_servers_resource_coverage(posture_plans, resources_by_type)
    servers_total = len(server_rows)
    servers_covered = sum(1 for r in server_rows if r.get("covered"))

    kpi_bar = (
        f'<div style="display:flex;gap:1.2rem;margin:.8rem 0;flex-wrap:wrap">'
        f'<div style="background:#e8f5e9;border-radius:10px;padding:.8rem 1.4rem;text-align:center;min-width:120px">'
        f'<div style="font-size:1.8rem;font-weight:700;color:#388E3C">{enabled_plans}</div>'
        f'<div style="font-size:.78rem;color:#777;text-transform:uppercase;font-weight:600">Plans Enabled</div></div>'
        f'<div style="background:#fde8e8;border-radius:10px;padding:.8rem 1.4rem;text-align:center;min-width:120px">'
        f'<div style="font-size:1.8rem;font-weight:700;color:#C00000">{free_plans}</div>'
        f'<div style="font-size:.78rem;color:#777;text-transform:uppercase;font-weight:600">Plans Free / Off</div></div>'
        f'<div style="background:#e8f0fe;border-radius:10px;padding:.8rem 1.4rem;text-align:center;min-width:120px">'
        f'<div style="font-size:1.8rem;font-weight:700;color:#1F4E79">{subs_with_plans}</div>'
        f'<div style="font-size:.78rem;color:#777;text-transform:uppercase;font-weight:600">Subscriptions</div></div>'
        f'<div style="background:#fff3cd;border-radius:10px;padding:.8rem 1.4rem;text-align:center;min-width:120px">'
        f'<div style="font-size:1.8rem;font-weight:700;color:#B8860B">{servers_covered}/{servers_total}</div>'
        f'<div style="font-size:.78rem;color:#777;text-transform:uppercase;font-weight:600">Servers Covered</div></div>'
        f'</div>'
    )

    # ── Plan table (subscription-level) ──
    _sorted_plans = sorted(
        posture_plans,
        key=lambda p: (sub_names.get(p.get("subscriptionId", ""), p.get("subscriptionId", "")),
                       p.get("planDisplayName", "")),
    )
    plan_table_rows = ""
    for p in _sorted_plans:
        sub_id = p.get("subscriptionId", "")
        enabled = p.get("enabled")
        tier_badge = (
            '<span style="background:#e8f5e9;color:#2e7d32;padding:.1rem .5rem;border-radius:6px;font-weight:600;font-size:.78rem">Standard</span>'
            if enabled else
            '<span style="background:#fde8e8;color:#c00000;padding:.1rem .5rem;border-radius:6px;font-weight:600;font-size:.78rem">Free</span>'
        )
        coverage = _esc(p.get("resourcesCoverageStatus", "") or "\u2014")
        sub_plan = _esc(p.get("subPlan", "") or "\u2014")
        exts = p.get("enabledExtensions", []) or []
        exts_str = _esc(", ".join(exts)) if exts else "\u2014"
        plan_table_rows += (
            f'<tr><td>{_esc(sub_names.get(sub_id, "Unknown"))}</td>'
            f'<td style="font-size:.74rem;color:#888">{_esc(sub_id)}</td>'
            f'<td>{_esc(p.get("planDisplayName", ""))}</td>'
            f'<td>{tier_badge}</td>'
            f'<td>{sub_plan}</td>'
            f'<td>{coverage}</td>'
            f'<td style="font-size:.76rem;color:#666">{exts_str}</td></tr>'
        )

    plan_filter_row = (
        '<tr class="filter-row">'
        + "".join(
            f'<th style="padding:.2rem .4rem;background:#e8f4f8"><input class="filter-input" '
            f'data-tbl="tbl-defender-plans" placeholder="&#8981; {lbl}..." '
            f'oninput="filterCol(this,\'tbl-defender-plans\',{i})"></th>'
            for i, lbl in enumerate(
                ["Subscription", "Sub ID", "Plan", "Tier", "Sub-plan", "Coverage", "Extensions"]
            )
        )
        + '</tr>'
    )
    plan_table = (
        f'<div style="margin:1.2rem 0">'
        f'<strong style="font-size:.9rem;color:#1F4E79">Defender Plans by Subscription</strong>'
        f'<p class="note" style="margin:.3rem 0 .5rem">Subscription-level plan enablement '
        f'(<code>Microsoft.Security/pricings</code>). For non-server workloads, status is '
        f'reported at the subscription scope only.</p>'
        f'<div class="table-scroll"><table class="dtable" id="tbl-defender-plans">'
        f'<thead><tr><th>Subscription</th><th>Subscription ID</th><th>Defender Plan</th>'
        f'<th>Tier</th><th>Sub-plan</th><th>Coverage</th><th>Enabled Extensions</th></tr>'
        f'{plan_filter_row}</thead>'
        f'<tbody>{plan_table_rows}</tbody></table></div></div>'
    )

    # ── Per-resource servers table (individual analysis) ──
    servers_section = ""
    if server_rows:
        _server_sorted = sorted(server_rows, key=lambda r: (not r.get("covered"), r.get("name", "")))
        srv_rows = ""
        for r in _server_sorted:
            covered = r.get("covered")
            status_badge = (
                '<span style="background:#e8f5e9;color:#2e7d32;padding:.1rem .5rem;border-radius:6px;font-weight:600;font-size:.78rem">Covered</span>'
                if covered else
                '<span style="background:#fde8e8;color:#c00000;padding:.1rem .5rem;border-radius:6px;font-weight:600;font-size:.78rem">Not covered</span>'
            )
            srv_rows += (
                f'<tr><td>{_esc(r.get("name", ""))}</td>'
                f'<td style="font-size:.76rem">{_esc(r.get("type", "").split("/")[-1])}</td>'
                f'<td>{status_badge}</td>'
                f'<td>{_esc(r.get("serversPlanTier", ""))}</td>'
                f'<td>{_esc(r.get("subPlan", "") or "\u2014")}</td>'
                f'<td>{_esc(r.get("location", ""))}</td>'
                f'<td>{_esc(r.get("resourceGroup", ""))}</td>'
                f'<td>{_esc(sub_names.get(r.get("subscriptionId", ""), r.get("subscriptionId", "")))}</td></tr>'
            )
        servers_section = (
            f'<div style="margin-top:1.5rem">'
            f'<strong style="font-size:.9rem;color:#1F4E79">\U0001f5a5\ufe0f Defender for Servers \u2014 Individual Resource Coverage '
            f'<span class="cnt">{servers_total}</span></strong>'
            f'<p class="note" style="margin:.3rem 0 .6rem">Per-resource view for VMs, VMSS and Arc Machines '
            f'(the only workloads with resource-level coverage in the pricings API). '
            f'Coverage is derived from the Defender for Servers plan tier of each subscription; '
            f'where coverage status is <em>PartiallyCovered</em>, individual VM-level overrides may apply.</p>'
            f'<div class="table-scroll"><table class="dtable">'
            f'<thead><tr><th>Resource</th><th>Type</th><th>Status</th><th>Plan Tier</th>'
            f'<th>Sub-plan</th><th>Location</th><th>RG</th><th>Subscription</th></tr></thead>'
            f'<tbody>{srv_rows}</tbody></table></div></div>'
        )

    segregation_note = (
        f'<div style="margin:.2rem 0 .8rem;padding:.6rem .8rem;background:#f0f4f8;border-left:4px solid #2E86AB;border-radius:6px;font-size:.8rem;color:#445">'
        f'<strong>\U0001f4dd Analysis scope:</strong> VMs / VMSS / Arc Machines are analysed '
        f'<strong>individually (per-resource)</strong> via the pricings API. All other workloads '
        f'(Storage, SQL, Containers, Key Vault, App Service, etc.) are reported at the '
        f'<strong>subscription level</strong>; their per-resource posture relies on the more '
        f'restrictive <em>Defender Assessments</em> section below (requires <code>Security Reader</code>). '
        f'This split is an official limitation of <code>Microsoft.Security/pricings</code>.'
        f'</div>'
    )

    gap_section = _build_defender_gap_section_html(posture_plans, resources_by_type)

    return (
        f'<div class="section" id="defender-posture">'
        f'<h2>\U0001f6e1\ufe0f Defender for Cloud \u2014 Plan Posture <span class="cnt">{len(posture_plans)}</span></h2>'
        f'<p class="note">Per-subscription Defender plan enablement via '
        f'<code>Microsoft.Security/pricings</code>. Requires only <code>Reader</code> RBAC.</p>'
        f'{segregation_note}'
        f'{kpi_bar}'
        f'{plan_table}'
        f'{servers_section}'
        f'{gap_section}'
        f'</div>'
    )


def _build_defender_gap_section_html(posture_plans: list, resources_by_type: dict) -> str:
    """
    B2 — Coverage gap & cost-to-protect: cross-references inventory with real
    plan posture to show how many billable units are unprotected per plan and
    the estimated monthly cost to close the gap.
    """
    from collectors.defender_pricing import compute_coverage_gap, total_gap_monthly_cost, pricing_source_label

    gap_rows = compute_coverage_gap(resources_by_type, posture_plans)
    if not gap_rows:
        return ""
    price_src = pricing_source_label(gap_rows)

    total_units = sum(r["total_units"] for r in gap_rows)
    total_unprotected = sum(r["unprotected_units"] for r in gap_rows)
    total_protected = total_units - total_unprotected
    gap_cost = total_gap_monthly_cost(gap_rows)
    pct_protected = round(total_protected / total_units * 100, 1) if total_units else 0.0

    table_rows = ""
    for r in gap_rows:
        price_str = f'${r["price"]:.2f}' if r["priceable"] else "Usage-based"
        gap_str = f'<strong>${r["gap_monthly_cost"]:.2f}</strong>' if r["priceable"] else "\u2014"
        unprotected_color = "#C00000" if r["unprotected_units"] > 0 else "#388E3C"
        table_rows += (
            f'<tr><td>{_esc(r["plan"])}</td><td>{_esc(r["unit"])}</td>'
            f'<td class="num">{r["total_units"]}</td>'
            f'<td class="num" style="color:#388E3C">{r["protected_units"]}</td>'
            f'<td class="num" style="color:{unprotected_color};font-weight:600">{r["unprotected_units"]}</td>'
            f'<td class="num">{price_str}</td>'
            f'<td class="num">{gap_str}</td>'
            f'<td style="font-size:.76rem;color:#777">{_esc(r["notes"])}</td></tr>'
        )
    table_rows += (
        f'<tr style="background:#e8f0fe;font-weight:700">'
        f'<td colspan="2">TOTAL</td>'
        f'<td class="num">{total_units}</td>'
        f'<td class="num" style="color:#388E3C">{total_protected}</td>'
        f'<td class="num" style="color:#C00000">{total_unprotected}</td>'
        f'<td></td><td class="num">${gap_cost:.2f}</td>'
        f'<td style="font-size:.76rem;color:#666">Monthly cost to protect all unprotected units (prices: {_esc(price_src)}).</td></tr>'
    )

    return (
        f'<div style="margin-top:1.5rem">'
        f'<strong style="font-size:.9rem;color:#1F4E79">\U0001f4b0 Coverage Gap &amp; Cost to Protect</strong>'
        f'<p class="note" style="margin:.3rem 0 .6rem">Billable units cross-referenced with the real plan posture. '
        f'<strong>{total_unprotected:,}</strong> of <strong>{total_units:,}</strong> units are currently '
        f'<strong>unprotected</strong> ({pct_protected}% protected). Estimated monthly cost to close the gap: '
        f'<strong>${gap_cost:,.2f}</strong> (prices: {_esc(price_src)} \u2014 EA/MCA/CSP discounts and usage-based plans not included).</p>'
        f'<div class="table-scroll"><table class="dtable">'
        f'<thead><tr><th>Plan</th><th>Billable Unit</th><th class="num">Total</th>'
        f'<th class="num">Protected</th><th class="num">Unprotected (gap)</th>'
        f'<th class="num">$/Unit/Mo</th><th class="num">Gap Monthly Cost</th><th>Notes</th></tr></thead>'
        f'<tbody>{table_rows}</tbody></table></div></div>'
    )


def _build_defender_section_html(defender_data: list, resources_by_type: dict) -> str:
    """Build the full Defender for Cloud section with severity/category breakdown and cost estimate."""
    if not defender_data:
        return ""

    sev_counts = Counter(d.get("severity", "Unknown") for d in defender_data)
    high = sev_counts.get("High", 0)
    medium = sev_counts.get("Medium", 0)
    low = sev_counts.get("Low", 0)

    cat_counts = Counter((d.get("category") or "Unknown") for d in defender_data)
    cat_rows = "".join(
        f'<tr><td>{cat}</td><td class="num">{cnt}</td></tr>'
        for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1])
    )
    resource_ids = set()
    scope_only = 0
    for d in defender_data:
        rid = (d.get("resourceDetails") or "").strip()
        if not rid:
            continue
        if "/providers/" in rid and "/Microsoft.Security/assessments" not in rid:
            resource_ids.add(rid)
        else:
            scope_only += 1
    resources_affected = len(resource_ids)
    unknown_categories = cat_counts.get("Unknown", 0)

    kpi_bar = (
        f'<div style="display:flex;gap:1.2rem;margin:.8rem 0;flex-wrap:wrap">'
        f'<div style="background:#fde8e8;border-radius:10px;padding:.8rem 1.4rem;text-align:center;min-width:110px">'
        f'<div style="font-size:1.8rem;font-weight:700;color:#C00000">{high}</div>'
        f'<div style="font-size:.78rem;color:#777;text-transform:uppercase;font-weight:600">High</div></div>'
        f'<div style="background:#fff3cd;border-radius:10px;padding:.8rem 1.4rem;text-align:center;min-width:110px">'
        f'<div style="font-size:1.8rem;font-weight:700;color:#B8860B">{medium}</div>'
        f'<div style="font-size:.78rem;color:#777;text-transform:uppercase;font-weight:600">Medium</div></div>'
        f'<div style="background:#e8f5e9;border-radius:10px;padding:.8rem 1.4rem;text-align:center;min-width:110px">'
        f'<div style="font-size:1.8rem;font-weight:700;color:#388E3C">{low}</div>'
        f'<div style="font-size:.78rem;color:#777;text-transform:uppercase;font-weight:600">Low</div></div>'
        f'<div style="background:#e8f0fe;border-radius:10px;padding:.8rem 1.4rem;text-align:center;min-width:110px">'
        f'<div style="font-size:1.8rem;font-weight:700;color:#1F4E79">{resources_affected}</div>'
        f'<div style="font-size:.78rem;color:#777;text-transform:uppercase;font-weight:600">Resources Affected</div></div>'
        f'</div>'
    )

    _DEF_SEV_ORDER = {"High": 0, "Medium": 1, "Low": 2}
    sorted_defender_data = sorted(defender_data, key=lambda x: _DEF_SEV_ORDER.get(x.get("severity", ""), 99))
    def_rows = _table_section(sorted_defender_data, [
        ("displayName", "Assessment"), ("severity", "Severity"),
        ("statusCode", "Status"), ("category", "Category"),
        ("implementationEffort", "Effort"), ("resourceDetails", "Resource"),
        ("subscriptionId", "Subscription"), ("resourceGroup", "RG"),
        ("remediationDescription", "Remediation"),
    ], table_id="tbl-defender")

    cat_table = (
        f'<div style="margin:1.2rem 0">'
        f'<strong style="font-size:.9rem;color:#1F4E79">Findings by Category</strong>'
        f'<p class="note" style="margin:.3rem 0 .5rem">'
        f'Unknown category: {unknown_categories:,}. '
        f'Fallback applied when Defender metadata.category is absent.</p>'
        f'<div class="table-scroll" style="margin-top:.5rem">'
        f'<table class="dtable"><thead><tr><th>Category</th><th class="num">Count</th></tr></thead>'
        f'<tbody>{cat_rows}</tbody></table></div></div>'
    )

    cost_rows = _compute_defender_cost_estimate(resources_by_type)
    cost_section = ""
    if cost_rows:
        p1_total_all = sum(r["p1_total"] for r in cost_rows)
        p2_total_all = sum(
            r["p2_total"] if r["p2_total"] is not None else r["p1_total"] for r in cost_rows
        )
        cost_table_rows = ""
        for r in cost_rows:
            p2_price_str = f'${r["p2_price"]:.2f}' if r["p2_price"] is not None else "N/A"
            p2_total_str = f'${r["p2_total"]:.2f}' if r["p2_total"] is not None else "\u2014"
            cost_table_rows += (
                f'<tr><td>{r["plan"]}</td><td>{r["unit"]}</td>'
                f'<td class="num">{r["count"]}</td>'
                f'<td class="num">${r["p1_price"]:.2f}</td>'
                f'<td class="num"><strong>${r["p1_total"]:.2f}</strong></td>'
                f'<td class="num">{p2_price_str}</td><td class="num">{p2_total_str}</td>'
                f'<td style="font-size:.76rem;color:#777">{r["notes"]}</td></tr>'
            )
        cost_table_rows += (
            f'<tr style="background:#e8f0fe;font-weight:700">'
            f'<td colspan="4">TOTAL MONTHLY ESTIMATE</td>'
            f'<td class="num">${p1_total_all:.2f}</td>'
            f'<td></td><td class="num">${p2_total_all:.2f}</td>'
            f'<td style="font-size:.76rem;color:#666">If all billable resources enrolled. EA/MCA discounts not included.</td></tr>'
        )
        cost_section = (
            f'<div style="margin-top:1.5rem">'
            f'<strong style="font-size:.9rem;color:#1F4E79">\U0001f4b0 Defender for Cloud Cost Estimate (Public Pricing)</strong>'
            f'<p class="note" style="margin:.3rem 0 .6rem">Estimated monthly cost if Defender plans enabled for all detected resources. '
            f'Based on public list pricing \u2014 EA/MCA/CSP discounts not included. See Excel <em>DefenderCostEstimate</em> sheet for full breakdown.</p>'
            f'<div class="table-scroll"><table class="dtable">'
            f'<thead><tr><th>Plan</th><th>Billable Unit</th><th class="num">Count</th>'
            f'<th class="num">P1 $/Unit/Mo</th><th class="num">P1 Est. Total</th>'
            f'<th class="num">P2 $/Unit/Mo</th><th class="num">P2 Est. Total</th>'
            f'<th>Notes</th></tr></thead>'
            f'<tbody>{cost_table_rows}</tbody></table></div></div>'
        )

    total = len(defender_data)
    return (
        f'<div class="section" id="defender">'
        f'<h2>\U0001f512 Defender for Cloud Assessments <span class="cnt">{total}</span></h2>'
        f'<p class="note">Unhealthy Defender for Cloud security assessments. Requires <code>Security Reader</code> RBAC role on SecurityResources.</p>'
        f'{kpi_bar}'
        f'<p class="note" style="margin-top:-.2rem">Resource mapping quality: {resources_affected:,} resource-level findings, '
        f'{scope_only:,} scope-level findings (subscription/other scope).</p>'
        f'{cat_table}'
        f'<strong style="font-size:.9rem;color:#1F4E79">All Findings</strong>'
        f'{def_rows}'
        f'{cost_section}'
        f'</div>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# HTML renderer
# ─────────────────────────────────────────────────────────────────────────────

def _mod_evidence_detail(d: dict) -> str:
    ev = d.get("evidence", {}) or {}
    m = d.get("method")
    if m == "proportion":
        return (f"modern={ev.get('modern', 0)}, legacy={ev.get('legacy', 0)}, "
                f"total={ev.get('total', 0)}")
    if m == "presence":
        fams = ev.get("families", {}) or {}
        present = ", ".join(f"{_fam_label(k)}={v}" for k, v in fams.items() if v) or "none"
        absent = ", ".join(_fam_label(k) for k, v in fams.items() if not v)
        base = f"{ev.get('present', 0)}/{ev.get('total', 0)} families present ({present})"
        return base + (f"; absent: {absent}" if absent else "")
    if m == "security":
        cov = ev.get("defender_coverage_pct")
        return (f"Defender coverage {cov if cov is not None else 'n/a'}% · "
                f"High misconfig {ev.get('high_misconfig', 0)}")
    if m == "governance":
        return (f"tags {ev.get('tag_pct')}% · policy compliance {ev.get('compliance_pct')}% · "
                f"Management Groups {ev.get('mg_count', 0)}")
    if m == "footprint":
        return (f"Microsoft {ev.get('microsoft', 0)} · Third-party {ev.get('third_party', 0)} "
                f"({ev.get('third_party_pct', 0)}%)")
    return ""


_METHOD_LABELS = {
    "proportion": "modern vs legacy proportion",
    "presence": "adoption breadth",
    "security": "security posture",
    "governance": "governance signals",
    "footprint": "publisher footprint (context)",
}

_METHOD_DESC = {
    "proportion": "share of modern vs legacy resources",
    "presence": "how many service families exist (breadth, not depth/volume)",
    "security": "Defender coverage + high-severity misconfigurations",
    "governance": "tags, policy compliance, management groups",
    "footprint": "Microsoft vs third-party publishers (context only)",
}


def _method_label(method: str) -> str:
    return _METHOD_LABELS.get(method, method or "")


_FAM_ACRONYMS = {"aks", "ai", "sql", "vm", "api", "aci", "acr", "cdn", "waf", "dns", "iot"}


_FAM_LABEL_OVERRIDES = {"openai_ai_services": "OpenAI / AI Services"}


def _fam_label(key: str) -> str:
    if key in _FAM_LABEL_OVERRIDES:
        return _FAM_LABEL_OVERRIDES[key]
    return " ".join(w.upper() if w.lower() in _FAM_ACRONYMS else w.capitalize()
                    for w in str(key).split("_"))


def _fam_checklist_html(d: dict) -> str:
    """Present/absent checklist of modern service families (presence dims only)."""
    if d.get("method") != "presence":
        return ""
    fams = (d.get("evidence", {}) or {}).get("families", {}) or {}
    if not fams:
        return ""
    items = "".join(
        f'<span class="fam {"fam-yes" if v else "fam-no"}">'
        f'{"✓" if v else "✗"} {_fam_label(k)}{f" ({v})" if v else ""}</span>'
        for k, v in fams.items()
    )
    return f'<div class="opp-fams">{items}</div>'


def _mod_band_color(score) -> str:
    if score is None:
        return "#9AA0A6"
    if score <= 33:
        return "#C00000"
    if score <= 66:
        return "#C55A11"
    return "#2E7D32"


def _signals_legend(dims: list) -> str:
    """Subtle legend below the signals table — only for the score bands, levels,
    confidences and methods actually present in the section."""
    scores = [d["score"] for d in dims if d["score"] is not None]
    bands = []
    if any(s <= 33 for s in scores):
        bands.append(("#C00000", "0–33 high opportunity"))
    if any(34 <= s <= 66 for s in scores):
        bands.append(("#C55A11", "34–66 intermediate"))
    if any(s >= 67 for s in scores):
        bands.append(("#2E7D32", "67–100 mature"))
    band_html = " ".join(
        f'<span class="lg-band" style="background:{c}"></span>{txt}' for c, txt in bands)

    levels = [lv for lv in ["Low", "Intermediate", "High", "N/A"]
              if lv in {d["level"] for d in dims}]
    confs = [c for c in ["High", "Medium", "Low"]
             if c in {d["confidence"] for d in dims}]
    methods = []
    seen = set()
    for d in dims:
        m = d["method"]
        if m in seen:
            continue
        seen.add(m)
        methods.append(f'<em>{_method_label(m)}</em> = {_METHOD_DESC.get(m, m)}')

    grps = []
    if band_html:
        grps.append(f'<span><strong>Score</strong> {band_html}</span>')
    if levels:
        grps.append(f'<span><strong>Level</strong> {" / ".join(levels)} (reflects the score band)</span>')
    if confs:
        grps.append(f'<span><strong>Confidence</strong> {" / ".join(confs)} — Low = weak / partial evidence</span>')
    if methods:
        grps.append('<span><strong>Method</strong> ' + '; '.join(methods) + '</span>')
    return '<div class="mod-tbl-legend">' + "".join(grps) + '</div>'


def _build_modernization_tech_html(assessment: dict) -> str:
    """Detailed technical modernization block, in four parts:
    1) Current environment (As-Is) KPIs + charts; 2) Modernization opportunities
    (readiness gauge + cards); 3) per-dimension evidence table; 4) expandable
    per-dimension detail. All INFERRED, evidence-backed."""
    if not assessment or not assessment.get("available"):
        return '<p class="no-data">No modernization signals available.</p>'
    import json as _json
    dims = assessment.get("dimensions", [])
    summary = assessment.get("summary", {})
    asis = summary.get("as_is", {})

    # ---- Part 1: As-Is KPI chips + charts -------------------------------
    sm = asis.get("service_model", {})
    bp = asis.get("business_pillar", {})
    sm_items = sorted(sm.get("counts", {}).items(), key=lambda x: -x[1])
    bp_items = sorted(bp.get("counts", {}).items(), key=lambda x: -x[1])[:8]
    sm_labels = _json.dumps([k for k, _ in sm_items])
    sm_values = _json.dumps([v for _, v in sm_items])
    bp_labels = _json.dumps([k for k, _ in bp_items])
    bp_values = _json.dumps([v for _, v in bp_items])
    readiness = summary.get("readiness")
    readiness_txt = "N/A" if readiness is None else f"{readiness}/100"
    total = asis.get("total_resources", 0)
    chips = [
        ("PaaS share", f"{asis.get('paas_pct', 0)}%", "#2E7D32"),
        ("IaaS share", f"{asis.get('iaas_pct', 0)}%", "#1F4E79"),
        ("Total resources", f"{total:,}", "#1F4E79"),
        ("Third-party (context)", f"{asis.get('third_party_pct', 0)}%", "#7F7F7F"),
    ]
    chips_html = "".join(
        f'<div class="mod-chip" style="border-top-color:{c}">'
        f'<div class="chip-val">{v}</div><div class="chip-lbl">{lbl}</div></div>'
        for lbl, v, c in chips
    )
    asis_html = f"""
      <details class="mod-fold" open>
      <summary class="mod-h3">1 · Current Environment (As-Is)</summary>
      <p class="note">Service model mix, business-pillar distribution, and overall modernization
        readiness (average of confidently-scored dimensions): <strong>{readiness_txt}</strong>.</p>
      <div class="mod-kpis">{chips_html}</div>
            <div class="two-col">
                <div>
                    <strong style="color:#1F4E79;font-size:.9rem">Service Model mix <span class="sm-info" title="Hybrid: cross-environment management such as Arc, VMware, or Azure Stack. Supporting Services: shared security, operations, governance, and monitoring. Other: unclassified or third-party / Marketplace resource types.">ⓘ</span></strong>
                    <details class="sm-help"><summary>What do Hybrid, Supporting Services, and Other mean?</summary><p><strong>Hybrid:</strong> Arc, VMware, Azure Stack, and cross-environment management. <strong>Supporting Services:</strong> shared security, operations, governance, and monitoring services. <strong>Other:</strong> unclassified or third-party / Marketplace resource types; not necessarily a concern. See the Excel <em>Classification</em> sheet for the resource-type breakdown.</p></details>
                    <div class="chart-box" style="margin-top:.5rem"><canvas id="modSvcChartT"></canvas></div>
                </div>
        <div><strong style="color:#1F4E79;font-size:.9rem">Resources by business pillar</strong><div class="chart-box" style="margin-top:.5rem"><canvas id="modPillarChartT"></canvas></div></div>
      </div>
      </details>"""

    # ---- Part 2: Modernization Opportunities (gauge + cards) ------------
    g_color = _mod_band_color(readiness)
    g_deg = 0 if readiness is None else round(readiness / 100 * 360)
    g_val = "N/A" if readiness is None else readiness
    gauge_html = (
        f'<div class="gauge" style="background:conic-gradient({g_color} {g_deg}deg,#e8edf3 0deg)">'
        f'<div class="gauge-inner"><div class="gauge-val" style="color:{g_color}">{g_val}</div>'
        f'<div class="gauge-cap">Modernization<br>Readiness</div></div></div>'
    )
    dim_by_id = {d["id"]: d for d in dims}
    cards = ""
    for o in summary.get("top_opportunities", []):
        d = dim_by_id.get(o["id"], {})
        score = o["score"] if o["score"] is not None else 0
        col = _mod_band_color(o["score"])
        fw = " · ".join(
            f'<a href="{f.get("url", "#")}" target="_blank">{f.get("name", "")}</a>'
            for f in d.get("framework_refs", []))
        cards += (
            f'<div class="opp-card" style="border-left-color:{col}">'
            f'<h4>{o["name"]}<span class="opp-score" style="color:{col}" title="{_mod_evidence_detail(d).replace(chr(34), chr(39))}">{o["score"] if o["score"] is not None else "N/A"}</span></h4>'
            f'<div class="opp-bar"><span style="width:{score}%;background:{col}"></span></div>'
            f'<div style="font-size:.84rem;color:#333;margin-top:.4rem">{d.get("narrative", "")}</div>'
            f'{_fam_checklist_html(d)}'
            f'<div class="opp-meta">Confidence: {o["confidence"]}'
            + (f' &middot; {fw}' if fw else "")
            + '</div></div>'
        )
    cards = cards or '<p class="no-data">No modernization opportunities identified above threshold.</p>'
    qw = summary.get("quick_wins", [])
    qw_html = ""
    if qw:
        names = ", ".join(f'{q["name"]} ({q["score"]})' for q in qw)
        qw_html = f'<div class="mod-qw">⚡ <strong>Quick wins:</strong> {names}</div>'
    opps_html = f"""
      <details class="mod-fold" open>
      <summary class="mod-h3">2 · Modernization Opportunities</summary>
      <div class="mod-legend">
        <span><i style="background:#C00000"></i>Lower score = higher opportunity (0–33)</span>
        <span><i style="background:#C55A11"></i>Intermediate (34–66)</span>
        <span><i style="background:#2E7D32"></i>Mature adoption (67–100)</span>
      </div>
      <p class="mod-breadth-note">Presence-based signals measure <strong>adoption breadth</strong> — how many distinct modern platform families are present (✓/✗ per card), <strong>not</strong> the volume or depth of any single one. Hover a score for the evidence.</p>
      <div class="mod-opps">
        <div class="mod-gauge-wrap">{gauge_html}
          <p class="gauge-note">Average of confidently-scored dimensions. Higher is more modern.</p>
        </div>
        <div class="opp-grid">{cards}</div>
      </div>
      {qw_html}
      </details>"""

    # ---- Part 3: evidence table + subtle legend -------------------------
    rows = ""
    for d in dims:
        score = "N/A" if d["score"] is None else d["score"]
        opp = ('<span style="color:#C00000;font-weight:700">YES</span>'
               if d["opportunity"] else "—")
        fw = ", ".join(
            f'<a href="{f.get("url", "#")}" target="_blank">{f.get("name", "")}</a>'
            for f in d.get("framework_refs", []))
        conf = d["confidence"]
        conf_html = (f'<span style="color:#999;font-style:italic">{conf}</span>'
                     if conf == "Low" else conf)
        rows += f"""<tr>
            <td><strong>{d['name']}</strong></td>
            <td class="num"><span style="background:{d.get('color', '#9AA0A6')};color:#fff;padding:.1rem .55rem;border-radius:8px;font-weight:700">{score}</span></td>
            <td>{d['level']}</td>
            <td>{conf_html}</td>
            <td style="font-size:.8rem;color:#666">{_method_label(d['method'])}</td>
            <td style="font-size:.86rem">{d['narrative']}</td>
            <td style="font-size:.8rem;color:#555">{_mod_evidence_detail(d)}</td>
            <td>{opp}</td>
            <td style="font-size:.78rem">{fw}</td>
        </tr>"""
    table_html = f"""
      <details class="mod-fold">
      <summary class="mod-h3">3 · Signals by Dimension</summary>
      <div class="table-scroll"><table class="dtable">
        <thead><tr><th>Dimension</th><th class="num">Score</th><th>Level</th><th>Confidence</th><th>Method</th><th>Signal (inferred)</th><th>Evidence</th><th>Opportunity</th><th>Frameworks</th></tr></thead>
        <tbody>{rows}</tbody>
      </table></div>
      {_signals_legend(dims)}
      </details>"""

    # ---- Part 4: expandable per-dimension detail ------------------------
    details = ""
    for d in dims:
        score = "N/A" if d["score"] is None else d["score"]
        opp_badge = ('<span style="color:#C00000;font-weight:700">· opportunity</span>'
                     if d["opportunity"] else "")
        fw = "".join(
            f'<li><a href="{f.get("url", "#")}" target="_blank">{f.get("name", "")}</a></li>'
            for f in d.get("framework_refs", []))
        details += f"""<details style="margin:.35rem 0;border:1px solid #e6eef7;border-radius:8px;padding:.5rem .8rem">
          <summary style="cursor:pointer;font-weight:600;color:#1F4E79">
            {d['name']} — <span style="background:{d.get('color', '#9AA0A6')};color:#fff;padding:.05rem .5rem;border-radius:8px">{score}</span>
            <span style="font-weight:400;color:#777;font-size:.82rem">({d['level']} · confidence {d['confidence']} {opp_badge})</span>
          </summary>
          <div style="margin-top:.5rem;font-size:.86rem;color:#333">
            <p style="margin-bottom:.4rem">{d['narrative']}</p>
            <p style="font-size:.8rem;color:#555"><strong>Method:</strong> {_method_label(d['method'])} &middot;
               <strong>Evidence:</strong> {_mod_evidence_detail(d)}</p>
            <p style="font-size:.8rem;color:#555;margin-top:.3rem"><strong>Reference frameworks:</strong></p>
            <ul style="margin:.2rem 0 0 1.1rem;font-size:.8rem">{fw or '<li>—</li>'}</ul>
          </div>
        </details>"""
    details_html = f"""
      <details class="mod-fold">
      <summary class="mod-h3">4 · Per-Dimension Detail</summary>
      {details}
      </details>"""

    return f"""
      <p class="note">{assessment.get('inferred_label', '')}</p>
      <p style="font-size:.9rem;color:#1F4E79;font-weight:600;margin:.4rem 0 .8rem">{summary.get('narrative', '')}</p>
      {asis_html}
      {opps_html}
      {table_html}
      {details_html}
      <script>
      (function(){{
        if(typeof Chart==='undefined')return;
        var s=document.getElementById('modSvcChartT');
        if(s)new Chart(s.getContext('2d'),{{type:'doughnut',data:{{labels:{sm_labels},datasets:[{{data:{sm_values},backgroundColor:['#1F4E79','#2E7D32','#2E86AB','#C55A11','#7F7F7F','#9AA0A6'],borderWidth:2,borderColor:'#fff'}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'right',labels:{{font:{{size:11}}}}}}}}}}}});
        var p=document.getElementById('modPillarChartT');
        if(p)new Chart(p.getContext('2d'),{{type:'bar',data:{{labels:{bp_labels},datasets:[{{label:'Count',data:{bp_values},backgroundColor:'#2E86AB',borderRadius:4}}]}},options:{{responsive:true,maintainAspectRatio:false,indexAxis:'y',plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{display:false}}}},y:{{grid:{{display:false}}}}}}}}}});
      }})();
      </script>"""


def _render_html(
    scan_date, tenant_id, tenant_name, subscriptions_list, summary,
    inventory_html, waf_html, policy_html, policy_summary_html, misconfig_html,
    health_html, deprecated_html, lz_html,
    defender_section, zerotrust_html, arc_section, modernization_detail_html, region_summary,
    sub_labels, sub_values, sev_labels, sev_values,
    has_defender, has_arc,
    policy_count, misconfig_count, health_count,
    deprecated_count, advisor_count,
    warnings_html="",
) -> str:
    kpi = summary
    def_nav = '<a href="#defender">🔒 Defender for Cloud</a>' if has_defender else ""
    arc_nav = '<a href="#arc">🌐 Azure Arc</a>' if has_arc else ""

    # Item 3: Regional distribution table
    region_rows = "".join(
        f"""<tr>
            <td><strong>{r['region']}</strong></td>
            <td class="num">{r['count']:,}</td>
            <td class="num">{r['percentage']}%</td>
        </tr>"""
        for r in region_summary.get('top_regions', [])
    ) or '<tr><td colspan="3" class="no-data">No regional data available.</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Azure Tenant Insights — Technical Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:#f0f4f8;color:#1a1a2e}}
.header{{background:linear-gradient(135deg,#1a3a5c,#1F4E79);color:#fff;padding:1.5rem 3rem}}
.header h1{{font-size:1.8rem;font-weight:700}}
.header .sub{{font-size:.88rem;opacity:.8;margin-top:.3rem}}
.meta-bar{{background:#0f2a42;color:#a8c6e0;padding:.5rem 3rem;font-size:.8rem;display:flex;gap:1.5rem;flex-wrap:wrap}}
.sidebar{{position:fixed;left:0;top:0;width:220px;height:100vh;background:#1a3a5c;color:#fff;padding:1rem 0;overflow-y:auto;z-index:100}}
.sidebar h3{{padding:.4rem 1.2rem;font-size:.7rem;text-transform:uppercase;color:#6aa3c8;letter-spacing:.08em;margin-top:.8rem}}
.sidebar a{{display:block;padding:.45rem 1.2rem;color:#a8c6e0;text-decoration:none;font-size:.84rem;transition:background .2s}}
.sidebar a:hover{{background:rgba(255,255,255,.1);color:#fff}}
.sidebar-logo{{padding:1rem 1.2rem;font-weight:700;color:#fff;border-bottom:1px solid rgba(255,255,255,.1)}}
.main{{margin-left:220px}}
.container{{max-width:1200px;margin:0 auto;padding:1.5rem 2rem}}
.section{{background:#fff;border-radius:12px;padding:1.8rem;margin:1.2rem 0;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
.section h2{{font-size:1.15rem;color:#1F4E79;border-bottom:2px solid #e8f0f7;padding-bottom:.7rem;margin-bottom:1rem;display:flex;align-items:center;justify-content:space-between}}
.note{{font-size:.82rem;color:#666;margin-bottom:.8rem}}
.dtable{{width:100%;border-collapse:collapse;font-size:.82rem}}
.mod-h3{{font-size:1rem;color:#1F4E79;margin:1.2rem 0 .5rem;padding-bottom:.35rem;border-bottom:1px dashed #d5e0ec}}
.mod-fold{{margin:.6rem 0}}
summary.mod-h3{{cursor:pointer;list-style:none;display:flex;align-items:center;gap:.5rem;user-select:none}}
summary.mod-h3::-webkit-details-marker{{display:none}}
summary.mod-h3::before{{content:'\\25B6';font-size:.72rem;color:#2E86AB;transition:transform .18s}}
details[open]>summary.mod-h3::before{{transform:rotate(90deg)}}
summary.mod-h3:hover{{color:#2E86AB}}
.sm-info{{display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px;border:1px solid #2E86AB;border-radius:50%;color:#2E86AB;font-size:.62rem;vertical-align:1px;cursor:help}}
.sm-help{{font-size:.71rem;color:#777;margin:.25rem 0 -.1rem}}
.sm-help summary{{cursor:pointer;color:#2E86AB;font-weight:600}}
.sm-help p{{margin:.3rem 0 0;line-height:1.4}}
.mod-kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.8rem;margin:.6rem 0 1rem}}
.mod-chip{{background:#fafcff;border:1px solid #e6eef7;border-top:3px solid #1F4E79;border-radius:10px;padding:.7rem;text-align:center}}
.mod-chip .chip-val{{font-size:1.5rem;font-weight:800;color:#1F4E79;line-height:1}}
.mod-chip .chip-lbl{{font-size:.72rem;color:#777;margin-top:.25rem;text-transform:uppercase;letter-spacing:.03em}}
.mod-legend{{display:flex;gap:1.2rem;flex-wrap:wrap;font-size:.74rem;color:#555;margin:.2rem 0 1rem}}
.mod-legend span{{display:inline-flex;align-items:center;gap:.35rem}}
.mod-legend i{{width:12px;height:12px;border-radius:3px;display:inline-block}}
.mod-opps{{display:grid;grid-template-columns:200px 1fr;gap:1.4rem;align-items:start}}
.mod-gauge-wrap{{text-align:center}}
.gauge{{width:170px;height:170px;border-radius:50%;margin:0 auto;display:flex;align-items:center;justify-content:center}}
.gauge-inner{{width:120px;height:120px;border-radius:50%;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:inset 0 0 6px rgba(0,0,0,.08)}}
.gauge-val{{font-size:2.3rem;font-weight:800;line-height:1}}
.gauge-cap{{font-size:.66rem;color:#777;text-transform:uppercase;letter-spacing:.04em;margin-top:.2rem;line-height:1.15}}
.gauge-note{{font-size:.68rem;color:#999;margin-top:.5rem;max-width:180px;margin-left:auto;margin-right:auto}}
.opp-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem}}
.opp-card{{border:1px solid #e6e0d8;border-left:5px solid #C55A11;border-radius:10px;padding:1rem;background:#fffdfa}}
.opp-card h4{{color:#1F4E79;font-size:.95rem;margin-bottom:.4rem}}
.opp-score{{float:right;font-weight:800;font-size:1.1rem}}
.opp-bar{{background:#eef1f5;border-radius:6px;height:9px;overflow:hidden}}
.opp-bar span{{display:block;height:100%;border-radius:6px}}
.opp-fams{{display:flex;flex-wrap:wrap;gap:.3rem;margin-top:.55rem}}
.opp-fams .fam{{font-size:.7rem;padding:.1rem .45rem;border-radius:10px;white-space:nowrap;font-weight:600}}
.opp-fams .fam-yes{{background:#eef7e6;color:#2E7D32}}
.opp-fams .fam-no{{background:#f3f4f6;color:#9aa0a6}}
.mod-breadth-note{{font-size:.72rem;color:#777;margin:-.3rem 0 1rem;font-style:italic}}
.opp-meta{{font-size:.75rem;color:#888;margin-top:.5rem}}
.opp-meta a{{color:#2E86AB;text-decoration:none}}
.mod-qw{{font-size:.82rem;color:#385723;background:#eef7e6;border-radius:8px;padding:.5rem .8rem;margin-top:.8rem}}
.mod-tbl-legend{{display:flex;flex-wrap:wrap;gap:.3rem 1.2rem;font-size:.68rem;color:#9aa4ad;margin:.5rem .2rem 0;line-height:1.5}}
.mod-tbl-legend strong{{color:#7a8894;font-weight:600;margin-right:.25rem}}
.mod-tbl-legend em{{font-style:italic;color:#8a95a0}}
.mod-tbl-legend .lg-band{{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 .2rem 0 .4rem;vertical-align:middle}}
@media(max-width:820px){{.mod-opps{{grid-template-columns:1fr}}}}
.dtable th{{background:#1F4E79;color:#fff;padding:.55rem .7rem;text-align:left;font-weight:600;white-space:nowrap}}
.dtable td{{padding:.45rem .7rem;border-bottom:1px solid #f0f0f0;vertical-align:top;word-break:break-word;max-width:280px}}
.dtable tr:nth-child(even){{background:#f8fafd}}
.dtable tr:hover{{background:#eef4fb}}
.table-scroll{{overflow-x:auto}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.mono{{font-family:monospace;font-size:.78rem}}
.cnt{{display:inline-block;background:#2E86AB;color:#fff;border-radius:12px;padding:.1rem .5rem;font-size:.75rem;margin-left:.4rem}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1rem;margin:.8rem 0}}
.kpi-card{{background:#f8faff;border-radius:10px;padding:1.1rem;text-align:center;border-top:3px solid #2E86AB}}
.kpi-val{{font-size:2rem;font-weight:700;color:#1F4E79}}
.kpi-lbl{{font-size:.75rem;color:#666;margin-top:.3rem}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:1.2rem}}
.chart-box{{position:relative;height:200px}}
.tab-bar{{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:1rem}}
.tab-btn{{padding:.45rem .9rem;border:2px solid var(--tc);background:#fff;color:var(--tc);border-radius:20px;cursor:pointer;font-size:.82rem;font-weight:600;transition:all .2s}}
.tab-btn:hover,.tab-btn.active{{background:var(--tc);color:#fff}}
.tc{{background:rgba(0,0,0,.12);border-radius:10px;padding:.1rem .4rem;font-size:.72rem;margin-left:.3rem}}
.pillar-hdr{{padding:.7rem 1rem;background:#f8faff;border-radius:0 8px 8px 0;margin-bottom:1rem;font-size:.92rem}}
.obs{{padding:.65rem 1rem;margin:.4rem 0;border-radius:8px;font-size:.88rem}}
.obs-warn{{background:#fff8e1;border-left:4px solid #FFC000}}
.obs-info{{background:#e8f4f8;border-left:4px solid #2E86AB}}
.no-data{{color:#888;font-style:italic;padding:.5rem;display:block}}
.info-cell{{text-align:center;color:#2E86AB;padding:.5rem;font-size:.8rem}}
.footer{{text-align:center;padding:2rem;color:#888;font-size:.8rem;margin-left:220px}}
@media(max-width:900px){{.sidebar{{display:none}}.main,.footer{{margin-left:0}}}}
.toggle-btn{{background:none;border:1.5px solid #2E86AB;border-radius:50%;width:26px;height:26px;cursor:pointer;font-size:.85rem;line-height:24px;text-align:center;color:#2E86AB;margin-left:.5rem;flex-shrink:0;transition:all .2s;padding:0}}
.toggle-btn:hover{{background:#2E86AB;color:#fff}}
.ctrl-bar{{display:flex;gap:.6rem;margin-bottom:1rem;padding:.5rem 0}}
.ctrl-btn{{padding:.35rem 1rem;border:1.5px solid #2E86AB;background:#fff;color:#2E86AB;border-radius:20px;cursor:pointer;font-size:.82rem;font-weight:600;transition:all .2s}}
.ctrl-btn:hover{{background:#2E86AB;color:#fff}}
.filter-input{{width:100%;padding:.22rem .4rem;border:1px solid #ccc;border-radius:4px;font-size:.74rem;color:#333;box-sizing:border-box}}
.filter-input:focus{{outline:none;border-color:#2E86AB;background:#f0f8ff}}
.pg-bar{{display:flex;align-items:center;gap:.6rem;margin:.5rem 0 .2rem;flex-wrap:wrap}}
.pg-btn{{padding:.28rem .9rem;border:1.5px solid #2E86AB;background:#2E86AB;color:#fff;border-radius:16px;cursor:pointer;font-size:.78rem;font-weight:600;transition:all .2s}}
.pg-btn:hover{{background:#1F4E79;border-color:#1F4E79}}
.pg-btn.ghost{{background:#fff;color:#2E86AB}}
.pg-btn.ghost:hover{{background:#eaf3fa}}
.pg-info{{font-size:.75rem;color:#888}}
</style>
</head>
<body>
<nav class="sidebar">
  <div class="sidebar-logo">⚡ ATI Technical</div>
      <h3>Overview</h3>
  <a href="#inventory">📦 Resource Inventory</a>
  {arc_nav}
  <a href="#regions">🌍 Regional Distribution</a>
  <h3>Modernization</h3>
  <a href="#modernization">🚀 Modernization Signals</a>
  <h3>Infrastructure</h3>
  <a href="#lz">🏗 Landing Zone</a>
  <h3>WAF Analysis</h3>
  <a href="#waf">🏛 WAF Pillar Findings</a>
  <h3>Security</h3>
  <a href="#policy">📋 Policy Compliance</a>
  <a href="#misconfig">⚠ Misconfigurations</a>
  {def_nav}
  <a href="#zerotrust">🛡 Zero Trust Posture</a>
  <h3>Reliability</h3>
  <a href="#health">❤ Resource Health</a>
  <a href="#deprecated">⛔ Deprecated Resources</a>
</nav>
<div class="main">
  <div class="header">
    <h1>Azure Tenant Insights — Technical Report</h1>
    <div class="sub">Engineering · Architecture · Security · Operations</div>
  </div>
  <div class="meta-bar">
    <span>📅 Scan Date: <strong>{scan_date}</strong></span>
    <span>🏢 Tenant: <strong>{tenant_name}</strong> <small style="opacity:.65">({tenant_id})</small></span>
    <span>📋 Subscriptions: <strong>{subscriptions_list}</strong></span>
    <span>📦 Resources: <strong>{kpi.get('total_resources',0):,}</strong></span>
    <span>🔢 Types: <strong>{kpi.get('total_resource_types',0)}</strong></span>
    <span style="opacity:.6;font-size:.72rem;align-self:center">&#9432; Collection details at end &mdash; <a href="#data-collection-notes" style="color:#a8c6e0;text-decoration:underline">Data Collection Notes</a></span>
  </div>
  <div class="container">
    <div class="ctrl-bar"><button class="ctrl-btn" onclick="expandAll()">&#8862; Expand All</button><button class="ctrl-btn" onclick="collapseAll()">&#8863; Collapse All</button></div>

    <!-- KPIs + Charts -->
    <div class="section">
      <div class="kpi-grid">
        <div class="kpi-card"><div class="kpi-val">{kpi.get('total_resources',0):,}</div><div class="kpi-lbl">Total Resources</div></div>
        <div class="kpi-card"><div class="kpi-val">{advisor_count}</div><div class="kpi-lbl">Advisor Findings</div></div>
        <div class="kpi-card"><div class="kpi-val">{misconfig_count}</div><div class="kpi-lbl">Misconfigs</div></div>
        <div class="kpi-card"><div class="kpi-val">{policy_count}</div><div class="kpi-lbl">Policy Violations</div></div>
        <div class="kpi-card"><div class="kpi-val">{health_count}</div><div class="kpi-lbl">Health Issues</div></div>
        <div class="kpi-card"><div class="kpi-val">{deprecated_count}</div><div class="kpi-lbl">Deprecated</div></div>
        <div class="kpi-card"><div class="kpi-val">{region_summary.get('total_regions',0)}</div><div class="kpi-lbl">Active Regions</div></div>
      </div>
      <div class="two-col" style="margin-top:1rem">
        <div><strong style="color:#1F4E79;font-size:.9rem">Resources by Subscription</strong><div class="chart-box" style="margin-top:.5rem"><canvas id="subChart"></canvas></div></div>
        <div><strong style="color:#1F4E79;font-size:.9rem">Misconfiguration Severity</strong><div class="chart-box" style="margin-top:.5rem"><canvas id="sevChart"></canvas></div></div>
      </div>
    </div>

    <div class="section" id="inventory">
      <h2>📦 Resource Inventory <span class="cnt">{kpi.get('total_resource_types',0)} types</span></h2>
      <p class="note">All resource types discovered dynamically via Azure Resource Graph.</p>
      {inventory_html}
    </div>

    {arc_section}

    <div class="section" id="regions">
      <h2>🌍 Regional Distribution
        <small style="font-size:.7rem;color:#888;font-weight:normal;margin-left:.5rem">(Resources by location)</small>
      </h2>
      <p class="note">Resource count by deployment region. Helps identify geographic spread and redundancy.</p>
      <div class="table-scroll">
        <table class="dtable">
          <thead><tr><th>Region</th><th class="num">Resource Count</th><th class="num">Percentage</th></tr></thead>
          <tbody>{region_rows}</tbody>
        </table>
      </div>
    </div>

    <div class="section" id="modernization">
      <h2>🚀 Cloud Modernization Signals &amp; Opportunity
        <small style="font-size:.7rem;color:#888;font-weight:normal;margin-left:.5rem">(INFERRED — signals from inventory; evidence-backed, not prescriptive)</small>
      </h2>
      <p class="note">Per-dimension maturity/adoption signals with the supporting resources and the scoring method used. Low-confidence rows indicate weak evidence — validate against your architecture.</p>
      {modernization_detail_html}
    </div>

    <div class="section" id="lz">
      <h2>🏗 Landing Zone Observations
        <small style="font-size:.7rem;color:#888;font-weight:normal;margin-left:.5rem">(Inferred — not authoritative API data)</small>
      </h2>
      <p class="note">Inferred observations from resource configuration patterns. Validate against your organizational Landing Zone design.
      Security observations reference the <a href="https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/design-area/security" target="_blank">CAF Security design area</a>.</p>
      {lz_html}
    </div>

    <div class="section" id="waf">
      <h2>🏛 Azure Well-Architected Framework Findings <span class="cnt">{advisor_count}</span></h2>
      <p class="note">Azure Advisor recommendations mapped to WAF pillars. Click a pillar to view details.</p>
      {waf_html}
    </div>

    <div class="section" id="policy">
      <h2>📋 Policy Compliance <span class="cnt">{policy_count}</span></h2>
      <p class="note">Resources non-compliant with assigned Azure Policy definitions.</p>
            {policy_summary_html}
      {policy_html}
    </div>

    <div class="section" id="misconfig">
      <h2>⚠ Known Misconfigurations <span class="cnt">{misconfig_count}</span></h2>
      <p class="note">Configuration findings based exclusively on official Microsoft Azure best practices. All rules are linked to documentation.</p>
      {misconfig_html}
    </div>

    {defender_section}

    {zerotrust_html}

    <div class="section" id="health">
      <h2>❤ Resource Health <span class="cnt">{health_count}</span></h2>
      <p class="note">Resources with degraded or unavailable health status at time of scan.</p>
      {health_html}
    </div>

    <div class="section" id="deprecated">
      <h2>⛔ Deprecated &amp; Retiring Resources <span class="cnt">{deprecated_count}</span></h2>
      <p class="note">Resources matching known Azure retirement announcements. Migration paths link to official Microsoft documentation.</p>
      {deprecated_html}
    </div>


  </div>
</div>
<div class="footer">
  Azure Tenant Insights v1.0.0 &mdash; Technical Report &mdash; {scan_date}<br>
  <small>Data sourced from Azure Resource Graph, Azure Advisor, Azure Policy Insights, and Resource Health APIs. Point-in-time assessment only.</small>
  {warnings_html}
  <div style="margin-top:.8rem;border-top:1px solid #ddd;padding-top:.8rem">
    <p style="font-size:.7rem;color:#bbb;margin-bottom:.3rem"><strong>Microsoft Documentation References</strong></p>
    <p style="font-size:.7rem;color:#bbb;line-height:1.9">
      <a href="https://learn.microsoft.com/en-us/azure/well-architected/" target="_blank" style="color:#bbb">Well-Architected Framework</a> &middot;
      <a href="https://learn.microsoft.com/en-us/azure/governance/resource-graph/" target="_blank" style="color:#bbb">Resource Graph</a> &middot;
      <a href="https://learn.microsoft.com/en-us/azure/advisor/" target="_blank" style="color:#bbb">Azure Advisor</a> &middot;
      <a href="https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/design-area/security" target="_blank" style="color:#bbb">CAF Security Design Area</a> &middot;
      <a href="https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/" target="_blank" style="color:#bbb">CAF Landing Zone</a> &middot;
      <a href="https://learn.microsoft.com/en-us/azure/governance/policy/" target="_blank" style="color:#bbb">Azure Policy</a> &middot;
      <a href="https://learn.microsoft.com/en-us/azure/defender-for-cloud/" target="_blank" style="color:#bbb">Defender for Cloud</a> &middot;
      <a href="https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/resource-providers-and-types" target="_blank" style="color:#bbb">Resource Providers</a>
    </p>
  </div>
</div>
<script>
document.querySelector('.tab-btn')?.click();
function showPillar(p){{
  document.querySelectorAll('.tab-content').forEach(e=>e.style.display='none');
  document.querySelectorAll('.tab-btn').forEach(e=>e.classList.remove('active'));
  const c=document.getElementById('waf-'+p),b=document.getElementById('tb-'+p);
  if(c)c.style.display='block';if(b)b.classList.add('active');
}}
const sCtx=document.getElementById('subChart')?.getContext('2d');
if(sCtx){{new Chart(sCtx,{{type:'bar',data:{{labels:{sub_labels},datasets:[{{label:'Resources',data:{sub_values},backgroundColor:'#2E86AB',borderRadius:4}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{maxRotation:45,font:{{size:10}}}}}},y:{{ticks:{{font:{{size:10}}}}}}}}}}}})}};
const vCtx=document.getElementById('sevChart')?.getContext('2d');
if(vCtx){{new Chart(vCtx,{{type:'pie',data:{{labels:{sev_labels},datasets:[{{data:{sev_values},backgroundColor:['#C00000','#FF4444','#FFC000','#70AD47','#aaa'],borderWidth:2,borderColor:'#fff'}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'right',labels:{{font:{{size:11}}}}}}}}}}}})}};
// ── Section collapse / expand (auto-inject toggle buttons) ─────────────────
document.addEventListener('DOMContentLoaded',function(){{
  document.querySelectorAll('.section').forEach(function(sec){{
    var h2=sec.querySelector('h2');
    if(!h2)return;
    var btn=document.createElement('button');
    btn.className='toggle-btn';
    btn.innerHTML='&#8964;';
    btn.title='Toggle section';
    btn.addEventListener('click',function(e){{e.stopPropagation();toggleSection(sec);}});
    h2.appendChild(btn);
    var body=document.createElement('div');
    body.className='section-body';
    var nxt=h2.nextSibling;
    while(nxt){{var tmp=nxt.nextSibling;body.appendChild(nxt);nxt=tmp;}}
    sec.appendChild(body);
  }});
}});
function toggleSection(sec){{
  var body=sec.querySelector('.section-body');
  var btn=sec.querySelector('.toggle-btn');
  if(!body||!btn)return;
  if(body.style.display==='none'){{body.style.display='';btn.innerHTML='&#8964;';}}
  else{{body.style.display='none';btn.innerHTML='&#8963;';}}
}}
function expandAll(){{
  document.querySelectorAll('.section-body').forEach(function(b){{b.style.display='';}});
  document.querySelectorAll('.toggle-btn').forEach(function(b){{b.innerHTML='&#8964;';}});
}}
function collapseAll(){{
  document.querySelectorAll('.section-body').forEach(function(b){{b.style.display='none';}});
  document.querySelectorAll('.toggle-btn').forEach(function(b){{b.innerHTML='&#8963;';}});
}}
// ── Table column filters + progressive pagination ──────────────────────────
var _tblFilters={{}};
var _pageState={{}};
function _dataRows(tbl){{
  return Array.prototype.filter.call(tbl.querySelectorAll('tbody tr'),function(r){{
    return !r.classList.contains('filter-row')&&!r.classList.contains('pg-note');
  }});
}}
function _hasActiveFilters(tableId){{
  var f=_tblFilters[tableId]||{{}};for(var k in f){{if(f[k])return true;}}return false;
}}
function filterCol(input,tableId,colIdx){{
  if(!_tblFilters[tableId])_tblFilters[tableId]={{}};
  _tblFilters[tableId][colIdx]=input.value.trim().toLowerCase();
  _applyFilters(tableId);
}}
function _applyFilters(tableId){{
  var tbl=document.getElementById(tableId);
  if(!tbl)return;
  var filters=_tblFilters[tableId]||{{}};
  var pg=_pageState[tableId];
  if(!_hasActiveFilters(tableId)&&pg){{_renderPage(tableId);_togglePgBar(tableId,true);return;}}
  if(pg)_togglePgBar(tableId,false);
  tbl.querySelectorAll('tbody tr').forEach(function(row){{
    if(row.classList.contains('filter-row')||row.classList.contains('pg-note'))return;
    var cells=row.querySelectorAll('td');
    var show=true;
    for(var col in filters){{
      var val=filters[col];
      if(val&&cells[+col]&&cells[+col].textContent.toLowerCase().indexOf(val)===-1){{show=false;break;}}
    }}
    row.style.display=show?'':'none';
  }});
}}
function initPaginated(){{
  document.querySelectorAll('table[data-paginate]').forEach(function(tbl){{
    var id=tbl.id;if(!id)return;
    var size=parseInt(tbl.getAttribute('data-paginate'),10)||30;
    var step=parseInt(tbl.getAttribute('data-page-step'),10)||size;
    _pageState[id]={{size:size,step:step,shown:size}};
    var bar=document.createElement('div');
    bar.className='pg-bar';bar.id='pgbar-'+id;
    var wrap=tbl.closest('.table-scroll')||tbl;
    wrap.parentNode.insertBefore(bar,wrap.nextSibling);
    _renderPage(id);
  }});
}}
function _renderPage(id){{
  var tbl=document.getElementById(id);var st=_pageState[id];if(!tbl||!st)return;
  var rows=_dataRows(tbl);var total=rows.length;
  rows.forEach(function(r,i){{r.style.display=(i<st.shown)?'':'none';}});
  var bar=document.getElementById('pgbar-'+id);if(!bar)return;
  bar.innerHTML='';
  if(st.shown>=total){{
    var sa=document.createElement('span');sa.className='pg-info';sa.textContent='Showing all '+total+' row(s)';bar.appendChild(sa);
    return;
  }}
  var next=Math.min(st.step,total-st.shown);
  var b1=document.createElement('button');b1.className='pg-btn';b1.innerHTML='&#9660; Load '+next+' more';
  b1.addEventListener('click',function(){{loadMore(id);}});
  var b2=document.createElement('button');b2.className='pg-btn ghost';b2.textContent='Show all ('+total+')';
  b2.addEventListener('click',function(){{loadAll(id);}});
  var si=document.createElement('span');si.className='pg-info';si.textContent='Showing '+st.shown+' of '+total;
  bar.appendChild(b1);bar.appendChild(b2);bar.appendChild(si);
}}
function loadMore(id){{var st=_pageState[id];if(!st)return;st.shown+=st.step;_renderPage(id);}}
function loadAll(id){{var st=_pageState[id];var tbl=document.getElementById(id);if(!st||!tbl)return;st.shown=_dataRows(tbl).length;_renderPage(id);}}
function _togglePgBar(id,show){{var bar=document.getElementById('pgbar-'+id);if(bar)bar.style.display=show?'':'none';}}
document.addEventListener('DOMContentLoaded',initPaginated);
</script>
</body></html>"""
