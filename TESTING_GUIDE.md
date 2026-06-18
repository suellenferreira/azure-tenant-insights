# Integration Testing Guide — Items 0-6

**Date:** June 16, 2026  
**Purpose:** Step-by-step validation of all 7 enhancement items before production release  
**Estimated Duration:** 30-45 minutes per Azure subscription test  
**Status:** Ready to execute

---

## Quick Test Summary

| Item | Feature | Command | Expected Result | Time |
|------|---------|---------|-----------------|------|
| 0 | Modernization Signals | `python invoke_ati.py` | 🚀 Badge + 6 signals in Technical HTML | 2 min |
| 1 | Flag Paradigm | `python invoke_ati.py --skip-defender` | NO Defender section | 2 min |
| 2 | Metadata | `python invoke_ati.py` | Meta-bar shows tenant + subs | 1 min |
| 3 | Regions | `python invoke_ati.py` | Chart + table with top 12 regions | 2 min |
| 4 | Report Name | `python invoke_ati.py` | Interactive prompt appears | 1 min |
| 5 | Excel Styling | `python invoke_ati.py` | Dark theme Overview sheet | 2 min |
| 6 | CAF Observations | `python invoke_ati.py` | 14 observations with ✓/⚠ | 2 min |

---

## Pre-Test Setup

```bash
# 1. Authenticate with Azure
az login

# 2. Verify subscription access
az account list --output table

# 3. Note your tenant ID and subscription ID(s)
TENANT_ID="00000000-0000-0000-0000-000000000000"
SUBSCRIPTION_ID="11111111-1111-1111-1111-111111111111"

# 4. Navigate to project directory
cd azure-tenant-insights

# 5. Verify Python and dependencies
python --version  # Should be 3.9+
pip list | grep azure  # Should have azure-* packages
```

---

## Test 1: Item 0 — Modernization Signals

### Objective
Verify that Technical HTML report displays Modernization Signals with 6 signal categories.

### Steps

```bash
python invoke_ati.py --tenant-id $TENANT_ID --subscription-id $SUBSCRIPTION_ID
```

**When prompted for report name:** Press Enter (use default)

### Validation Checklist

- [ ] Scan completes successfully
- [ ] Output shows 3 files:
  - `ATI_Scan_*_Inventory.xlsx`
  - `ATI_Scan_*_Executive.html`
  - `ATI_Scan_*_Technical.html`

- [ ] Open `ATI_Scan_*_Technical.html` in browser
- [ ] Look for section: **"🚀 Modernization Signals"** in Infrastructure area
- [ ] Verify appears **below** "Technology & Platform Adoption" heading
- [ ] Check that 6 signal categories are listed (or fewer if no matches):
  - ✓ AI/ML Detected (count)
  - ✓ Containers Detected (count)
  - ✓ Serverless Detected (count)
  - ✓ Data Lakes Detected (count)
  - ✓ Streaming Detected (count)
  - ✓ APIs Detected (count)

### Expected Behavior

```
🚀 Modernization Signals (Infrastructure Readiness)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ 3 AI/ML resources detected (Azure OpenAI, Cognitive Services, Machine Learning)
✓ 2 Container resources detected (AKS, Container Instances)
✗ No Serverless resources detected
✓ 1 Data Lake resource detected (Data Factory)
✗ No Streaming resources detected
✓ 4 API resources detected (API Management, Service Bus)
```

### Pass Criteria

- ✅ Signal section appears in Technical report
- ✅ Shows detected signals with counts
- ✅ Shows "No X resources detected" for missing signals
- ✅ No JavaScript errors in browser console

---

## Test 2: Item 1 — Flag Paradigm (--skip-defender)

### Objective
Verify that Defender data is included by default and can be skipped with `--skip-defender` flag.

### Test 2a: Default Behavior (Defender Included)

```bash
python invoke_ati.py --tenant-id $TENANT_ID --subscription-id $SUBSCRIPTION_ID
```

**Validation:**
- [ ] Scan completes
- [ ] Open `ATI_Scan_*_Technical.html`
- [ ] Look for section: **"🔒 Security Assessments"** (or similar Defender section)
- [ ] Verify section shows Defender findings
- [ ] Check Excel file has **"SecurityAssessments"** sheet

### Test 2b: Skip Defender

```bash
python invoke_ati.py --tenant-id $TENANT_ID --subscription-id $SUBSCRIPTION_ID --skip-defender
```

**Validation:**
- [ ] Scan completes
- [ ] Open `ATI_Scan_*_Technical.html`
- [ ] Search for "Defender" — **NO matches found**
- [ ] Look for "Security Assessments" section — **NOT present**
- [ ] Check Excel file — **NO "SecurityAssessments" sheet**

### Test 2c: Skip Costs

```bash
python invoke_ati.py --tenant-id $TENANT_ID --subscription-id $SUBSCRIPTION_ID --skip-costs
```

**Validation:**
- [ ] Scan completes
- [ ] Check Excel file — **NO "Costs" sheet**
- [ ] Look for cost data in Technical HTML — **NOT present**

### Test 2d: Skip Both

```bash
python invoke_ati.py --tenant-id $TENANT_ID --subscription-id $SUBSCRIPTION_ID --skip-defender --skip-costs
```

**Validation:**
- [ ] Scan completes
- [ ] Excel file has **NO "SecurityAssessments" or "Costs" sheets**

### Pass Criteria

- ✅ Default behavior includes Defender and Costs
- ✅ `--skip-defender` excludes Defender data
- ✅ `--skip-costs` excludes Cost data
- ✅ Both flags can be combined

---

## Test 3: Item 2 — Tenant & Subscription Metadata

### Objective
Verify tenant name/ID and subscriptions list appear in meta-bar of both HTML reports.

### Steps

```bash
python invoke_ati.py --tenant-id $TENANT_ID --subscription-id $SUBSCRIPTION_ID
```

### Validation Checklist

**In Executive HTML Report:**
- [ ] Open `ATI_Scan_*_Executive.html`
- [ ] Look at **top-right meta-bar**
- [ ] Verify format: `Tenant: [Azure Tenant Name] ([tenant-id]) | Subscriptions: [sub1], [sub2], ...`
- [ ] Tenant ID matches: `$TENANT_ID`
- [ ] Subscription names display correctly

**In Technical HTML Report:**
- [ ] Open `ATI_Scan_*_Technical.html`
- [ ] Look at **top-right meta-bar**
- [ ] Verify **same format** as Executive (metadata synchronized)
- [ ] Verify **same tenant name and IDs**

**In Excel Report:**
- [ ] Open `ATI_Scan_*_Inventory.xlsx`
- [ ] Go to **"Overview" sheet**
- [ ] Check metadata row: "Tenant ID:", "Subscriptions:"
- [ ] Verify IDs match reports

### Expected Format

```
Tenant: Contoso Corp (12345678-abcd-1234-abcd-123456789012) | 
Subscriptions: Production (prod-123abc), Staging (staging-456def), Dev (dev-789ghi)
```

### Pass Criteria

- ✅ Meta-bar visible in both HTML reports
- ✅ Tenant name displays correctly
- ✅ Tenant ID matches command-line input
- ✅ Subscriptions list is complete and accurate
- ✅ Metadata synchronized between Executive and Technical reports

---

## Test 4: Item 3 — Active Regions Distribution

### Objective
Verify regional aggregation appears in both Executive chart and Technical table.

### Steps

```bash
python invoke_ati.py --tenant-id $TENANT_ID --subscription-id $SUBSCRIPTION_ID
```

### Validation Checklist

**In Executive HTML Report:**
- [ ] Open `ATI_Scan_*_Executive.html`
- [ ] Scroll to middle section
- [ ] Find **"🌍 Active Regions Distribution"** chart
- [ ] Verify **horizontal bar chart** appears
- [ ] Chart shows **region names on Y-axis** (e.g., "East US", "West Europe")
- [ ] Chart shows **resource counts on X-axis**
- [ ] Bars are **colored green** (#70AD47)
- [ ] **Top 12 regions** displayed (or fewer if subscription has fewer regions)
- [ ] Order by count (descending)

**In Technical HTML Report:**
- [ ] Open `ATI_Scan_*_Technical.html`
- [ ] Look in **"Infrastructure" section sidebar** (left nav)
- [ ] Click on **"🌍 Regional Distribution"** link
- [ ] Verify **table appears** with columns:
  - Region name
  - Count (number of resources)
  - Percentage (e.g., 18.5%)
- [ ] Verify **percentages sum to ~100%** (allowing small rounding error)
- [ ] Regions sorted by count (descending)

### Expected Data Sample

```
Region              | Count | Percentage
────────────────────┼───────┼───────────
East US            |  45   | 18.5%
West Europe        |  38   | 15.6%
Central US         |  32   | 13.1%
Southeast Asia     |  28   | 11.5%
...
```

### Pass Criteria

- ✅ Executive report shows chart with top regions
- ✅ Technical report shows table with regions, counts, percentages
- ✅ Percentages are mathematically correct
- ✅ Both reports show same top regions (same data source)
- ✅ "Global" locations excluded (CDN, DNS, etc.)

---

## Test 5: Item 4 — Interactive Report Naming

### Objective
Verify interactive prompt for custom report name works correctly.

### Test 5a: Custom Name

```bash
python invoke_ati.py --tenant-id $TENANT_ID --subscription-id $SUBSCRIPTION_ID
```

**When prompted:**
```
[Optional] Custom report name (or press Enter for default):
[DEFAULT] Format: ATI_Scan_YYYY-MM-DD_HH-MM-SS
> 
```

**Type:** `Production_Audit_Q2`

**Validation:**
- [ ] Scan completes
- [ ] Output files are named:
  - `ATI_Production_Audit_Q2_2026-06-16_14-30-45_Inventory.xlsx`
  - `ATI_Production_Audit_Q2_2026-06-16_14-30-45_Executive.html`
  - `ATI_Production_Audit_Q2_2026-06-16_14-30-45_Technical.html`

### Test 5b: Default Name (Enter Pressed)

```bash
python invoke_ati.py --tenant-id $TENANT_ID --subscription-id $SUBSCRIPTION_ID
```

**When prompted:** Press `Enter` (don't type anything)

**Validation:**
- [ ] Scan completes
- [ ] Output files are named:
  - `ATI_Scan_2026-06-16_14-30-45_Inventory.xlsx`
  - `ATI_Scan_2026-06-16_14-30-45_Executive.html`
  - `ATI_Scan_2026-06-16_14-30-45_Technical.html`

### Pass Criteria

- ✅ Prompt appears after "Scanning subscriptions..."
- ✅ Custom name incorporated into filenames
- ✅ Default format used when Enter pressed
- ✅ Timestamp always appended (not duplicate)
- ✅ All 3 output files use same prefix

---

## Test 6: Item 5 — Excel Overview Sheet Styling

### Objective
Verify Excel Overview sheet has professional dark-theme styling.

### Steps

```bash
python invoke_ati.py --tenant-id $TENANT_ID --subscription-id $SUBSCRIPTION_ID
```

### Validation Checklist

**Open Excel file:** `ATI_Scan_*_Inventory.xlsx`

**Select "Overview" sheet:**
- [ ] Title row (A1) has **dark blue background** (#1F4E79)
- [ ] Title text is **white, bold, large font** (18px)
- [ ] Title height is **42px** (generous padding)

**Metadata section (row 2):**
- [ ] Labels have **light gray background** (#E7E6E6)
- [ ] Label text is **bold, 10px**
- [ ] Data cells have **very light gray background** (#F5F5F5)

**KPI cards (rows 5-14):**
- [ ] Each metric value has **colored background**:
  - Green (#70AD47) for healthy metrics
  - Yellow (#FFFF99) for medium priority
  - Orange (#FFC000) for high priority
  - Red (#C00000) for critical alerts
- [ ] Values are **centered, bold**
- [ ] Values have **thin gray borders** (#D3D3D3)
- [ ] Row heights are **22px** (good spacing)

**Section headers (row 4):**
- [ ] "KEY METRICS" header has **navy blue background** (#1F4E79)
- [ ] Text is **white, bold, 11px**
- [ ] Header height is **24px**

**Column widths:**
- [ ] A: ~28px (labels fit)
- [ ] B: ~18px (values centered)
- [ ] D: ~32px (resource types fit)
- [ ] E: ~14px (counts centered)

**Print Preview:**
- [ ] Go to **File → Print Preview**
- [ ] Verify page margins are appropriate (0.5" left/right, 0.75" top/bottom)
- [ ] Verify content fits on **1 page** (width-wise)
- [ ] Verify styling renders correctly

### Expected Visual

```
┌─────────────────────────────────────────────────────────┐
│ Azure Tenant Insights — Environment Overview           │  ← Navy blue header
├─────────────────────────────────────────────────────────┤
│ Scan Date: 2026-06-16 | Tenant ID: 12345... | Cloud...  │  ← Gray metadata
├─────────────────────────────────────────────────────────┤
│ KEY METRICS          │ TOP RESOURCE TYPES │ ADVISOR    │  ← Navy headers
├──────────────────┬──────┬──────────────────┬────┬────────┤
│ Total Resources  │ 245  │ Storage Accounts │ 23 │ Security│  ← Color-coded values
│ Subscriptions    │  3   │ Virtual Machines │ 18 │ Ops    │
│ ...              │      │                  │    │ ...    │
└────────────────────────────────────────────────────────────┘
```

### Pass Criteria

- ✅ Dark theme styling renders correctly
- ✅ All color codes match specification
- ✅ Text alignment is centered and readable
- ✅ Print Preview shows proper page layout
- ✅ No overlapping text or cells

---

## Test 7: Item 6 — CAF Landing Zone Observations

### Objective
Verify Technical report displays 14+ CAF-aligned Landing Zone observations with actionable guidance.

### Steps

```bash
python invoke_ati.py --tenant-id $TENANT_ID --subscription-id $SUBSCRIPTION_ID
```

### Validation Checklist

**In Technical HTML Report:**
- [ ] Open `ATI_Scan_*_Technical.html`
- [ ] Look for **"🏗 Landing Zone"** section (use sidebar navigation)
- [ ] Verify **multiple observations** appear (should be 10+)

**Check observation format:**
- [ ] Each observation has indicator: **✓** (green) or **⚠** (orange)
- [ ] Each observation includes descriptive message
- [ ] Each observation mentions **CAF pillar** in parentheses, e.g.:
  - `(CAF security pillar)`
  - `(CAF cost management)`
  - `(CAF operational excellence)`
  - `(CAF reliability pillar)`
  - `(CAF governance)`

**Verify 5 CAF Pillar Coverage:**

1. **Security Pillar** — Look for observations mentioning:
   - [ ] Entra ID / identity configuration
   - [ ] Network segmentation / VNets / NSGs
   - [ ] Private endpoints / DNS zones
   - [ ] Key Vault
   - [ ] Defender findings

2. **Cost Management Pillar** — Look for:
   - [ ] Tag coverage analysis
   - [ ] Chargeback model
   - [ ] Cost allocation enforcement

3. **Operational Excellence Pillar** — Look for:
   - [ ] Log Analytics
   - [ ] Application Insights
   - [ ] Deprecated resources migration

4. **Reliability Pillar** — Look for:
   - [ ] Recovery Services / Backup
   - [ ] Resource health

5. **Governance Pillar** — Look for:
   - [ ] Management Groups hierarchy
   - [ ] Policy compliance

**Sample Observations:**

```
✓ Management Group hierarchy detected (5 groups). Enterprise governance 
  structure is in place. (CAF governance)

⚠ Low tag coverage (45%). Without consistent tags, cost allocation is impaired. 
  Enforce via Azure Policy (CAF cost management).

✓ 3 Log Analytics Workspace(s) detected. Validate centralized logging aligns 
  with your operational model (CAF operational excellence).

⚠ No Recovery Services Vault detected. Implement backup strategy per CAF 
  reliability design principles.
```

**Check for actionable guidance:**
- [ ] Each ⚠ observation includes **remediation step**
- [ ] Remediation references **specific Azure service**
- [ ] Remediation references **CAF guidance**

### Expected Count

- ✅ Should show **14+ observations** across all CAF pillars
- ✅ Mix of ✓ (green) and ⚠ (orange) findings
- ✅ At least 2-3 observations per pillar

### Pass Criteria

- ✅ Landing Zone section appears with 🏗 icon
- ✅ Shows 14+ CAF-aligned observations
- ✅ Each observation has ✓ or ⚠ indicator
- ✅ Each observation mentions CAF pillar
- ✅ ⚠ observations include actionable remediation
- ✅ All 5 CAF pillars represented

---

## Integration Test Conclusion Checklist

After all 7 tests pass:

- [ ] **Item 0** — Modernization Signals display correctly
- [ ] **Item 1** — Flag paradigm works (default + skip-* flags)
- [ ] **Item 2** — Tenant/subscription metadata shows in both reports
- [ ] **Item 3** — Regional distribution chart + table appear
- [ ] **Item 4** — Interactive naming prompt works
- [ ] **Item 5** — Excel Overview sheet has dark theme styling
- [ ] **Item 6** — CAF Landing Zone observations with 5 pillars

### Sign-Off

If all tests pass:
- [ ] Mark as "Ready for Production"
- [ ] Tag release as v2.0
- [ ] Update version in `pyproject.toml` and `invoke_ati.py`
- [ ] Create GitHub release with CHANGELOG_ITEMS_0-6.md notes
- [ ] Notify stakeholders

---

## Troubleshooting During Testing

### Issue: "Scan takes 20+ minutes"
**Solution:** Your subscription has 5,000+ resources. This is normal. Reduce scope with `--resource-group` or `--subscription-id` for faster testing.

### Issue: "No Modernization Signals detected"
**Solution:** Your subscription may not have resources matching the 6 signal patterns. This is correct behavior. Verify by checking resource types in Azure portal.

### Issue: "Regional Distribution chart not displaying"
**Solution:** Charts require internet (CDN for Chart.js). Verify browser can reach `cdn.jsdelivr.net`. Tables will still show without internet.

### Issue: "Excel styling looks different in LibreOffice"
**Solution:** Some style features (e.g., PatternFill) render differently. Use Excel 2016+ for full fidelity. Core data is still readable in LibreOffice.

### Issue: "CAF observations missing some checks"
**Solution:** Observations are pattern-based. If you don't have certain resource types, some checks will show "No X detected". This is correct.

---

**Test Duration:** 30-45 minutes  
**Resources Required:** Active Azure subscription with Reader access  
**Expected Pass Rate:** 100% (all 7 items)  
**Next Step After Testing:** Production release
