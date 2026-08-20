"""Generate an actionable, review-only report for ATI's local catalogs."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
DECISION_OPTIONS = ("confirmed", "update_required", "false_alarm", "source_unavailable")

REVIEW_GUIDANCE = {
    "deprecated_types": (
        "Confirm the retirement date, current status, replacement service, announcement URL, "
        "and migration path against Microsoft sources."
    ),
    "misconfiguration_rules": (
        "Confirm the condition, expected value, severity, evidence wording, and Microsoft "
        "documentation URL; keep heuristic findings distinct from Policy and Defender results."
    ),
    "drawio_stencils": (
        "Confirm each stencil path exists in the supported diagrams.net library and that an "
        "appropriate generic fallback remains available."
    ),
    "modernization_signals": (
        "Confirm signal criteria, confidence language, opportunity interpretation, and source links."
    ),
    "resource_classification": (
        "Confirm resource-type mappings, precedence, Service Model, Business Pillar, and technical category."
    ),
    "resource_enrichment": (
        "Confirm projected Resource Graph/ARM property paths and the rules that consume promoted fields."
    ),
    "network_placement": (
        "Confirm resource relationship properties, placement behavior, and fallback topology handling."
    ),
    "security_overlay": (
        "Confirm severity colors, finding mappings, Zero Trust references, and visual fallback behavior."
    ),
}


def _walk_urls(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_urls(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_urls(item)
    elif isinstance(value, str) and value.startswith(("https://", "http://")):
        yield value


def _load(path: Path) -> Any:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _url_status(url: str) -> str:
    try:
        response = requests.head(url, allow_redirects=True, timeout=15)
        if response.status_code in {403, 405}:
            response = requests.get(url, allow_redirects=True, timeout=15, stream=True)
        return str(response.status_code)
    except requests.RequestException as error:
        return f"ERROR: {type(error).__name__}"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finding(catalog: Dict[str, Any], issue: str, evidence: str, priority: str) -> Dict[str, str]:
    catalog_id = catalog.get("id", "unknown")
    return {
        "catalog_id": catalog_id,
        "catalog": catalog.get("display_name", catalog_id),
        "file": catalog.get("file", ""),
        "issue": issue,
        "evidence": evidence,
        "priority": priority,
        "source": catalog.get("source", ""),
        "recommended_action": REVIEW_GUIDANCE.get(
            catalog_id,
            "Review the catalog content and source evidence, update it if required, then run tests.",
        ),
    }


def analyze_catalogs(
    root: Path = ROOT,
    check_urls: bool = True,
    today: Optional[date] = None,
) -> Dict[str, Any]:
    config = root / "config"
    current_date = today or datetime.now(timezone.utc).date()
    manifest_path = config / "catalog_metadata.json"
    try:
        manifest = _load(manifest_path)
        if not isinstance(manifest, dict):
            raise ValueError("Catalog manifest root must be an object.")
        review_due_days = int(manifest["review_due_days"])
        stale_days = int(manifest["stale_days"])
        if review_due_days <= 0 or stale_days <= review_due_days:
            raise ValueError("Freshness thresholds are invalid.")
    except (json.JSONDecodeError, yaml.YAMLError, OSError, UnicodeError, TypeError, ValueError, KeyError) as error:
        finding = _finding(
            {
                "id": "catalog_manifest",
                "display_name": "Catalog manifest",
                "file": "catalog_metadata.json",
            },
            "Invalid catalog manifest",
            str(error),
            "critical",
        )
        return {
            "catalog_version": "unknown",
            "generated_at": current_date.isoformat(),
            "catalogs": [],
            "findings": [finding],
            "checked_urls": 0,
            "actionable": True,
            "decision_options": DECISION_OPTIONS,
        }
    catalogs = []
    findings = []
    checked_urls = 0

    for item in manifest.get("catalogs", []):
        path = config / item["file"]
        if not path.is_file():
            findings.append(_finding(item, "Missing catalog", str(path), "critical"))
            continue

        try:
            data = _load(path)
        except (json.JSONDecodeError, yaml.YAMLError, OSError, UnicodeError) as error:
            findings.append(_finding(item, "Invalid catalog", str(error), "critical"))
            continue

        try:
            verified = date.fromisoformat(item["last_verified"])
        except (KeyError, TypeError, ValueError) as error:
            findings.append(
                _finding(item, "Invalid last_verified date", str(error), "critical")
            )
            continue
        age = max((current_date - verified).days, 0)
        state = "stale" if age > stale_days else (
            "review_due" if age > review_due_days else "current"
        )
        catalogs.append({**item, "age_days": age, "status": state, "sha256": _sha256(path)})

        if state != "current":
            findings.append(
                _finding(
                    item,
                    f"Catalog is {state}",
                    f"Last verified {item['last_verified']} ({age} days ago)",
                    "high" if state == "stale" else "normal",
                )
            )

        if check_urls:
            source_urls = {item["source"]} if str(item.get("source", "")).startswith("http") else set()
            for url in sorted(set(_walk_urls(data)) | source_urls):
                checked_urls += 1
                status = _url_status(url)
                if not status.startswith(("2", "3")):
                    findings.append(
                        _finding(item, "Source URL requires review", f"{status} {url}", "normal")
                    )

    return {
        "catalog_version": manifest.get("catalog_version", "unknown"),
        "generated_at": current_date.isoformat(),
        "catalogs": catalogs,
        "findings": findings,
        "checked_urls": checked_urls,
        "actionable": bool(findings),
        "decision_options": DECISION_OPTIONS,
    }


def _source_reference(source: str) -> str:
    return f"[source]({source})" if source.startswith(("http://", "https://")) else source or "-"


def _report_lines(result: Dict[str, Any]) -> list[str]:
    catalog_rows = [
        f"| {item['display_name']} | `{item['file']}` | {item['last_verified']} | "
        f"{item['age_days']} | {item['status']} | `{item['sha256'][:12]}` |"
        for item in result["catalogs"]
    ]
    finding_rows = [
        f"| {finding['priority']} | [{finding['catalog']}](../config/{finding['file']}) | "
        f"{finding['issue']} | {finding['evidence']} | "
        f"{_source_reference(str(finding['source']))} | "
        f"{finding['recommended_action']} |"
        for finding in result["findings"]
    ] or ["| - | - | No actionable findings | - | - | No catalog changes required. |"]
    decision_sections = []
    for index, finding in enumerate(result["findings"], 1):
        decision_sections.extend(
            [
                f"### {index}. {finding['catalog']} — {finding['issue']}",
                "",
                *[f"- [ ] `{option}`" for option in result["decision_options"]],
                "",
            ]
        )
    if not decision_sections:
        decision_sections = ["No reviewer decision is required for this run.", ""]

    return [
        "# ATI Catalog Maintenance Report",
        "",
        f"Generated (UTC): {result['generated_at']}",
        f"Catalog version: `{result['catalog_version']}`",
        f"Actionable review required: **{'yes' if result['actionable'] else 'no'}**",
        "",
        "This report is review-only. It does not update catalog rules, verification dates, or production content.",
        "",
        "## Catalog Freshness and Integrity",
        "",
        "| Catalog | File | Last verified | Age (days) | Status | SHA-256 |",
        "|---|---|---:|---:|---|---|",
        *catalog_rows,
        "",
        "## Actionable Findings",
        "",
        "| Priority | Catalog | Issue | Evidence | Source | Recommended action |",
        "|---|---|---|---|---|---|",
        *finding_rows,
        "",
        "## Reviewer Decision",
        "",
        "Record one decision for each actionable item:",
        "",
        *decision_sections,
        "## Review Checklist",
        "",
        "- [ ] Open the affected catalog and source links listed above.",
        "- [ ] Confirm whether the source meaning changed, not only whether the URL responds.",
        "- [ ] Update catalog content only when supported by reviewed evidence.",
        "- [ ] Update `last_verified` only after semantic review is complete.",
        "- [ ] Run catalog and project tests; inspect the diff for changed findings or mappings.",
        "- [ ] Obtain review approval before merge and include changes in a versioned release.",
        "",
        "## Validation Summary",
        "",
        f"- Catalogs parsed: {len(result['catalogs'])}",
        f"- URLs checked: {result['checked_urls']}",
        f"- Actionable findings: {len(result['findings'])}",
        "",
    ]


def generate_report(
    output: Path,
    check_urls: bool = True,
    root: Path = ROOT,
    today: Optional[date] = None,
) -> int:
    result = analyze_catalogs(root=root, check_urls=check_urls, today=today)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(_report_lines(result)), encoding="utf-8")
    return 0


def _write_github_output(path: Optional[Path], actionable: bool) -> None:
    if path:
        with path.open("a", encoding="utf-8") as output:
            output.write(f"actionable={'true' if actionable else 'false'}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=ROOT / "docs" / "catalog-maintenance-report.md",
    )
    parser.add_argument("--offline", action="store_true", help="Skip source URL checks.")
    parser.add_argument("--github-output", type=Path, help="Write actionable state for GitHub Actions.")
    args = parser.parse_args()

    result = analyze_catalogs(check_urls=not args.offline)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(_report_lines(result)), encoding="utf-8")
    _write_github_output(args.github_output, result["actionable"])
    print(f"Catalog review actionable: {result['actionable']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
