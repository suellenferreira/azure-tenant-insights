# Changelog

All notable changes to Azure Tenant Insights are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

**French documentation**
- Added a complete `README.fr.md` translation preserving commands, links, output guidance, disclaimers, limitations, catalog governance, and draw.io viewing instructions.
- Added reciprocal language navigation and documented the French guide in `DOCUMENTATION_INDEX.md`.

**Local catalog governance and provenance**
- Added `config/catalog_metadata.json` with catalog version, verification dates, evidence levels, sources, and affected outputs.
- Catalog freshness is evaluated locally as `current`, `review_due`, or `stale`; customer scans never fetch or update catalog rules online.
- Technical HTML now includes contextual catalog indicators and a central Catalog Status section; stale catalogs add a concise Executive disclaimer.
- Excel now includes a `CatalogStatus` sheet and provenance comments on deprecated/misconfiguration findings; draw.io Overview records catalog version/status.
- Added tests for freshness thresholds, warning generation, HTML disclosure, and Excel provenance.

**Customer data handling disclosure**
- Added a consolidated customer-facing disclaimer to multilingual READMEs and detailed documentation.
- Clarified that ATI uses customer-controlled identity/scope and writes reports only to the selected local directory or storage destination.
- Added concise sensitivity and output-location guidance to Executive and Technical report footers.

**Bounded Azure Resource Graph throttling retries**
- `429 TooManyRequests` responses now honor `Retry-After`, with a 30-second fallback and a 120-second per-attempt cap.
- Each Resource Graph page is retried at most five times; completed pages are preserved and explicitly reported as potentially incomplete if retries are exhausted.
- Management Group subscription discovery now uses the shared paginated Resource Graph engine and the same retry policy.
- Added standard-library unit coverage for retry delays, HTTP-date parsing, retry exhaustion, and partial-result preservation.

**Executive/Technical Report and Excel Refinements**
- Executive HTML now includes a factual **Executive Evidence Summary**, a separate WAF Pillar Profile, Defender plan posture KPIs, and the renamed **High/Critical Security Signals** KPI with explanatory tooltip.
- Technical HTML top KPI cards now include subscriptions, High/Critical Security Signals, Defender Plans Observed, Disabled Defender Plans, and Non-Compliant Policy Records.
- HTML pagination now supports **Show less** after `Load More` / `Show all` expansion for paginated tables and cards.
- Excel `Classification` now includes **BY TECHNICAL CATEGORY** distribution next to Service Model and Business Pillar summaries.
- Excel `ModernizationSignals` now receives populated Technical Category counts and percentages from the modernization as-is summary.
- Excel `ResiliencyEvidence` now includes regional matrices by Service Model, Business Pillar, and Technical Category.

**Phase 3A: Resource Classification Taxonomy Refinement & Technical Report Enhancements**
- `config/resource_classification.yaml`: Added type-exact overrides for Azure Container Registry (ACR) resources to enable sub-namespace granularity:
  - `microsoft.containerregistry/registries` → Technical Category: "Compute - Containers - Registry" (Business Pillar: Compute, Service Model: PaaS)
  - `microsoft.containerregistry/registries/replications` → Technical Category: "Compute - Containers - Registry Replication" (Business Pillar: Compute, Service Model: PaaS)
  - Type-exact matching precedence: exact type > provider namespace > default (non-Microsoft)

- `writers/excel_writer.py`: Enhanced AllResources sheet with new "Detailed Technical Category" column:
  - Column position: After "Service Model" (column 8 of 13+)
  - Data source: `classify_resource_type()` function returning refined technical category
  - Width: 35 characters for full category display (e.g., "Compute - Containers - Registry", "Storage - Blob Accounts")
  - Impact: Users can now pivot/filter Excel by granular technical categories, enabling more precise cost, compliance, and modernization analysis

- `writers/html_technical.py`: New Technical HTML report section "📊 Technical Category Distribution":
  - Function: `_build_technical_categories_section(resources_by_type)` (lines 1836-1872)
  - Location: Infrastructure section, immediately after "📦 Resource Inventory", before Azure Arc section
  - Pagination: 5 categories initially displayed + "Load More" button for additional categories
  - Columns: Technical Category | Resource Count
  - Sidebar Navigation: Added link "📊 Technical Categories" → anchor `#technical-categories`
  - Aggregation: Resources grouped by refined technical category with count totals, sorted descending by resource count
  - Output Format: Interactive HTML table with pagination attributes (`data-paginate="5" data-page-step="5"`)

**Excel Sheet Enhancement: Technical Category Dimension** *(NEW)*
- `writers/excel_writer.py`: Enhanced **ModernizationSignals** sheet with "BY TECHNICAL CATEGORY" mini-table:
  - Location: Columns I-K, row 5 (alongside Service Model and Business Pillar sections)
  - Display: Technical Category labels with resource counts and percentages
  - Data Source: `asis.get("technical_category", {})` from modernization assessment summary
  - Impact: Enables cross-dimensional analysis of modernization signals by technical category

- `writers/excel_writer.py`: Enhanced **ResiliencyEvidence** sheet with "TECHNICAL CATEGORY DISTRIBUTION" section:
  - Location: Columns 10-11, row 3 (alongside Service Model and Business Pillar distributions)
  - Display: Technical Category labels with resource counts
  - Data Source: `env.get("technical_category_distribution", {})` from resiliency assessment
  - Width: 35 characters for full technical category names (e.g., "Compute - Containers - Registry")
  - Impact: Provides technical category breakdown of regional resiliency posture

- `processors/resiliency.py`: Updated resiliency assessment pipeline to compute technical category aggregations:
  - `_resource_dimensions()`: Added technical_category dimension alongside service_model and business_pillar
  - `_regional_rows()`: Added technical_categories breakdown per region for cross-dimensional regional analysis
  - `_build_subscription_rows()`: Added technical_category_distribution per subscription for subscription-level analysis
  - `build_resiliency_assessment()`: Exposed technical_category_distribution in environment object (top-level tenant view)

**Post-Scan Report Adjustments (8 items completed)**
- Defender for Cloud pagination: Defender Plans table and Individual Resource Coverage table now display 10 initial rows + "Load More" button
- All Findings table: 5 initial rows + "Load More" button for progressive disclosure of findings
- Landing Zone Observations: Confirmed color alternation (blue info / yellow warn) working as designed; no changes required
- Service Model table: Wrapped in `.table-scroll` div for responsive horizontal scrolling on smaller screens
- Excel ResiliencyEvidence: Removed duplicate "MULTI-ZONE RESOURCE VALIDATION LIST" section (was redundant with first section)

**Classification System Evolution**
- 3-tier classification system expanded to support granular sub-namespace categorization:
  - Tier 1: `technical_category` (refined e.g., "Compute - Containers - Registry" vs "Compute - Containers")
  - Tier 2: `business_pillar` (Compute, Data Platform, Security, Operations, etc.)
  - Tier 3: `service_model` (IaaS | PaaS | SaaS | Hybrid | Supporting Services | Other)
  - Tier 4 (type-exact): `types:` section in YAML for highest-precedence overrides
- Minimum scope: ACR (Registry + Replication) type-exacts; extensible to other namespaces via YAML configuration

### Changed

- Technical HTML report structure: "Technical Category Distribution" now appears in Infrastructure section (after Resource Inventory) to enable top-down classification analysis before WAF/Defender sections

### Fixed

- Excel ResiliencyEvidence sheet: Removed duplicate "MULTI-ZONE RESOURCE VALIDATION LIST" section, keeping first section as the authoritative inventory
- Report pagination consistency: All large tables now follow standard pagination pattern (5–10 initial rows, "Load More" button, generic `initPaginated()` JS function)

---

### Added

**Cloud Modernization & Opportunity Assessment (INFERRED)**
- New `processors/modernization.py` + `config/modernization_signals.yaml`: evolves the assessment from an inventory view into a maturity/opportunity view. Ten dimensions (Infrastructure, Application, Database, Data Platform & Analytics, AI Readiness, Automation, Security, Governance/Landing Zone, Observability, and a neutral Azure-Native vs Third-Party footprint) each get a **0–100 score**, a **level**, a **confidence**, an inferred **signal**, supporting **evidence**, and an **opportunity** indicator. Scoring methods: proportion, presence (family breadth), security (Defender coverage + misconfig density), governance (tags + policy compliance + Management Group structure), and footprint (publisher split).
- Fully config-driven, **non-prescriptive** (signals & opportunity indicators, never deterministic recommendations), evidence-backed, with **deterministic** (non-AI) narrative templates and framework references (WAF / CAF / ESLZ / AI-Ready / Defender). No third-party vendors are named. Derived entirely from already-collected data — no extra Azure calls.
- Surfaced as: an Executive report **heatmap + opportunity cards + narrative** (moved before *Top Priority Findings*), a Technical report **evidence table** (moved before *WAF Findings*), and a new Excel **`ModernizationSignals`** sheet. Replaces the previous simple "Technology & Modernization Signals" list.

**Architecture Diagram — draw.io (Phase D)**
- New `writers/drawio_writer.py` generates a multi-page `.drawio` (diagrams.net) architecture diagram: **Overview** (KPIs by Service Model and Business Pillar with cross-page links), **Service Model**, **Business Pillar**, and one **Resources** page per subscription (resource-group containers with `N × Type` nodes, region, and classification tooltips).
- **Organization** page (`collectors/mgmt_groups.py` + `processors/org_tree.py`): top-down **Tenant → Management Groups → Subscriptions** tree with per-subscription resource counts. The Management Group hierarchy is reconstructed from each subscription's `managementGroupAncestorsChain` (Resource Graph, no extra SDK/permissions) and degrades gracefully to a flat Tenant → Subscriptions view when unavailable. Skippable with `--skip-org`.
- **Network Topology** page (`processors/network_topology.py`): VNets rendered as containers (CIDR + VNet corner icon) holding their subnets, with Azure icons for reserved subnets (GatewaySubnet / AzureBastionSubnet / AzureFirewallSubnet). Peering edges are colored **green (Connected)** / **red dashed (Disconnected or orphan)**; peerings to VNets outside the scan scope link to an **External VNet** placeholder. Connectivity-aware layout places peered VNets adjacently and routes edges through a lane below each row to avoid crossing unrelated VNets. Derived entirely from already-collected Resource Graph data (no extra Azure calls) and skipped when the tenant has no VNets.
- **Network Detail** page (`processors/network_detail.py` + `config/network_placement.yaml`): detailed view placing resources **inside their subnets** — VMs (via NIC join), Private Endpoints, Azure Firewall, VPN/ExpressRoute Gateways, Application Gateways, Load Balancers, Bastion, SQL Managed Instance — with an **NSG shield** per subnet, **loose (unattached) NIC** aggregation, and an **On-Premises** node per subscription that has a VPN/ExpressRoute gateway. Subscriptions are grouped in a subtle bordered container with the Subscriptions icon; resources aggregate to `N × Type` above a configurable threshold (default 8). Placement is config-driven (subnet-resolution JSON paths), so new resource types need only a YAML entry. A `--network-detail-per-subscription` flag renders one page per subscription for very large tenants; peering edges are lane-routed with a **Broken Peering** marker on disconnected links.
- **Security Posture** overlay (`processors/security_overlay.py` + `config/security_overlay.yaml`): severity **risk badges** on Network Detail resource nodes (worst of misconfiguration, Defender unhealthy assessment, and policy non-compliance per resource — with the Zero Trust principle in the tooltip) plus a dedicated **Security Posture** page of per-subscription cards (risk-colored header + subscription icon, High/Medium/Low chips, Defender coverage bar, Zero Trust breakdown). Config-driven severity colors and Zero Trust mapping; enabled automatically when security data is present and disabled with `--no-security-overlay`.
- **Network Topology** and **Network Detail** group VNets by subscription in a subtle bordered container (Subscriptions icon + name) for quick attribution.
- Diagrams are generated **without gridlines** (`grid="0"`) for a cleaner canvas on open.
- Real **Azure 2019 icon stencils** driven by `config/drawio_stencils.yaml` (exact type → provider namespace fallback). A generic `All_Resources` fallback icon guarantees every node is iconified — keeping the diagram flexible for brand-new Azure resource types.
- Row-based flow layout for resource-group containers (no overlap regardless of type count); subscription pages are prefixed with `Sub-` for quick navigation.
- `invoke_ati.py` gains a `--no-diagram` flag to skip diagram generation; `*.drawio` outputs are git-ignored.

**Resource Classification Taxonomy (Phase C)**
- Config-driven 3-tier taxonomy (`config/resource_classification.yaml`) + `processors/classifier.py`: Technical Category, Business Pillar, Service Model (IaaS/PaaS/SaaS/Hybrid/Supporting Services/Other), and Publisher (Microsoft/Third-party). Matching precedence: exact type → provider namespace → third-party/default.
- New Excel **`Classification`** sheet (right after `Index`) with summary pivots (by Service Model and by Business Pillar) and a per-type detail table.
- `AllResources` gains **Business Pillar** and **Service Model** columns; `Overview` gains a **Service Model** summary block.

**Excel Navigation, Category & Report UX (Phase C)**
- Excel: new **`Index`** navigation sheet (after `Overview`) with a hyperlink to every tab, plus a **↩ Index** back-link on each sheet.
- Excel: collision-free, namespace-aware per-type sheet names — a short provider prefix is added only when two providers would otherwise produce the same name (e.g. `Cmp-Virtualmachinetemplates` vs `VMw-Virtualmachinetemplates`).
- Excel: all resource types get a sheet up to Excel's 255-sheet limit (the rest stay in `AllResources`), with scope-aware sheet-count warnings (subscription ≥ 40, management group ≥ 60, tenant ≥ 75; env-overridable) and a hard warning at 200.
- Excel: new **`Category`** column in `AllResources` and a **Resource Origin** summary in `Overview` (Azure-native / Hybrid-Arc / Migrate).
- Excel: **Data Collection Notes** section in `Overview`, mirroring the HTML reports.
- Executive HTML: collapsible sections with Expand All / Collapse All, priority-colored recommendation cards, color-coded Zero Trust posture with descriptions, and a link to the Data Collection Notes.
- Technical HTML: **Resources by Subscription** chart labeled by subscription name; WAF findings tables with progressive loading (30 at a time, up to 300 per pillar; full list in the Excel export); column search on the Defender Plans by Subscription table; link to the Data Collection Notes.

**Robustness & Packaging (Phase C)**
- `collectors/resource_graph.py`: subscriptions are queried in chunks of up to 1000 (Resource Graph per-request limit) instead of silently dropping the excess.
- `invoke_ati.py`: the report-name prompt is skipped in non-interactive runs (`--yes` or no TTY), defaulting to `ATI_Report`.
- `pyproject.toml`: fixed build backend (`setuptools.build_meta`), packaged the `invoke_ati` entry module (`py-modules`), and added upper version bounds to dependencies for reproducible installs.
- Documentation: README (EN/PT-BR/ES) and `DOCUMENTATION.md` updated for the new features and given a Troubleshooting section; removed the third-party tool comparison section.

**Enhanced Excel Inventory (Phase A/B)**
- `AllResources` now includes common Azure Resource Graph / ARM inventory columns such as display type, subscription name, tenant ID, SKU details, provisioning state, created time, identity type, zones, resource ID, and raw properties.
- `Subscriptions` now summarizes resource inventory by subscription, resource group, location, and resource type instead of only listing one row per subscription.
- Per-resource-type sheets now use configured display names, prioritize core Azure resource types, and include the union of promoted `enriched_*` columns across all rows, ordered by `config/resource_enrichment.yaml`.
- Added/expanded declarative profiles for core resource types including VMs, disks, NICs, public IPs, NSGs, VNets, storage accounts, App Services, App Service Plans, Key Vaults, SQL servers/databases, and Private Endpoints.
- Column selection is grounded in official Microsoft Learn references: [Azure Resource Graph table/resource type reference](https://learn.microsoft.com/en-us/azure/governance/resource-graph/reference/supported-tables-resources) and [ARM template resource definitions](https://learn.microsoft.com/en-us/azure/templates/).

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
