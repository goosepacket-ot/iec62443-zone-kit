"""Turn assets + allowed flows into zones, conduits, a firewall matrix and an FR assessment."""
from __future__ import annotations

from collections import defaultdict

from .model import Asset, Conduit, Flow, Zone


def build_zones(assets: list[Asset]) -> dict[str, Zone]:
    zones: dict[str, Zone] = {}
    for a in assets:
        zn = a.zone_name()
        z = zones.setdefault(zn, Zone(name=zn, level=a.level))
        z.assets.append(a)
        if not z.level and a.level:
            z.level = a.level
    return zones


def _zone_of(name: str, assets: list[Asset], zones: dict[str, Zone]) -> str:
    """A flow endpoint may name a zone directly or an asset. Resolve to a zone name."""
    if name in zones:
        return name
    for a in assets:
        if name in (a.name, a.ip):
            return a.zone_name()
    return name  # external / unknown endpoint — kept as its own pseudo-zone


def build_conduits(flows: list[Flow], assets: list[Asset], zones: dict[str, Zone]) -> list[Conduit]:
    conduits: dict[tuple, Conduit] = {}
    for fl in flows:
        sz = _zone_of(fl.src, assets, zones)
        dz = _zone_of(fl.dst, assets, zones)
        if sz == dz:
            continue  # intra-zone traffic needs no conduit
        c = Conduit(sz, dz)
        conduits.setdefault(c.key(), Conduit(sz, dz)).flows.append(fl)
    return list(conduits.values())


def firewall_matrix(conduits: list[Conduit]) -> list[dict]:
    """One allow-rule row per distinct flow crossing a conduit."""
    rows = []
    for c in conduits:
        for fl in c.flows:
            rows.append({
                "conduit": f"{c.src_zone} <-> {c.dst_zone}",
                "action": "ALLOW",
                "source_zone": fl.src if fl.src in (c.src_zone, c.dst_zone) else c.src_zone,
                "dest_zone": fl.dst if fl.dst in (c.src_zone, c.dst_zone) else c.dst_zone,
                "protocol": fl.protocol or "any",
                "port": fl.port or "any",
                "direction": fl.direction,
                "purpose": fl.purpose,
            })
    # implicit deny is the backbone of restricted data flow — state it explicitly
    rows.append({"conduit": "*", "action": "DENY", "source_zone": "any", "dest_zone": "any",
                 "protocol": "any", "port": "any", "direction": "-", "purpose": "Default deny (implicit, logged)"})
    return rows


# ------------------------------------------------------------------ IEC 62443-3-3 foundational requirements
FR = {
    "FR1": ("Identification & authentication control",
            "Every human and device on the zone is identified and authenticated before it can act."),
    "FR2": ("Use control",
            "Authenticated users/devices are restricted to the actions (read / write / control) they are permitted."),
    "FR3": ("System integrity",
            "Integrity of data and of the control logic is protected in transit and at rest."),
    "FR4": ("Data confidentiality",
            "Information at rest and in transit is protected from disclosure where required."),
    "FR5": ("Restricted data flow",
            "The network is segmented into zones and conduits; only the approved flows cross them."),
    "FR6": ("Timely response to events",
            "Security events are detected, logged and responded to."),
    "FR7": ("Resource availability",
            "The control system remains available under load, fault and attack."),
}


def assess(zones: dict[str, Zone], conduits: list[Conduit], flows: list[Flow]) -> list[dict]:
    """A plain-language gap checklist per foundational requirement. Status is a prompt for the assessor,
    derived only from what the inputs can show — it never claims compliance on its own."""
    has_dmz = any("dmz" in z.lower() or "3.5" in (zones[z].level or "") for z in zones)
    any_crypto = any(f.protocol.lower() in ("https", "tls", "mqtts", "opcua-sign", "sftp", "ssh", "ipsec")
                     for f in flows)
    results = []
    for code, (title, desc) in FR.items():
        status, note = "review", ""
        if code == "FR5":
            if conduits:
                status, note = "partial", f"{len(zones)} zones and {len(conduits)} conduits defined; confirm the firewall enforces exactly these flows with a default-deny."
            else:
                status, note = "gap", "No cross-zone conduits derived — either everything is in one flat zone, or the baseline is incomplete."
            if not has_dmz and len(zones) > 2:
                note += " No industrial DMZ (Level 3.5) found — enterprise↔OT traffic should transit a DMZ, not flow directly."
        elif code == "FR4":
            status = "partial" if any_crypto else "gap"
            note = "Some flows use encrypted transports." if any_crypto else "No encrypted transports in the baseline — management and historian links in clear text are an FR4 gap."
        elif code == "FR1":
            note = "Confirm device/user authentication on each zone (no shared accounts, no default credentials, SNMPv3 not v1/v2c)."
        elif code == "FR2":
            note = "Confirm write/control is allow-listed per source in the conduit rules (e.g. only the SCADA zone may write to controllers)."
        elif code == "FR3":
            note = "Confirm integrity controls on control logic and GOOSE/SV where applicable (IEC 62351), and change management on PLC programs."
        elif code == "FR6":
            note = "Confirm logging/monitoring exists at each conduit (firewall logs, OT IDS) and is reviewed."
        elif code == "FR7":
            note = "Confirm redundancy / DoS resistance appropriate to the highest SL-T zone."
        results.append({"fr": code, "title": title, "description": desc, "status": status, "note": note})
    return results


def sl_summary(zones: dict[str, Zone]) -> list[dict]:
    return [{"zone": z.name, "level": z.level, "assets": len(z.assets),
             "suggested_sl_t": z.sl_t,
             "criticality": max((a.criticality for a in z.assets), key=lambda c: {"low": 0, "medium": 1, "high": 2, "safety": 3}.get(c.lower(), 1), default="medium")}
            for z in sorted(zones.values(), key=lambda z: z.name)]
