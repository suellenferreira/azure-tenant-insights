"""Generate a review-only report for ATI's version-controlled catalogs."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Iterable

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
MANIFEST = CONFIG / "catalog_metadata.json"


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


def generate_report(output: Path, check_urls: bool = True) -> int:
    manifest = _load(MANIFEST)
    rows = []
    urls = set()
    errors = []
    today = datetime.now(timezone.utc).date()

    for item in manifest.get("catalogs", []):
        path = CONFIG / item["file"]
        if not path.is_file():
            errors.append(f"Missing catalog: {item['file']}")
            continue
        data = _load(path)
        urls.update(_walk_urls(data))
        age = max((today - datetime.fromisoformat(item["last_verified"]).date()).days, 0)
        state = "stale" if age > manifest["stale_days"] else (
            "review_due" if age > manifest["review_due_days"] else "current"
        )
        rows.append((item["display_name"], item["file"], item["last_verified"], age, state))

    url_rows = [(url, _url_status(url)) for url in sorted(urls)] if check_urls else []
    failed_urls = [row for row in url_rows if not row[1].startswith(("2", "3"))]
    lines = [
        "# ATI Catalog Maintenance Report",
        "",
        f"Generated (UTC): {today.isoformat()}",
        f"Catalog version: `{manifest.get('catalog_version', 'unknown')}`",
        "",
        "This report is review-only. It does not update catalog rules.",
        "",
        "## Catalog Freshness",
        "",
        "| Catalog | File | Last verified | Age (days) | Status |",
        "|---|---|---:|---:|---|",
        *[f"| {name} | `{file}` | {verified} | {age} | {state} |" for name, file, verified, age, state in rows],
        "",
        "## Validation",
        "",
        f"- Missing or invalid catalogs: {len(errors)}",
        f"- URLs checked: {len(url_rows)}",
        f"- URLs requiring review: {len(failed_urls)}",
        "",
        *[f"- {error}" for error in errors],
        *[f"- `{status}` {url}" for url, status in failed_urls],
        "",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return 1 if errors else 0


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "catalog-maintenance-report.md"
    raise SystemExit(generate_report(target, check_urls="--offline" not in sys.argv))