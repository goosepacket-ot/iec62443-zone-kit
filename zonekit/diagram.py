"""Render the zone & conduit model as Mermaid and Graphviz DOT."""
from __future__ import annotations

import re

from .model import Conduit, Zone


def _id(name: str) -> str:
    return "z_" + re.sub(r"[^A-Za-z0-9]", "_", name)


def mermaid(zones: dict[str, Zone], conduits: list[Conduit]) -> str:
    L = ["graph TD"]
    for z in sorted(zones.values(), key=lambda z: z.name):
        L.append(f'  subgraph {_id(z.name)}["{z.name}  (SL-T {z.sl_t})"]')
        for a in z.assets:
            L.append(f'    {_id(z.name)}_{_id(a.name)}["{a.name}<br/>{a.ip}"]')
        L.append("  end")
    for c in conduits:
        label = ", ".join(sorted({f.protocol for f in c.flows if f.protocol})) or "see rules"
        L.append(f'  {_id(c.src_zone)} ==>|"{label}"| {_id(c.dst_zone)}')
    return "\n".join(L)


def dot(zones: dict[str, Zone], conduits: list[Conduit]) -> str:
    L = ["digraph zones {", "  rankdir=TB;", '  node [shape=box, style="rounded,filled", fillcolor="#eef3f8", fontname="Helvetica"];',
         '  graph [fontname="Helvetica"]; edge [fontname="Helvetica", penwidth=2];']
    for z in sorted(zones.values(), key=lambda z: z.name):
        L.append(f'  subgraph cluster_{_id(z.name)} {{')
        L.append(f'    label="{z.name}  (SL-T {z.sl_t})"; style="rounded"; color="#4a6fa5";')
        for a in z.assets:
            L.append(f'    "{a.name}" [label="{a.name}\\n{a.ip}"];')
        L.append("  }")
    for c in conduits:
        label = ", ".join(sorted({f.protocol for f in c.flows if f.protocol})) or "see rules"
        src = c.flows[0].src if c.flows else c.src_zone
        dst = c.flows[0].dst if c.flows else c.dst_zone
        # anchor the edge on representative assets if the endpoints are assets, else cluster labels
        L.append(f'  "{_anchor(c, zones, True)}" -> "{_anchor(c, zones, False)}" [label="{label}", color="#c0392b"];')
    L.append("}")
    return "\n".join(L)


def _anchor(c: Conduit, zones: dict[str, Zone], src: bool) -> str:
    zname = c.src_zone if src else c.dst_zone
    z = zones.get(zname)
    if z and z.assets:
        return z.assets[0].name
    return zname
