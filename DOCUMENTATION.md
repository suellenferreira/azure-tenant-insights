# Azure Tenant Insights — Technical Documentation

> **Version:** 3.1
> **Last Updated:** August 6, 2026
> **Audience:** Architects, engineers, security and governance teams, contributors, and reviewers
>
> This document explains how ATI collects, processes, and presents Azure tenant
> information. It complements the user-oriented [README.md](./README.md), which
> explains why and when to run the tool.

---

## 📋 Table of Contents

- [Item 0: Modernization Signals](#item-0-modernization-signals)
- [Item 1: Flag Paradigm Inversion](#item-1-flag-paradigm-inversion)
- [Item 2: Tenant & Subscription Metadata](#item-2-tenant--subscription-metadata)
- [Item 3: Active Regions Analytics](#item-3-active-regions-analytics)
- [Item 4: Interactive Report Naming](#item-4-interactive-report-naming)
- [Item 5: Excel Overview Sheet Styling](#item-5-excel-overview-sheet-styling)
- [Item 6: CAF Landing Zone Observations](#item-6-caf-landing-zone-observations)
- [Item 7: Defender Posture, Coverage Gap & Live Pricing](#item-7-defender-for-cloud--posture-coverage-gap--live-pricing)
- [Item 8: Excel Navigation & Report UX Enhancements](#item-8-excel-navigation--report-ux-enhancements)
- [Item 9: Resource Classification Taxonomy](#item-9-resource-classification-taxonomy)
- [Item 10: Architecture Diagrams (draw.io)](#item-10-architecture-diagrams-drawio)
- [Item 11: Cloud Modernization & Opportunity Assessment](#item-11-cloud-modernization--opportunity-assessment)
- [How to Use This Document](#how-to-use-this-document)
- [Assessment Model](#assessment-model)
- [Data Sources & References](#data-sources--references)

---

## How to Use This Document

This is the technical reference for understanding ATI's methodology and boundaries.

Use it when you need to:

- Validate where a report value comes from;
- Understand which Azure API or property supports a finding;
- Review how a classification or signal is calculated;
- Distinguish observed data, rules-based findings, and inferred signals;
- Configure or extend ATI;
- Review limitations before using the output in a customer or executive discussion.

For first-time users, start with the [README.md](./README.md), especially the
[Why and When to Run ATI](./README.md#why-and-when-to-run-ati) section.

The [TESTING_GUIDE.md](./TESTING_GUIDE.md) is maintained separately for contributors
and reviewers who need to validate implementation behavior. It is not part of the
standard end-user reading path.

## Assessment Model

ATI presents three levels of assessment information:

### Observed Data

Information directly collected from official Azure APIs or aggregated from collected
resources. Examples include resource types and properties, subscription and
resource-group relationships, regions, Policy states, Advisor recommendations,
Resource Health events, Defender posture, and Cost Management data when available.

### Rules-Based Findings

Findings produced by applying documented rules to observed data. Examples include
misconfiguration findings, deprecated resource matches, CAF landing zone
observations, WAF pillar groupings, and Defender coverage gaps.

### Inferred Signals

Signals derived from resource patterns and classifications. These support discovery
and prioritization, not definitive claims. Examples include modernization dimension
scores, cloud-native technology presence, AI/data/integration adoption signals, and
opportunity indicators.

Inferred signals should be validated against application architecture, business
requirements, technical constraints, and organizational standards.

---

## Item 0: Modernization Signals

### What It Does
Detects technology adoption patterns indicating cloud-native modernization readiness. Reports **8 distinct modernization categories** with resource counts.

### Data Source
[Azure Resource Graph](https://learn.microsoft.com/en-us/azure/governance/resource-graph/overview) — Resource type enumeration via KQL queries. All resource type names are the official ARM provider namespaces as enumerated by Azure Resource Graph (`type` field).

### Signals Detected

| Signal Category | Official ARM Resource Types | MS Documentation |
|---|---|---|
| **AI/ML & Azure AI Foundry** | `microsoft.cognitiveservices/accounts`<br>`microsoft.machinelearningservices/workspaces`<br>`microsoft.botservice/botservices` | [Cognitive Services](https://learn.microsoft.com/en-us/azure/cognitive-services/) · [Azure ML / AI Foundry](https://learn.microsoft.com/en-us/azure/machine-learning/) |
| **Microsoft Fabric** | `microsoft.fabric/capacities` | [Microsoft Fabric Admin](https://learn.microsoft.com/en-us/fabric/admin/capacity-settings) |
| **Containerization** | `microsoft.containerregistry/registries`<br>`microsoft.containerservice/managedclusters`<br>`microsoft.app/containerapps`<br>`microsoft.containerinstance/containergroups` | [AKS](https://learn.microsoft.com/en-us/azure/aks/) · [Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/) |
| **Serverless & Integration** | `microsoft.logic/workflows`<br>`microsoft.eventgrid/namespaces`<br>`microsoft.eventgrid/topics` | [Logic Apps](https://learn.microsoft.com/en-us/azure/logic-apps/) · [Event Grid](https://learn.microsoft.com/en-us/azure/event-grid/) |
| **Data & Analytics Platform** | `microsoft.databricks/workspaces`<br>`microsoft.synapse/workspaces`<br>`microsoft.datafactory/factories`<br>`microsoft.datalakestore/accounts`<br>`microsoft.analysisservices/servers` | [Databricks](https://learn.microsoft.com/en-us/azure/databricks/) · [Synapse](https://learn.microsoft.com/en-us/azure/synapse-analytics/) · [Data Factory](https://learn.microsoft.com/en-us/azure/data-factory/) |
| **Real-time Streaming** | `microsoft.eventhub/namespaces`<br>`microsoft.streamanalytics/streamingjobs`<br>`microsoft.kusto/clusters` | [Event Hubs](https://learn.microsoft.com/en-us/azure/event-hubs/) · [Stream Analytics](https://learn.microsoft.com/en-us/azure/stream-analytics/) · [ADX](https://learn.microsoft.com/en-us/azure/data-explorer/) |
| **Modern PaaS Databases** | `microsoft.documentdb/databaseaccounts`<br>`microsoft.sql/managedinstances`<br>`microsoft.dbforpostgresql/flexibleservers`<br>`microsoft.dbformysql/flexibleservers`<br>`microsoft.cache/redis`<br>`microsoft.cache/redisenterprise` | [Cosmos DB](https://learn.microsoft.com/en-us/azure/cosmos-db/) · [SQL MI](https://learn.microsoft.com/en-us/azure/azure-sql/managed-instance/) · [PostgreSQL Flexible](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/) · [Redis](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/) |
| **API & Integration Platform** | `microsoft.apimanagement/service`<br>`microsoft.apicenter/services`<br>`microsoft.servicebus/namespaces` | [API Management](https://learn.microsoft.com/en-us/azure/api-management/) · [API Center](https://learn.microsoft.com/en-us/azure/api-center/) · [Service Bus](https://learn.microsoft.com/en-us/azure/service-bus-messaging/) |

> **Note on AI Foundry**: Azure AI Foundry Hubs and Projects share the `microsoft.machinelearningservices/workspaces` resource provider with Azure Machine Learning, differentiated by the `kind` property (`Hub` or `Project`). ATI enumerates by resource type, so any such workspace correctly signals a modern AI platform presence.

> **Note on Microsoft Fabric**: `microsoft.fabric/capacities` is the GA ARM resource type for Microsoft Fabric F-SKU capacities, available since November 2023.

### Methodology

**Location:** `writers/html_technical.py::_detect_modernization_signals()`

Each category is defined as a list of official ARM resource type strings. For each category, ATI sums the count of resources matching any of those types (via `resources_by_type.get(rt, [])`) and appends a signal entry when count > 0.

**Signal Output Format:**
```json
{
    "message": "AI/ML & Azure AI Foundry resources detected (Cognitive Services, Azure ML, AI Foundry)",
    "count": 5
}
```

### Limitations & Notes

⚠️ **INFERRED ANALYSIS** — No official Microsoft API provides modernization readiness scores.  
✓ Based on official ARM resource type enumeration from Azure Resource Graph — no inferences or fabricated types.  
✓ Signals are indicative only — validate against your organizational architecture and development standards.  
✓ Azure Functions are deployed as `microsoft.web/sites` (kind=functionapp); ATI does not count these to avoid false positives from App Service web apps.

### Reports Where Shown

- **Executive Report**: Circular badge indicators (🚀 Modernization Signals)
- **Technical Report**: Detailed list with counts in Infrastructure section

---

## Item 1: Flag Paradigm Inversion

### What It Does
Changes command-line interface from opt-in model (`--include-*`) to opt-out model (`--skip-*`).  
**Impact:** Defender for Cloud and Cost Management are now **enabled by default**.

### Before (Old Paradigm)
```bash
# Had to explicitly include each optional data source
python invoke_ati.py --include-defender --include-costs
```

### After (New Paradigm)
```bash
# Defender and Costs are ON by default; skip them if not needed
python invoke_ati.py                              # Includes defender + costs
python invoke_ati.py --skip-defender              # Excludes defender only
python invoke_ati.py --skip-defender --skip-costs # Excludes both
```

### Files Modified

- **`invoke_ati.py`** (lines 88-101):
  - Changed argparse definitions: `--skip-defender`, `--skip-costs` instead of `--include-*`
  - Changed conditionals: `if not args.skip_defender` instead of `if args.include_defender`
  - Docstring updated (lines 1-30)

- **`README.pt-BR.md`** (Parameters Reference table):
  - Updated to document new `--skip-*` paradigm

### Rationale

**User Experience:** Most users want full analysis; opt-out is more intuitive than opt-in.  
**Security Data:** Defender is critical for compliance — should be included by default.  
**Cost Tracking:** Organizations benefit from cost visibility — included by default.

---

## Item 2: Tenant & Subscription Metadata

### What It Does
Displays tenant name/ID and subscriptions list in both HTML report headers.  
**Format:** `Tenant: Azure Tenant Name (tenant-id) | Subscriptions: sub1, sub2, sub3`

### Data Source

[Azure Subscription Client](https://learn.microsoft.com/en-us/python/api/azure-mgmt-subscription/) via `SubscriptionClient.subscriptions.list()`

### Implementation

**Executive Report:** `writers/html_executive.py` (lines 25-37, 69-85)
```python
tenant_name = metadata.get("tenant_name", "Unknown")
subscriptions = [sub.get("displayName") for sub in subscriptions_list]
# Display in meta-bar: "Tenant: {tenant_name} ({tenant_id})"
# Display: "Subscriptions: {', '.join(subscriptions)}"
```

**Technical Report:** `writers/html_technical.py` (lines 43-62)
```python
# Same extraction logic as executive report
# Metadata synchronized across both reports
```

### Reports Where Shown

- **Executive Report**: Meta-bar (top-right corner)
- **Technical Report**: Meta-bar (synchronized format)
- **Excel Workbook**: Subscriptions sheet + Overview metadata

---

## Item 3: Active Regions Analytics

### What It Does
Extracts resource location data and aggregates by Azure region. Displays top 12 regions with counts and percentages.

### Data Source

`properties.location` field from [Azure Resource Graph](https://learn.microsoft.com/en-us/azure/governance/resource-graph/overview) resources

### Methodology

**Location:** `writers/html_executive.py::_analyze_regions()` & `writers/html_technical.py::_analyze_regions()`

```python
def _analyze_regions(resources_by_type: dict) -> dict:
    """
    Extract locations from all resources and aggregate by region.
    
    Steps:
    1. Iterate resources_by_type dictionary
    2. For each resource, extract: location = resource.get("location", "").strip()
    3. Filter: skip empty, skip "global", skip "n/a"
    4. Group by region name, count occurrences
    5. Sort by count descending, take top 12
    6. Calculate percentage: (region_count / total) * 100
    7. Return dict with top_regions, region_labels (JSON), region_values (JSON)
    """
    region_counts = {}
    for resource_list in resources_by_type.values():
        for resource in resource_list:
            location = resource.get("location", "").strip()
            if location and location.lower() not in ["global", "n/a"]:
                region_counts[location] = region_counts.get(location, 0) + 1
    
    total = sum(region_counts.values())
    sorted_regions = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)[:12]
    
    top_regions = [{
        "region": r[0].replace("_", " ").title(),
        "count": r[1],
        "percentage": round((r[1]/total*100), 1)
    } for r in sorted_regions]
    
    return {
        "top_regions": top_regions,
        "region_labels": json.dumps([r["region"] for r in top_regions]),
        "region_values": json.dumps([r["count"] for r in top_regions]),
        "total_regions": len(region_counts)
    }
```

### Output

**Executive Report:**
- Horizontal bar chart (Chart.js v4.4.0)
- Color: #70AD47 (Microsoft green)
- Title: "🌍 Active Regions Distribution"

**Technical Report:**
- Detailed table: Region | Count | Percentage
- Sidebar navigation link: "🌍 Regional Distribution"
- Section: Infrastructure category

### Use Cases

✓ Identify primary deployment regions  
✓ Validate HA/DR regional spread  
✓ Spot consolidation opportunities  
✓ Regional capacity planning  
✓ Cost optimization (region-based pricing analysis)

### Limitations

⚠️ "Global" resources (CDN endpoints, DNS zones) are excluded.  
⚠️ Multi-region resources appear once per region.  
⚠️ Does not analyze actual traffic distribution — location-based only.

---

## Item 4: Interactive Report Naming

### What It Does
Prompts user for custom report prefix at scan start. If user presses Enter, uses default timestamp-based name.

### Implementation

**Location:** `invoke_ati.py` (lines 146-162)

```python
# After "Scanning subscriptions..." message
print("\n[Optional] Custom report name (or press Enter for default):")
print("[DEFAULT] Format: ATI_Scan_YYYY-MM-DD_HH-MM-SS")
custom_name = input("> ").strip()

if custom_name:
    report_prefix = f"ATI_{custom_name}_{scan_timestamp}"
else:
    report_prefix = f"ATI_Scan_{scan_timestamp}"

# report_prefix is used for all output filenames
```

### Output File Examples

```
# Default (Enter pressed)
ATI_Scan_2026-06-16_14-30-45_Inventory.xlsx
ATI_Scan_2026-06-16_14-30-45_Executive.html
ATI_Scan_2026-06-16_14-30-45_Technical.html

# Custom name provided
ATI_Production_Audit_2026-06-16_14-30-45_Inventory.xlsx
ATI_Production_Audit_2026-06-16_14-30-45_Executive.html
ATI_Production_Audit_2026-06-16_14-30-45_Technical.html
```

### UX Benefits

✓ Descriptive names for archival and comparison  
✓ Fast default if detailed naming not needed  
✓ No breaking changes (existing behavior preserved)

---

## Item 5: Excel Overview Sheet Styling

### What It Does
Implements professional dark-theme styling for the Excel Overview sheet with color-coded metrics and improved visual hierarchy.

### Design Elements

**Location:** `writers/excel_writer.py::_write_overview_sheet()`

#### 1. Dark Theme Header
- Background Color: #1F4E79 (Microsoft Navy Blue)
- Font Color: White
- Font Size: 18px, Bold
- Row Height: 42px

#### 2. Metadata Section
- Background: #E7E6E6 (Light Gray)
- Font: Bold, 10px
- Data Background: #F5F5F5 (Very Light Gray)
- Creates visual separation for scan metadata

#### 3. KPI Cards
- Color Coding:
  - Green (#70AD47): Healthy metrics
  - Yellow (#FFFF99): Medium priority
  - Orange (#FFC000): High priority
  - Red (#C00000): Critical alerts
- Borders: 1pt thin #D3D3D3
- Row Heights: 22px for data rows
- Alignment: Centered, vertically centered

#### 4. Section Headers (for Top Resource Types & Advisor)
- Background: #1F4E79 (Navy Blue)
- Font Color: White, Bold, 11px
- Merged Cells for alignment
- Height: 24px

#### 5. Column Widths (optimized)
```
A: 28px (labels)
B: 18px (KPI values)
C: 16px (spacer)
D: 32px (resource type labels)
E: 14px (resource counts)
F: 4px  (spacer)
G: 28px (advisor labels)
H: 14px (advisor counts)
```

#### 6. Page Setup
- Margin Left: 0.5"
- Margin Right: 0.5"
- Margin Top: 0.75"
- Margin Bottom: 0.75"
- Paper Size: Letter

### Implementation Details

```python
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

# Header styling
title_cell.fill = PatternFill("solid", fgColor=COLOR_HEADER_BG)  # #1F4E79
title_cell.font = Font(bold=True, size=18, color="FFFFFF")

# KPI values with color coding
value_cell.fill = PatternFill("solid", fgColor=color)  # Dynamic by severity
value_cell.border = Border(
    left=Side(style="thin", color="D3D3D3"),
    right=Side(style="thin", color="D3D3D3"),
    top=Side(style="thin", color="D3D3D3"),
    bottom=Side(style="thin", color="D3D3D3"),
)
```

### Output

Opens in Excel/Calc with professional, customer-friendly appearance:
- Executive-ready styling
- Clear visual hierarchy
- Instant metric recognition via color coding
- Print-optimized page setup

---

## Item 6: CAF Landing Zone Observations

### What It Does
Evaluates infrastructure against [Microsoft Cloud Adoption Framework](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/) (CAF) governance and design principles. Provides 5 pillar assessment with actionable remediation guidance.

### Data Sources

| Source | API/Service | Data Used |
|---|---|---|
| Resource Graph | [Azure Resource Graph](https://learn.microsoft.com/en-us/azure/governance/resource-graph/overview) | Resource types (Management Groups, VNets, NSGs, Key Vault, etc.) |
| Azure Advisor | [Azure Advisor](https://learn.microsoft.com/en-us/azure/advisor/) | WAF recommendations (Security, Cost, Performance, etc.) |
| Azure Policy | [Policy Insights](https://learn.microsoft.com/en-us/azure/governance/policy/overview) | Compliance violations, assigned policies |
| Resource Health | [Resource Health API](https://learn.microsoft.com/en-us/azure/resource-health/resource-health-overview) | Degraded resources, health events |
| Defender for Cloud | [Defender API](https://learn.microsoft.com/en-us/azure/defender-for-cloud/) | Security findings (if enabled) |

### CAF Pillars Assessed

#### 1. Security Pillar
**Primary Reference:** [Security design in Azure — CAF Landing Zone Design Area | Microsoft Learn](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/design-area/security)

> This is the authoritative CAF guidance for security controls in Azure Landing Zones. It covers identity, network topology, encryption, security posture, compliance, and governance controls.

**Additional References:**
- [CAF Security Pillar overview](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/secure/)
- [Identity and access management design area](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/design-area/identity-access)
- [Network topology and connectivity design area](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/design-area/network-topology-and-connectivity)
- [Encryption and key management in Azure](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/design-area/encryption-and-keys)

| Check | Resource Types | Condition | CAF Area |
|---|---|---|---|
| **Entra ID Config** | `microsoft.aad/*` | Count + conditional access guidance | Identity &amp; Access |
| **Network Segmentation** | `microsoft.network/virtualnetworks`, `microsoft.network/networksecuritygroups` | VNet + NSG presence for micro-segmentation | Network topology |
| **Private Connectivity** | `microsoft.network/privateendpoints`, `microsoft.network/privatednszones` | Private endpoints for PaaS isolation | Network isolation |
| **Secrets Management** | `microsoft.keyvault/vaults` | Key Vault configuration validation | Encryption &amp; keys |
| **Security Posture** | Defender findings | Advisor + Defender recommendations | Security posture |

**How the reference appears in reports:**
- **Technical HTML** — each security observation contains an inline link to the CAF Security design area page
- **Technical HTML** — a reference block appears at the bottom of the Landing Zone section
- **Executive HTML** — security strategic recommendations link to the CAF Security design area
- **Executive HTML** — footer includes the CAF Security design area reference
- **Excel** — SecurityAssessments sheet has a reference row (row 1) before the data headers
- **Excel** — Overview sheet has a "CAF References" section (row 20–21)

#### 2. Cost Management Pillar
**Reference:** [CAF Cost Management](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/govern/cost-management-discipline/)

| Check | Data Source | Condition |
|---|---|---|
| **Tag Coverage** | Resource properties tags | Percentage of tagged resources (threshold: 60% = warn, 80% = pass) |
| **Chargeback Model** | Tags + Policy | Enforcement of environment/owner/cost-center tags |
| **Policy Enforcement** | Azure Policy | Automatic cost controls via policy |

#### 3. Operational Excellence Pillar
**Reference:** [CAF Operational Excellence](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/operational-excellence/)

| Check | Resource Types | Condition |
|---|---|---|
| **Centralized Logging** | Log Analytics Workspaces | Count + guidance for federated vs. centralized |
| **Monitoring** | Application Insights | Count + observability recommendations |
| **Modernization Path** | Deprecated resources | Migration guidance for retiring services |

#### 4. Reliability Pillar
**Reference:** [CAF Reliability Pillar](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/operational-excellence/define-reliability/)

| Check | Resource Types | Condition |
|---|---|---|
| **Backup Strategy** | Recovery Services Vaults | RPO/RTO validation |
| **Availability Monitoring** | Resource Health | Health events + degraded resources |

#### 5. Governance Pillar
**Reference:** [CAF Governance](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/govern/)

| Check | Resource Types | Condition |
|---|---|---|
| **Hierarchy** | Management Groups | Enterprise governance structure |
| **Policy Compliance** | Azure Policy Insights | Non-compliant resources count |

### Observation Format

**Location:** `writers/html_technical.py::_landing_zone_section()`

Each observation follows this pattern:

```
✓ [GREEN] Compliant finding — with inline CAF Security link for security-pillar items
  
⚠ [ORANGE] Remediation needed — with inline CAF Security link for security-pillar items
```

Security-pillar observations include a direct hyperlink to the CAF Security design area, identifying the sub-area (e.g., "Identity & Access Management", "Network isolation & private access").

### Reports Where Shown

- **Technical Report**: "🏗 Landing Zone" section — CAF Security Design Area reference block at bottom of section
- **Executive Report**: Strategic recommendation for Security — action field includes CAF Security URL; footer includes the reference
- **Excel**: SecurityAssessments sheet — reference row (row 1, light blue); Overview sheet — CAF References section
- **Format**: Separate div for each observation with color-coded indicator
- **Disclaimers**: Clearly labeled as INFERRED with validation instructions

### Limitations & Notes

⚠️ **INFERRED ANALYSIS** — Pattern-based on resource presence, not organizational design review.  
✓ **CAF-Aligned** — References official Microsoft CAF documentation for each pillar.  
✓ **Actionable** — Provides specific remediation steps linked to CAF guidance.  
✓ **Governance-Focused** — Emphasizes policy automation and role-based access control.

---

## Item 7: Defender for Cloud — Posture, Coverage Gap & Live Pricing

### What It Does

Adds three Defender for Cloud capabilities on top of the existing assessments collector:

1. **Plan posture (B1)** — reports which Defender plans are actually enabled per subscription, plus per-resource coverage for servers.
2. **Coverage gap & cost to protect (B2)** — cross-references the inventory with the real posture to estimate how many billable units are **not yet protected** and the **monthly cost to close the gap**.
3. **Live pricing** — fetches current Defender unit prices from the public Azure Retail Prices API, with the built-in list prices kept as an offline fallback.

### Data Sources

| Capability | Source | Auth / RBAC |
|---|---|---|
| Plan posture | [`Microsoft.Security/pricings`](https://learn.microsoft.com/en-us/rest/api/defenderforcloud/pricings/list) via Azure Resource Graph (`securityresources` table) | `Reader` |
| Unit prices | [Azure Retail Prices API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices) (`https://prices.azure.com/api/retail/prices`) | None (public) |

### Methodology

**Posture** — `collectors/defender_posture.py` queries the `securityresources` table for `type == 'microsoft.security/pricings'`. `pricingTier == 'Standard'` means the plan is enabled. VMs / VMSS / Arc Machines support per-resource status, so they are analysed individually; other workloads are reported at the subscription/plan level (an official limitation of the pricings API, not of ATI).

**Coverage gap** — `collectors/defender_pricing.py::compute_coverage_gap()` counts billable units per plan from the inventory, marks units in subscriptions where the plan is disabled as **unprotected**, and multiplies by the unit price to estimate the monthly cost to protect them. Usage-based plans (e.g. Cosmos DB, per 100 RU/s) are counted but not priced.

**Live pricing** — `fetch_live_prices()` queries the Retail Prices API once per run (process-level cache), filtering `serviceName eq 'Microsoft Defender for Cloud'`, matching each plan to its retail meter (excluding Trial meters), and normalising hourly meters to monthly (× 730). On any failure it logs a warning and returns an empty map, so `compute_coverage_gap()` falls back to the hardcoded list prices and labels each row accordingly (`price_source` = `live` / `fallback`).

### Reports Where Shown

- **Excel**: `DefenderPosture`, `DefenderServersCoverage`, `DefenderCoverageGap`, `DefenderCostEstimate` sheets.
- **Executive Report**: Defender posture summary + coverage-gap line (with price source).
- **Technical Report**: "Defender — Plan Posture" section and "Coverage Gap & Cost to Protect" table (with price source).

### Limitations & Notes

⚠️ **APPROXIMATE ESTIMATE** — Prices are public **list** pricing; EA/MCA/CSP discounts, free tiers, and usage-based plans are not reflected.  
✓ Live prices track Microsoft's current published pricing; the offline fallback is clearly labelled as possibly outdated.  
✓ A failed/offline price fetch is surfaced in the terminal **COLLECTION WARNINGS / ERRORS** block and in the report's **Data collection notes**.  
✓ Plan posture needs only `Reader` RBAC — less restrictive than the `Security Reader` required for Defender assessments.

---

## Item 8: Excel Navigation & Report UX Enhancements

### What It Does
Adds navigation, classification, and transparency features across the Excel workbook and both HTML reports.

**Excel (`writers/excel_writer.py`):**
- **Index sheet** — positioned right after `Overview`, lists every worksheet with a hyperlink; each sheet carries a **↩ Index** back-link.
- **Collision-free sheet naming** — a single, shared `resource_type → sheet name` map. A short namespace token is prefixed **only** when two providers would otherwise produce the same name (e.g., `Cmp-Virtualmachinetemplates` vs `VMw-Virtualmachinetemplates`).
- **All types up to the Excel limit** — every resource type gets its own sheet up to Excel's hard cap of 255; the remainder stay in `AllResources`. A **scope-aware warning** is logged when the type-sheet count is high (subscription ≥ 40, management group ≥ 60, tenant ≥ 75; env-overridable), plus a hard warning at 200.
- **Category classification** — `AllResources` gains a **Category** column (Azure-native / Hybrid-Arc / Migrate) and `Overview` gains a **Resource Origin** summary.
- **Data Collection Notes** — the Overview footer mirrors the HTML "Data Collection Notes" (collector warnings / skipped sources).

**Executive HTML (`writers/html_executive.py`):**
- Collapsible sections with **Expand All / Collapse All** and per-section toggles.
- Strategic recommendations rendered as **priority-colored cards**.
- **Zero Trust** posture summary as color-coded cards with per-principle descriptions.
- Subtle header link to the **Data Collection Notes** at the end.

**Technical HTML (`writers/html_technical.py`):**
- **Resources by Subscription** chart labeled by subscription **name** (not GUID).
- WAF findings tables use **progressive loading** (30 rows at a time, up to 300 per pillar; the full list is in the Excel export). Column filters remain search-all across loaded rows.
- **Column search** on the **Defender Plans by Subscription** table.
- Subtle header link to the **Data Collection Notes**.

---

## Item 9: Resource Classification Taxonomy

### What It Does
Classifies every resource type into a 3-tier assessment taxonomy plus a Publisher axis, driven by `config/resource_classification.yaml`.

- **Tier 1 — Technical Category** (~20): Compute-VMs, Compute-Containers, Compute-Platform Apps, Networking, Storage, Database-Relational/NoSQL, Cache, Analytics & Data Platform, AI & ML, Integration & Messaging, API Management, Identity & Access, Security, Monitoring & Operations, Backup & DR, Governance, Hybrid & Multicloud, Migration, DevOps & Automation, IoT.
- **Tier 2 — Business Pillar** (~12): Compute, AI, Data Platform, Network, Storage, Security, Integration, Operations, Business Continuity, Hybrid, Governance, Migration.
- **Tier 3 — Service Model**: IaaS | PaaS | SaaS | Hybrid | **Supporting Services** | Other. Cross-cutting services (Monitor, Defender, Key Vault, Policy, Log Analytics, Backup, Automation) are grouped as **Supporting Services**.
- **Publisher**: Microsoft (namespace `microsoft.*`) vs Third-party (Marketplace / partner providers).

### How It Works
`processors/classifier.py::classify_resource_type()` resolves each type by precedence: **exact type → provider namespace → third-party/default**, returning `{technical_category, business_pillar, service_model, publisher}`.

### Where It Appears
- **Excel `Classification` sheet** (right after `Index`): summary pivots (by Service Model and by Business Pillar) + a per-type table (`Resource Type | Technical Category | Business Pillar | Service Model | Publisher | Count | Sheet Tab`).
- **`AllResources`**: new `Business Pillar` and `Service Model` columns.
- **`Overview`**: a `SERVICE MODEL` summary block alongside `RESOURCE ORIGIN`.

The taxonomy is fully editable and also feeds the draw.io **Service Model** and **Business Pillar** diagram pages (see Item 10).

---

## Item 10: Architecture Diagrams (draw.io)

### What It Does
Generates a multi-page draw.io (`.drawio`) architecture diagram with real Azure icons, alongside the Excel and HTML outputs. Everything is derived from data already collected via Azure Resource Graph — no extra Azure calls.

### Pages
- **Overview** — KPIs by Service Model and Business Pillar, with clickable links to every page.
- **Organization** — Tenant → Management Groups → Subscriptions tree with per-subscription resource counts (`collectors/mgmt_groups.py`, `processors/org_tree.py`). Reconstructed from each subscription's `managementGroupAncestorsChain`; degrades to a flat Tenant → Subscriptions view.
- **Service Model** / **Business Pillar** — resource types grouped by the classification taxonomy (Item 9).
- **Network Topology** — VNets, subnets and peering, grouped by subscription; peering edges colored green (Connected) / red dashed (Disconnected/orphan) with a Broken Peering marker (`processors/network_topology.py`).
- **Network Detail** — resources placed inside their subnets (VMs via NIC join, private endpoints, firewall, gateways, load balancers, bastion, SQL MI), NSG shield, loose-NIC aggregation, and an On-Premises node (`processors/network_detail.py`, `config/network_placement.yaml`).
- **Security Posture** — per-subscription risk cards (Defender coverage, Zero Trust) plus severity badges on Network Detail resources (`processors/security_overlay.py`, `config/security_overlay.yaml`).
- **Resources** — one page per subscription with resource-group containers.

### How It Works
`writers/drawio_writer.py` emits uncompressed `<mxfile>` XML with multiple pages. Icons come from draw.io's bundled Azure 2019 stencils (`config/drawio_stencils.yaml`) with a generic fallback so brand-new resource types stay iconified. Gridlines are disabled for a clean canvas on open.

### Flags
| Flag | Effect |
|---|---|
| `--no-diagram` | Skip diagram generation entirely |
| `--skip-org` | Skip Management Group collection (Organization degrades to flat) |
| `--network-detail-per-subscription` | One Network Detail page per subscription (large tenants) |
| `--no-security-overlay` | Disable the Security Posture badges + page |

### Config
- `config/drawio_stencils.yaml` — resource type → Azure icon mapping (+ generic fallback)
- `config/network_placement.yaml` — resource → subnet resolution paths (Network Detail)
- `config/security_overlay.yaml` — severity colors and Zero Trust rule mapping

Open the `.drawio` file in the draw.io web/desktop app or the VS Code draw.io extension.

---

## Item 11: Cloud Modernization & Opportunity Assessment

### What It Does
Evolves the assessment from an *inventory* view into a *maturity & opportunity* view. Ten dimensions are scored 0-100 (INFERRED) with a level, a confidence, an inferred signal, supporting evidence, and an opportunity indicator — aligned to WAF / CAF / ESLZ / AI-Ready / Defender.

### Dimensions
Infrastructure Modernization, Application Modernization, Database Modernization, Data Platform & Analytics, AI Readiness & Adoption, Automation & Operations, Security Modernization, Governance & Landing Zone (CAF/ESLZ), Observability, and a neutral **Azure-Native vs Third-Party Footprint** (context only — no vendor names, never framed as an opportunity).

### Scoring methods (`processors/modernization.py`, driven by `config/modernization_signals.yaml`)
- **proportion** — `modern / (modern + legacy) * 100` (e.g. PaaS vs IaaS compute; managed DB vs SQL-on-VM).
- **presence** — `(# signal families present / total families) * 100` (breadth, avoids big-tenant bias).
- **security** — Defender coverage % blended with misconfiguration density.
- **governance** — tag coverage %, policy compliance %, and Management Group structure.
- **footprint** — Microsoft vs Third-party publisher split (context only).

### Guardrails
Non-prescriptive by design: it surfaces *signals* and *opportunity indicators*, never deterministic recommendations. Every dimension carries a confidence and evidence; low-confidence signals are visually muted. Narrative is deterministic (no AI). All framework references are links only.

### Where It Appears
- **Executive report**: heatmap of dimension tiles + top-opportunity cards + narrative (before *Top Priority Findings*).
- **Technical report**: evidence table (score, confidence, method, signal, supporting evidence, opportunity, frameworks) before *WAF Findings*.
- **Excel**: `ModernizationSignals` sheet.

### Limitations
⚠️ INFERRED — no official Microsoft API returns modernization scores. Signals are indicative; validate against your architecture and standards.

---

## Data Sources & References

### Primary Azure APIs

| Service | Documentation | Used For |
|---|---|---|
| **Azure Resource Graph** | [Overview](https://learn.microsoft.com/en-us/azure/governance/resource-graph/overview) | Core resource enumeration, KQL queries, regional data, resource types |
| **Azure Advisor** | [Overview](https://learn.microsoft.com/en-us/azure/advisor/) | WAF pillar recommendations, cost insights |
| **Azure Policy** | [Overview](https://learn.microsoft.com/en-us/azure/governance/policy/overview) | Compliance violations, policy assignment tracking |
| **Resource Health** | [Documentation](https://learn.microsoft.com/en-us/azure/resource-health/resource-health-overview) | Degraded resources, availability events |
| **Defender for Cloud** | [Overview](https://learn.microsoft.com/en-us/azure/defender-for-cloud/) | Security assessments, vulnerability findings |
| **Defender plan posture** | [`Microsoft.Security/pricings`](https://learn.microsoft.com/en-us/rest/api/defenderforcloud/pricings/list) | Plan enablement per subscription, per-resource servers coverage |
| **Azure Retail Prices** | [Retail Prices API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices) | Live Defender unit prices for the coverage-gap cost estimate |
| **Cost Management** | [Documentation](https://learn.microsoft.com/en-us/azure/cost-management-billing/) | Cost by RG, service, current month spending |

### Well-Architected Framework

| Pillar | Documentation | Usage |
|---|---|---|
| **Security** | [WAF Security Pillar](https://learn.microsoft.com/en-us/azure/architecture/framework/security/) | HTML report WAF categorization |
| **Reliability** | [WAF Reliability](https://learn.microsoft.com/en-us/azure/architecture/framework/resiliency//) | Health events, backup assessment |
| **Performance** | [WAF Performance](https://learn.microsoft.com/en-us/azure/architecture/framework/scalability/) | Resource sizing recommendations |
| **Operational Excellence** | [WAF Ops Excellence](https://learn.microsoft.com/en-us/azure/architecture/framework/devops/) | Monitoring, logging, automation |
| **Cost** | [WAF Cost Optimization](https://learn.microsoft.com/en-us/azure/architecture/framework/cost/cost-optimization/) | Tag coverage, cost allocation |

### Cloud Adoption Framework

| Component | Documentation | Usage in ATI |
|---|---|---|
| **Security Pillar** | [CAF Security](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/secure/) | Landing Zone security validation |
| **Governance Discipline** | [CAF Governance](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/govern/) | Management Group structure, policy compliance |
| **Cost Management** | [CAF Cost Mgmt](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/govern/cost-management-discipline/) | Tag coverage, chargeback model |
| **Operations** | [CAF Operations](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/manage/) | Monitoring, backup, disaster recovery |
| **Reliability** | [CAF Reliability](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/operational-excellence/define-reliability/) | RPO/RTO, availability, health |

### External References

- **Azure Updates**: [Official](https://azure.microsoft.com/en-us/updates/) — Retirement announcements
- **Microsoft Learn**: [Training](https://learn.microsoft.com/) — Best practices, architecture patterns
- **Chart.js**: [Documentation](https://www.chartjs.org/) — Visualization library (v4.4.0)

---

## Configuration & Mapping Files

### `config/resource_enrichment.yaml`
- Defines per-type property promotion rules
- Used by `writers/excel_writer.py` for column enrichment
- Extends base resource data with nested `properties.*` fields

### `config/deprecated_types.json`
- Contains official Azure retirement announcements
- Source: [Azure Updates](https://azure.microsoft.com/en-us/updates/)
- Used by `processors/deprecation.py` for resource matching

### `config/misconfiguration_rules.yaml`
- Security/configuration validation rules
- Each rule references official Microsoft documentation
- Used by `processors/misconfig_detector.py`

---

## Contributor Validation Checklist

Use this checklist when changing ATI or reviewing a release. It is not required for
an initial customer assessment:

- [ ] **Modernization Signals**: Verify detected signals match your actual infrastructure
- [ ] **Regional Distribution**: Confirm regional aggregation matches expected pattern
- [ ] **CAF Observations**: Review recommendations against your organizational Landing Zone design
- [ ] **Excel Styling**: Print Preview to ensure theme renders correctly in Excel/Calc
- [ ] **HTML Charts**: Open in browser, verify Chart.js loads (requires internet for CDN)
- [ ] **Metadata**: Verify tenant name and subscriptions display correctly
- [ ] **Flag Behavior**: Test `--skip-defender` and `--skip-costs` flags
- [ ] **Diagram**: Open the `*_Diagram.drawio` in draw.io; verify Overview, Organization, Network Topology/Detail, and Security Posture pages

### Interpretation Boundaries

ATI should be used as an evidence-gathering and prioritization tool.

It does not:

- Perform a formal compliance certification;
- Replace a security audit or penetration test;
- Determine application architecture from infrastructure alone;
- Guarantee modernization readiness;
- Produce a migration business case;
- Recommend a specific target architecture without additional discovery;
- Measure business criticality, application dependencies, or organizational readiness.

A high or low signal should be treated as a prompt for further investigation. The
appropriate next step depends on application context, business priorities, regulatory
requirements, and the organization's architecture standards.

---

## Troubleshooting

### Issue: "No Defender data available"
**Solution**: Use `--skip-defender` to exclude if not enabled, or enable Defender for Cloud in Azure portal.

### Issue: "Regional Distribution shows all resources in one region"
**Solution**: Some resources report "global" location. Check that --skip-* flags allow regional data collection.

### Issue: "CAF observations not showing"
**Solution**: Ensure Technical report HTML generation is enabled (not using `--no-html` flag).

### Issue: "Excel styling appears incorrect"
**Solution**: Use Excel 2016+ or LibreOffice Calc 6+. Older versions may not support PatternFill styles.

---

**Document Version**: 3.1  
**Last Updated**: August 6, 2026
**Status**: Technical methodology and interpretation boundaries documented for the current ATI outputs.
