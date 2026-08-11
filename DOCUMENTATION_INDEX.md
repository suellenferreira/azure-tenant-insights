# Documentation Index — Azure Tenant Insights

**Purpose:** Navigation guide for users, architects, operators, contributors, and reviewers
**Last Updated:** August 6, 2026

---

## Quick Navigation

### 🚀 For First-Time Users
Start with **[README.md](./README.md)**.
- Why and when to run ATI
- What problem ATI helps investigate
- Difference between inventory and assessment signals
- How to run a focused first scan
- What each output contains
- Authentication, RBAC, scope, and data-handling considerations

### 📖 For Understanding Features
Start here → **[DOCUMENTATION.md](./DOCUMENTATION.md)**
- Collection and processing methodology
- Data sources and Azure API references
- WAF, CAF, Zero Trust, Defender, modernization, and resiliency posture signals
- Configuration and extension points
- Limitations and interpretation boundaries

### 🧪 For Contributors and Maintainers
Start here → **[TESTING_GUIDE.md](./TESTING_GUIDE.md)**
- Integration and regression testing procedures
- Test commands and expected results
- Troubleshooting and validation checkpoints
- Release review checklist

### 📝 For Historical Implementation Reference
Start here → **[CHANGELOG_ITEMS_0-6.md](./CHANGELOG_ITEMS_0-6.md)**
- Item-by-item implementation details
- Files modified with line numbers
- Backward compatibility notes
- Historical implementation summary; use `CHANGELOG.md` for current release history

### ✏️ For Updating README Files
Start here → **[README.UPDATES.md](./README.UPDATES.md)**
- Exact changes needed in README.md
- Portuguese (PT-BR) translation guide
- Spanish (ES) translation guide
- Verification checklist
- Timeline for production release

---

## Document Overview

| Document | Purpose | Length | Read Time |
|----------|---------|--------|-----------|
| [README.md](./README.md) | Purpose, use cases, quick start, outputs, and limitations | User guide | 5-10 min |
| [DOCUMENTATION.md](./DOCUMENTATION.md) | Feature methodologies, data sources, and interpretation boundaries | Technical reference | 20 min |
| [CHANGELOG.md](./CHANGELOG.md) | Release history and notable changes | Historical reference | As needed |
| [TESTING_GUIDE.md](./TESTING_GUIDE.md) | Integration testing procedures | 4,500 words | 30 min (+ testing) |
| [README.UPDATES.md](./README.UPDATES.md) | README maintenance notes | Contributor reference | As needed |

The standard end-user reading path is README → generated reports → DOCUMENTATION.md
when methodology details are needed. TESTING_GUIDE.md is maintained for contributors
and reviewers and is not required for an initial customer assessment.

---

## Documentation by Audience

### Customer, Executive, or Account Team

1. Read [Why and When to Run ATI](./README.md#why-and-when-to-run-ati).
2. Review the synthetic [Example Outputs](./README.md#example-outputs).
3. Run ATI against one subscription first.
4. Review the Executive HTML report.
5. Use the Technical report and Excel workbook for evidence and follow-up.
6. Consult [DOCUMENTATION.md](./DOCUMENTATION.md) for methodology details.

### Enterprise Architect

Focus on modernization signals, CAF observations, WAF findings, Service Model and
Business Pillar classifications, regional distribution, and architecture diagrams.

### Security and Governance Team

Focus on Defender posture and coverage, Policy compliance, misconfiguration findings,
Zero Trust observations, CAF security and governance observations, Resource Health,
and deprecated resources.

### DevOps and Operations Team

Focus on scan scope, regional distribution, Resource Health, Advisor findings, cost
data, Defender coverage gaps, report naming, and repeatable snapshot workflows.

### Contributors and Maintainers

Use [TESTING_GUIDE.md](./TESTING_GUIDE.md) for validation, [CHANGELOG.md](./CHANGELOG.md)
for release history, and [DOCUMENTATION.md](./DOCUMENTATION.md) for architecture,
methodology, and extension points.

---

## Feature and Methodology Reference

The current implementation covers inventory, posture, framework visibility, diagrams,
and inferred modernization signals. The detailed methodology is maintained in
[DOCUMENTATION.md](./DOCUMENTATION.md).

| Area | Description | Detailed Reference |
|---|---|---|
| Resource inventory | Dynamic discovery and normalized Azure resource data | [README.md](./README.md#output-files) |
| Security posture | Defender plans, assessments, coverage, and security signals | [DOCUMENTATION.md](./DOCUMENTATION.md#item-7-defender-for-cloud--posture-coverage-gap--live-pricing) |
| WAF findings | Azure Advisor recommendations grouped by WAF pillar | [DOCUMENTATION.md](./DOCUMENTATION.md#data-sources--references) |
| CAF observations | Landing zone observations across security, governance, cost, operations, and reliability | [DOCUMENTATION.md](./DOCUMENTATION.md#item-6-caf-landing-zone-observations) |
| Modernization signals | Inferred technology adoption and maturity signals | [DOCUMENTATION.md](./DOCUMENTATION.md#item-11-cloud-modernization--opportunity-assessment) |
| Resiliency posture signals | Regional distribution and multi-zone resource configuration (observed from inventory) | [DOCUMENTATION.md](./DOCUMENTATION.md#item-12-resiliency-posture-signals) |
| Resource classification | Technical category, business pillar, service model, and publisher | [README.md](./README.md#output-files) |
| Architecture diagrams | Organization, service model, network, security, and subscription views | [DOCUMENTATION.md](./DOCUMENTATION.md#item-10-architecture-diagrams-drawio) |
| Regional analytics | Resource distribution by Azure region | [DOCUMENTATION.md](./DOCUMENTATION.md#item-3-active-regions-analytics) |
| Deprecated resources | Detection based on known Azure retirement announcements | [README.md](./README.md#output-files) |

### Historical Feature Summary

The following implementation summary is retained for historical traceability. It is
not the recommended reading path for end users.

#### Items Completed (0-7)

#### Item 0: Modernization Signals ✅
- **What:** Detects 6 technology adoption patterns (AI/ML, Containers, Serverless, Data Lakes, Streaming, APIs)
- **Where:** Technical HTML report, Infrastructure section
- **Data Source:** Azure Resource Graph
- **Documentation:** [DOCUMENTATION.md → Item 0](./DOCUMENTATION.md#item-0-modernization-signals)

#### Item 1: Flag Paradigm Inversion ✅
- **What:** Changed from `--include-*` (opt-in) to `--skip-*` (opt-out)
- **Impact:** Defender + Costs **enabled by default**
- **Backward Compatibility:** Breaking change (requires flag migration)
- **Documentation:** [DOCUMENTATION.md → Item 1](./DOCUMENTATION.md#item-1-flag-paradigm-inversion)

#### Item 2: Tenant & Subscription Metadata ✅
- **What:** Displays tenant name/ID + subscriptions list in HTML meta-bar
- **Where:** Both Executive and Technical reports (top-right corner)
- **Data Source:** Azure Subscription API
- **Documentation:** [DOCUMENTATION.md → Item 2](./DOCUMENTATION.md#item-2-tenant--subscription-metadata)

#### Item 3: Active Regions Analytics ✅
- **What:** Aggregates resources by Azure region, shows top 12
- **Output:** Executive chart + Technical table with counts/percentages
- **Data Source:** Resource `properties.location` from Azure Resource Graph
- **Documentation:** [DOCUMENTATION.md → Item 3](./DOCUMENTATION.md#item-3-active-regions-analytics)

#### Item 4: Interactive Report Naming ✅
- **What:** Prompts user for custom report prefix (or use default)
- **UX:** Simple prompt after scanning starts
- **Example:** `ATI_Production_Audit_2026-06-16_14-30-45_*.{xlsx,html}`
- **Documentation:** [DOCUMENTATION.md → Item 4](./DOCUMENTATION.md#item-4-interactive-report-naming)

#### Item 5: Excel Overview Sheet Styling ✅
- **What:** Professional dark-theme design with color-coded KPI metrics
- **Features:** Navy blue headers, color-coded values, borders, optimized spacing
- **Print-Friendly:** Page setup configured (0.5"/0.75" margins)
- **Documentation:** [DOCUMENTATION.md → Item 5](./DOCUMENTATION.md#item-5-excel-overview-sheet-styling)

#### Item 6: CAF Landing Zone Observations ✅
- **What:** 14+ observations aligned with 5 CAF pillars
- **Pillars:** Security, Cost Management, Operational Excellence, Reliability, Governance
- **Format:** ✓ (compliant) or ⚠ (remediation needed) with CAF references
- **Data Sources:** Azure Resource Graph, Advisor, Policy, Health, Defender
- **Documentation:** [DOCUMENTATION.md → Item 6](./DOCUMENTATION.md#item-6-caf-landing-zone-observations)

#### Item 7: Defender Posture, Coverage Gap & Live Pricing ✅
- **What:** Real Defender plan posture per subscription, unprotected billable units + monthly cost to protect, and live Defender unit prices
- **Where:** Executive + Technical HTML reports; Excel `DefenderPosture`, `DefenderServersCoverage`, `DefenderCoverageGap`, `DefenderCostEstimate` sheets
- **Data Sources:** `Microsoft.Security/pricings` (Resource Graph) + Azure Retail Prices API (with offline fallback)
- **RBAC:** Plan posture needs only `Reader`
- **Documentation:** [DOCUMENTATION.md → Item 7](./DOCUMENTATION.md#item-7-defender-for-cloud--posture-coverage-gap--live-pricing)

---

## Data Sources & References

All features use **official Azure APIs** only:

| Service | Reference |
|---------|-----------|
| Azure Resource Graph | [Overview](https://learn.microsoft.com/en-us/azure/governance/resource-graph/) |
| Azure Advisor | [Overview](https://learn.microsoft.com/en-us/azure/advisor/) |
| Azure Policy | [Overview](https://learn.microsoft.com/en-us/azure/governance/policy/) |
| Resource Health | [Documentation](https://learn.microsoft.com/en-us/azure/resource-health/) |
| Defender for Cloud | [Overview](https://learn.microsoft.com/en-us/azure/defender-for-cloud/) |
| Defender plan posture | [`Microsoft.Security/pricings`](https://learn.microsoft.com/en-us/rest/api/defenderforcloud/pricings/list) |
| Azure Retail Prices | [Retail Prices API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices) |
| Cost Management | [Documentation](https://learn.microsoft.com/en-us/azure/cost-management-billing/) |

**Frameworks Referenced:**
- [Well-Architected Framework](https://learn.microsoft.com/en-us/azure/architecture/framework/)
- [Cloud Adoption Framework](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/)

---

## Data Sources and Framework References

All features use official Azure APIs where the relevant data source is enabled and
accessible. See [DOCUMENTATION.md](./DOCUMENTATION.md#data-sources--references) for
the complete source and framework reference list.

---

## Files Modified in Historical Package

### Production Code
- ✅ `invoke_ati.py` — Flag paradigm + interactive naming (Items 1, 4); Defender posture pre-warm + collection warnings summary (Item 7)
- ✅ `writers/html_executive.py` — Region chart (Item 3); Defender posture + coverage gap (Item 7)
- ✅ `writers/html_technical.py` — Signals, metadata, regions, CAF observations (Items 0, 2, 3, 6); Defender posture + coverage gap (Item 7)
- ✅ `writers/excel_writer.py` — Dark theme styling (Item 5); Defender posture/coverage/cost sheets (Item 7)
- ✅ `collectors/defender_posture.py` — Defender plan posture via `Microsoft.Security/pricings` (Item 7)
- ✅ `collectors/defender_pricing.py` — Coverage gap + live Azure Retail Prices with offline fallback (Item 7)

### New Documentation
- ✅ `DOCUMENTATION.md` — Comprehensive methodology guide
- ✅ `CHANGELOG_ITEMS_0-6.md` — Implementation history
- ✅ `TESTING_GUIDE.md` — Integration testing procedures
- ✅ `README.UPDATES.md` — README update instructions
- ✅ `DOCUMENTATION_INDEX.md` — This file

---

## Historical Validation Notes

### Validation Status
- ✅ **Syntax:** All files compile without errors
- ✅ **Imports:** No new external dependencies required
- ✅ **Type Hints:** Existing patterns followed
- ✅ **Backward Compatibility:** 6 non-breaking, 1 breaking change (Item 1)

### Test Coverage
- ✅ All 7 items have dedicated test procedures (see [TESTING_GUIDE.md](./TESTING_GUIDE.md))
- ⏳ Ready for integration testing with live Azure subscription

---

## Contributor Release Checklist

Use this checklist when changing ATI or reviewing a release. It is not required for
an initial customer assessment.

### Before Release
- [ ] Integration testing passes (all 7 items)
- [ ] README.md updated with new features
- [ ] README.pt-BR.md translated
- [ ] README.es.md translated
- [ ] CHANGELOG.md updated in main repository
- [ ] Version bumped to 2.0 in `pyproject.toml` and `invoke_ati.py`
- [ ] GitHub release created with detailed release notes

### Documentation Requirements
- [ ] DOCUMENTATION.md included in repository
- [ ] CHANGELOG_ITEMS_0-6.md included in repository
- [ ] TESTING_GUIDE.md included in repository
- [ ] README files link to DOCUMENTATION.md for methodology

### Communication
- [ ] Release notes mention breaking change (Item 1: `--include-*` → `--skip-*`)
- [ ] Migration guide provided for existing scripts
- [ ] CAF alignment documented (Item 6)
- [ ] Data sources documented (all items)

---

## Typical User Journey

### End User
1. Read [Why and When to Run ATI](./README.md#why-and-when-to-run-ati).
2. Review the synthetic [Example Outputs](./README.md#example-outputs).
3. Run ATI against one subscription first.
4. Review the Executive HTML report.
5. Use the Technical report and Excel workbook for evidence and follow-up.
6. Consult [DOCUMENTATION.md](./DOCUMENTATION.md) when methodology details are needed.

### Enterprise Architect
1. **Review:** CAF Landing Zone observations in Technical report
2. **Reference:** [CAF documentation](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/)
3. **Remediate:** Follow actionable guidance per observation
4. **Validate:** Run periodic scans to track progress

### DevOps/Operations
1. **Automate:** Use `--skip-defender --skip-costs` if desired
2. **Archive:** Custom report naming for monthly audits
3. **Monitor:** Regional distribution trends over time
4. **Integrate:** Embed reports in dashboards or documentation

### Data Analyst
1. **Extract:** Excel inventory sheets (all resource types)
2. **Analyze:** Top resource types, advisor findings, costs
3. **Report:** Use Excel styling for executive presentations
4. **Validate:** Cross-reference with Azure portal for accuracy

---

## FAQ

### Q: Where do I start?
**A:** Read the [Why and When to Run ATI](./README.md#why-and-when-to-run-ati) section
in README.md, then run a focused scan against one subscription.

### Q: Why should I run ATI if I already use Azure Portal or Defender for Cloud?
**A:** ATI does not replace those services. It consolidates information from multiple
Azure sources into repeatable Executive, Technical, Excel, and architecture views.

### Q: Does ATI certify security, CAF, WAF, or modernization readiness?
**A:** No. ATI provides evidence and assessment signals. Formal certification, audit,
and architecture decisions require additional validation.

### Q: Does ATI change anything in Azure?
**A:** No. ATI is read-only and does not create, modify, or delete Azure resources.

### Q: I broke my existing scripts with `--include-defender`
**A:** Item 1 is a breaking change. Replace `--include-*` with nothing (included by default) or use `--skip-*` to exclude. See [CHANGELOG_ITEMS_0-6.md → Item 1](./CHANGELOG_ITEMS_0-6.md#item-1-flag-paradigm-inversion-skip--vs-include-).

### Q: How is "CAF Landing Zone" different from general findings?
**A:** Observations are specifically aligned with Microsoft CAF pillars (Security, Cost, Ops, Reliability, Governance). Each references official CAF documentation. See [DOCUMENTATION.md → Item 6](./DOCUMENTATION.md#item-6-caf-landing-zone-observations).

### Q: Can I skip all optional data (Defender, Costs, Advisor)?
**A:** Yes: `python invoke_ati.py --skip-defender --skip-costs --skip-advisor`. You'll get core inventory + policy + health only.

### Q: Where can I learn more about a specific feature?
**A:** See [DOCUMENTATION.md](./DOCUMENTATION.md) for methodology, data sources, and limitations for each feature.

### Q: Where are the tests and validation procedures?
**A:** Contributors and maintainers should use [TESTING_GUIDE.md](./TESTING_GUIDE.md).
It is not required reading for someone performing an initial customer assessment.

---

## Support & Contributions

### Reporting Issues
If you find an issue, reference:
- The affected output or workflow
- The feature or collector involved
- Expected vs. actual behavior
- [TESTING_GUIDE.md](./TESTING_GUIDE.md) test case number (if applicable)

### Contributing
See [DOCUMENTATION.md](./DOCUMENTATION.md) for architecture and data flow to understand how to extend features.

---

## Historical Version History

| Version | Date | Items | Status |
|---------|------|-------|--------|
| 1.0 | (Previous) | 0 | Stable |
| 2.0 | June 16, 2026 | 0-6 | Historical implementation package |

---

## Key References

**Official Azure Documentation:**
- [Azure Resource Graph](https://learn.microsoft.com/en-us/azure/governance/resource-graph/)
- [Azure Advisor](https://learn.microsoft.com/en-us/azure/advisor/)
- [Cloud Adoption Framework](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/)
- [Well-Architected Framework](https://learn.microsoft.com/en-us/azure/architecture/framework/)

**This Repository:**
- [Main README](./README.md) — Feature overview
- [DOCUMENTATION.md](./DOCUMENTATION.md) — Detailed methodology
- [TESTING_GUIDE.md](./TESTING_GUIDE.md) — Integration testing
- [CHANGELOG_ITEMS_0-6.md](./CHANGELOG_ITEMS_0-6.md) — Implementation history

---

**Status:** Documentation index updated for the current ATI user and contributor journeys.
**Questions?** Start with [README.md](./README.md), then reference [DOCUMENTATION.md](./DOCUMENTATION.md).

