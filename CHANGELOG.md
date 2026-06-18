# Changelog

All notable changes to Azure Tenant Insights are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

**Defender for Cloud — Plan Posture (B1)**
- `collectors/defender_posture.py` — collects the real Defender plan enablement per subscription from the `Microsoft.Security/pricings` data via Azure Resource Graph (`securityresources` table). Requires only `Reader` RBAC.
- VMs / VMSS / Arc Machines are analysed **individually** (per-resource coverage); other workloads are reported at the subscription/plan level (official limitation of the pricings API).
- New Excel sheets: `DefenderPosture` (plan enablement per subscription) and `DefenderServersCoverage` (per-resource VM/VMSS/Arc coverage).
- New Technical HTML section "Defender — Plan Posture" and a posture summary in the Executive HTML report.

**Defender for Cloud — Coverage Gap & Cost to Protect (B2)**
- `collectors/defender_pricing.py` — cross-references the inventory with the real plan posture to estimate how many billable units are **not yet protected** and the **monthly cost to close the gap** per plan.
- New Excel sheet `DefenderCoverageGap` (total / protected / unprotected units, unit price, gap monthly cost per plan, with grand total).
- New Technical HTML "Coverage Gap & Cost to Protect" table and a coverage-gap line in the Executive HTML report.
- New Excel sheet `DefenderCostEstimate` (estimated Defender plan cost from inventory).
- Usage-based plans (e.g. Cosmos DB, per 100 RU/s) are counted but their cost is intentionally **not** estimated.

**Live Defender pricing (Azure Retail Prices API)**
- Defender unit prices are now fetched **live** from the public [Azure Retail Prices API](https://prices.azure.com/api/retail/prices) (no authentication required) so estimates track Microsoft's current published list pricing instead of going stale.
- Hardcoded list prices remain as an **offline fallback**: on any network/parse failure (or when a meter is not found) the tool degrades gracefully to the built-in values.
- Prices are fetched **once per run** (process-level cache) and reused by all report writers — no repeated network calls.
- Every gap report (Excel + both HTML reports) shows the **price source** — "live from the Azure Retail Prices API (date)" or "built-in list prices (offline fallback … may be outdated)".

**Operational diagnostics**
- Terminal **COLLECTION WARNINGS / ERRORS** summary block printed after `SCAN COMPLETE`, grouped by collector (up to 30 entries listed).
- A failed/offline live-pricing fetch is captured in `collection_warnings`, so it appears both in the terminal summary and the report's **Data collection notes** section.
- Resource Graph collector failures are now attributed to the correct collector (new `caller=` parameter on `query_resource_graph`), e.g. logged under `collectors.defender_posture`.
- Transient Azure CLI authentication failures (`Failed to invoke the Azure CLI`, `AzureCliCredential`) are retried with exponential backoff (3 attempts, 2/4/8 s).

### Changed

- `RBAC Requirements`: Defender **plan posture** needs only `Reader` (less restrictive than the `Security Reader` required for Defender **assessments**).

---

## [1.0.0] — 2026-06-15

### Added

**Core Architecture**
- Dynamic resource type discovery via Azure Resource Graph — no hardcoded type list required
- Paginated Resource Graph query engine with throttle-aware retry and 429 handling
- `DefaultAzureCredential` support: Azure CLI, Managed Identity, Service Principal, Environment Variables
- Management Group scope (`--management-group`) to scan all subscriptions in a hierarchy
- Tag-based resource filtering (`--tag-key`, `--tag-value`)
- Resource Group scope filtering (`--resource-group`)

**Data Collectors**
- `collectors/resources.py` — dynamic collection of ALL resource types with configurable property enrichment
- `collectors/advisor.py` — Azure Advisor recommendations from `AdvisorResources` Resource Graph table
- `collectors/policy.py` — non-compliant policy states from `PolicyResources` Resource Graph table
- `collectors/health.py` — degraded/unavailable resources from `HealthResources` Resource Graph table
- `collectors/defender.py` — Defender for Cloud assessments (optional, `Security Reader` required)
- `collectors/costs.py` — Cost Management data grouped by resource group (optional, `Cost Management Reader` required)

**Processors**
- `processors/deprecation.py` — matches resources against `config/deprecated_types.json` (official retirement announcements)
- `processors/misconfig_detector.py` — evaluates resources against rules in `config/misconfiguration_rules.yaml`
- `processors/waf_mapper.py` — groups Advisor recommendations by WAF pillar (Reliability, Security, Cost Optimization, Operational Excellence, Performance Efficiency)
- `processors/summary.py` — computes KPI metrics for all report types

**Excel Output (`*_Inventory.xlsx`)**
- Multi-sheet workbook with one sheet per resource type (up to 40 sheets)
- `Overview` sheet with KPIs, top resource types, and Advisor by pillar
- `AllResources` flat table across all types
- `AdvisorFindings`, `PolicyCompliance`, `ResourceHealth`, `DeprecatedResources`, `MisconfigFindings` sheets
- Optional `SecurityAssessments` and `Costs` sheets
- Conditional formatting by severity (Critical/High/Medium/Low)
- Auto-filter and freeze panes on all data sheets
- Column widths optimized per sheet

**Executive HTML Report (`*_Executive.html`)**
- Self-contained single HTML file, opens offline (data tables only; charts require internet for CDN)
- Overall risk level banner derived from critical finding count
- 8 KPI tiles with color-coded states
- Donut chart: Advisor recommendations by WAF pillar
- Bar chart: top 8 resource types
- Top 5 priority findings with severity badges
- Strategic recommendations derived from findings
- Modernization/technology signals (clearly labeled as INFERRED)

**Technical HTML Report (`*_Technical.html`)**
- Self-contained single HTML file with fixed sidebar navigation
- Tabbed WAF pillar findings (Advisor recommendations grouped by pillar)
- Resource inventory summary table
- Policy compliance violations table
- Misconfiguration findings table with link to official documentation
- Defender for Cloud assessments section (if data available)
- Resource health events table
- Deprecated resources table with official migration links
- Landing Zone observations (clearly labeled as INFERRED)
- Azure Arc resources section (if present)

**Configuration Files**
- `config/resource_enrichment.yaml` — property promotion rules for 16 common resource types
- `config/deprecated_types.json` — 5 known Azure retirement entries (Classic VMs, Classic VNets, Classic Storage, Basic VPN Gateway, SQL Basic tier)
- `config/misconfiguration_rules.yaml` — 10 security/configuration rules based on official Azure Security Benchmark

**CLI (`invoke_ati.py`)**
- Full argument parser with `--help` and comprehensive usage examples
- Authentication: `--tenant-id`, `--client-id`, `--client-secret`
- Scope: `--subscription-id`, `--management-group`, `--resource-group`, `--tag-key`, `--tag-value`
- Data sources: `--include-defender`, `--include-costs`, `--include-tags`, `--skip-policy`, `--skip-advisor`
- Output: `--output-dir`, `--report-name`, `--no-excel`, `--no-html`
- Performance: `--throttle-delay`, `--cloud`
- Debug: `--debug`, `--version`

**Documentation**
- `README.md` — English (primary), comprehensive usage guide
- `README.pt-BR.md` — Portuguese (Brazil)
- `README.es.md` — Spanish
- `pyproject.toml` — packaging configuration

---

## Future Scope (Not yet implemented)

- **Network topology diagrams** — feasibility assessed; implementation pending (Network Watcher topology API + D3.js)
- **Multi-tenant scanning** — architecture supports Azure Lighthouse; v2 target
- **Trend analysis / historical comparison** — requires scheduled run infrastructure; v2 target
- **AI readiness scoring via official API** — no such API exists in Azure as of v1; monitored for future availability
- **Automated `deprecated_types.json` updates** from Azure RSS feed

---

[Unreleased]: https://github.com/suellenferreira/azure-tenant-insights/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/suellenferreira/azure-tenant-insights/releases/tag/v1.0.0
