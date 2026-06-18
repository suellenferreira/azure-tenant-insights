# README Updates Required — Items 0-6

**Date:** June 16, 2026  
**Status:** Documentation created; READMEs need updates for production release

---

## Summary

3 README files exist and need updates to reflect 7 enhancement items (Items 0-6):

1. ✅ **`DOCUMENTATION.md`** — Created (comprehensive methodology + sources)
2. ✅ **`CHANGELOG_ITEMS_0-6.md`** — Created (item-by-item history + test cases)
3. ⏳ **`README.md`** (English) — Needs updates
4. ⏳ **`README.pt-BR.md`** (Portuguese-BR) — Needs updates
5. ⏳ **`README.es.md`** (Spanish) — Needs updates

---

## What Needs to Change in Each README

### Section 1: Parameters Reference — "Optional Data Sources"

**Current (Outdated):**
```markdown
| Parameter | Description | Extra RBAC Required |
|---|---|---|
| `--include-defender` | Collect Defender for Cloud assessments | `Security Reader` |
| `--include-costs` | Collect Cost Management data (current month) | `Cost Management Reader` |
| `--include-tags` | Add resource tags column to Excel inventory | None |
| `--skip-policy` | Skip Azure Policy compliance collection | — |
| `--skip-advisor` | Skip Azure Advisor recommendations | — |
```

**New (Item 1 — Flag Paradigm):**
```markdown
### Optional Data Sources

**Default behavior:** Defender for Cloud, Costs, and Advisor data are **included by default**. Use the `--skip-*` flags below to exclude them if not needed.

| Parameter | Description | Extra RBAC Required |
|---|---|---|
| `--skip-defender` | Exclude Defender for Cloud assessments (enabled by default) | — |
| `--skip-costs` | Exclude Cost Management data (enabled by default) | — |
| `--include-tags` | Add resource tags column to Excel inventory | None |
| `--skip-policy` | Skip Azure Policy compliance collection | — |
| `--skip-advisor` | Skip Azure Advisor recommendations | — |
| `--report-name <NAME>` | Custom prefix for report files (interactive prompt if not provided) | — |
```

**Why:** Item 1 (Flag Paradigm Inversion) inverts default behavior from opt-in to opt-out.

---

### Section 2: Output Files — Executive Report Description

**Current (Outdated):**
```markdown
### `*_Executive.html` — Executive Report

Self-contained HTML file. Open in any modern browser — **no internet required**.

- Overall risk level banner
- KPI tiles (resources, subscriptions, critical findings, deprecated, tag coverage)
- Advisor recommendations by WAF pillar (donut chart)
- Top resource types (bar chart)
- Top 5 priority findings
- Strategic recommendations (linked to findings)
- Modernization signals *(labeled as INFERRED)*
```

**New (Items 0 + 3):**
```markdown
### `*_Executive.html` — Executive Report

Self-contained HTML file. Open in any modern browser — **no internet required**.

- Overall risk level banner
- KPI tiles (resources, subscriptions, critical findings, deprecated, tag coverage)
- Advisor recommendations by WAF pillar (donut chart)
- Top resource types (bar chart)
- Active regions distribution (horizontal bar chart) ← **NEW (Item 3)**
- Top 5 priority findings
- Strategic recommendations (linked to findings)
- Modernization signals *(labeled as INFERRED)* ← **Confirmed (Item 0)**
```

**Why:** Item 3 adds Regional Distribution chart to Executive report.

---

### Section 3: Output Files — Technical Report Description

**Current (Outdated):**
```markdown
### `*_Technical.html` — Technical Report

Self-contained HTML file with sidebar navigation.

- Resource inventory summary
- WAF pillar findings (tabbed by pillar)
- Policy compliance violations
- Known misconfigurations (linked to official documentation)
- Defender for Cloud assessments *(if `--include-defender`)*
- Resource health events
- Deprecated/retiring resources with migration links
- Landing Zone observations *(labeled as INFERRED)*
- Azure Arc resources *(if present)*
```

**New (Items 0 + 2 + 3 + 6):**
```markdown
### `*_Technical.html` — Technical Report

Self-contained HTML file with sidebar navigation.

- Tenant & subscription metadata in header ← **NEW (Item 2)**
- Resource inventory summary
- WAF pillar findings (tabbed by pillar)
- Policy compliance violations
- Known misconfigurations (linked to official documentation)
- Defender for Cloud assessments *(if `--skip-defender` not used)* ← **Updated (Item 1)**
- Resource health events
- Deprecated/retiring resources with migration links
- Technology & Modernization Signals (6 categories detected) ← **NEW (Item 0)**
- Regional distribution table (top 12 regions by resource count) ← **NEW (Item 3)**
- Landing Zone observations with CAF alignment *(labeled as INFERRED)* ← **Enhanced (Item 6)**
- Azure Arc resources *(if present)*
```

**Why:** Items 0, 2, 3 add new content; Item 1 inverts flag; Item 6 enhances existing section.

---

### Section 4: Add New Section — "Report Features & Methodologies"

**Add after "Output Files" section:**

```markdown
---

## Report Features & Methodologies

### Modernization Signals (Item 0)

Detects 6 technology adoption patterns: **AI/ML**, **Containers**, **Serverless**, **Data Lakes**, **Streaming**, **APIs**.

**Data Source:** [Azure Resource Graph](https://learn.microsoft.com/en-us/azure/governance/resource-graph/overview)

**Location in Reports:**
- Executive: Circular badge indicators (🚀)
- Technical: Detailed list in Infrastructure section

**Methodology:** Iterates resource types and counts matches against curated patterns. INFERRED analysis only.

---

### Active Regions Analytics (Item 3)

Aggregates resources by Azure region, calculates regional penetration percentages, displays top 12 regions.

**Data Source:** `properties.location` field from [Azure Resource Graph](https://learn.microsoft.com/en-us/azure/governance/resource-graph/overview)

**Output:**
- Executive Report: Horizontal bar chart
- Technical Report: Table with Region | Count | Percentage

**Use Cases:** Identify deployment regions, validate HA/DR spread, cost optimization.

---

### Cloud Adoption Framework Landing Zone (Item 6)

Evaluates infrastructure alignment with [Microsoft CAF](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/) across 5 pillars: **Security**, **Cost Management**, **Operational Excellence**, **Reliability**, **Governance**.

**Data Sources:**
- Azure Resource Graph (resource types)
- Azure Advisor (recommendations)
- Azure Policy (compliance)
- Resource Health (availability)
- Defender for Cloud (security findings)

**Output:** 14 CAF-aligned observations with actionable remediation guidance.

**Location:** Technical report "🏗 Landing Zone" section.

---

### Tenant & Subscription Metadata (Item 2)

Displays tenant name/ID and subscriptions list in HTML report meta-bar headers.

**Format:** `Tenant: Name (ID) | Subscriptions: sub1, sub2, sub3`

**Location:** Top-right corner meta-bar in both Executive and Technical reports.

---

### Interactive Report Naming (Item 4)

Prompts user for custom report prefix. If Enter pressed, uses default timestamp-based name.

**Example:**
```bash
$ python invoke_ati.py
[Optional] Custom report name (or press Enter for default):
[DEFAULT] Format: ATI_Scan_YYYY-MM-DD_HH-MM-SS
> Production_Audit
# Files: ATI_Production_Audit_2026-06-16_14-30-45_*.{xlsx,html}
```

---

### Excel Overview Sheet Styling (Item 5)

Professional dark-theme design with color-coded KPI metrics:
- Dark Navy header (#1F4E79) with white text
- Color-coded values: Green (OK) | Yellow (Medium) | Orange (High) | Red (Critical)
- Optimized page setup for printing (0.5"/0.75" margins)

---

## Data Sources & References

### Primary Azure APIs

| Service | Reference | Used For |
|---|---|---|
| Azure Resource Graph | [Overview](https://learn.microsoft.com/en-us/azure/governance/resource-graph/overview) | Resource enumeration, regional data |
| Azure Advisor | [Overview](https://learn.microsoft.com/en-us/azure/advisor/) | WAF recommendations |
| Azure Policy | [Overview](https://learn.microsoft.com/en-us/azure/governance/policy/overview) | Compliance violations |
| Resource Health | [Docs](https://learn.microsoft.com/en-us/azure/resource-health/resource-health-overview) | Degraded resources |
| Defender for Cloud | [Overview](https://learn.microsoft.com/en-us/azure/defender-for-cloud/) | Security assessments |

### Well-Architected Framework & CAF

- **WAF**: [Official Framework](https://learn.microsoft.com/en-us/azure/architecture/framework/)
- **CAF**: [Cloud Adoption Framework](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/)

For detailed methodology on each feature, see [DOCUMENTATION.md](./DOCUMENTATION.md).
```

**Why:** Explains new features added in Items 0-6 and provides data source references.

---

### Section 5: Note on Charts

**Current:**
```markdown
> **Note on Charts:** Reports use [Chart.js](https://www.chartjs.org/) loaded from CDN (`cdn.jsdelivr.net`). An internet connection is required to display charts. All data tables are visible without internet.
```

**New:**
```markdown
> **Note on Charts:** Reports use [Chart.js](https://www.chartjs.org/) v4.4.0 loaded from CDN (`cdn.jsdelivr.net`). An internet connection is required to display charts (Executive report charts, Regional distribution chart). All data tables are visible without internet.
```

**Why:** Specifies Chart.js version and clarifies which reports have charts.

---

### Section 6: Update "Estimated Runtime"

Consider adding note about additional data collection:

```markdown
> **Note:** Runtime estimates above assume standard data collection (resources, advisor, policy). 
> With `--skip-defender` and `--skip-costs`, runtime may be 10-15% faster.
> Regional aggregation adds negligible overhead (<1s).
```

---

## Files to Update

### 1. README.md (English)
Apply all changes above (Sections 1-6)

### 2. README.pt-BR.md (Portuguese-Brazil)
Apply same structure with Portuguese translations:
- "Fonte de Dados Opcionals" → "Fontes de Dados Opcionais"
- "Parâmetro" → "Parâmetro"
- Translate all descriptions and examples

### 3. README.es.md (Spanish)
Apply same structure with Spanish translations:
- "Fuentes de Datos Opcionales"
- "Parámetro"
- Translate all descriptions and examples

---

## Verification Checklist

After updating all 3 READMEs:

- [ ] Section "Optional Data Sources" mentions `--skip-defender`, `--skip-costs` (Item 1)
- [ ] Executive report description mentions "Active regions distribution" chart (Item 3)
- [ ] Technical report description mentions:
  - Tenant & subscription metadata (Item 2)
  - Modernization Signals (Item 0)
  - Regional distribution table (Item 3)
  - CAF Landing Zone observations (Item 6)
- [ ] New "Report Features & Methodologies" section added with all 7 items
- [ ] "Data Sources & References" section includes Azure APIs and CAF documentation
- [ ] Links to DOCUMENTATION.md for detailed methodology
- [ ] All 3 languages translated consistently

---

## Additional Documentation Files Created

| File | Purpose | Status |
|------|---------|--------|
| `DOCUMENTATION.md` | Comprehensive methodology + sources for all features | ✅ Created |
| `CHANGELOG_ITEMS_0-6.md` | Item-by-item changelog with test cases | ✅ Created |
| `README.UPDATES.md` | This file — instructions for README updates | ✅ Created |

---

## Timeline for Production Release

1. ✅ **Code Implementation** (Complete)
2. ✅ **Code Validation** (Complete — all files compile)
3. ✅ **Documentation Creation** (Complete — DOCUMENTATION.md + CHANGELOG created)
4. ⏳ **README Updates** (This task — 30 min estimated)
5. ⏳ **Integration Testing** (Ready to execute)
6. ⏳ **Production Release** (After testing passes)

---

**Next Action:** Update the 3 README files with changes documented in this file, then proceed to integration testing.

**Questions?** Refer to DOCUMENTATION.md for detailed methodology on any feature.
