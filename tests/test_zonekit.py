import os

import pytest

from zonekit.build import assess, build_conduits, build_zones, firewall_matrix
from zonekit.diagram import dot, mermaid
from zonekit.model import Asset, Flow, load_assets, load_flows
from zonekit.report import assemble, write_all

EX = os.path.join(os.path.dirname(__file__), "..", "examples")


@pytest.fixture(scope="module")
def model():
    assets = load_assets(os.path.join(EX, "assets.csv"))
    flows = load_flows(os.path.join(EX, "flows.yaml"))
    return assemble(assets, flows, source="assets.csv")


def test_assets_and_flows_load(model):
    assert len(model["zones"]) == 6
    assert len(model["flows"]) == 10


def test_safety_zone_gets_highest_slt(model):
    sl = {s["zone"]: s["suggested_sl_t"] for s in model["sl"]}
    assert sl["Safety"] == 4                      # safety criticality -> SL-T 4
    assert sl["Enterprise (L4)"] == 2


def test_conduits_cross_zone_only(model):
    for c in model["conduits"]:
        assert c.src_zone != c.dst_zone


def test_no_direct_enterprise_to_control_conduit(model):
    pairs = {tuple(sorted((c.src_zone, c.dst_zone))) for c in model["conduits"]}
    assert ("Enterprise (L4)", "Process (L0-L1)") not in pairs
    # enterprise only reaches the DMZ
    ent = [c for c in model["conduits"] if "Enterprise (L4)" in (c.src_zone, c.dst_zone)]
    assert ent and all("Industrial DMZ" in (c.src_zone, c.dst_zone) for c in ent)


def test_firewall_matrix_ends_with_default_deny(model):
    assert model["matrix"][-1]["action"] == "DENY"
    assert all(r["action"] == "ALLOW" for r in model["matrix"][:-1])


def test_assessment_has_all_seven_frs(model):
    frs = [a["fr"] for a in model["assessment"]]
    assert frs == ["FR1", "FR2", "FR3", "FR4", "FR5", "FR6", "FR7"]


def test_fr5_partial_when_dmz_and_conduits_present(model):
    fr5 = next(a for a in model["assessment"] if a["fr"] == "FR5")
    assert fr5["status"] == "partial"


def test_flat_network_flags_fr5_gap():
    assets = [Asset("a", "1.1.1.1", zone="Flat"), Asset("b", "1.1.1.2", zone="Flat")]
    flows = [Flow("a", "b", "Modbus/TCP", "502")]
    m = assemble(assets, flows)
    fr5 = next(a for a in m["assessment"] if a["fr"] == "FR5")
    assert fr5["status"] == "gap"


def test_diagrams_render(model):
    mmd = mermaid(model["zones"], model["conduits"])
    assert mmd.startswith("graph TD") and "subgraph" in mmd
    d = dot(model["zones"], model["conduits"])
    assert d.startswith("digraph") and "cluster_" in d


def test_write_all(model, tmp_path):
    paths = write_all(model, str(tmp_path))
    names = {os.path.basename(p) for p in paths}
    assert names == {"zones.mmd", "zones.dot", "firewall-rules.csv", "report.md", "report.html", "model.json"}
    for p in paths:
        assert os.path.getsize(p) > 0
    html = open(os.path.join(str(tmp_path), "report.html")).read()
    assert "mermaid" in html and "Foundational requirements" in html
