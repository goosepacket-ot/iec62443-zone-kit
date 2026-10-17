"""Data model and loaders for the zone & conduit kit.

Inputs:
  * assets CSV   — one row per device, columns: name, ip, zone, level, criticality, type, notes
  * flows YAML   — the allowed communication baseline (list of src/dst/protocol/purpose)

Everything downstream (zones, conduits, diagrams, firewall matrix, FR assessment) is built from these two.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from typing import Optional

import yaml

# Purdue reference model levels — used when an asset gives a level but no explicit zone.
PURDUE = {
    "0": "Level 0 — Process (field I/O, sensors, actuators)",
    "1": "Level 1 — Basic control (PLC, RTU, IED)",
    "2": "Level 2 — Supervisory control (SCADA, HMI, engineering)",
    "3": "Level 3 — Operations (historian, MES, OT servers)",
    "3.5": "Level 3.5 — Industrial DMZ",
    "4": "Level 4 — Enterprise (business network)",
    "5": "Level 5 — Enterprise / internet",
}

# Criticality → suggested target security level (SL-T). A starting point for discussion, not a verdict.
CRIT_TO_SL = {"low": 1, "medium": 2, "high": 3, "safety": 4}


@dataclass
class Asset:
    name: str
    ip: str = ""
    zone: str = ""
    level: str = ""
    criticality: str = "medium"
    type: str = ""
    notes: str = ""

    def zone_name(self) -> str:
        if self.zone:
            return self.zone
        if self.level in PURDUE:
            return PURDUE[self.level].split(" — ")[0]
        return "Unassigned"


@dataclass
class Flow:
    src: str          # zone name or asset name
    dst: str
    protocol: str = ""
    port: str = ""
    purpose: str = ""
    direction: str = "unidirectional"   # unidirectional | bidirectional

    def key(self):
        return (self.src, self.dst, self.protocol, self.port)


@dataclass
class Zone:
    name: str
    assets: list = field(default_factory=list)
    level: str = ""
    criticality: str = "medium"

    @property
    def sl_t(self) -> int:
        return max((CRIT_TO_SL.get(a.criticality.lower(), 2) for a in self.assets), default=CRIT_TO_SL.get(self.criticality.lower(), 2))


@dataclass
class Conduit:
    src_zone: str
    dst_zone: str
    flows: list = field(default_factory=list)

    def key(self):
        return tuple(sorted((self.src_zone, self.dst_zone)))


def load_assets(path: str) -> list[Asset]:
    out = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            if not row.get("name"):
                continue
            out.append(Asset(name=row["name"], ip=row.get("ip", ""), zone=row.get("zone", ""),
                             level=row.get("level", ""), criticality=row.get("criticality", "medium") or "medium",
                             type=row.get("type", ""), notes=row.get("notes", "")))
    return out


def load_flows(path: str) -> list[Flow]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    raw = data.get("flows", data) if isinstance(data, dict) else data
    out = []
    for item in raw or []:
        out.append(Flow(src=str(item.get("src", item.get("from", ""))),
                        dst=str(item.get("dst", item.get("to", ""))),
                        protocol=str(item.get("protocol", item.get("proto", ""))),
                        port=str(item.get("port", "")),
                        purpose=str(item.get("purpose", "")),
                        direction=str(item.get("direction", "unidirectional"))))
    return [f for f in out if f.src and f.dst]
