# Documentation Index — Azure Tenant Insights v2.0 (Items 0-6)

**Last Updated:** June 16, 2026  
**Status:** ✅ All features implemented and documented  
**Version:** 2.0

---

## Quick Navigation

### 🚀 For Users Running Tests
Start here → **[TESTING_GUIDE.md](./TESTING_GUIDE.md)**
- Step-by-step validation for all 7 items
- Test commands and expected results
- Troubleshooting section
- ~45 minutes per subscription

### 📖 For Understanding Features
Start here → **[DOCUMENTATION.md](./DOCUMENTATION.md)**
- Comprehensive methodology for each feature
- Data sources and Azure API references
- Cloud Adoption Framework (CAF) alignment
- Configuration files documentation
- Use cases and limitations

### 📝 For Historical Reference
Start here → **[CHANGELOG_ITEMS_0-6.md](./CHANGELOG_ITEMS_0-6.md)**
- Item-by-item implementation details
- Files modified with line numbers
- Backward compatibility notes
- Session 2 completion summary

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
| [DOCUMENTATION.md](./DOCUMENTATION.md) | Feature methodologies + data sources | 7,200 words | 20 min |
| [CHANGELOG_ITEMS_0-6.md](./CHANGELOG_ITEMS_0-6.md) | Implementation history + details | 5,000 words | 15 min |
| [TESTING_GUIDE.md](./TESTING_GUIDE.md) | Integration testing procedures | 4,500 words | 30 min (+ testing) |
| [README.UPDATES.md](./README.UPDATES.md) | README update instructions | 3,000 words | 10 min |

**Total Documentation:** 19,700+ words  
**Total Reading Time:** ~55 minutes (without testing)

---

## Feature Implementation Summary

### Items Completed (7/7)

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

## Files Modified in Codebase

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

## Code Quality

### Validation Status
- ✅ **Syntax:** All files compile without errors
- ✅ **Imports:** No new external dependencies required
- ✅ **Type Hints:** Existing patterns followed
- ✅ **Backward Compatibility:** 6 non-breaking, 1 breaking change (Item 1)

### Test Coverage
- ✅ All 7 items have dedicated test procedures (see [TESTING_GUIDE.md](./TESTING_GUIDE.md))
- ⏳ Ready for integration testing with live Azure subscription

---

## Production Release Checklist

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

## Typical Workflow After Release

### End User
1. **Install/Update:** `pip install azure-tenant-insights==2.0`
2. **Read:** Quick overview in README.md
3. **Run:** `python invoke_ati.py --tenant-id <ID>`
4. **Review:** 3 output files (Excel + 2 HTML reports)
5. **Deep Dive:** Link to [DOCUMENTATION.md](./DOCUMENTATION.md) for feature details

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
**A:** Read [TESTING_GUIDE.md](./TESTING_GUIDE.md) for a quick overview of all 7 items, then run tests.

### Q: I broke my existing scripts with `--include-defender`
**A:** Item 1 is a breaking change. Replace `--include-*` with nothing (included by default) or use `--skip-*` to exclude. See [CHANGELOG_ITEMS_0-6.md → Item 1](./CHANGELOG_ITEMS_0-6.md#item-1-flag-paradigm-inversion-skip--vs-include-).

### Q: How is "CAF Landing Zone" different from general findings?
**A:** Observations are specifically aligned with Microsoft CAF pillars (Security, Cost, Ops, Reliability, Governance). Each references official CAF documentation. See [DOCUMENTATION.md → Item 6](./DOCUMENTATION.md#item-6-caf-landing-zone-observations).

### Q: Can I skip all optional data (Defender, Costs, Advisor)?
**A:** Yes: `python invoke_ati.py --skip-defender --skip-costs --skip-advisor`. You'll get core inventory + policy + health only.

### Q: Where can I learn more about a specific feature?
**A:** See [DOCUMENTATION.md](./DOCUMENTATION.md) for methodology, data sources, and limitations for each feature.

### Q: Is there a video or demo?
**A:** No, but [TESTING_GUIDE.md](./TESTING_GUIDE.md) provides step-by-step instructions that show exactly what to expect.

---

## Support & Contributions

### Reporting Issues
If you find issues with Items 0-6, reference:
- Specific item number (0-6)
- Feature name (from table above)
- Expected vs. actual behavior
- [TESTING_GUIDE.md](./TESTING_GUIDE.md) test case number (if applicable)

### Contributing
See [DOCUMENTATION.md](./DOCUMENTATION.md) for architecture and data flow to understand how to extend features.

---

## Version History

| Version | Date | Items | Status |
|---------|------|-------|--------|
| 1.0 | (Previous) | 0 | Stable |
| 2.0 | June 16, 2026 | 0-6 | ✅ Ready for Testing |

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

**Status:** ✅ Complete  
**Next Step:** Integration Testing (follow [TESTING_GUIDE.md](./TESTING_GUIDE.md))  
**Questions?** See FAQ section or reference [DOCUMENTATION.md](./DOCUMENTATION.md)

