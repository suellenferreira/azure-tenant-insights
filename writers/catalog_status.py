"""HTML presentation helpers for local ATI catalog provenance."""

from html import escape
from typing import Any, Dict, Iterable

_ICONS = {"current": "&#9432;", "review_due": "&#9888;", "stale": "&#9888;"}
_COLORS = {"current": "#777777", "review_due": "#9A6700", "stale": "#C00000"}


def catalog_item(status: Dict[str, Any], catalog_id: str) -> Dict[str, Any]:
    return next(
        (item for item in status.get("catalogs", []) if item.get("id") == catalog_id),
        {},
    )


def catalog_badge_html(status: Dict[str, Any], catalog_ids: Iterable[str]) -> str:
    items = [catalog_item(status, catalog_id) for catalog_id in catalog_ids]
    items = [item for item in items if item]
    if not items:
        return ""
    worst = "current"
    if any(item.get("status") == "stale" for item in items):
        worst = "stale"
    elif any(item.get("status") == "review_due" for item in items):
        worst = "review_due"
    details = "; ".join(
        f"{item['display_name']}: {item['status']}, version {status.get('catalog_version', 'unknown')}, "
        f"verified {item['last_verified']}. Review is flagged after {status.get('review_due_days', 90)} "
        f"days and stale after {status.get('stale_days', 180)} days. Warnings do not block the scan "
        "or update files automatically."
        for item in items
    )
    return (
        f'<span class="catalog-badge catalog-{worst}" title="{escape(details, quote=True)}">'
        f'{_ICONS[worst]}</span>'
    )


def catalog_status_html(status: Dict[str, Any]) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{escape(str(item.get('display_name', '')))}</td>"
        f"<td>{escape(str(status.get('catalog_version', 'unknown')))}</td>"
        f"<td>{escape(str(item.get('last_verified', '')))}</td>"
        f"<td>{item.get('age_days', 0)}</td>"
        f"<td style=\"color:{_COLORS.get(item.get('status'), '#777777')};font-weight:600\">"
        f"{escape(str(item.get('status', 'unknown')))}</td>"
        f"<td>{escape(', '.join(item.get('used_by', [])))}</td>"
        "</tr>"
        for item in status.get("catalogs", [])
    )
    return f"""<div class="section" id="catalog-status">
      <h2>Catalog Status</h2>
    <p class="note">Version-controlled catalogs are evaluated locally on every scan. Catalogs older than {status.get('review_due_days', 90)} days are flagged for review and catalogs older than {status.get('stale_days', 180)} days are marked stale. These warnings do not block the scan or update files automatically. ATI does not fetch or validate catalog rules against Microsoft documentation during a scan.</p>
      <div class="table-scroll"><table class="dtable">
        <thead><tr><th>Catalog</th><th>Version</th><th>Last verified</th><th>Age (days)</th><th>Status</th><th>Used by</th></tr></thead>
        <tbody>{rows}</tbody>
      </table></div>
    </div>"""