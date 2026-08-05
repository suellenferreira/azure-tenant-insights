#!/usr/bin/env python3
"""
Azure Tenant Insights (ATI) v1.0.0
===================================
Scans an Azure tenant and generates:
  - Structured Excel inventory (multi-sheet, per resource type)
  - Executive HTML report  (C-Level / stakeholder view)
  - Technical HTML report  (engineering / architecture / security)

All data is collected via official Azure APIs:
  - Azure Resource Graph (primary)
  - Azure Advisor, Policy Insights, Resource Health (via Resource Graph tables)
  - Azure Cost Management REST API (default, can be skipped)
  - Microsoft Defender for Cloud (default, can be skipped, requires Security Reader RBAC)

Usage:
  python invoke_ati.py                                      # all subscriptions (default)
  python invoke_ati.py --tenant-id <GUID>                   # all subs in specific tenant
  python invoke_ati.py --all-subscriptions -y               # all subs, skip confirmation
  python invoke_ati.py --subscription-id <ID1> <ID2>        # targeted scan
  python invoke_ati.py --max-subscriptions 10               # cap to first 10 subs
  python invoke_ati.py --tenant-id <GUID> --management-group <MG-ID>
  python invoke_ati.py --tenant-id <GUID> --skip-costs --skip-defender

RBAC requirements (minimum):
  - Reader           -> all core features
  - Security Reader  -> Defender for Cloud (enabled by default, use --skip-defender to exclude)
  - Cost Mgmt Reader -> Cost data (enabled by default, use --skip-costs to exclude)
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


BANNER = """
╔══════════════════════════════════════════════════════════╗
║          Azure Tenant Insights (ATI) v1.0.0             ║
║   Powered by Azure Resource Graph + Official Azure APIs  ║
╚══════════════════════════════════════════════════════════╝
"""


class _CollectorWarnings(logging.Handler):
    """Captures WARNING/ERROR from collector modules for embedding in reports."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self._records: list = []

    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
        if record.name.startswith("collectors."):
            self._records.append({
                "collector": record.name.split(".", 1)[-1],
                "level": record.levelname,
                "message": record.getMessage(),
            })

    @property
    def records(self) -> list:
        return self._records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="invoke_ati",
        description="Azure Tenant Insights — Scan your Azure tenant and generate reports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan ALL subscriptions in the tenant (default — no flags needed)
  python invoke_ati.py
  python invoke_ati.py --tenant-id <GUID>
  python invoke_ati.py --tenant-id <GUID> --all-subscriptions -y

  # Scan specific subscriptions only
  python invoke_ati.py --subscription-id <ID1> <ID2>

  # Cap to first 10 subscriptions (useful for large tenants)
  python invoke_ati.py --max-subscriptions 10

  # Skip optional collectors (faster for large tenants)
  python invoke_ati.py --skip-costs --skip-defender

  # Full custom run
  python invoke_ati.py --tenant-id <GUID> --management-group <MG-ID>
  python invoke_ati.py --tenant-id <GUID> --skip-tags --output-dir ./reports

RBAC Requirements:
  Reader             required for all core features
  Security Reader    required for Defender (enabled by default, use --skip-defender to exclude)
  Cost Mgmt Reader   required for Cost data (enabled by default, use --skip-costs to exclude)
        """,
    )

    # ── Authentication ────────────────────────────────────────────
    auth = parser.add_argument_group("Authentication")
    auth.add_argument("--tenant-id", metavar="GUID",
                      help="Azure Tenant ID (optional — auto-detected from CLI login)")
    auth.add_argument("--client-id", metavar="ID",
                      help="Service Principal App ID")
    auth.add_argument("--client-secret", metavar="SECRET",
                      help="Service Principal Client Secret")

    # ── Scope ────────────────────────────────────────────────────
    scope = parser.add_argument_group("Scope")
    scope.add_argument("--all-subscriptions", action="store_true", default=True,
                       help="Scan ALL accessible subscriptions in the tenant (default behaviour)")
    scope.add_argument("--subscription-id", nargs="+", metavar="ID",
                       help="Limit scan to specific subscription ID(s); disables --all-subscriptions")
    scope.add_argument("--management-group", metavar="ID",
                       help="Scan all subscriptions under a Management Group")
    scope.add_argument("--resource-group", nargs="+", metavar="NAME",
                       help="Limit scan to specific resource group(s)")
    scope.add_argument("--tag-key", metavar="KEY",
                       help="Filter resources by tag key")
    scope.add_argument("--tag-value", metavar="VALUE",
                       help="Filter resources by tag value")
    scope.add_argument("--max-subscriptions", type=int, default=0, metavar="N",
                       help="Cap the number of subscriptions scanned (0 = no limit)")
    scope.add_argument("--yes", "-y", action="store_true",
                       help="Skip confirmation prompt when scanning many subscriptions")

    # ── Optional Data Sources ────────────────────────────────────
    optional = parser.add_argument_group("Optional Data Sources")
    optional.add_argument("--skip-defender", action="store_true",
                          help="Skip Defender for Cloud assessments (included by default)")
    optional.add_argument("--skip-costs", action="store_true",
                          help="Skip Cost Management data (included by default)")
    optional.add_argument("--skip-tags", action="store_true",
                          help="Skip resource tags in Excel inventory (included by default)")
    optional.add_argument("--skip-policy", action="store_true",
                          help="Skip Azure Policy compliance collection")
    optional.add_argument("--skip-advisor", action="store_true",
                          help="Skip Azure Advisor recommendations")
    optional.add_argument("--skip-org", action="store_true",
                          help="Skip Management Group hierarchy collection (Organization diagram)")

    # ── Output ───────────────────────────────────────────────────
    output = parser.add_argument_group("Output")
    output.add_argument("--output-dir", metavar="PATH", default="./AzureTenantInsights",
                        help="Output directory (default: ./AzureTenantInsights)")
    output.add_argument("--report-name", metavar="NAME",
                        help="Custom prefix for report file names")
    output.add_argument("--no-excel", action="store_true",
                        help="Skip Excel inventory generation")
    output.add_argument("--no-html", action="store_true",
                        help="Skip HTML report generation")
    output.add_argument("--no-diagram", action="store_true",
                        help="Skip draw.io diagram generation")
    output.add_argument("--network-detail-per-subscription", action="store_true",
                        help="Network Detail: one page per subscription instead of a "
                             "single page (useful for very large tenants)")
    output.add_argument("--no-security-overlay", action="store_true",
                        help="Disable the diagram Security Posture overlay (badges + page)")

    # ── Performance ──────────────────────────────────────────────
    perf = parser.add_argument_group("Performance")
    perf.add_argument("--throttle-delay", type=float, default=1.0, metavar="SECONDS",
                      help="Delay between Resource Graph queries to avoid throttling (default: 1.0)")
    perf.add_argument("--cloud", default="AzurePublicCloud",
                      choices=["AzurePublicCloud", "AzureUSGovernment",
                               "AzureChinaCloud", "AzureGermanCloud"],
                      help="Azure cloud environment (default: AzurePublicCloud)")

    # ── Debug ────────────────────────────────────────────────────
    parser.add_argument("--debug", action="store_true",
                        help="Enable verbose debug logging")
    parser.add_argument("--version", action="version", version="Azure Tenant Insights v1.0.0")

    return parser.parse_args()


def setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main() -> None:
    args = parse_args()
    setup_logging(args.debug)
    logger = logging.getLogger("ati.main")

    print(BANNER)

    start_time = time.time()
    scan_timestamp = datetime.now(timezone.utc)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Report naming (Item 4: Optional custom report name) ──
    if args.report_name:
        base_report_name = args.report_name
    elif args.yes or not sys.stdin.isatty():
        # Non-interactive (CI / --yes / no TTY): use the default without prompting.
        base_report_name = "ATI_Report"
    else:
        print("\n📋 Custom Report Name (optional)")
        print("   Press Enter to use default 'ATI_Report', or type a custom name:")
        try:
            custom_name = input("   > ").strip()
        except EOFError:
            custom_name = ""
        base_report_name = custom_name if custom_name else "ATI_Report"
        if custom_name:
            print(f"   ✓ Report name: {base_report_name}\n")

    ts = scan_timestamp.strftime("%Y%m%d_%H%M%S")
    report_prefix = f"{base_report_name}_{ts}"

    try:
        # ── 1. Authentication ─────────────────────────────────────
        logger.info("Authenticating to Azure...")
        from collectors.auth import get_credential
        credential = get_credential(
            tenant_id=args.tenant_id,
            client_id=args.client_id,
            client_secret=args.client_secret,
            cloud=args.cloud,
        )

        # ── 2. Subscription Discovery ────────────────────────────
        # When --subscription-id is provided, scope to those only (--all-subscriptions ignored).
        # Otherwise, default to scanning ALL accessible subscriptions in the tenant.
        _scope_mode = "targeted" if args.subscription_id else "all-subscriptions"
        logger.info(
            "Discovering accessible subscriptions "
            f"(mode: {_scope_mode})"
        )
        from collectors.subscriptions import get_subscriptions
        subscriptions = get_subscriptions(
            credential=credential,
            subscription_ids=args.subscription_id,
            management_group=args.management_group,
            cloud=args.cloud,
        )

        if not subscriptions:
            logger.error(
                "No accessible subscriptions found. "
                "Verify your account has at least 'Reader' on the subscriptions."
            )
            sys.exit(1)

        # A requested tenant is an explicit safety boundary. Do not continue
        # with subscriptions returned by a different cached CLI/VS Code account.
        if args.tenant_id:
            requested_tenant = args.tenant_id.lower()
            mismatched = [
                sub for sub in subscriptions
                if sub.get("tenantId") and sub["tenantId"].lower() != requested_tenant
            ]
            if mismatched:
                logger.error(
                    "Discovered subscription(s) do not belong to the requested "
                    "--tenant-id. Verify the active Azure credential/account."
                )
                sys.exit(1)

        # Apply --max-subscriptions cap (0 = no cap)
        if args.max_subscriptions and len(subscriptions) > args.max_subscriptions:
            logger.warning(
                f"--max-subscriptions {args.max_subscriptions}: capping from "
                f"{len(subscriptions)} to {args.max_subscriptions} subscriptions."
            )
            subscriptions = subscriptions[: args.max_subscriptions]

        subscription_ids = [s["subscriptionId"] for s in subscriptions]
        n_subs = len(subscription_ids)
        logger.info(f"Found {n_subs} subscription(s) to scan")

        # All-subscriptions scans can produce sensitive, tenant-wide inventory.
        # Require an explicit interactive confirmation; --yes is the automation bypass.
        if _scope_mode == "all-subscriptions" and n_subs and not args.yes and sys.stdin.isatty():
            print(f"""
⚠️  ALL-SUBSCRIPTIONS MODE
   Found {n_subs} accessible subscriptions in this tenant.
   Estimated scan time: ~{max(1, n_subs // 5)} – {max(2, n_subs // 2)} minutes
   (depending on resource count and throttle settings)

   Subscriptions to be scanned:""")
            for _s in subscriptions[:10]:
                print(f"     • {_s.get('displayName', 'Unknown'):50s}  [{_s.get('subscriptionId','')}]")
            if n_subs > 10:
                print(f"     … and {n_subs - 10} more")
            print()
            _confirm = input("   Proceed? [Y/n] > ").strip().lower()
            if _confirm and _confirm not in ("y", "yes", ""):
                logger.info("Scan aborted by user.")
                sys.exit(0)
            print()

        # Resolve actual tenant GUID from subscription data if not explicitly provided
        actual_tenant_id = (
            args.tenant_id
            or next((s.get("tenantId") for s in subscriptions if s.get("tenantId")), None)
            or "N/A"
        )

        # Resolve tenant display name via Tenants REST API (api-version=2022-12-01).
        # The azure-mgmt-subscription SDK uses an older API version that does not
        # populate displayName on TenantIdDescription objects, so we call REST directly.
        # Reference: https://learn.microsoft.com/en-us/rest/api/resources/tenants/list
        tenant_name = "N/A"
        try:
            import requests as _requests
            _token = credential.get_token("https://management.azure.com/.default")
            _headers = {"Authorization": f"Bearer {_token.token}"}
            _resp = _requests.get(
                "https://management.azure.com/tenants?api-version=2022-12-01",
                headers=_headers,
                timeout=15,
            )
            _resp.raise_for_status()
            _tenants_raw = _resp.json().get("value", [])
            if _tenants_raw:
                _match = next(
                    (t for t in _tenants_raw if t.get("tenantId") == actual_tenant_id),
                    None,
                )
                if args.tenant_id and _match is None:
                    logger.error(
                        "The authenticated credential cannot access the requested "
                        "--tenant-id. Verify the active Azure account or Service Principal."
                    )
                    sys.exit(1)
                _match = _match or _tenants_raw[0]
                if actual_tenant_id in ("N/A", None):
                    actual_tenant_id = _match.get("tenantId") or "N/A"
                tenant_name = _match.get("displayName") or "N/A"
        except Exception as _te:
            logger.warning(f"Could not resolve tenant display name: {_te}")

        # Install lightweight warning capture for collector modules
        _warn_handler = _CollectorWarnings()
        logging.getLogger().addHandler(_warn_handler)

        # ── 3. Resource Collection ───────────────────────────────
        logger.info("Collecting resources via Azure Resource Graph...")
        from collectors.resources import collect_resources
        resources_by_type = collect_resources(
            credential=credential,
            subscription_ids=subscription_ids,
            resource_groups=args.resource_group,
            tag_key=args.tag_key,
            tag_value=args.tag_value,
            throttle_delay=args.throttle_delay,
            cloud=args.cloud,
        )
        total_resources = sum(len(v) for v in resources_by_type.values())
        logger.info(
            f"Collected {total_resources} resources across {len(resources_by_type)} types"
        )

        # ── 4. Advisor ───────────────────────────────────────────
        advisor_data = []
        if not args.skip_advisor:
            logger.info("Collecting Azure Advisor recommendations...")
            from collectors.advisor import collect_advisor
            advisor_data = collect_advisor(
                credential=credential,
                subscription_ids=subscription_ids,
                throttle_delay=args.throttle_delay,
                cloud=args.cloud,
            )
            logger.info(f"Advisor: {len(advisor_data)} recommendations")

        # ── 5. Policy ────────────────────────────────────────────
        policy_data = []
        if not args.skip_policy:
            logger.info("Collecting Azure Policy compliance states...")
            from collectors.policy import collect_policy
            policy_data = collect_policy(
                credential=credential,
                subscription_ids=subscription_ids,
                throttle_delay=args.throttle_delay,
                cloud=args.cloud,
            )
            logger.info(f"Policy: {len(policy_data)} non-compliant records")

        # ── 6. Resource Health ───────────────────────────────────
        logger.info("Collecting Resource Health events...")
        from collectors.health import collect_health
        health_data = collect_health(
            credential=credential,
            subscription_ids=subscription_ids,
            throttle_delay=args.throttle_delay,
            cloud=args.cloud,
        )
        logger.info(f"Health: {len(health_data)} non-healthy resources")

        # ── 7. Defender for Cloud (default, can be skipped) ─────────────────────
        defender_data = []
        defender_posture = []
        if not args.skip_defender:
            logger.info("Collecting Defender for Cloud assessments...")
            from collectors.defender import collect_defender
            defender_data = collect_defender(
                credential=credential,
                subscription_ids=subscription_ids,
                throttle_delay=args.throttle_delay,
                cloud=args.cloud,
            )
            logger.info(f"Defender: {len(defender_data)} assessments")

            # ── 7b. Defender for Cloud — plan posture (Reader RBAC) ─────────────
            # VMs/VMSS/Arc are analysed individually (per-resource); other
            # workloads are subscription-level + assessment-based (see step 7).
            logger.info("Collecting Defender for Cloud plan posture...")
            from collectors.defender_posture import collect_defender_posture
            defender_posture = collect_defender_posture(
                credential=credential,
                subscription_ids=subscription_ids,
                throttle_delay=args.throttle_delay,
                cloud=args.cloud,
            )
            logger.info(f"Defender posture: {len(defender_posture)} plan records")

            # ── 7c. Defender pricing — warm the live price cache ────────────────
            # Fetch current Defender unit prices from the public Azure Retail
            # Prices API now, while the warning handler is still attached, so a
            # failed/offline fetch is captured in collection_warnings and shows
            # up in the terminal summary AND the report's data-collection notes.
            # The report writers reuse this cached result (no second network call).
            if defender_posture:
                logger.info("Fetching live Defender pricing (Azure Retail Prices API)...")
                from collectors.defender_pricing import get_effective_prices
                _live_prices = get_effective_prices(use_live=True)
                if _live_prices:
                    logger.info(
                        f"Live Defender pricing: {len(_live_prices)} plan(s) loaded."
                    )

        # ── 8. Cost Management (default, can be skipped) ────────────────────────
        costs_data = []
        if not args.skip_costs:
            logger.info("Collecting Cost Management data (current month)...")
            from collectors.costs import collect_costs
            costs_data = collect_costs(
                credential=credential,
                subscription_ids=subscription_ids,
                cloud=args.cloud,
            )
            logger.info(f"Costs: {len(costs_data)} cost records")

        # ── 8b. Management Group hierarchy (for the Organization diagram) ───────
        management_groups = None
        if not args.skip_org and not args.no_diagram:
            logger.info("Collecting Management Group hierarchy...")
            from collectors.mgmt_groups import get_management_group_tree
            management_groups = get_management_group_tree(
                credential=credential,
                subscription_ids=subscription_ids,
                throttle_delay=args.throttle_delay,
                tenant_name=tenant_name,
            )

        # ── 9. Processing ─────────────────────────────────────────
        # Uninstall warning capture before processing phase
        logging.getLogger().removeHandler(_warn_handler)
        collection_warnings = _warn_handler.records
        logger.info("Processing and enriching data...")
        from processors.deprecation import detect_deprecated
        from processors.misconfig_detector import detect_misconfigurations
        from processors.summary import compute_summary
        from processors.waf_mapper import map_waf_pillars

        deprecated_matches = detect_deprecated(resources_by_type)
        misconfig_findings = detect_misconfigurations(resources_by_type)
        waf_findings = map_waf_pillars(advisor_data)
        summary_metrics = compute_summary(
            subscriptions=subscriptions,
            resources_by_type=resources_by_type,
            advisor_data=advisor_data,
            policy_data=policy_data,
            health_data=health_data,
            deprecated_matches=deprecated_matches,
            misconfig_findings=misconfig_findings,
            defender_data=defender_data,
        )

        # Assemble the full scan data payload
        scan_data = {
            "metadata": {
                "scan_timestamp": scan_timestamp.isoformat() + "Z",
                "tenant_id": actual_tenant_id,
                "tenant_name": tenant_name,
                "subscriptions": subscriptions,
                "subscription_count": len(subscriptions),
                "scan_scope": (
                    "management-group" if args.management_group
                    else "subscription" if args.subscription_id
                    else "tenant"
                ),
                "total_resources": total_resources,
                "cloud": args.cloud,
                "report_name": report_prefix,
            },
            "collection_warnings": collection_warnings,
            "subscriptions": subscriptions,
            "resources_by_type": resources_by_type,
            "management_groups": management_groups,
            "advisor_data": advisor_data,
            "policy_data": policy_data,
            "health_data": health_data,
            "defender_data": defender_data,
            "defender_posture": defender_posture,
            "costs_data": costs_data,
            "deprecated_matches": deprecated_matches,
            "misconfig_findings": misconfig_findings,
            "waf_findings": waf_findings,
            "summary_metrics": summary_metrics,
            "options": {
                "include_tags": not args.skip_tags,
                "include_defender": not args.skip_defender,
                "include_costs": not args.skip_costs,
            },
        }

        # ── 10. Output Generation ─────────────────────────────────
        output_files = []

        if not args.no_excel:
            logger.info("Generating Excel inventory...")
            from writers.excel_writer import write_excel
            excel_path = output_dir / f"{report_prefix}_Inventory.xlsx"
            write_excel(scan_data, str(excel_path))
            output_files.append(str(excel_path))

        if not args.no_html:
            logger.info("Generating Executive HTML report...")
            from writers.html_executive import write_executive_report
            exec_path = output_dir / f"{report_prefix}_Executive.html"
            write_executive_report(scan_data, str(exec_path))
            output_files.append(str(exec_path))

            logger.info("Generating Technical HTML report...")
            from writers.html_technical import write_technical_report
            tech_path = output_dir / f"{report_prefix}_Technical.html"
            write_technical_report(scan_data, str(tech_path))
            output_files.append(str(tech_path))

        if not args.no_diagram:
            logger.info("Generating draw.io diagram...")
            from writers.drawio_writer import write_drawio
            diagram_path = output_dir / f"{report_prefix}_Diagram.drawio"
            write_drawio(scan_data, str(diagram_path),
                         network_detail_per_subscription=args.network_detail_per_subscription,
                         security_overlay=not args.no_security_overlay)
            output_files.append(str(diagram_path))

        # ── Summary ───────────────────────────────────────────────
        elapsed = time.time() - start_time
        print(f"""
╔══════════════════════════════════════════════════════════╗
║                    SCAN COMPLETE                         ║
╠══════════════════════════════════════════════════════════╣
║  Duration       : {elapsed:.1f}s
║  Subscriptions  : {len(subscriptions)}
║  Resources      : {total_resources:,}
║  Resource Types : {len(resources_by_type)}
║  Advisor Recs   : {len(advisor_data)}
║  Policy Records : {len(policy_data)}
║  Deprecated     : {len(deprecated_matches)}
║  Misconfigs     : {len(misconfig_findings)}
║  Health Issues  : {len(health_data)}
╠══════════════════════════════════════════════════════════╣
║  Output Files:
{''.join(f"║    → {f}" + chr(10) for f in output_files)}╚══════════════════════════════════════════════════════════╝
""")

        # ── Collection warnings/errors summary (parallel to SCAN COMPLETE) ──
        if collection_warnings:
            from collections import Counter as _Counter
            by_collector = _Counter(w.get("collector", "unknown") for w in collection_warnings)
            errors = [w for w in collection_warnings if w.get("level") == "ERROR"]
            warns = [w for w in collection_warnings if w.get("level") != "ERROR"]
            print(f"""
╔══════════════════════════════════════════════════════════╗
║              COLLECTION WARNINGS / ERRORS                ║
╠══════════════════════════════════════════════════════════╣
║  Total          : {len(collection_warnings)}  (Errors: {len(errors)}, Warnings: {len(warns)})
║  By collector   : {', '.join(f'{k}={v}' for k, v in sorted(by_collector.items()))}
╠══════════════════════════════════════════════════════════╣""")
            for w in collection_warnings[:30]:
                _lvl = "ERR " if w.get("level") == "ERROR" else "WARN"
                _msg = str(w.get("message", ""))[:150]
                print(f"║  [{_lvl}] {w.get('collector','')}: {_msg}")
            if len(collection_warnings) > 30:
                print(f"║  ... and {len(collection_warnings) - 30} more (see report 'Data collection notes')")
            print("╚══════════════════════════════════════════════════════════╝")

    except KeyboardInterrupt:
        logger.warning("Scan interrupted by user.")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
