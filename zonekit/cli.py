"""Command line: zonekit build assets.csv flows.yaml --out model/"""
from __future__ import annotations

import argparse
import sys

from . import __version__
from .model import load_assets, load_flows
from .report import assemble, write_all


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="zonekit",
                                 description="Build an IEC 62443 zone & conduit model from an asset list and an allowed-flow baseline.")
    ap.add_argument("--version", action="version", version=f"zonekit {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="build the model and write all outputs")
    b.add_argument("assets", help="assets CSV (name, ip, zone, level, criticality, type, notes)")
    b.add_argument("flows", help="allowed-flows YAML")
    b.add_argument("--out", default="zone-model", help="output directory (default: zone-model)")
    b.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    assets = load_assets(args.assets)
    flows = load_flows(args.flows)
    model = assemble(assets, flows, source=args.assets)
    paths = write_all(model, args.out)
    if not args.quiet:
        print(f"{len(model['zones'])} zones, {len(model['conduits'])} conduits, {len(flows)} flows")
        gaps = [a for a in model["assessment"] if a["status"] == "gap"]
        for g in gaps:
            print(f"  [GAP] {g['fr']} {g['title']}: {g['note']}")
        print("outputs:", ", ".join(paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
