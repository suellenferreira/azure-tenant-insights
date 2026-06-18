# Azure Tenant Insights (ATI)

> **A dynamic, scalable Azure tenant scanner that generates structured Excel inventories and dual HTML reports (Executive + Technical) aligned with the Azure Well-Architected Framework.**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Azure Resource Graph](https://img.shields.io/badge/Azure-Resource%20Graph-0078D4)](https://learn.microsoft.com/en-us/azure/governance/resource-graph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](./LICENSE)

---

## Table of Contents

- [Overview](#overview)
- [What Makes ATI Different from ARI](#what-makes-ati-different-from-ari)
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
- [Contributing](#contributing)

---

## Overview

Azure Tenant Insights (ATI) scans an Azure tenant (single or multiple subscriptions, or a Management Group hierarchy) and produces three output files:

| Output | Audience | Contents |
|---|---|---|
| `*_Inventory.xlsx` | All teams | Structured, multi-sheet Excel inventory organized by resource type |
| `*_Executive.html` | C-Level / Stakeholders | Risk score, KPIs, strategic recommendations, modernization signals |
| `*_Technical.html` | Engineers / Architects | WAF pillar findings, policy violations, misconfigs, health, deprecated resources |

All data is sourced **exclusively from official Azure APIs** — Azure Resource Graph, Azure Advisor, Azure Policy Insights, Resource Health, and optionally Defender for Cloud and Cost Management.

---

## What Makes ATI Different from ARI

[Azure Resource Inventory (ARI)](https://github.com/microsoft/ARI) is a widely used PowerShell tool for Azure documentation. ATI is a complementary Python-based solution that addresses key gaps:

| Dimension | ARI | ATI |
|---|---|---|
| **Language** | PowerShell 7+ | Python 3.9+ |
| **Resource type coverage** | Static modules per type (~80+ hardcoded) | **Dynamic** — all types discovered and captured automatically |
| **New resource type handling** | Manual module update required | Captured generically; enrichment is additive and optional |
| **Executive HTML report** | ❌ | ✅ |
| **Technical HTML report** | ❌ | ✅ |
| **WAF pillar mapping** | ❌ | ✅ via Azure Advisor categories |
| **Misconfiguration detection** | ❌ | ✅ rules-based, official sources only |
| **Policy compliance** | Optional | Always collected |
| **Deprecated resource detection** | ❌ | ✅ based on official retirement announcements |
| **Azure Arc resources** | Not explicit | Captured via `hybridcompute` type |

ATI **does not replace ARI** — both tools can be used together. ATI extends the analysis layer with HTML reports, WAF alignment, and dynamic type coverage.

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

# Azure Cloud Shell — pre-installed, no action needed
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
# No installation needed — Python and az are pre-installed
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
| `Overview` | KPI summary, top resource types, Advisor by WAF pillar |
| `Subscriptions` | One row per subscription with resource count |
| `AllResources` | Flat table of ALL resources across all types |
| `[ResourceType]` | One sheet per resource type (e.g., `VirtualMachines`) |
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

### `*_Executive.html` — Executive Report

Self-contained HTML file. Open in any modern browser — **no internet required**.

- Overall risk level banner
- KPI tiles (resources, subscriptions, critical findings, deprecated, tag coverage)
- Advisor recommendations by WAF pillar (donut chart)
- Top resource types (bar chart)
- Top 5 priority findings
- Defender plan posture summary and **coverage gap** (unprotected billable units + estimated monthly cost to protect) *(if Defender data is available)*
- Strategic recommendations (linked to findings)
- Modernization signals *(labeled as INFERRED)*

### `*_Technical.html` — Technical Report

Self-contained HTML file with sidebar navigation.

- Resource inventory summary
- WAF pillar findings (tabbed by pillar)
- Policy compliance violations
- Known misconfigurations (linked to official documentation)
- Defender for Cloud assessments *(omitted if `--skip-defender`)*
- Defender **plan posture** (enabled/disabled plans per subscription) and per-resource servers coverage *(if Defender data is available)*
- Defender **coverage gap & cost to protect** table (unprotected billable units × unit price per plan) *(if Defender data is available)*
- Resource health events
- Deprecated/retiring resources with migration links
- Landing Zone observations *(labeled as INFERRED)*
- Azure Arc resources *(if present)*

> **Note on Charts:** Reports use [Chart.js](https://www.chartjs.org/) loaded from CDN (`cdn.jsdelivr.net`). An internet connection is required to display charts. All data tables are visible without internet.

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
│   ├── deprecated_types.json       ← Known Azure retirement announcements
│   └── misconfiguration_rules.yaml ← Security/config rule definitions
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
│   └── costs.py                    ← Cost Management data
│
├── processors/                     ← Data enrichment & analysis
│   ├── normalizer.py               ← String/type normalization utilities
│   ├── deprecation.py              ← Deprecated resource detection
│   ├── waf_mapper.py               ← WAF pillar grouping
│   ├── misconfig_detector.py       ← Misconfiguration rule evaluation
│   └── summary.py                  ← KPI metric computation
│
└── writers/                        ← Output generation
    ├── excel_writer.py             ← Excel workbook builder (openpyxl)
    ├── html_executive.py           ← Executive HTML report
    └── html_technical.py           ← Technical HTML report
```

---

## Configuration Files

### `config/resource_enrichment.yaml`

Defines which nested `properties.*` fields to promote to named columns per resource type. Resources without a rule entry are still collected — their raw `properties` JSON is stored in the `AllResources` sheet.

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
