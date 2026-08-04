"""
draw.io (.drawio) diagram writer.

Generates a single multi-page .drawio file (uncompressed mxGraphModel XML that opens
directly in https://draw.io / diagrams.net) with assessment-oriented pages:

  - Overview        : metadata, KPIs (by Service Model / Business Pillar), legend,
                      and clickable links to the other pages
  - Service Model   : resource types grouped by IaaS / PaaS / SaaS / Hybrid /
                      Supporting Services / Other
  - Business Pillar : resource types grouped by business pillar
  - Resources       : one page per subscription — resource groups (with region)
                      and aggregated "N x Type" nodes

Resource types are rendered with real Azure 2019 icons from draw.io's bundled
stencil library (config/drawio_stencils.yaml, verified paths). Types without a
mapped icon fall back to a colored card. Taxonomy comes from processors.classifier.
"""

import logging
import os
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as _xml_escape

logger = logging.getLogger(__name__)

STENCILS_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "drawio_stencils.yaml"
)

# (stroke, fill) per service model
SERVICE_MODEL_COLORS: Dict[str, Tuple[str, str]] = {
    "IaaS": ("#1F4E79", "#DCE6F1"),
    "PaaS": ("#2E86AB", "#D6E4F0"),
    "SaaS": ("#548235", "#E2EFDA"),
    "Hybrid": ("#BF8F00", "#FFF2CC"),
    "Supporting Services": ("#C55A11", "#FCE4D6"),
    "Other": ("#7F7F7F", "#F2F2F2"),
}
_PILLAR_PALETTE = [
    ("#1F4E79", "#DCE6F1"), ("#2E86AB", "#D6E4F0"), ("#548235", "#E2EFDA"),
    ("#BF8F00", "#FFF2CC"), ("#C55A11", "#FCE4D6"), ("#7030A0", "#E9DDF3"),
    ("#C00000", "#F8D7DA"), ("#0E7C7B", "#D7EFEE"), ("#4472C4", "#DAE3F3"),
    ("#7F6000", "#FFF2CC"), ("#385723", "#E2EFDA"), ("#7F7F7F", "#F2F2F2"),
]

# Layout constants
NODE_W = 120
NODE_H = 88
ICON = 44
PAD = 16
HEADER_H = 34
GROUP_COLS = 7
PAGE_MARGIN = 40
_MAX_SUB_PAGES = int(os.getenv("ATI_DIAGRAM_MAX_SUBS", "60"))

_STENCILS: Optional[dict] = None


def _load_stencils() -> dict:
    global _STENCILS
    if _STENCILS is not None:
        return _STENCILS
    cfg: dict = {}
    try:
        import yaml

        with open(STENCILS_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception as e:  # noqa: BLE001 - degrade gracefully to colored cards
        logger.warning(f"Could not load drawio stencils config: {e}")
    cfg.setdefault("base", "img/lib/azure2")
    cfg.setdefault("fallback", "general/All_Resources.svg")
    cfg.setdefault("types", {})
    cfg.setdefault("namespaces", {})
    _STENCILS = cfg
    return _STENCILS


def _icon_path(resource_type: str) -> Optional[str]:
    cfg = _load_stencils()
    rt = (resource_type or "").lower()
    rel = cfg["types"].get(rt)
    if not rel:
        ns = rt.split("/", 1)[0] if "/" in rt else rt
        rel = cfg["namespaces"].get(ns)
    if not rel:
        rel = cfg.get("fallback")  # generic Azure icon — never leave a node blank
    if not rel:
        return None
    return f"{cfg['base']}/{rel}"


def _icon_style(image_path: str) -> str:
    return (
        "sketch=0;html=1;strokeColor=none;fillColor=none;labelPosition=center;"
        "verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;"
        f"shape=image;aspect=fixed;image={image_path};"
    )


def _stencil(rel_path: str) -> str:
    """Absolute stencil image ref from a path relative to the Azure2 base."""
    return f"{_load_stencils()['base']}/{rel_path}"


# Reserved-subnet role → Azure icon (relative to the stencil base).
_SUBNET_ICON = {
    "gateway": "networking/Virtual_Network_Gateways.svg",
    "bastion": "networking/Bastions.svg",
    "firewall": "networking/Firewalls.svg",
    "routeserver": "networking/Route_Tables.svg",
}
_VNET_ICON_REL = "networking/Virtual_Networks.svg"
_EDGE_OK = (
    "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#2E7D32;strokeWidth=2;"
    "endArrow=none;startArrow=none;fontColor=#2E7D32;fontSize=10;jettySize=auto;"
    "exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;"
)
_EDGE_BROKEN = (
    "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#C00000;strokeWidth=2;"
    "dashed=1;endArrow=none;startArrow=none;fontColor=#C00000;fontSize=10;jettySize=auto;"
    "exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;"
)


def _esc(value) -> str:
    return _xml_escape("" if value is None else str(value), {'"': "&quot;", "'": "&apos;"})


def _display_name(resource_type: str) -> str:
    from processors.normalizer import clean_resource_type

    return clean_resource_type(resource_type)


class _Page:
    def __init__(self, page_id: str, name: str):
        self.id = page_id
        self.name = name
        self.cells: List[str] = []
        self._n = 0

    def _next(self, prefix="c") -> str:
        self._n += 1
        return f"{self.id}-{prefix}{self._n}"

    def vertex(self, value, style, x, y, w, h, parent="1", tooltip=None):
        cid = self._next()
        geom = f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>'
        if tooltip:
            self.cells.append(
                f'<UserObject label="{_esc(value)}" tooltip="{_esc(tooltip)}" id="{cid}">'
                f'<mxCell style="{style}" vertex="1" parent="{parent}">{geom}</mxCell>'
                f'</UserObject>'
            )
        else:
            self.cells.append(
                f'<mxCell id="{cid}" value="{_esc(value)}" style="{style}" '
                f'vertex="1" parent="{parent}">{geom}</mxCell>'
            )
        return cid

    def link(self, value, style, x, y, w, h, target_page_id, parent="1"):
        cid = self._next("l")
        geom = f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>'
        self.cells.append(
            f'<UserObject label="{_esc(value)}" link="data:page/id,{target_page_id}" id="{cid}">'
            f'<mxCell style="{style}" vertex="1" parent="{parent}">{geom}</mxCell>'
            f'</UserObject>'
        )
        return cid

    def edge(self, source_id, target_id, style, label="", parent="1", points=None):
        cid = self._next("e")
        val = f' value="{_esc(label)}"' if label else ""
        if points:
            pts = "".join(f'<mxPoint x="{int(px)}" y="{int(py)}"/>' for px, py in points)
            geom = (f'<mxGeometry relative="1" as="geometry">'
                    f'<Array as="points">{pts}</Array></mxGeometry>')
        else:
            geom = '<mxGeometry relative="1" as="geometry"/>'
        self.cells.append(
            f'<mxCell id="{cid}"{val} style="{style}" edge="1" parent="{parent}" '
            f'source="{source_id}" target="{target_id}">{geom}</mxCell>'
        )
        return cid

    def to_xml(self) -> str:
        body = "".join(self.cells)
        return (
            f'<diagram id="{self.id}" name="{_esc(self.name)}">'
            f'<mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" '
            f'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
            f'pageWidth="1700" pageHeight="1200" math="0" shadow="0">'
            f'<root><mxCell id="0"/><mxCell id="1" parent="0"/>{body}</root>'
            f'</mxGraphModel></diagram>'
        )


_TITLE_STYLE = (
    "rounded=0;whiteSpace=wrap;html=1;fillColor=#1F4E79;fontColor=#FFFFFF;"
    "strokeColor=none;fontSize=18;fontStyle=1;align=left;verticalAlign=middle;spacingLeft=16;"
)
_META_STYLE = (
    "rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;fontColor=#333333;"
    "strokeColor=#D3D3D3;fontSize=11;align=left;verticalAlign=middle;spacingLeft=10;"
)


def _group_style(stroke: str, fill: str) -> str:
    return (
        f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
        f"fontColor={stroke};fontSize=13;fontStyle=1;align=left;verticalAlign=top;"
        f"spacingLeft=12;spacingTop=8;arcSize=3;container=1;collapsible=0;"
    )


def _card_style(stroke: str) -> str:
    return (
        f"rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor={stroke};"
        f"fontColor=#222222;fontSize=10;align=center;verticalAlign=middle;arcSize=10;"
    )


def _layout_group(page: _Page, title: str, items: List[Tuple[str, str, Optional[str]]],
                  colors: Tuple[str, str], x: int, y: int) -> Tuple[int, int]:
    """Render a titled container with a grid of nodes.
    items = [(label, tooltip, icon_path_or_None)]. Returns (width, height)."""
    stroke, fill = colors
    n = max(len(items), 1)
    cols = min(GROUP_COLS, n)
    rows = (n + cols - 1) // cols
    inner_w = cols * NODE_W + 2 * PAD
    inner_h = HEADER_H + rows * NODE_H + PAD

    cont = page.vertex(f"{title}  ({len(items)})", _group_style(stroke, fill),
                       x, y, inner_w, inner_h)
    for i, (label, tooltip, icon) in enumerate(items):
        r, c = divmod(i, cols)
        nx = PAD + c * NODE_W
        ny = HEADER_H + r * NODE_H
        if icon:
            page.vertex(label, _icon_style(icon),
                        nx + (NODE_W - ICON) // 2, ny + 6, ICON, ICON,
                        parent=cont, tooltip=tooltip)
        else:
            page.vertex(label, _card_style(stroke),
                        nx + 6, ny + 16, NODE_W - 12, 46, parent=cont, tooltip=tooltip)
    return inner_w, inner_h


def _group_dims(n_items: int) -> Tuple[int, int]:
    """Container (width, height) for a group with n_items nodes."""
    n = max(n_items, 1)
    cols = min(GROUP_COLS, n)
    rows = (n + cols - 1) // cols
    return cols * NODE_W + 2 * PAD, HEADER_H + rows * NODE_H + PAD


def _counts_by(scan_data: dict, key: str) -> Dict[str, int]:
    from processors.classifier import classify_resource_type

    out: Dict[str, int] = {}
    for rtype, resources in scan_data.get("resources_by_type", {}).items():
        g = classify_resource_type(rtype)[key]
        out[g] = out.get(g, 0) + len(resources)
    return out


def _type_tooltip(rtype: str, n: int, cls: dict) -> str:
    return (f"{rtype}\nCount: {n:,}\nTechnical: {cls['technical_category']}\n"
            f"Pillar: {cls['business_pillar']}\nModel: {cls['service_model']}\n"
            f"Publisher: {cls['publisher']}")


def _add_sm_legend(page: _Page, x: int, y: int) -> None:
    """Service Model color legend box at (x, y)."""
    page.vertex("Legend — Service Model colors", _group_style("#7F7F7F", "#FFFFFF"),
                x, y, 300, HEADER_H + len(SERVICE_MODEL_COLORS) * 28 + PAD)
    for i, (model, (stroke, fill)) in enumerate(SERVICE_MODEL_COLORS.items()):
        page.vertex(model,
                    f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
                    f"fontColor={stroke};fontSize=11;align=left;spacingLeft=8;",
                    x + PAD, y + HEADER_H + i * 28, 300 - 2 * PAD, 24)


def _page_group_by(scan_data: dict, page_id: str, name: str, key: str) -> _Page:
    from processors.classifier import classify_resource_type, service_model_order

    page = _Page(page_id, name)
    resources_by_type = scan_data.get("resources_by_type", {})

    groups: Dict[str, List[tuple]] = {}
    for rtype, resources in resources_by_type.items():
        cls = classify_resource_type(rtype)
        groups.setdefault(cls[key], []).append((rtype, len(resources), cls))

    if key == "service_model":
        order = [g for g in service_model_order() if g in groups]
        order += [g for g in groups if g not in order]
    else:
        order = sorted(groups, key=lambda g: -sum(n for _, n, _ in groups[g]))

    pillar_colors = {g: _PILLAR_PALETTE[i % len(_PILLAR_PALETTE)] for i, g in enumerate(order)}

    total = sum(len(v) for v in resources_by_type.values())
    page.vertex(f"{name} — {total:,} resources / {len(resources_by_type)} types",
                _TITLE_STYLE, PAGE_MARGIN, PAGE_MARGIN, 1500, 40)

    y = PAGE_MARGIN + 60
    for g in order:
        items = []
        for rtype, n, cls in sorted(groups[g], key=lambda t: -t[1]):
            items.append((f"{_display_name(rtype)}\n{n:,}", _type_tooltip(rtype, n, cls),
                          _icon_path(rtype)))
        colors = (SERVICE_MODEL_COLORS.get(g, ("#7F7F7F", "#F2F2F2"))
                  if key == "service_model" else pillar_colors[g])
        _, h = _layout_group(page, g, items, colors, PAGE_MARGIN, y)
        y += h + PAD * 2
    if key == "service_model":
        _add_sm_legend(page, PAGE_MARGIN + 960, PAGE_MARGIN + 60)
    return page


def _page_overview(scan_data: dict, pages: List[Tuple[str, str]]) -> _Page:
    from processors.classifier import service_model_order

    meta = scan_data.get("metadata", {})
    page = _Page("ati-overview", "Overview")

    page.vertex("Azure Tenant Insights — Diagram Overview", _TITLE_STYLE,
                PAGE_MARGIN, PAGE_MARGIN, 1300, 44)
    page.vertex(
        f"Tenant: {meta.get('tenant_name', 'N/A')}   ·   "
        f"Scan: {str(meta.get('scan_timestamp', ''))[:10]}   ·   "
        f"Subscriptions: {meta.get('subscription_count', 0)}   ·   "
        f"Resources: {sum(len(v) for v in scan_data.get('resources_by_type', {}).values()):,}",
        _META_STYLE, PAGE_MARGIN, PAGE_MARGIN + 52, 1300, 28)

    sm = _counts_by(scan_data, "service_model")
    pil = _counts_by(scan_data, "business_pillar")
    sm_order = [m for m in service_model_order() if sm.get(m)] + \
               [m for m in sm if m not in service_model_order()]

    y0 = PAGE_MARGIN + 100
    sm_cards = [(f"{m}\n{sm[m]:,}", f"Service Model: {m}\nResources: {sm[m]:,}", None) for m in sm_order]
    _layout_group(page, "By Service Model", sm_cards, ("#1F4E79", "#DCE6F1"), PAGE_MARGIN, y0)

    pil_cards = [(f"{p}\n{c:,}", f"Business Pillar: {p}\nResources: {c:,}", None)
                 for p, c in sorted(pil.items(), key=lambda x: -x[1])]
    _layout_group(page, "By Business Pillar", pil_cards, ("#2E86AB", "#D6E4F0"),
                  PAGE_MARGIN, y0 + 180)

    ny = y0 + 400
    page.vertex("Pages", _group_style("#385723", "#E2EFDA"),
                PAGE_MARGIN, ny, 380, HEADER_H + len(pages) * (44 + 10) + PAD)
    link_style = (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#385723;"
        "fontColor=#0563C1;fontSize=12;fontStyle=4;align=center;verticalAlign=middle;arcSize=10;"
    )
    for i, (pid, pname) in enumerate(pages):
        page.link(f"→ {pname}", link_style,
                  PAGE_MARGIN + PAD, ny + HEADER_H + i * (44 + 10), 380 - 2 * PAD, 44, pid)
    return page


def _layout_vnet(page: _Page, vnet: dict, x: int, y: int) -> Tuple[str, int, int]:
    """Render a VNet as a container of subnet nodes. Returns (container_id, w, h)."""
    subnets = vnet.get("subnets", [])
    n = max(len(subnets), 1)
    cols = min(GROUP_COLS, n)
    rows = (n + cols - 1) // cols
    header = 48  # two lines: name/region + CIDR
    w = cols * NODE_W + 2 * PAD
    h = header + rows * NODE_H + PAD

    cidr = ", ".join(vnet.get("address_prefixes") or []) or "—"
    title = f"{vnet['name']}  ·  {vnet.get('location') or '—'}\nCIDR: {cidr}"
    cont = page.vertex(title, _group_style("#1F4E79", "#DCE6F1"), x, y, w, h)

    # VNet icon badge in the top-right corner of the container.
    page.vertex("", _icon_style(_stencil(_VNET_ICON_REL)),
                w - 30, 6, 24, 24, parent=cont)

    for i, sn in enumerate(subnets):
        r, c = divmod(i, cols)
        nx = PAD + c * NODE_W
        ny = header + r * NODE_H
        special = sn.get("special")
        tip = (f"Subnet: {sn['name']}\nPrefix: {sn.get('prefix') or '—'}"
               + (f"\nRole: {special}" if special else ""))
        icon_rel = _SUBNET_ICON.get(special)
        label = f"{sn['name']}\n{sn.get('prefix') or ''}".strip()
        if icon_rel:
            page.vertex(label, _icon_style(_stencil(icon_rel)),
                        nx + (NODE_W - ICON) // 2, ny + 6, ICON, ICON,
                        parent=cont, tooltip=tip)
        else:
            page.vertex(label, _card_style("#7F7F7F"),
                        nx + 6, ny + 16, NODE_W - 12, 46, parent=cont, tooltip=tip)
    return cont, w, h


def _page_network(scan_data: dict) -> Optional[_Page]:
    """Network Topology page: VNets (with subnets) + peering edges.
    Returns None when the tenant has no virtual networks."""
    from processors.network_topology import build_network_topology

    topo = build_network_topology(scan_data)
    vnets = topo["vnets"]
    if not vnets:
        return None

    st = topo["stats"]
    page = _Page("ati-network", "Network Topology")
    page.vertex(
        f"Network Topology — {st['vnet_count']} VNets · {st['subnet_count']} subnets · "
        f"{st['peering_count']} peerings · {st['broken_count']} broken/orphan",
        _TITLE_STYLE, PAGE_MARGIN, PAGE_MARGIN, 1500, 40)

    # Legend (peering edge colors).
    lx = PAGE_MARGIN + 1180
    page.vertex("Legend", _group_style("#7F7F7F", "#FFFFFF"), lx, PAGE_MARGIN, 320, 90)
    page.vertex("Peering: Connected", "rounded=0;html=1;fillColor=#FFFFFF;strokeColor=#2E7D32;"
                "fontColor=#2E7D32;fontSize=11;align=left;spacingLeft=8;",
                lx + PAD, PAGE_MARGIN + HEADER_H, 320 - 2 * PAD, 20)
    page.vertex("Peering: Disconnected / orphan", "rounded=0;html=1;fillColor=#FFFFFF;"
                "strokeColor=#C00000;fontColor=#C00000;fontSize=11;align=left;spacingLeft=8;dashed=1;",
                lx + PAD, PAGE_MARGIN + HEADER_H + 24, 320 - 2 * PAD, 20)

    # ---- Connectivity-aware placement (item 5): keep peered VNets adjacent and
    # route each peering edge through a lane *below* its row, so it never crosses
    # an unrelated VNet. In-scope peerings define connected components; each
    # component gets its own row (hub first, then BFS neighbours). Isolated VNets
    # flow-pack afterwards. Orphan peerings link to external placeholders.
    page_right = PAGE_MARGIN + 1620
    vnet_by_id = {v["id"]: v for v in vnets}
    id_set = set(vnet_by_id)

    in_scope = [pe for pe in topo["peerings"] if pe["dst"] in id_set]
    orphans = [pe for pe in topo["peerings"] if pe["dst"] not in id_set]

    adj: Dict[str, set] = {i: set() for i in vnet_by_id}
    for pe in in_scope:
        adj[pe["src"]].add(pe["dst"])
        adj[pe["dst"]].add(pe["src"])

    seen: set = set()
    components: List[List[str]] = []
    for i in sorted(vnet_by_id, key=lambda n: vnet_by_id[n]["name"]):
        if i in seen or not adj[i]:
            continue
        stack, comp = [i], []
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp.append(x)
            stack.extend(adj[x] - seen)
        components.append(comp)
    components.sort(key=len, reverse=True)

    def _order_component(comp: List[str]) -> List[str]:
        hub = max(sorted(comp), key=lambda n: len(adj[n]))
        order, cseen, queue = [], set(), [hub]
        while queue:
            n = queue.pop(0)
            if n in cseen:
                continue
            cseen.add(n)
            order.append(n)
            queue.extend(sorted(adj[n] - cseen, key=lambda m: -len(adj[m])))
        return order

    def _vnet_dims(v: dict) -> Tuple[int, int]:
        k = max(len(v["subnets"]), 1)
        cols = min(GROUP_COLS, k)
        rows = (k + cols - 1) // cols
        return cols * NODE_W + 2 * PAD, 48 + rows * NODE_H + PAD

    pos: Dict[str, str] = {}
    geom: Dict[str, Tuple[int, int, int, int]] = {}
    comp_of: Dict[str, int] = {}
    comp_lane_y: Dict[int, int] = {}

    y = PAGE_MARGIN + 140  # start below the legend (fixes item 2 overlap)

    for ci, comp in enumerate(components):
        comp_set = set(comp)
        x = PAGE_MARGIN
        row_h = 0
        for vid in _order_component(comp):
            v = vnet_by_id[vid]
            w, h = _vnet_dims(v)
            cont, _, _ = _layout_vnet(page, v, x, y)
            pos[vid] = cont
            geom[vid] = (x, y, w, h)
            comp_of[vid] = ci
            x += w + PAD * 2
            row_h = max(row_h, h)
        row_bottom = y + row_h
        n_edges = sum(1 for pe in in_scope
                      if pe["src"] in comp_set and pe["dst"] in comp_set)
        comp_lane_y[ci] = row_bottom + 24
        y = row_bottom + 24 + max(1, n_edges) * 16 + PAD * 2

    # Isolated VNets (no in-scope peering) flow-pack after the components.
    x_cursor = PAGE_MARGIN
    row_y = y
    row_max_h = 0
    for vid in sorted((i for i in vnet_by_id if i not in pos),
                      key=lambda n: (vnet_by_id[n]["subscriptionId"], vnet_by_id[n]["name"])):
        v = vnet_by_id[vid]
        w, h = _vnet_dims(v)
        if x_cursor + w > page_right and x_cursor > PAGE_MARGIN:
            x_cursor = PAGE_MARGIN
            row_y += row_max_h + PAD * 2
            row_max_h = 0
        cont, _, _ = _layout_vnet(page, v, x_cursor, row_y)
        pos[vid] = cont
        geom[vid] = (x_cursor, row_y, w, h)
        x_cursor += w + PAD * 2
        row_max_h = max(row_max_h, h)

    # In-scope peering edges routed through their component's lane.
    lane_used: Dict[int, int] = {}
    for pe in in_scope:
        ci = comp_of.get(pe["src"])
        if ci is None or pe["src"] not in geom or pe["dst"] not in geom:
            continue
        x1, _, w1, _ = geom[pe["src"]]
        x2, _, w2, _ = geom[pe["dst"]]
        sx, dx = x1 + w1 // 2, x2 + w2 // 2
        k = lane_used.get(ci, 0)
        lane_used[ci] = k + 1
        lane_y = comp_lane_y[ci] + k * 16
        style = _EDGE_BROKEN if pe["broken"] else _EDGE_OK
        page.edge(pos[pe["src"]], pos[pe["dst"]], style, label=pe["state"],
                  points=[(sx, lane_y), (dx, lane_y)])

    # External (orphan) VNet placeholders + dashed edges beneath the topology.
    ext_pos: Dict[str, str] = {}
    ext_x = PAGE_MARGIN
    ext_y = row_y + row_max_h + PAD * 3
    for pe in orphans:
        if pe["src"] not in pos:
            continue
        if pe["dst"] not in ext_pos:
            node = page.vertex(
                f"External VNet\n{pe['dst_name']}", _card_style("#C00000"),
                ext_x, ext_y, 170, 60,
                tooltip=f"Peered VNet outside scan scope\n{pe['dst']}")
            ext_pos[pe["dst"]] = node
            ext_x += 190
            if ext_x > page_right:
                ext_x = PAGE_MARGIN
                ext_y += 80
        page.edge(pos[pe["src"]], ext_pos[pe["dst"]], _EDGE_BROKEN, label="orphan")

    return page


def _pages_resources(scan_data: dict) -> List[_Page]:
    from processors.classifier import classify_resource_type

    subs = scan_data.get("subscriptions", [])
    resources_by_type = scan_data.get("resources_by_type", {})

    # subId -> rg -> type -> count   and   subId -> rg -> set(regions)
    idx: Dict[str, Dict[str, Dict[str, int]]] = {}
    regions: Dict[str, Dict[str, set]] = {}
    for rtype, resources in resources_by_type.items():
        for r in resources:
            sid = r.get("subscriptionId", "unknown")
            rg = r.get("resourceGroup", "") or "(no resource group)"
            idx.setdefault(sid, {}).setdefault(rg, {}).setdefault(rtype, 0)
            idx[sid][rg][rtype] += 1
            loc = (r.get("location") or "").strip()
            if loc:
                regions.setdefault(sid, {}).setdefault(rg, set()).add(loc)

    pages: List[_Page] = []
    ordered = sorted(subs, key=lambda s: -sum(
        sum(t.values()) for t in idx.get(s.get("subscriptionId", ""), {}).values()))
    for i, sub in enumerate(ordered):
        if i >= _MAX_SUB_PAGES:
            logger.warning(
                f"Diagram: {len(ordered) - _MAX_SUB_PAGES} subscription page(s) omitted "
                f"(cap {_MAX_SUB_PAGES}). Set ATI_DIAGRAM_MAX_SUBS to include more."
            )
            break
        sid = sub.get("subscriptionId", "")
        rgs = idx.get(sid, {})
        if not rgs:
            continue
        page = _Page(f"ati-sub-{i}", f"Sub-{(sub.get('displayName') or sid)}"[:40])
        total = sum(sum(t.values()) for t in rgs.values())
        page.vertex(f"Resources — {sub.get('displayName', sid)}  ({total:,})",
                    _TITLE_STYLE, PAGE_MARGIN, PAGE_MARGIN, 1500, 40)

        # Row-based flow layout: respect each container's real width, wrap at the
        # page width and track the tallest container per row (prevents overlap).
        page_right = PAGE_MARGIN + 1620
        x_cursor = PAGE_MARGIN
        row_y = PAGE_MARGIN + 60
        row_max_h = 0
        for rg, types in sorted(rgs.items(), key=lambda kv: -sum(kv[1].values())):
            rg_regions = regions.get(sid, {}).get(rg, set())
            region_txt = ", ".join(sorted(rg_regions)) if rg_regions else "—"
            items = []
            for rtype, n in sorted(types.items(), key=lambda kv: -kv[1]):
                cls = classify_resource_type(rtype)
                items.append((
                    f"{n} x {_display_name(rtype)}",
                    f"{rtype}\nResource Group: {rg}\nRegion: {region_txt}\nCount: {n}\n"
                    f"Model: {cls['service_model']} · Pillar: {cls['business_pillar']}",
                    _icon_path(rtype),
                ))
            w, h = _group_dims(len(items))
            if x_cursor + w > page_right and x_cursor > PAGE_MARGIN:
                x_cursor = PAGE_MARGIN
                row_y += row_max_h + PAD * 2
                row_max_h = 0
            _layout_group(page, f"{rg}  ·  {region_txt}", items,
                          ("#2E86AB", "#EAF3FA"), x_cursor, row_y)
            x_cursor += w + PAD * 2
            row_max_h = max(row_max_h, h)
        pages.append(page)
    return pages


def write_drawio(scan_data: dict, output_path: str) -> None:
    """Build the multi-page .drawio file and write it to output_path."""
    logger.info(f"Building draw.io diagram: {output_path}")

    sm_page = _page_group_by(scan_data, "ati-servicemodel", "Service Model", "service_model")
    pillar_page = _page_group_by(scan_data, "ati-pillar", "Business Pillar", "business_pillar")
    network_page = _page_network(scan_data)
    resource_pages = _pages_resources(scan_data)

    nav = [(sm_page.id, sm_page.name), (pillar_page.id, pillar_page.name)]
    if network_page:
        nav.append((network_page.id, network_page.name))
    nav += [(p.id, f"Resources · {p.name}") for p in resource_pages[:12]]
    overview = _page_overview(scan_data, nav)

    all_pages = [overview, sm_page, pillar_page]
    if network_page:
        all_pages.append(network_page)
    all_pages += resource_pages
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<mxfile host="AzureTenantInsights" type="device" version="1.0">'
           + "".join(p.to_xml() for p in all_pages)
           + '</mxfile>')

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml)
    logger.info(f"draw.io diagram saved: {output_path} ({len(all_pages)} pages)")
