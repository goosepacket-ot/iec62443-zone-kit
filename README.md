# iec62443-zone-kit

**Turn an asset list and an allowed-flow baseline into an IEC 62443 zone & conduit model — with a segmentation diagram, a firewall rule matrix and a foundational-requirement checklist.**

Segmentation is the heart of IEC 62443, but the first draft is almost always done by hand: a spreadsheet of assets, a whiteboard of zones, and a lot of arguing about what should talk to what. This kit takes the two things you already have — **who the assets are** and **which flows are actually allowed** — and generates the rest:

- a **zone & conduit model** grouped by zone or Purdue level, with a suggested **SL-T** per zone;
- a **segmentation diagram** (Mermaid, rendered in the HTML report, plus Graphviz DOT);
- a **firewall rule matrix** (one ALLOW row per approved flow, ending in an explicit default-DENY);
- a **foundational-requirement (FR1–FR7) checklist** in plain language, pre-filled from what the model can see.

```
$ zonekit build assets.csv flows.yaml --out model/
6 zones, 5 conduits, 10 flows
outputs: model/zones.mmd, model/zones.dot, model/firewall-rules.csv, model/report.md, model/report.html, model/model.json
```

See a rendered example in [`docs/example-model/`](docs/example-model/), built from [`examples/`](examples/).

> This is a **working model to drive an assessment, not a certification**. SL-T values are a starting suggestion from asset criticality; confirm zones, conduits and SL-T with a formal IEC 62443-3-2 risk assessment.

## Why I built it

After 5+ years in OT networking I have drawn the same Purdue diagram a hundred times. The segmentation is never the hard part — capturing the *allowed flows* and then proving the firewall matches them is. This kit makes the allowed-flow list the single source of truth: the diagram, the firewall rules and the FR5 evidence all fall out of the same YAML, so when a flow changes you regenerate everything instead of editing three documents and hoping they agree.

## Install

```bash
git clone https://github.com/goosepacket/iec62443-zone-kit
cd iec62443-zone-kit
pip install -e .
```

Python 3.9+ and PyYAML (its only dependency).

## Inputs

**`assets.csv`** — one row per device:

| column | meaning |
|---|---|
| `name` | device name (required) |
| `ip` | IP address |
| `zone` | explicit zone name; if blank, the Purdue `level` is used instead |
| `level` | Purdue level: `0`,`1`,`2`,`3`,`3.5`,`4`,`5` |
| `criticality` | `low` / `medium` / `high` / `safety` → drives the suggested SL-T |
| `type` | PLC, RTU, HMI, SCADA, Server… |
| `notes` | free text |

**`flows.yaml`** — the allowed communication baseline. Anything not listed is denied in the generated matrix:

```yaml
flows:
  - src: SCADA-Server          # an asset name, an IP, or a zone name
    dst: Field-IO-1
    protocol: Modbus/TCP
    port: "502"
    purpose: Poll and command line 1 PLC
    direction: bidirectional   # or unidirectional
```

## Outputs

| File | Contents |
|---|---|
| `report.html` | Full report — zones, SL-T, **rendered Mermaid diagram**, firewall matrix, FR1–FR7 checklist |
| `report.md` | The same in Markdown (with a ```mermaid``` block) for your assessment document |
| `zones.mmd` / `zones.dot` | Diagram sources — paste into mermaid.live, or `dot -Tpng zones.dot -o zones.png` |
| `firewall-rules.csv` | ALLOW row per flow + a final default-DENY — the basis for the ruleset |
| `model.json` | The whole model, structured |

## What the FR checklist does (and doesn't) do

It pre-fills the IEC 62443-3-3 foundational requirements from what the inputs reveal, and marks each `gap` / `partial` / `review`:

- **FR5 (restricted data flow)** — `partial` once zones and conduits exist; `gap` if everything lands in one flat zone. It also warns when enterprise and OT have a conduit but there is **no Level 3.5 industrial DMZ** between them.
- **FR4 (data confidentiality)** — `gap` if no flow uses an encrypted transport; `partial` otherwise.
- **FR1, FR2, FR3, FR6, FR7** — left as `review` with a specific prompt, because they can't be judged from a flow list alone (they need device config, logging and redundancy evidence you bring to the assessment).

The tool is deliberately honest here: it won't tell you you're compliant. It gives you the scaffolding and the right questions.

## How SL-T is suggested

Each zone's suggested SL-T is the **highest** of its assets' criticalities: `low→1`, `medium→2`, `high→3`, `safety→4`. So a safety PLC pulls its zone to SL-T 4. This is a conversation starter for the IEC 62443-3-2 risk assessment, not its conclusion.

## Development

```bash
pip install -e ".[dev]"
pytest -q
```

CI runs on Python 3.9–3.12 (`.github/workflows/ci.yml`).

## License

MIT — see [LICENSE](LICENSE).
