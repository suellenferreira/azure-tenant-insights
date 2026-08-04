# Azure Tenant Insights (ATI)

> **A dynamic, scalable Azure tenant scanner that generates structured Excel inventories, dual HTML reports (Executive + Technical), and multi-page architecture diagrams (draw.io) aligned with the Azure Well-Architected Framework.**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Azure Resource Graph](https://img.shields.io/badge/Azure-Resource%20Graph-0078D4)](https://learn.microsoft.com/en-us/azure/governance/resource-graph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](./LICENSE)

---

## Table of Contents

- [Overview](#overview)
- [Key Capabilities](#key-capabilities)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Parameters Reference](#parameters-reference)
- [RBAC Requirements](#rbac-requirements)
- [Output Files](#output-files)
- [Project Structure](#project-structure)
- [Configuration Files](#configuration-files)
- [Supported Cloud Environments](#supported-cloud-environments)
- [Limitations](#limitations)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Overview

Azure Tenant Insights (ATI) scans an Azure tenant (single or multiple subscriptions, or a Management Group hierarchy) and produces four output files:

| Output | Audience | Contents |
|---|---|---|
| `*_Inventory.xlsx` | All teams | Structured, multi-sheet Excel inventory organized by resource type |
| `*_Executive.html` | C-Level / Stakeholders | Risk score, KPIs, strategic recommendations, modernization signals |
| `*_Technical.html` | Engineers / Architects | WAF pillar findings, policy violations, misconfigs, health, deprecated resources |
| `*.drawio` | Architects | Multi-page architecture diagram — Overview, Organization, Service Model, Business Pillar, Network Topology, Network Detail, Security Posture, and per-subscription Resources — with real Azure icons; open in [draw.io](https://app.diagrams.net) |

All data is sourced **exclusively from official Azure APIs** — Azure Resource Graph, Azure Advisor, Azure Policy Insights, Resource Health, and optionally Defender for Cloud and Cost Management.

---

## Key Capabilities

- **Dynamic resource-type coverage** — every resource type in the tenant is discovered and captured automatically. New Azure types are handled generically (no code change); per-type enrichment is optional and additive via `config/resource_enrichment.yaml`.
- **Structured multi-sheet Excel** — one sheet per resource type with declarative property enrichment, a flat `AllResources` table, an **Index** navigation sheet (hyperlinks to every tab, with per-sheet back-links), a **Category** column (Azure-native / Hybrid-Arc / Migrate), and a **Data Collection Notes** section.
- **Dual HTML reports** — an Executive report (risk score, KPIs, priority-colored recommendation cards, Zero Trust posture) and a Technical report (WAF pillar findings, policy, misconfigs, health, deprecated resources); both self-contained, with collapsible sections and offline-friendly tables.
- **draw.io architecture diagram** — a multi-page `.drawio` with real Azure icons: Overview (KPIs + cross-page links), **Organization** (Tenant → Management Groups → Subscriptions tree with resource counts), Service Model, Business Pillar, **Network Topology** (VNets/subnets/peering with broken-peering detection), a **Network Detail** page (resources placed inside their subnets: VMs, private endpoints, firewall, gateways, NSG shield, On-Premises node), a **Security Posture** page (per-subscription risk cards + severity badges on resources), and one Resources page per subscription. Config-driven icon map with a generic fallback, so new Azure resource types are diagrammed automatically. Skip with `--no-diagram`.
- **WAF pillar mapping** — Advisor recommendations organized by Well-Architected Framework pillar.
- **Rules-based misconfiguration detection** — official-source rules mapped to Zero Trust principles.
- **Policy compliance & deprecated-resource detection** — non-compliant resources and matches against official Azure retirement announcements.
- **Defender for Cloud posture** — plan enablement per subscription, per-resource server coverage, and coverage-gap cost-to-protect.
- **100% read-only** — sourced exclusively from official Azure APIs (Resource Graph, Advisor, Policy Insights, Resource Health, optionally Defender and Cost Management).

---

## Prerequisites

- **Python 3.9 or higher**
- **Azure account** with at least `Reader` access on the subscriptions to scan
- One of the following authentication methods:
  - `az login` (Azure CLI — recommended for local interactive use; no secrets required)
  - Managed Identity (when running on Azure compute)
  - Service Principal via environment variables (advanced automation scenario; see `.env.example`)

### Install Azure CLI (optional but recommended)

```bash
# Windows (winget)
winget install -e --id Microsoft.AzureCLI

# macOS
brew install azure-cli

# Azure Cloud Shell — az CLI already installed and signed in
```

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/suellenferreira/azure-tenant-insights.git
cd azure-tenant-insights

# 2. (Recommended) Create a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Dependencies

```
azure-identity>=1.15.0
azure-mgmt-resourcegraph>=8.0.0
azure-mgmt-subscription>=3.1.1
requests>=2.31.0
openpyxl>=3.1.2
pyyaml>=6.0.1
```

---

## Quick Start

```bash
# Authenticate via Azure CLI
az login

# Run ATI against all accessible subscriptions
python invoke_ati.py

# Run against a specific tenant
python invoke_ati.py --tenant-id 00000000-0000-0000-0000-000000000000
```

Output files are saved to `./AzureTenantInsights/` by default.

---

## Usage

### Basic Examples

```bash
# Full tenant scan (all accessible subscriptions)
python invoke_ati.py --tenant-id <TENANT-ID>

# Scope to specific subscription(s)
python invoke_ati.py --tenant-id <TENANT-ID> --subscription-id <SUB-ID-1> <SUB-ID-2>

# Scope to a Management Group (scans all subscriptions under it)
python invoke_ati.py --tenant-id <TENANT-ID> --management-group <MG-ID>

# All data sources are ON by default. Skip specific ones if needed:
python invoke_ati.py --tenant-id <TENANT-ID> --skip-costs        # exclude Cost Management
python invoke_ati.py --tenant-id <TENANT-ID> --skip-defender     # exclude Defender for Cloud
python invoke_ati.py --tenant-id <TENANT-ID> --skip-tags         # exclude tag columns from Excel

# Filter to specific resource group(s)
python invoke_ati.py --tenant-id <TENANT-ID> --resource-group rg-production rg-staging

# Filter by tag
python invoke_ati.py --tenant-id <TENANT-ID> --tag-key environment --tag-value production

# Optional: Service Principal authentication for automation
# Prefer environment variables so secrets are not stored in shell history.
export AZURE_TENANT_ID=<TENANT-ID>
export AZURE_CLIENT_ID=<APP-ID>
export AZURE_CLIENT_SECRET=<SECRET>
python invoke_ati.py

# Custom output directory and report name
python invoke_ati.py --tenant-id <TENANT-ID> \
  --output-dir ./reports \
  --report-name MyCompany_Quarterly

# Skip specific data sources for faster runs
python invoke_ati.py --tenant-id <TENANT-ID> \
  --skip-advisor \
  --skip-policy \
  --no-html

# Debug mode (verbose logging)
python invoke_ati.py --tenant-id <TENANT-ID> --debug
```

### Azure Cloud Shell

```bash
# Python & az are pre-installed and az is already signed in — just install the Python deps:
git clone https://github.com/suellenferreira/azure-tenant-insights.git
cd azure-tenant-insights
pip install -r requirements.txt --quiet
python invoke_ati.py
```

---

## Parameters Reference

### Authentication

| Parameter | Description |
|---|---|
| `--tenant-id <GUID>` | Azure Tenant ID. Optional — auto-detected from `az login` context |
| `--client-id <ID>` | Service Principal Application ID |
| `--client-secret <SECRET>` | Service Principal Client Secret. Prefer `AZURE_CLIENT_SECRET` for automation to avoid shell history exposure |

### Scope

| Parameter | Description |
|---|---|
| `--subscription-id <ID> [<ID> ...]` | Limit scan to specific subscription(s) |
| `--management-group <ID>` | Scan all subscriptions under a Management Group |
| `--resource-group <NAME> [...]` | Limit to specific resource group(s) |
| `--tag-key <KEY>` | Filter resources by tag key |
| `--tag-value <VALUE>` | Filter resources by tag value (requires `--tag-key`) |

### Optional Data Sources

All data sources are **enabled by default**. Use `--skip-*` flags to exclude them:

| Parameter | Description | Extra RBAC Required |
|---|---|---|
| `--skip-defender` | Exclude Defender for Cloud assessments | — |
| `--skip-costs` | Exclude Cost Management data | — |
| `--skip-tags` | Exclude resource tag columns from Excel | — |
| `--skip-policy` | Exclude Azure Policy compliance collection | — |
| `--skip-advisor` | Exclude Azure Advisor recommendations | — |

### Output

| Parameter | Description |
|---|---|
| `--output-dir <PATH>` | Output directory (default: `./AzureTenantInsights`) |
| `--report-name <NAME>` | Custom prefix for report files |
| `--no-excel` | Skip Excel inventory generation |
| `--no-html` | Skip HTML reports generation |
| `--no-diagram` | Skip draw.io architecture diagram generation |
| `--network-detail-per-subscription` | Network Detail: one page per subscription (for very large tenants) |
| `--skip-org` | Skip Management Group hierarchy collection (Organization diagram) |
| `--no-security-overlay` | Disable the diagram Security Posture overlay (badges + page) |

### Performance

| Parameter | Default | Description |
|---|---|---|
| `--throttle-delay <SECONDS>` | `1.0` | Delay between Resource Graph queries |
| `--cloud <NAME>` | `AzurePublicCloud` | Target cloud environment |

---

## RBAC Requirements

| Feature | Minimum Role | Scope |
|---|---|---|
| Core inventory | `Reader` | Subscription(s) |
| Policy compliance | `Reader` | Subscription(s) |
| Azure Advisor | `Reader` | Subscription(s) |
| Resource Health | `Reader` | Subscription(s) |
| Management Group scope | `Reader` | Management Group |
| Defender plan posture | `Reader` | Subscription(s) |
| Defender for Cloud assessments | `Security Reader` | Subscription(s) |
| Cost data | `Cost Management Reader` | Subscription(s) or Billing Account |

> **Principle of Least Privilege:** ATI is 100% read-only. It makes no changes to any Azure resource.

---

## Output Files

Generated reports can include tenant metadata, subscription IDs, resource names, costs, security findings, and configuration details. Keep generated files local by default and do not publish `AzureTenantInsights/`, `*.xlsx`, `*.html`, or `*.log` outputs.

Three files are generated per run:

### `*_Inventory.xlsx` — Excel Inventory

| Sheet | Contents |
|---|---|
| `Overview` | KPI summary, top resource types, Advisor by WAF pillar, **Resource Origin** (Azure-native / Hybrid-Arc / Migrate), a **Service Model** summary (IaaS/PaaS/SaaS/Hybrid/Supporting), and **Data Collection Notes** |
| `Index` | Navigation sheet (positioned after `Overview`) with a hyperlink to every tab; each sheet has a **↩ Index** back-link |
| `Classification` | Resource **taxonomy** per type — Technical Category, Business Pillar, Service Model, Publisher (Microsoft/Third-party) — with summary pivots (config-driven) |
| `Subscriptions` | Resource aggregation by subscription, resource group, location, and resource type |
| `AllResources` | Flat table across all types with common Azure Resource Graph / ARM columns, a **Category** column (Azure-native / Hybrid-Arc / Migrate), **Business Pillar** and **Service Model** columns, and raw properties |
| `[ResourceType]` | One sheet per resource type using configured display names and declarative property enrichment |
| `AdvisorFindings` | All Advisor recommendations with WAF pillar |
| `PolicyCompliance` | Non-compliant resources |
| `ResourceHealth` | Degraded/unavailable resources |
| `DeprecatedResources` | Resources matching retirement announcements |
| `MisconfigFindings` | Known misconfiguration findings |
| `SecurityAssessments` | Defender for Cloud assessments (omitted if `--skip-defender`) |
| `DefenderCostEstimate` | Estimated Defender plan cost from the inventory (omitted if `--skip-defender`) |
| `DefenderPosture` | Defender plan enablement per subscription via `Microsoft.Security/pricings` (omitted if `--skip-defender`) |
| `DefenderServersCoverage` | Per-resource Defender for Servers coverage for VMs / VMSS / Arc Machines (omitted if `--skip-defender`) |
| `DefenderCoverageGap` | Unprotected billable units and **monthly cost to protect** per plan (omitted if `--skip-defender`) |
| `Costs` | Cost by resource group/service (omitted if `--skip-costs`) |

> **Sheet naming:** per-type sheet names come from configured display names; a short namespace prefix is added **only** when two providers would otherwise collide (e.g., `Cmp-Virtualmachinetemplates` vs `VMw-Virtualmachinetemplates`). Every resource type gets its own sheet up to Excel's hard cap of 255; the rest stay in `AllResources`. A scope-aware warning is logged when the type-sheet count is high (subscription ≥ 40, management group ≥ 60, tenant ≥ 75; env-overridable).

### `*_Executive.html` — Executive Report

Self-contained HTML file. Open in any modern browser — **no internet required**.

- Overall risk level banner
- KPI tiles (resources, subscriptions, critical findings, deprecated, tag coverage)
- Advisor recommendations by WAF pillar (donut chart)
- Top resource types (bar chart)
- Top priority findings (5, or up to 10 for large environments)
- Defender plan posture summary and **coverage gap** (unprotected billable units + estimated monthly cost to protect) *(if Defender data is available)*
- Strategic recommendations as **priority-colored cards**
- **Zero Trust** posture summary (color-coded by principle, with descriptions)
- Modernization signals *(labeled as INFERRED)*
- Collapsible sections with **Expand All / Collapse All** controls; subtle link to **Data Collection Notes**

### `*_Technical.html` — Technical Report

Self-contained HTML file with sidebar navigation.

- Resource inventory summary; **Resources by Subscription** chart labeled by subscription name
- WAF pillar findings (tabbed by pillar) with **progressive loading** (30 rows at a time; large lists point to the Excel export) and **column search**
- Policy compliance violations
- Known misconfigurations (linked to official documentation)
- Defender for Cloud assessments *(omitted if `--skip-defender`)*
- Defender **plan posture** (enabled/disabled plans per subscription, with **column search**) and per-resource servers coverage *(if Defender data is available)*
- Defender **coverage gap & cost to protect** table (unprotected billable units × unit price per plan) *(if Defender data is available)*
- Resource health events
- Deprecated/retiring resources with migration links
- Landing Zone observations *(labeled as INFERRED)*
- Azure Arc resources *(if present)*
- Collapsible sections with **Expand All / Collapse All**; subtle link to **Data Collection Notes**

> **Note on Charts:** Reports use [Chart.js](https://www.chartjs.org/) loaded from CDN (`cdn.jsdelivr.net`). An internet connection is required to display charts. All data tables are visible without internet.

### `*_Diagram.drawio` — Architecture Diagram

A multi-page [draw.io](https://app.diagrams.net) file (uncompressed XML) with real Azure icons. Open it in the draw.io web/desktop app or the VS Code draw.io extension. Pages:

- **Overview** — KPIs by Service Model and Business Pillar, with clickable links to every page
- **Organization** — Tenant → Management Groups → Subscriptions tree with per-subscription resource counts
- **Service Model** / **Business Pillar** — resource types grouped by IaaS/PaaS/SaaS/… and by business pillar
- **Network Topology** — VNets, subnets and peering (green = Connected, red dashed = Disconnected/orphan), grouped by subscription
- **Network Detail** — resources placed inside their subnets (VMs, private endpoints, firewall, gateways, NSG shield, On-Premises node)
- **Security Posture** — per-subscription risk cards (Defender coverage, Zero Trust) plus severity badges on Network Detail resources *(when security data is available)*
- **Resources** — one page per subscription with resource-group containers

Icons come from draw.io's bundled Azure 2019 stencils, with a generic fallback so brand-new resource types are still iconified. Skip generation with `--no-diagram`; use `--network-detail-per-subscription` for one Network Detail page per subscription and `--no-security-overlay` to disable the security badges/page.

---

## Project Structure

```
azure-tenant-insights/
│
├── invoke_ati.py                   ← Main entry point
├── requirements.txt
├── pyproject.toml
├── README.md                       ← This file (EN)
├── README.pt-BR.md                 ← Portuguese (BR)
├── README.es.md                    ← Spanish
├── CHANGELOG.md
│
├── config/
│   ├── resource_enrichment.yaml    ← Per-type property promotion rules
│   ├── resource_classification.yaml ← 3-tier taxonomy (Service Model / Business Pillar)
│   ├── deprecated_types.json       ← Known Azure retirement announcements
│   ├── misconfiguration_rules.yaml ← Security/config rule definitions
│   ├── drawio_stencils.yaml        ← Resource type → Azure icon mapping (diagram)
│   ├── network_placement.yaml      ← Resource → subnet resolution (Network Detail)
│   └── security_overlay.yaml       ← Severity colors + Zero Trust mapping (diagram)
│
├── collectors/                     ← Azure API data collection
│   ├── auth.py                     ← Authentication (DefaultAzureCredential / SP)
│   ├── subscriptions.py            ← Subscription enumeration
│   ├── resource_graph.py           ← Core paginated Resource Graph engine (CLI retry/backoff)
│   ├── resources.py                ← Dynamic resource collection
│   ├── advisor.py                  ← Azure Advisor recommendations
│   ├── policy.py                   ← Azure Policy compliance states
│   ├── health.py                   ← Resource Health events
│   ├── defender.py                 ← Defender for Cloud assessments
│   ├── defender_posture.py         ← Defender plan posture (Microsoft.Security/pricings)
│   ├── defender_pricing.py         ← Coverage gap + live pricing (Azure Retail Prices API)
│   ├── costs.py                    ← Cost Management data
│   └── mgmt_groups.py              ← Management Group hierarchy (Organization diagram)
│
├── processors/                     ← Data enrichment & analysis
│   ├── normalizer.py               ← String/type normalization utilities
│   ├── deprecation.py              ← Deprecated resource detection
│   ├── waf_mapper.py               ← WAF pillar grouping
│   ├── misconfig_detector.py       ← Misconfiguration rule evaluation
│   ├── classifier.py               ← Resource classification taxonomy
│   ├── org_tree.py                 ← Tenant → MG → Subscription tree (diagram)
│   ├── network_topology.py         ← VNet/subnet/peering graph (diagram)
│   ├── network_detail.py           ← Resource-in-subnet placement (diagram)
│   ├── security_overlay.py         ← Per-resource/subscription risk (diagram)
│   └── summary.py                  ← KPI metric computation
│
└── writers/                        ← Output generation
    ├── excel_writer.py             ← Excel workbook builder (openpyxl)
    ├── html_executive.py           ← Executive HTML report
    ├── html_technical.py           ← Technical HTML report
    └── drawio_writer.py            ← Multi-page draw.io architecture diagram
```

---

## Configuration Files

### `config/resource_enrichment.yaml`

Defines which nested `properties.*` fields to promote to named columns per resource type. Resources without a rule entry are still collected — their raw `properties` JSON is stored in the `AllResources` sheet.

Promoted fields must be based on official Microsoft references, primarily the [Azure Resource Graph table and resource type reference](https://learn.microsoft.com/en-us/azure/governance/resource-graph/reference/supported-tables-resources) and the [Azure Resource Manager template resource definitions](https://learn.microsoft.com/en-us/azure/templates/). Treat suggested columns as a starting point; verify provider properties against Microsoft Learn before adding them.

To add enrichment for a new resource type:

```yaml
resource_types:
  "microsoft.newservice/resourcetype":
    display_name: "My New Resource"
    promoted_fields:
      - path: "properties.someProperty"
        column: "some_property"
```

### `config/deprecated_types.json`

Contains known Azure retirement announcements. Each entry specifies the resource type, retirement date, severity, and links to the official announcement and migration path.

Update this file when new retirement announcements are published at [Azure Updates](https://azure.microsoft.com/en-us/updates/).

### `config/misconfiguration_rules.yaml`

Defines configuration checks for specific resource types. All rules reference official Microsoft documentation. Supported operators: `equals`, `not_equals`, `equals_true`, `equals_false`, `is_null`, `is_not_null`, `contains`, `not_contains`.

---

## Supported Cloud Environments

| Flag | Environment |
|---|---|
| `AzurePublicCloud` | Azure Global (default) |
| `AzureUSGovernment` | Azure US Government |
| `AzureChinaCloud` | Azure China (21Vianet) |
| `AzureGermanCloud` | Azure Germany |

---

## Estimated Runtime

| Tenant Size | Estimated Runtime |
|---|---|
| < 500 resources | ~2 minutes |
| 500–5,000 resources | ~5–15 minutes |
| 5,000–50,000 resources | ~15–60 minutes |
| > 50,000 resources | > 60 minutes (recommend scheduling overnight) |

For large tenants, consider using `--skip-advisor`, `--skip-policy`, or `--no-html` to reduce runtime.

---

## Limitations

- **Resource Graph page limit:** 1,000 records/page. Pagination is handled automatically.
- **Rate limiting:** Resource Graph throttles queries per user. Use `--throttle-delay` to adjust.
- **Not all properties exposed:** Resource Graph uses the latest non-preview API per type. Some preview-only properties may not appear.
- **Cost data requires elevated RBAC:** `Cost Management Reader` is needed, which is higher than `Reader`.
- **Defender cost estimates are approximate:** Unit prices are fetched live from the public Azure Retail Prices API (public **list** pricing). When the API is unreachable, built-in fallback prices are used and the reports label them as a possibly-outdated offline fallback. EA/MCA/CSP discounts, free tiers, and usage-based plans (e.g. Cosmos DB) are not reflected.
- **Charts require internet:** Chart.js is loaded from CDN. All data tables display without internet.
- **Point-in-time only:** ATI produces snapshots. Trend analysis requires scheduling regular runs.
- **Modernization signals are INFERRED:** No official Azure API returns an AI-readiness or modernization score. ATI infers these from detected resource types only.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Authentication failed` / no subscriptions found | Not logged in, or wrong tenant | Run `az login` (or `az login --tenant <ID>`); confirm with `az account show` |
| `AuthorizationFailed` / `403` in the log for some data | Missing RBAC on a subscription | Ensure at least `Reader`; add `Security Reader` (Defender) / `Cost Management Reader` (costs), or use `--skip-defender` / `--skip-costs` |
| Scan is slow or logs `429 TooManyRequests` | Resource Graph throttling | Increase `--throttle-delay` (e.g. `2.0`); narrow the scope with `--subscription-id` or `--management-group` |
| Runs for a long time | Default scope is **all** subscriptions in the tenant | Scope the scan, or pass `-y` to skip the confirmation |
| Hangs on the "Custom Report Name" prompt in CI | No interactive terminal (TTY) | Pass `--report-name <NAME>` or `-y` (both skip the prompt) |
| Charts don't render | Offline / CDN blocked | Data tables still work offline; charts need `cdn.jsdelivr.net` |
| Very verbose HTTP logs | `--debug` enabled | Omit `--debug`; the Azure SDK redacts tokens as `REDACTED` |

> **Service Principal auth** reads `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` from the **environment**. Export them (or simply use `az login`) — a `.env` file is not auto-loaded.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-improvement`
3. Make changes and test against a real Azure subscription
4. Submit a Pull Request with a clear description

To add a new misconfiguration rule, edit `config/misconfiguration_rules.yaml` and provide:
- A unique `id`
- A reference to official Microsoft documentation in `documentation_url`
- The exact `condition_path` and `expected_value` sourced from official API documentation

---

## License

MIT License — see [LICENSE](./LICENSE) for details.

> This project is not an official Microsoft product. It uses only publicly documented, official Azure APIs.
