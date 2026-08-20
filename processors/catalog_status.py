"""Evaluate the age and provenance of version-controlled ATI catalogs locally."""

from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

CATALOG_METADATA_PATH = Path(__file__).resolve().parent.parent / "config" / "catalog_metadata.json"


def load_catalog_status(
    path: Path = CATALOG_METADATA_PATH,
    as_of: Optional[date] = None,
) -> Dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    current_date = as_of or datetime.now(timezone.utc).date()
    review_due_days = int(manifest.get("review_due_days", 90))
    stale_days = int(manifest.get("stale_days", 180))
    catalogs: List[Dict[str, Any]] = []

    for raw in manifest.get("catalogs", []):
        verified = date.fromisoformat(raw["last_verified"])
        age_days = max((current_date - verified).days, 0)
        if age_days > stale_days:
            status = "stale"
        elif age_days > review_due_days:
            status = "review_due"
        else:
            status = "current"
        catalogs.append({**raw, "age_days": age_days, "status": status})

    overall_status = "current"
    if any(item["status"] == "stale" for item in catalogs):
        overall_status = "stale"
    elif any(item["status"] == "review_due" for item in catalogs):
        overall_status = "review_due"

    return {
        "catalog_version": manifest.get("catalog_version", "unknown"),
        "evaluated_at_utc": current_date.isoformat(),
        "review_due_days": review_due_days,
        "stale_days": stale_days,
        "overall_status": overall_status,
        "catalogs": catalogs,
    }


def catalog_warnings(status: Dict[str, Any]) -> List[Dict[str, str]]:
    return [
        {
            "collector": "catalog_status",
            "message": (
                f"{item['display_name']} catalog is {item['status']} "
                f"({item['age_days']} days since verification on {item['last_verified']}). "
                "Results use the local version-controlled catalog."
            ),
        }
        for item in status.get("catalogs", [])
        if item.get("status") in {"review_due", "stale"}
    ]