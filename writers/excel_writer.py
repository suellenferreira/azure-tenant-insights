"""
Excel inventory writer using openpyxl.

Generates a formatted, multi-sheet Excel workbook from collected scan data.

Sheets produced:
  Overview         - KPI summary + top resource types + Advisor by pillar
  Subscriptions    - One row per subscription with resource count
  AllResources     - Flat table of ALL resources across all types
  [ResourceType]   - One sheet per resource type (up to MAX_TYPE_SHEETS)
  AdvisorFindings  - All Advisor recommendations with WAF pillar
  PolicyCompliance - Non-compliant resources
  ResourceHealth   - Degraded/unavailable resources
  DeprecatedRes    - Resources matching retirement announcements
  MisconfigFindgs  - Known misconfiguration findings
  SecurityAssessmt - Defender for Cloud assessments (optional)
  DefenderPosture  - Defender plan enablement per subscription (optional)
  DefenderServersCoverage - Per-resource VM/VMSS/Arc Defender coverage (optional)
  DefenderCoverageGap - Unprotected billable units & cost to protect (optional)
  Costs            - Cost by RG/Service (optional)
"""

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Excel column color constants
COLOR_HEADER_BG = "1F4E79"
COLOR_HEADER_FG = "FFFFFF"
COLOR_CRITICAL = "C00000"
COLOR_HIGH = "FF4444"
COLOR_MEDIUM = "FFC000"
COLOR_LOW = "FFFF99"
COLOR_OK = "70AD47"
COLOR_SECTION_BG = "D6E4F0"
COLOR_ALT_ROW = "F2F7FB"

MAX_TYPE_SHEETS = 40  # Practical limit to avoid unwieldy workbooks


def write_excel(scan_data: dict, output_path: str) -> None:
    """Main entry point — builds the full Excel workbook."""
    import openpyxl

    logger.info(f"Building Excel workbook: {output_path}")
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove the default empty sheet

    options = scan_data.get("options", {})
    include_tags = options.get("include_tags", False)

    _write_overview_sheet(wb, scan_data)
    _write_subscriptions_sheet(wb, scan_data)
    _write_all_resources_sheet(wb, scan_data, include_tags)
    _write_resource_type_sheets(wb, scan_data, include_tags)
    _write_advisor_sheet(wb, scan_data)
    _write_policy_sheet(wb, scan_data)
    _write_health_sheet(wb, scan_data)
    _write_deprecated_sheet(wb, scan_data)
    _write_misconfig_sheet(wb, scan_data)

    if scan_data.get("defender_data"):
        _write_defender_sheet(wb, scan_data)
        _write_defender_cost_estimate_sheet(wb, scan_data)

    if scan_data.get("defender_posture"):
        _write_defender_posture_sheet(wb, scan_data)
        _write_defender_servers_coverage_sheet(wb, scan_data)
        _write_defender_coverage_gap_sheet(wb, scan_data)

    if scan_data.get("costs_data"):
        _write_costs_sheet(wb, scan_data)

    wb.save(output_path)
    logger.info(f"Excel workbook saved: {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _header_style(ws, row_num: int, num_cols: int):
    from openpyxl.styles import Alignment, Font, PatternFill
    fill = PatternFill("solid", fgColor=COLOR_HEADER_BG)
    font = Font(bold=True, color=COLOR_HEADER_FG, size=11)
    align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for col in range(1, num_cols + 1):
        cell = ws.cell(row=row_num, column=col)
        cell.fill = fill
        cell.font = font
        cell.alignment = align


def _auto_filter(ws, header_row: int, num_cols: int):
    from openpyxl.utils import get_column_letter
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(num_cols)}{header_row}"


def _freeze(ws, freeze_row: int = 2):
    ws.freeze_panes = f"A{freeze_row}"


def _col_widths(ws, widths: List[int]):
    from openpyxl.utils import get_column_letter
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def _severity_fill(severity: str):
    from openpyxl.styles import PatternFill
    colors = {
        "Critical": COLOR_CRITICAL,
        "High": COLOR_HIGH,
        "Medium": COLOR_MEDIUM,
        "Low": COLOR_LOW,
    }
    color = colors.get(severity)
    return PatternFill("solid", fgColor=color) if color else None


# ─────────────────────────────────────────────────────────────────────────────
# Sheet writers
# ─────────────────────────────────────────────────────────────────────────────

def _write_overview_sheet(wb, scan_data: dict):
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

    ws = wb.create_sheet("Overview", 0)
    ws.sheet_view.showGridLines = False
    ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
    ws.page_margins.left = 0.5
    ws.page_margins.right = 0.5
    ws.page_margins.top = 0.75
    ws.page_margins.bottom = 0.75

    meta = scan_data.get("metadata", {})
    summary = scan_data.get("summary_metrics", {})

    # Dark theme header bar
    ws.merge_cells("A1:H1")
    title_cell = ws["A1"]
    title_cell.value = "Azure Tenant Insights — Environment Overview"
    title_cell.font = Font(bold=True, size=18, color="FFFFFF")
    title_cell.fill = PatternFill("solid", fgColor=COLOR_HEADER_BG)
    title_cell.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 42

    # Metadata section with subtle background
    meta_fill = PatternFill("solid", fgColor="E7E6E6")
    meta_font = Font(bold=True, size=10)
    ws["A2"] = "Scan Date"
    ws["A2"].fill = meta_fill
    ws["A2"].font = meta_font
    ws["B2"] = meta.get("scan_timestamp", "")[:10]
    ws["B2"].fill = PatternFill("solid", fgColor="F5F5F5")

    ws["C2"] = "Tenant ID"
    ws["C2"].fill = meta_fill
    ws["C2"].font = meta_font
    ws["D2"] = meta.get("tenant_id", "N/A")
    ws["D2"].fill = PatternFill("solid", fgColor="F5F5F5")

    ws["E2"] = "Cloud"
    ws["E2"].fill = meta_fill
    ws["E2"].font = meta_font
    ws["F2"] = meta.get("cloud", "AzurePublicCloud")
    ws["F2"].fill = PatternFill("solid", fgColor="F5F5F5")

    ws["A3"] = "Tenant Name"
    ws["A3"].fill = meta_fill
    ws["A3"].font = meta_font
    ws.merge_cells("B3:F3")
    ws["B3"] = meta.get("tenant_name", "N/A")
    ws["B3"].fill = PatternFill("solid", fgColor="F5F5F5")
    ws.row_dimensions[3].height = 18

    # Section 1: Key Metrics (with dark header)
    section_header_fill = PatternFill("solid", fgColor="1F4E79")
    section_header_font = Font(bold=True, size=11, color="FFFFFF")

    ws.merge_cells("A4:B4")
    ws["A4"].value = "KEY METRICS"
    ws["A4"].fill = section_header_fill
    ws["A4"].font = section_header_font
    ws["A4"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[4].height = 24

    kpi_rows = [
        ("Total Resources", summary.get("total_resources", 0), COLOR_SECTION_BG),
        ("Subscriptions", summary.get("total_subscriptions", 0), COLOR_SECTION_BG),
        ("Resource Types", summary.get("total_resource_types", 0), COLOR_SECTION_BG),
        ("Active Regions", summary.get("total_regions", 0), COLOR_SECTION_BG),
        ("Advisor Recommendations", summary.get("total_advisor_recommendations", 0), COLOR_MEDIUM),
        ("Policy Non-Compliant", summary.get("total_non_compliant_policies", 0), COLOR_MEDIUM),
        ("Deprecated Resources", summary.get("total_deprecated", 0), COLOR_HIGH),
        ("Critical Findings", summary.get("critical_findings_count", 0), COLOR_CRITICAL),
        ("Tag Coverage", f"{summary.get('tag_coverage_pct', 0)}%", COLOR_SECTION_BG),
        ("Health Issues", summary.get("total_health_issues", 0), COLOR_MEDIUM),
    ]

    for idx, (label, value, color) in enumerate(kpi_rows):
        row = 5 + idx
        label_cell = ws.cell(row=row, column=1)
        label_cell.value = label
        label_cell.font = Font(bold=True, size=10)
        label_cell.fill = PatternFill("solid", fgColor="F5F5F5")
        label_cell.alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[row].height = 22

        value_cell = ws.cell(row=row, column=2)
        value_cell.value = value
        value_cell.fill = PatternFill("solid", fgColor=color)
        value_cell.font = Font(bold=True, size=11)
        value_cell.alignment = Alignment(horizontal="center", vertical="center")
        value_cell.border = Border(
            left=Side(style="thin", color="D3D3D3"),
            right=Side(style="thin", color="D3D3D3"),
            top=Side(style="thin", color="D3D3D3"),
            bottom=Side(style="thin", color="D3D3D3"),
        )

    # Section 2: Top Resource Types (with dark header)
    ws.merge_cells("D4:E4")
    ws["D4"].value = "TOP RESOURCE TYPES"
    ws["D4"].fill = section_header_fill
    ws["D4"].font = section_header_font
    ws["D4"].alignment = Alignment(horizontal="center", vertical="center")

    for idx, (rtype, count) in enumerate(summary.get("top_resource_types", [])[:10]):
        row = 5 + idx
        display = rtype.split("/")[-1].replace("-", " ").title()
        type_cell = ws.cell(row=row, column=4)
        type_cell.value = display
        type_cell.fill = PatternFill("solid", fgColor="F5F5F5")
        type_cell.font = Font(size=10)

        count_cell = ws.cell(row=row, column=5)
        count_cell.value = count
        count_cell.fill = PatternFill("solid", fgColor="D6E4F0")
        count_cell.font = Font(bold=True, size=10)
        count_cell.alignment = Alignment(horizontal="center")
        count_cell.border = Border(
            left=Side(style="thin", color="D3D3D3"),
            right=Side(style="thin", color="D3D3D3"),
        )

    # Section 3: Advisor by Pillar (with dark header)
    ws.merge_cells("G4:H4")
    ws["G4"].value = "ADVISOR BY WAF PILLAR"
    ws["G4"].fill = section_header_fill
    ws["G4"].font = section_header_font
    ws["G4"].alignment = Alignment(horizontal="center", vertical="center")

    for idx, (pillar, count) in enumerate(summary.get("advisor_by_pillar", {}).items()):
        row = 5 + idx
        pillar_cell = ws.cell(row=row, column=7)
        pillar_cell.value = pillar
        pillar_cell.fill = PatternFill("solid", fgColor="F5F5F5")
        pillar_cell.font = Font(size=10)

        count_cell = ws.cell(row=row, column=8)
        count_cell.value = count
        count_cell.fill = PatternFill("solid", fgColor="D6E4F0")
        count_cell.font = Font(bold=True, size=10)
        count_cell.alignment = Alignment(horizontal="center")
        count_cell.border = Border(
            left=Side(style="thin", color="D3D3D3"),
            right=Side(style="thin", color="D3D3D3"),
        )

    _col_widths(ws, [28, 18, 16, 32, 14, 4, 28, 14])

    # Section 4: Microsoft References (5 links)
    _REFERENCES = [
        ("Azure Well-Architected Framework overview",
         "https://learn.microsoft.com/en-us/azure/well-architected/"),
        ("CAF Security design area",
         "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/design-area/security"),
        ("Azure Advisor documentation",
         "https://learn.microsoft.com/en-us/azure/advisor/advisor-overview"),
        ("Microsoft Defender for Cloud overview",
         "https://learn.microsoft.com/en-us/azure/defender-for-cloud/defender-for-cloud-introduction"),
        ("Azure Policy documentation",
         "https://learn.microsoft.com/en-us/azure/governance/policy/overview"),
    ]
    ref_start_row = 20

    ws.merge_cells(f"A{ref_start_row}:H{ref_start_row}")
    ref_header = ws[f"A{ref_start_row}"]
    ref_header.value = "MICROSOFT REFERENCES — CAF & WAF"
    ref_header.fill = section_header_fill
    ref_header.font = section_header_font
    ref_header.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[ref_start_row].height = 24

    for i, (label, url) in enumerate(_REFERENCES):
        ref_row = ref_start_row + 1 + i
        ws.merge_cells(f"A{ref_row}:H{ref_row}")
        c = ws[f"A{ref_row}"]
        c.value = f"{label} — {url}"
        c.font = Font(size=9, color="1F4E79", italic=True)
        c.fill = PatternFill("solid", fgColor="D6E4F0")
        c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws.row_dimensions[ref_row].height = 18

    # Section 5: Active Regions Distribution (table + bar chart)
    from openpyxl.chart import BarChart, Reference

    region_data = summary.get("resources_by_location", {})
    top_regions = sorted(region_data.items(), key=lambda x: -x[1])[:12]

    chart_data_start = ref_start_row + len(_REFERENCES) + 2  # gap row

    ws.merge_cells(f"A{chart_data_start}:H{chart_data_start}")
    rgn_header = ws[f"A{chart_data_start}"]
    rgn_header.value = "ACTIVE REGIONS DISTRIBUTION"
    rgn_header.fill = section_header_fill
    rgn_header.font = section_header_font
    rgn_header.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[chart_data_start].height = 24

    # Write data table (cols A-B) and chart data (cols A-B, reused)
    tbl_header_row = chart_data_start + 1
    ws.cell(row=tbl_header_row, column=1).value = "Region"
    ws.cell(row=tbl_header_row, column=2).value = "Resources"
    _header_style(ws, tbl_header_row, 2)
    ws.row_dimensions[tbl_header_row].height = 20

    if top_regions:
        for r_idx, (region, count) in enumerate(top_regions):
            data_row = tbl_header_row + 1 + r_idx
            ws.cell(row=data_row, column=1).value = region
            ws.cell(row=data_row, column=2).value = count
            ws.cell(row=data_row, column=1).fill = PatternFill("solid", fgColor="F5F5F5")
            ws.cell(row=data_row, column=2).fill = PatternFill("solid", fgColor="D6E4F0")
            ws.cell(row=data_row, column=2).alignment = Alignment(horizontal="center")
            ws.row_dimensions[data_row].height = 18

        chart = BarChart()
        chart.type = "bar"
        chart.grouping = "clustered"
        chart.title = "Active Regions — Resource Count"
        chart.y_axis.title = "Resources"
        chart.style = 10
        chart.width = 18
        chart.height = 12

        data_ref = Reference(
            ws,
            min_col=2, max_col=2,
            min_row=tbl_header_row,
            max_row=tbl_header_row + len(top_regions),
        )
        cats_ref = Reference(
            ws,
            min_col=1,
            min_row=tbl_header_row + 1,
            max_row=tbl_header_row + len(top_regions),
        )
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)

        # Ensure the category axis (region names, left side) is visible.
        chart.x_axis.delete = False
        chart.x_axis.tickLblPos = "nextTo"

        # Apply a distinct colour per bar using DataPoint so each region is visually distinct.
        # Palette: 12 colours derived from the Microsoft blue-to-teal/green spectrum.
        _BAR_PALETTE = [
            "1F4E79", "2E75B6", "4472C4", "70AD47",
            "ED7D31", "FFC000", "5BA3C9", "A9D18E",
            "FF7C80", "9DC3E6", "F4B183", "C5E0B4",
        ]
        from openpyxl.chart.data_source import NumDataSource, NumRef
        from openpyxl.chart.series import DataPoint
        ser = chart.series[0]
        for idx in range(len(top_regions)):
            pt = DataPoint(idx=idx)
            pt.graphicalProperties.solidFill = _BAR_PALETTE[idx % len(_BAR_PALETTE)]
            pt.graphicalProperties.line.solidFill = _BAR_PALETTE[idx % len(_BAR_PALETTE)]
            ser.dPt.append(pt)

        # Hide the legend — categories on the axis already identify each bar.
        chart.legend = None

        ws.add_chart(chart, f"C{chart_data_start}")



def _write_subscriptions_sheet(wb, scan_data: dict):
    ws = wb.create_sheet("Subscriptions")
    headers = ["Subscription ID", "Display Name", "State", "Tenant ID", "Resource Count"]
    for col, h in enumerate(headers, 1):
        ws.cell(row=1, column=col).value = h
    _header_style(ws, 1, len(headers))
    _auto_filter(ws, 1, len(headers))
    _freeze(ws, 2)

    summary = scan_data.get("summary_metrics", {})
    sub_counts = summary.get("resources_by_subscription", {})
    for row, sub in enumerate(scan_data.get("subscriptions", []), 2):
        sid = sub.get("subscriptionId", "")
        ws.cell(row=row, column=1).value = sid
        ws.cell(row=row, column=2).value = sub.get("displayName", "")
        ws.cell(row=row, column=3).value = sub.get("state", "")
        ws.cell(row=row, column=4).value = sub.get("tenantId", "")
        ws.cell(row=row, column=5).value = sub_counts.get(sid, 0)

    _col_widths(ws, [38, 40, 12, 38, 16])


def _write_all_resources_sheet(wb, scan_data: dict, include_tags: bool):
    from processors.normalizer import safe_str, clean_resource_type, excel_safe_sheet_name

    ws = wb.create_sheet("AllResources")

    # Build resource_type → sheet_name mapping (same ordering as _write_resource_type_sheets)
    resources_by_type = scan_data.get("resources_by_type", {})
    sorted_types = sorted(resources_by_type.items(), key=lambda x: -len(x[1]))[:MAX_TYPE_SHEETS]
    type_to_sheet = {
        rtype: excel_safe_sheet_name(clean_resource_type(rtype))
        for rtype, _ in sorted_types
    }

    headers = [
        "Resource Tab",
        "Name", "Type", "Location", "Resource Group", "Subscription ID",
        "Kind", "SKU Name", "SKU Tier",
    ]
    if include_tags:
        headers.append("Tags")
    headers.append("Resource ID")

    for col, h in enumerate(headers, 1):
        ws.cell(row=1, column=col).value = h
    _header_style(ws, 1, len(headers))
    _auto_filter(ws, 1, len(headers))
    _freeze(ws, 2)

    row = 2
    for rtype, resources in resources_by_type.items():
        tab_name = type_to_sheet.get(rtype, "—")
        for resource in resources:
            sku = resource.get("sku") or {}
            sku_name = sku.get("name", "") if isinstance(sku, dict) else ""
            sku_tier = sku.get("tier", "") if isinstance(sku, dict) else ""

            col = 1
            ws.cell(row=row, column=col).value = tab_name
            col += 1
            for val in [
                resource.get("name", ""),
                rtype,
                resource.get("location", ""),
                resource.get("resourceGroup", ""),
                resource.get("subscriptionId", ""),
                safe_str(resource.get("kind", "")),
                safe_str(sku_name),
                safe_str(sku_tier),
            ]:
                ws.cell(row=row, column=col).value = val
                col += 1

            if include_tags:
                tags = resource.get("tags") or {}
                ws.cell(row=row, column=col).value = json.dumps(tags) if tags else ""
                col += 1

            ws.cell(row=row, column=col).value = resource.get("id", "")
            row += 1

    _col_widths(ws, [22, 35, 42, 20, 30, 38, 20, 25, 20, 60, 60])


def _write_resource_type_sheets(wb, scan_data: dict, include_tags: bool):
    from processors.normalizer import (
        clean_resource_type,
        excel_safe_sheet_name,
        safe_str,
    )

    resources_by_type = scan_data.get("resources_by_type", {})

    # Build security findings index: resource_id_lower -> [findings]
    findings_index: dict = {}
    for _f in scan_data.get("misconfig_findings", []):
        _rid = _f.get("resourceId", "").lower()
        if _rid:
            findings_index.setdefault(_rid, []).append(_f)

    # Sort by count descending; cap at MAX_TYPE_SHEETS
    sorted_types = sorted(
        resources_by_type.items(), key=lambda x: -len(x[1])
    )[:MAX_TYPE_SHEETS]

    for rtype, resources in sorted_types:
        if not resources:
            continue

        sheet_name = excel_safe_sheet_name(clean_resource_type(rtype))
        first = resources[0] if resources else {}
        enriched_cols = sorted(
            k for k in first.keys() if k.startswith("enriched_")
        )

        base_headers = [
            "Name", "Resource Group", "Subscription ID",
            "Location", "Kind", "SKU",
        ]
        enriched_display = [c.replace("enriched_", "").replace("_", " ").title() for c in enriched_cols]
        extra = ["Tags", "Resource ID"] if include_tags else ["Resource ID"]
        all_headers = base_headers + enriched_display + extra

        ws = wb.create_sheet(sheet_name)
        for col, h in enumerate(all_headers, 1):
            ws.cell(row=1, column=col).value = h
        _header_style(ws, 1, len(all_headers))
        _auto_filter(ws, 1, len(all_headers))
        _freeze(ws, 2)

        for row, resource in enumerate(resources, 2):
            sku = resource.get("sku") or {}
            sku_str = safe_str(sku.get("name", "") if isinstance(sku, dict) else sku)

            ws.cell(row=row, column=1).value = resource.get("name", "")
            ws.cell(row=row, column=2).value = resource.get("resourceGroup", "")
            ws.cell(row=row, column=3).value = resource.get("subscriptionId", "")
            ws.cell(row=row, column=4).value = resource.get("location", "")
            ws.cell(row=row, column=5).value = safe_str(resource.get("kind", ""))
            ws.cell(row=row, column=6).value = sku_str

            for e_idx, e_col in enumerate(enriched_cols, 7):
                ws.cell(row=row, column=e_idx).value = safe_str(resource.get(e_col))

            next_col = 7 + len(enriched_cols)
            if include_tags:
                tags = resource.get("tags") or {}
                ws.cell(row=row, column=next_col).value = json.dumps(tags) if tags else ""
                next_col += 1
            ws.cell(row=row, column=next_col).value = resource.get("id", "")

            # Highlight rows that have security findings
            rid_lower = resource.get("id", "").lower()
            row_findings = findings_index.get(rid_lower, [])
            if row_findings:
                from openpyxl.styles import PatternFill
                from openpyxl.comments import Comment
                warn_fill = PatternFill("solid", fgColor="FFF2CC")
                for c_idx in range(1, len(all_headers) + 1):
                    ws.cell(row=row, column=c_idx).fill = warn_fill
                finding_lines = "\n".join(
                    f"⚠ {f['title']} [{f.get('severity','')}]"
                    for f in row_findings[:5]
                )
                if len(row_findings) > 5:
                    finding_lines += f"\n... +{len(row_findings) - 5} more findings"
                cmt = Comment(finding_lines, "ATI Security")
                cmt.width = 320
                cmt.height = max(60, 22 * min(len(row_findings), 5))
                ws.cell(row=row, column=1).comment = cmt


def _write_advisor_sheet(wb, scan_data: dict):
    from openpyxl.styles import PatternFill

    ws = wb.create_sheet("AdvisorFindings")
    headers = [
        "WAF Pillar", "Category", "Impact", "Impacted Field", "Impacted Value",
        "Short Description", "Solution", "Potential Benefits",
        "Subscription ID", "Resource Group", "Learn More",
    ]
    for col, h in enumerate(headers, 1):
        ws.cell(row=1, column=col).value = h
    _header_style(ws, 1, len(headers))
    _auto_filter(ws, 1, len(headers))
    _freeze(ws, 2)

    IMPACT_COLORS = {"High": COLOR_CRITICAL, "Medium": COLOR_MEDIUM, "Low": COLOR_LOW}

    for row, rec in enumerate(scan_data.get("advisor_data", []), 2):
        impact = rec.get("impact", "")
        vals = [
            rec.get("wafPillar", ""),
            rec.get("category", ""),
            impact,
            rec.get("impactedField", ""),
            rec.get("impactedValue", ""),
            rec.get("shortDescription", ""),
            rec.get("solution", ""),
            rec.get("potentialBenefits", ""),
            rec.get("subscriptionId", ""),
            rec.get("resourceGroup", ""),
            rec.get("learnMoreLink", ""),
        ]
        for col, val in enumerate(vals, 1):
            ws.cell(row=row, column=col).value = val
        if impact in IMPACT_COLORS:
            ws.cell(row=row, column=3).fill = PatternFill("solid", fgColor=IMPACT_COLORS[impact])

    _col_widths(ws, [22, 22, 10, 35, 40, 60, 60, 30, 38, 25, 50])


def _write_policy_sheet(wb, scan_data: dict):
    ws = wb.create_sheet("PolicyCompliance")
    headers = [
        "Resource ID", "Resource Type", "Policy Assignment",
        "Policy Definition", "Effect", "Category",
        "Subscription ID", "Resource Group", "Compliance State",
    ]
    for col, h in enumerate(headers, 1):
        ws.cell(row=1, column=col).value = h
    _header_style(ws, 1, len(headers))
    _auto_filter(ws, 1, len(headers))
    _freeze(ws, 2)

    for row, state in enumerate(scan_data.get("policy_data", []), 2):
        for col, key in enumerate(
            ["resourceId", "resourceType", "policyAssignmentName",
             "policyDefinitionName", "policyDefinitionAction",
             "policyDefinitionCategory", "subscriptionId",
             "resourceGroup", "complianceState"],
            1,
        ):
            ws.cell(row=row, column=col).value = state.get(key, "")

    _col_widths(ws, [55, 40, 35, 35, 12, 25, 38, 28, 16])


def _write_health_sheet(wb, scan_data: dict):
    ws = wb.create_sheet("ResourceHealth")
    headers = [
        "Resource Name", "Availability State", "Summary",
        "Reason Type", "Reason Chronicity", "Occurred Time",
        "Subscription ID", "Resource Group", "Location",
    ]
    for col, h in enumerate(headers, 1):
        ws.cell(row=1, column=col).value = h
    _header_style(ws, 1, len(headers))
    _auto_filter(ws, 1, len(headers))
    _freeze(ws, 2)

    for row, event in enumerate(scan_data.get("health_data", []), 2):
        for col, key in enumerate(
            ["name", "availabilityState", "summary", "reasonType",
             "reasonChronicity", "occurredTime",
             "subscriptionId", "resourceGroup", "location"],
            1,
        ):
            ws.cell(row=row, column=col).value = event.get(key, "")

    _col_widths(ws, [35, 18, 60, 25, 20, 22, 38, 28, 18])


def _write_deprecated_sheet(wb, scan_data: dict):
    from openpyxl.styles import PatternFill

    ws = wb.create_sheet("DeprecatedResources")
    headers = [
        "Resource Name", "Resource Type", "Retirement Date", "Severity",
        "Subscription ID", "Resource Group", "Location",
        "Migration Path", "Announcement URL", "Notes",
    ]
    for col, h in enumerate(headers, 1):
        ws.cell(row=1, column=col).value = h
    _header_style(ws, 1, len(headers))
    _auto_filter(ws, 1, len(headers))
    _freeze(ws, 2)

    for row, match in enumerate(scan_data.get("deprecated_matches", []), 2):
        severity = match.get("severity", "")
        for col, key in enumerate(
            ["resourceName", "resourceType", "retirementDate", "severity",
             "subscriptionId", "resourceGroup", "location",
             "migrationPath", "retirementAnnouncementUrl", "notes"],
            1,
        ):
            ws.cell(row=row, column=col).value = match.get(key, "")
        fill = _severity_fill(severity)
        if fill:
            ws.cell(row=row, column=4).fill = fill

    _col_widths(ws, [35, 40, 16, 12, 38, 28, 18, 55, 55, 50])


def _write_misconfig_sheet(wb, scan_data: dict):
    ws = wb.create_sheet("MisconfigFindings")
    headers = [
        "Rule ID", "Title", "Severity", "WAF Pillar",
        "Resource Name", "Resource Type",
        "Subscription ID", "Resource Group", "Location",
        "Actual Value", "Expected Value",
        "Description", "Documentation URL",
    ]
    for col, h in enumerate(headers, 1):
        ws.cell(row=1, column=col).value = h
    _header_style(ws, 1, len(headers))
    _auto_filter(ws, 1, len(headers))
    _freeze(ws, 2)

    for row, finding in enumerate(scan_data.get("misconfig_findings", []), 2):
        severity = finding.get("severity", "")
        keys = [
            "ruleId", "title", "severity", "wafPillar",
            "resourceName", "resourceType",
            "subscriptionId", "resourceGroup", "location",
            "actualValue", "expectedValue",
            "description", "documentationUrl",
        ]
        for col, key in enumerate(keys, 1):
            ws.cell(row=row, column=col).value = finding.get(key, "")
        fill = _severity_fill(severity)
        if fill:
            ws.cell(row=row, column=3).fill = fill

    _col_widths(ws, [12, 45, 10, 22, 35, 40, 38, 28, 18, 20, 20, 60, 55])


def _write_defender_sheet(wb, scan_data: dict):
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    ws = wb.create_sheet("SecurityAssessments")

    # Reference row — CAF Security Design (row 1)
    _CAF_SECURITY_URL = (
        "https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/"
        "ready/landing-zone/design-area/security"
    )
    ws.merge_cells(f"A1:{get_column_letter(10)}1")
    ref_cell = ws["A1"]
    ref_cell.value = (
        "Reference: Security design in Azure — CAF Landing Zone | Microsoft Learn — "
        + _CAF_SECURITY_URL
    )
    ref_cell.font = Font(italic=True, size=9, color="1F4E79")
    ref_cell.fill = PatternFill("solid", fgColor="D6E4F0")
    ref_cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 20

    headers = [
        "Display Name", "Severity", "Status", "Category",
        "Implementation Effort", "Resource",
        "Subscription ID", "Resource Group",
        "Status Cause", "Remediation",
    ]
    for col, h in enumerate(headers, 1):
        ws.cell(row=2, column=col).value = h
    _header_style(ws, 2, len(headers))
    _auto_filter(ws, 2, len(headers))
    _freeze(ws, 3)

    for row, assessment in enumerate(scan_data.get("defender_data", []), 3):
        severity = assessment.get("severity", "")
        keys = [
            "displayName", "severity", "statusCode", "category",
            "implementationEffort", "resourceDetails",
            "subscriptionId", "resourceGroup",
            "statusCause", "remediationDescription",
        ]
        for col, key in enumerate(keys, 1):
            ws.cell(row=row, column=col).value = assessment.get(key, "")
        fill = _severity_fill(severity)
        if fill:
            ws.cell(row=row, column=2).fill = fill

    _col_widths(ws, [55, 10, 14, 25, 22, 55, 38, 28, 20, 60])


def _write_costs_sheet(wb, scan_data: dict):
    ws = wb.create_sheet("Costs")
    headers = ["Subscription ID", "Resource Group", "Service Name", "Currency", "Total Cost (MTD)"]
    for col, h in enumerate(headers, 1):
        ws.cell(row=1, column=col).value = h
    _header_style(ws, 1, len(headers))
    _auto_filter(ws, 1, len(headers))
    _freeze(ws, 2)

    for row, cost in enumerate(scan_data.get("costs_data", []), 2):
        ws.cell(row=row, column=1).value = cost.get("subscriptionId", "")
        ws.cell(row=row, column=2).value = cost.get("ResourceGroupName", cost.get("resourceGroupName", ""))
        ws.cell(row=row, column=3).value = cost.get("ServiceName", cost.get("serviceName", ""))
        ws.cell(row=row, column=4).value = cost.get("Currency", cost.get("currency", ""))
        ws.cell(row=row, column=5).value = cost.get("Cost", cost.get("totalCost", 0))

    _col_widths(ws, [38, 35, 40, 12, 18])


def _write_defender_cost_estimate_sheet(wb, scan_data: dict):
    """Defender for Cloud cost estimate sheet (resource counts x public pricing)."""
    from openpyxl.styles import Alignment, Font, PatternFill, numbers
    from openpyxl.utils import get_column_letter

    ws = wb.create_sheet("DefenderCostEstimate")

    # Title row
    ws.merge_cells(f"A1:{get_column_letter(8)}1")
    title_cell = ws["A1"]
    title_cell.value = "Defender for Cloud — Cost Estimate (Public List Pricing)"
    title_cell.font = Font(bold=True, size=13, color="FFFFFF")
    title_cell.fill = PatternFill("solid", fgColor="1F4E79")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    # Disclaimer row
    ws.merge_cells(f"A2:{get_column_letter(8)}2")
    disc_cell = ws["A2"]
    disc_cell.value = (
        "NOTE: Estimates based on public list pricing. EA/MCA/CSP discounts, free tiers, and included units are NOT reflected. "
        "Billable unit counts are inferred from Resource Graph data. Actual costs may differ."
    )
    disc_cell.font = Font(italic=True, size=9, color="7F7F7F")
    disc_cell.fill = PatternFill("solid", fgColor="FFF2CC")
    disc_cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.row_dimensions[2].height = 30

    headers = [
        "Defender Plan", "Billable Unit", "Unit Count",
        "P1 Price/Unit/Mo (USD)", "P1 Est. Monthly Cost",
        "P2 Price/Unit/Mo (USD)", "P2 Est. Monthly Cost",
        "Notes",
    ]
    for col, h in enumerate(headers, 1):
        ws.cell(row=3, column=col).value = h
    _header_style(ws, 3, len(headers))
    _auto_filter(ws, 3, len(headers))
    _freeze(ws, 4)

    # Compute rows using the same logic as HTML report
    resources_by_type = scan_data.get("resources_by_type", {})
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

    plan_rows = [
        ("Defender for Servers", "VM / Arc Machine", vms, 4.95, vms * 4.95, 13.95, vms * 13.95,
         "P1: foundational + Defender XDR. P2: full vuln mgmt + JIT access."),
        ("Defender for Storage", "Storage Account", storage, 10.00, storage * 10.00, None, None,
         "Malware scanning + sensitive data discovery."),
        ("Defender for Containers", "AKS Cluster (est.)", aks, 7.00, aks * 7.00, None, None,
         "$7/vCore/mo estimate; varies by cluster size."),
        ("Defender for App Service", "App Service Instance", app_services, 14.60, app_services * 14.60, None, None,
         "Threat detection for web apps and APIs."),
        ("Defender for Key Vault", "Key Vault", key_vaults, 2.00, key_vaults * 2.00, None, None,
         "Est. ~$0.02/10K ops; $2/vault/mo at moderate use."),
        ("Defender for SQL", "SQL Server / MI", sql, 15.00, sql * 15.00, None, None,
         "Est. $0.015/vCore/hr; $15/server at ~4 vCores avg."),
    ]

    p1_grand_total = 0.0
    p2_grand_total = 0.0
    row_num = 4
    for plan, unit, count, p1_price, p1_total, p2_price, p2_total, notes in plan_rows:
        if count == 0:
            continue
        ws.cell(row=row_num, column=1).value = plan
        ws.cell(row=row_num, column=2).value = unit
        ws.cell(row=row_num, column=3).value = count
        ws.cell(row=row_num, column=4).value = p1_price
        ws.cell(row=row_num, column=5).value = round(p1_total, 2)
        ws.cell(row=row_num, column=6).value = p2_price
        ws.cell(row=row_num, column=7).value = round(p2_total, 2) if p2_total is not None else None
        ws.cell(row=row_num, column=8).value = notes
        p1_grand_total += p1_total
        p2_grand_total += (p2_total if p2_total is not None else p1_total)
        row_num += 1

    # Grand total row
    if row_num > 4:
        from openpyxl.styles import Border, Side
        top_border = Border(top=Side(style="medium"))
        for col in range(1, 9):
            ws.cell(row=row_num, column=col).border = top_border
        ws.cell(row=row_num, column=1).value = "TOTAL MONTHLY ESTIMATE"
        ws.cell(row=row_num, column=1).font = Font(bold=True)
        ws.cell(row=row_num, column=5).value = round(p1_grand_total, 2)
        ws.cell(row=row_num, column=5).font = Font(bold=True)
        ws.cell(row=row_num, column=7).value = round(p2_grand_total, 2)
        ws.cell(row=row_num, column=7).font = Font(bold=True)
        ws.cell(row=row_num, column=8).value = "If all billable resources enrolled. EA/MCA discounts not included."
        ws.cell(row=row_num, column=8).fill = PatternFill("solid", fgColor="DAEEF3")
        for col in [1, 5, 7, 8]:
            ws.cell(row=row_num, column=col).fill = PatternFill("solid", fgColor="DAEEF3")

    _col_widths(ws, [32, 22, 14, 24, 24, 24, 24, 60])


def _write_defender_posture_sheet(wb, scan_data: dict):
    """Defender for Cloud plan posture per subscription (Microsoft.Security/pricings)."""
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    ws = wb.create_sheet("DefenderPosture")

    # Title + reference row
    ws.merge_cells(f"A1:{get_column_letter(7)}1")
    title_cell = ws["A1"]
    title_cell.value = (
        "Defender for Cloud — Plan Posture (Microsoft.Security/pricings). "
        "VMs/VMSS/Arc are analysed per-resource (see DefenderServersCoverage); "
        "other workloads are subscription-level. Requires Reader RBAC."
    )
    title_cell.font = Font(italic=True, size=9, color="1F4E79")
    title_cell.fill = PatternFill("solid", fgColor="D6E4F0")
    title_cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 30

    headers = [
        "Subscription ID", "Defender Plan", "Tier (Standard=On)",
        "Enabled", "Sub-plan", "Resources Coverage", "Enabled Extensions",
    ]
    for col, h in enumerate(headers, 1):
        ws.cell(row=2, column=col).value = h
    _header_style(ws, 2, len(headers))
    _auto_filter(ws, 2, len(headers))
    _freeze(ws, 3)

    sub_names = {
        s.get("subscriptionId", ""): s.get("displayName", "")
        for s in scan_data.get("subscriptions", [])
    }
    _ = sub_names  # subscription name available if a column is added later

    posture = scan_data.get("defender_posture", [])
    posture_sorted = sorted(
        posture,
        key=lambda p: (p.get("subscriptionId", ""), p.get("planDisplayName", "")),
    )
    for row, p in enumerate(posture_sorted, 3):
        ws.cell(row=row, column=1).value = p.get("subscriptionId", "")
        ws.cell(row=row, column=2).value = p.get("planDisplayName", p.get("plan", ""))
        ws.cell(row=row, column=3).value = p.get("pricingTier", "")
        ws.cell(row=row, column=4).value = "Yes" if p.get("enabled") else "No"
        ws.cell(row=row, column=5).value = p.get("subPlan", "")
        ws.cell(row=row, column=6).value = p.get("resourcesCoverageStatus", "")
        ws.cell(row=row, column=7).value = ", ".join(p.get("enabledExtensions", []) or [])
        fill = PatternFill("solid", fgColor=COLOR_OK) if p.get("enabled") else PatternFill("solid", fgColor=COLOR_LOW)
        ws.cell(row=row, column=4).fill = fill

    _col_widths(ws, [38, 38, 18, 10, 18, 22, 45])


def _write_defender_servers_coverage_sheet(wb, scan_data: dict):
    """Per-resource Defender for Servers coverage for VMs / VMSS / Arc Machines."""
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from collectors.defender_posture import build_servers_resource_coverage

    rows = build_servers_resource_coverage(
        scan_data.get("defender_posture", []),
        scan_data.get("resources_by_type", {}),
    )
    if not rows:
        return

    ws = wb.create_sheet("DefenderServersCoverage")

    ws.merge_cells(f"A1:{get_column_letter(8)}1")
    title_cell = ws["A1"]
    title_cell.value = (
        "Defender for Servers — Individual Resource Coverage (per-resource). "
        "Derived from the Defender for Servers plan tier of each subscription; "
        "VM-level overrides may apply where coverage is PartiallyCovered."
    )
    title_cell.font = Font(italic=True, size=9, color="1F4E79")
    title_cell.fill = PatternFill("solid", fgColor="D6E4F0")
    title_cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 30

    headers = [
        "Resource", "Type", "Covered", "Plan Tier",
        "Sub-plan", "Location", "Resource Group", "Subscription ID",
    ]
    for col, h in enumerate(headers, 1):
        ws.cell(row=2, column=col).value = h
    _header_style(ws, 2, len(headers))
    _auto_filter(ws, 2, len(headers))
    _freeze(ws, 3)

    rows_sorted = sorted(rows, key=lambda r: (not r.get("covered"), r.get("name", "")))
    for row, r in enumerate(rows_sorted, 3):
        ws.cell(row=row, column=1).value = r.get("name", "")
        ws.cell(row=row, column=2).value = r.get("type", "").split("/")[-1]
        ws.cell(row=row, column=3).value = "Yes" if r.get("covered") else "No"
        ws.cell(row=row, column=4).value = r.get("serversPlanTier", "")
        ws.cell(row=row, column=5).value = r.get("subPlan", "")
        ws.cell(row=row, column=6).value = r.get("location", "")
        ws.cell(row=row, column=7).value = r.get("resourceGroup", "")
        ws.cell(row=row, column=8).value = r.get("subscriptionId", "")
        fill = PatternFill("solid", fgColor=COLOR_OK) if r.get("covered") else PatternFill("solid", fgColor=COLOR_HIGH)
        ws.cell(row=row, column=3).fill = fill

    _col_widths(ws, [40, 22, 10, 14, 16, 16, 28, 38])


def _write_defender_coverage_gap_sheet(wb, scan_data: dict):
    """B2 — Coverage gap & cost to protect (inventory × real plan posture)."""
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from collectors.defender_pricing import compute_coverage_gap, total_gap_monthly_cost, pricing_source_label

    gap_rows = compute_coverage_gap(
        scan_data.get("resources_by_type", {}),
        scan_data.get("defender_posture", []),
    )
    if not gap_rows:
        return
    price_src = pricing_source_label(gap_rows)

    ws = wb.create_sheet("DefenderCoverageGap")

    ws.merge_cells(f"A1:{get_column_letter(8)}1")
    title_cell = ws["A1"]
    title_cell.value = "Defender for Cloud — Coverage Gap & Cost to Protect"
    title_cell.font = Font(bold=True, size=13, color="FFFFFF")
    title_cell.fill = PatternFill("solid", fgColor="1F4E79")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    ws.merge_cells(f"A2:{get_column_letter(8)}2")
    disc_cell = ws["A2"]
    disc_cell.value = (
        "Billable units cross-referenced with the real plan posture (Microsoft.Security/pricings). "
        "'Unprotected' = units in subscriptions where the plan is NOT enabled. "
        f"Prices: {price_src}; EA/MCA/CSP discounts, free tiers, and usage-based plans (e.g. Cosmos DB) not reflected."
    )
    disc_cell.font = Font(italic=True, size=9, color="7F7F7F")
    disc_cell.fill = PatternFill("solid", fgColor="FFF2CC")
    disc_cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.row_dimensions[2].height = 30

    headers = [
        "Defender Plan", "Billable Unit", "Total Units",
        "Protected", "Unprotected (gap)", "Price/Unit/Mo (USD)",
        "Gap Monthly Cost (USD)", "Notes",
    ]
    for col, h in enumerate(headers, 1):
        ws.cell(row=3, column=col).value = h
    _header_style(ws, 3, len(headers))
    _auto_filter(ws, 3, len(headers))
    _freeze(ws, 4)

    row_num = 4
    for r in gap_rows:
        ws.cell(row=row_num, column=1).value = r["plan"]
        ws.cell(row=row_num, column=2).value = r["unit"]
        ws.cell(row=row_num, column=3).value = r["total_units"]
        ws.cell(row=row_num, column=4).value = r["protected_units"]
        ws.cell(row=row_num, column=5).value = r["unprotected_units"]
        ws.cell(row=row_num, column=6).value = r["price"] if r["priceable"] else "Usage-based"
        ws.cell(row=row_num, column=7).value = r["gap_monthly_cost"] if r["priceable"] else None
        ws.cell(row=row_num, column=8).value = r["notes"]
        if r["unprotected_units"] > 0:
            ws.cell(row=row_num, column=5).fill = PatternFill("solid", fgColor=COLOR_HIGH)
        else:
            ws.cell(row=row_num, column=5).fill = PatternFill("solid", fgColor=COLOR_OK)
        row_num += 1

    # Grand total row
    total_units = sum(r["total_units"] for r in gap_rows)
    total_unprotected = sum(r["unprotected_units"] for r in gap_rows)
    total_protected = total_units - total_unprotected
    gap_cost = total_gap_monthly_cost(gap_rows)
    top_border = Border(top=Side(style="medium"))
    for col in range(1, 9):
        ws.cell(row=row_num, column=col).border = top_border
        ws.cell(row=row_num, column=col).fill = PatternFill("solid", fgColor="DAEEF3")
    ws.cell(row=row_num, column=1).value = "TOTAL"
    ws.cell(row=row_num, column=1).font = Font(bold=True)
    ws.cell(row=row_num, column=3).value = total_units
    ws.cell(row=row_num, column=4).value = total_protected
    ws.cell(row=row_num, column=5).value = total_unprotected
    ws.cell(row=row_num, column=7).value = round(gap_cost, 2)
    ws.cell(row=row_num, column=7).font = Font(bold=True)
    ws.cell(row=row_num, column=8).value = f"Monthly cost to protect all unprotected units (prices: {price_src})."

    _col_widths(ws, [34, 22, 12, 12, 18, 20, 24, 55])


