"""
"Engine Reference — Studio Metaphor" pitch PDF.

The sales leave-behind: maps the engine onto a DAW / mastering-studio signal
chain (raw take -> console -> rack -> master), with metaphor cards, a
transport-controls/API table with Active/Planned status, execution + mental
model panels, and a "why teams buy it" section — all on the shared report kit
so it matches every other NgineAgent artifact.

Served at GET /pitch.pdf; pure reportlab so it renders per-request on the VPS.
"""

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Flowable, Paragraph, Spacer, Table, TableStyle

from .report_kit import (
    BRAND,
    CONTENT_W,
    GRIDC,
    INK,
    MUTED,
    SLATE,
    TEAL,
    TEAL_DK,
    ZEBRA,
    Pill,
    build_document,
    hero_block,
    kit_styles,
    now_utc,
    panel,
    section,
    table_block,
)

_STAGES = [
    ("RAW TAKE", "Upload", "CSV / XLSX catalog, as recorded"),
    ("CONSOLE", "Validate", "every field gets a channel strip"),
    ("RACK", "Correct", "deterministic fixes, like plugins"),
    ("MASTER", "Bounce = Export", "CSV · XLSX · branded PDF"),
]

# the same pipeline, no metaphor — what a technical diligence reader wants to see
_LITERAL_STAGES = [
    ("HTTP API", "FastAPI", "multipart upload, JSON + file responses"),
    ("VALIDATORS", "Schema + rule packs", "per-domain JSON, regex + required"),
    ("CORRECTORS", "Worksheet apply", "reviewed fixes merged onto the take"),
    ("EXPORTERS", "csv · xlsx · pdf", "pandas / openpyxl / reportlab"),
]

_MAPPING = [
    ("Console", "Validation engine", "Schema + domain rules, per field"),
    ("Channel strips", "Field validators", "One strip per column"),
    ("Meters", "Severity findings", "HIGH red · MEDIUM amber · LOW blue"),
    ("Effects rack", "Correctors", "Auto-fix worksheet, then apply"),
    ("Master bus", "Health score", "0–100 acceptance grade per run"),
    ("Presets", "Domain packs", "music · healthcare · comms · accounting · inspection"),
]

_TRANSPORT = [
    ("Record", "Load a take (file upload)", "POST /validation/validate", "Active"),
    ("Mix", "Build the fix worksheet (CSV)", "POST /validation/worksheet", "Active"),
    ("Process", "Apply the rack — fixes onto the take", "POST /correction/apply", "Active"),
    ("Bounce", "Export the master (CSV / XLSX / PDF)", "POST /export/file", "Active"),
    ("Print", "Validation report (branded PDF)", "POST /validation/report", "Active"),
    ("A/B", "Original vs corrected, side by side", "original + correction columns", "Active"),
    ("Loop", "Scheduled re-scan + drift detection", "recurring runs", "Planned"),
    ("Punch-in", "Re-validate only the rows you touched", "row-scoped runs", "Planned"),
]

_EXEC_MODEL = [
    ("Ordering", "Deterministic per run"),
    ("State", "Stateless HTTP · per-run artifacts"),
    ("Concurrency", "Parallel runs, isolated Run IDs"),
    ("Scaling", "Share-nothing: add processes"),
]

_MENTAL_MODEL = [
    ("You get", "A mastering studio for data"),
    ("Scale", "Any CSV / XLSX catalog"),
    ("Extension", "New domain presets"),
    ("Output", "Procurement-ready masters"),
]


class SignalChain(Flowable):
    """A four-stage boxed pipeline with arrows between stages."""

    BOX_H = 58
    ARROW_W = 24

    def __init__(self, stages=None):
        super().__init__()
        self.stages = stages if stages is not None else _STAGES
        self.width = CONTENT_W

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        return availWidth, self.BOX_H

    def draw(self):
        c = self.canv
        n = len(self.stages)
        box_w = (self.width - self.ARROW_W * (n - 1)) / n
        x = 0.0
        for i, (title, mid, caption) in enumerate(self.stages):
            c.setFillColor(colors.white)
            c.setStrokeColor(GRIDC)
            c.setLineWidth(0.9)
            c.roundRect(x, 0, box_w, self.BOX_H, 8, stroke=1, fill=1)
            # teal top accent
            c.setFillColor(TEAL)
            c.roundRect(x, self.BOX_H - 4, box_w, 4, 2, stroke=0, fill=1)

            cx = x + box_w / 2
            c.setFillColor(TEAL_DK)
            c.setFont("Helvetica-Bold", 8.5)
            c.drawCentredString(cx, self.BOX_H - 19, title)
            c.setFillColor(INK)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(cx, self.BOX_H - 32, mid)
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 6.3)
            c.drawCentredString(cx, self.BOX_H - 44, caption)

            if i < n - 1:
                ax = x + box_w + self.ARROW_W / 2
                ay = self.BOX_H / 2
                c.setStrokeColor(TEAL)
                c.setLineWidth(1.6)
                c.line(x + box_w + 5, ay, ax + 4, ay)
                c.setFillColor(TEAL)
                p = c.beginPath()
                p.moveTo(ax + 9, ay)
                p.lineTo(ax + 3, ay + 3.5)
                p.lineTo(ax + 3, ay - 3.5)
                p.close()
                c.drawPath(p, stroke=0, fill=1)
            x += box_w + self.ARROW_W


def _metaphor_cards(st: dict) -> list:
    """The what-maps-to-what grid: two rows of three centered cards."""
    title_s = ParagraphStyle("mc-t", fontName="Helvetica-Bold", fontSize=9, leading=12,
                             textColor=TEAL_DK, alignment=TA_CENTER)
    mid_s = ParagraphStyle("mc-m", fontName="Helvetica-Bold", fontSize=8, leading=11,
                           textColor=INK, alignment=TA_CENTER)
    cap_s = ParagraphStyle("mc-c", fontName="Helvetica", fontSize=6.5, leading=9,
                           textColor=MUTED, alignment=TA_CENTER)
    gap = 8
    card_w = (CONTENT_W - 2 * gap) / 3

    def card(title, mid, caption):
        t = Table(
            [[Paragraph(title, title_s)], [Paragraph(mid, mid_s)], [Paragraph(caption, cap_s)]],
            colWidths=[card_w],
        )
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.8, GRIDC),
            ("ROUNDEDCORNERS", [8, 8, 8, 8]),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (0, 0), 9),
            ("TOPPADDING", (0, 1), (0, -1), 2),
            ("BOTTOMPADDING", (0, -1), (0, -1), 9),
        ]))
        return t

    rows = []
    for start in (0, 3):
        trio = _MAPPING[start:start + 3]
        cells, widths = [], []
        for j, (title, mid, caption) in enumerate(trio):
            cells.append(card(title, mid, caption))
            widths.append(card_w)
            if j < 2:
                cells.append("")
                widths.append(gap)
        row = Table([cells], colWidths=widths)
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        rows.append(row)
        rows.append(Spacer(1, gap))
    return rows[:-1]


def _model_panels(st: dict) -> Table:
    """Execution Model and Mental Model, side by side."""
    label_s = ParagraphStyle("mp-l", fontName="Helvetica", fontSize=8, leading=12, textColor=SLATE)
    value_s = ParagraphStyle("mp-v", fontName="Courier-Bold", fontSize=7.5, leading=12, textColor=INK)
    head_s = st["section"]
    gap = 10
    panel_w = (CONTENT_W - gap) / 2
    inner_w = panel_w - 24

    def model(title, pairs):
        body = [[Paragraph(title, head_s), ""]]
        for k, v in pairs:
            body.append([Paragraph(k, label_s), Paragraph(v, value_s)])
        t = Table(body, colWidths=[inner_w * 0.38, inner_w * 0.62])
        t.setStyle(TableStyle([
            ("SPAN", (0, 0), (1, 0)),
            ("LINEBELOW", (0, 1), (-1, -2), 0.5, ZEBRA),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, 0), 0),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ]))
        wrap = Table([[t]], colWidths=[panel_w])
        wrap.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.8, GRIDC),
            ("ROUNDEDCORNERS", [8, 8, 8, 8]),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        return wrap

    row = Table(
        [[model("EXECUTION MODEL", _EXEC_MODEL), "", model("MENTAL MODEL", _MENTAL_MODEL)]],
        colWidths=[panel_w, gap, panel_w],
    )
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return row


def build_pitch_pdf() -> bytes:
    st = kit_styles()
    mono_s = ParagraphStyle("api", fontName="Courier", fontSize=7.5, leading=10, textColor=INK)

    story = []

    # hero
    story.append(hero_block(
        "ENGINE REFERENCE · STUDIO METAPHOR", "blue",
        "A Mastering Studio for Data",
        [
            f"{BRAND} runs your catalog through a studio-grade signal chain: load the raw take, "
            "scan it on the console, process it through the correction rack, and bounce a "
            "procurement-ready master — your corrected CSV / XLSX / branded-PDF export.",
            f"5 domain presets · HTTP API · branded PDF artifacts · generated {now_utc()}",
        ],
        None, st,
    ))
    story.append(Spacer(1, 16))

    # signal chain (metaphor)
    story.append(section(
        "The signal chain", st,
        SignalChain(),
        Spacer(1, 6),
        Paragraph(
            "Every run is a session: the same take through the same chain produces the same "
            "master, every time — with a Run ID on every artifact for the audit trail.",
            st["small"],
        ),
    ))
    story.append(Spacer(1, 16))

    # the same pipeline, literally
    story.append(section(
        "Under the hood — the literal pipeline", st,
        SignalChain(_LITERAL_STAGES),
        Spacer(1, 6),
        Paragraph(
            "Same four stages, no metaphor: a FastAPI service, per-domain JSON schema + rule "
            "packs, a worksheet-based correction pass, and pandas / openpyxl / reportlab "
            "exporters. No browser, no GPU, no queue, no external calls.",
            st["small"],
        ),
        Spacer(1, 4),
        Paragraph(
            "<b>\"Branded PDF\" means:</b> your company name, URL, accent colors and optional logo "
            "on every artifact's letterhead, footer and accents — configured once in branding.json, "
            "not hardcoded. Rendering is pure reportlab; there is no headless Chrome to maintain.",
            st["small"],
        ),
    ))
    story.append(Spacer(1, 16))

    # metaphor mapping
    story.append(section("Studio metaphor — what maps to what", st, *_metaphor_cards(st)))
    story.append(Spacer(1, 16))

    # transport controls
    transport_rows = []
    for control, action, api, status in _TRANSPORT:
        transport_rows.append([
            control,
            action,
            Paragraph(api, mono_s),
            Pill(status, "green" if status == "Active" else "amber"),
        ])
    story.append(section(
        "Transport controls", st,
        table_block(
            [("Control", 0.9), ("Studio action", 2.2), ("API", 2.2), ("Status", 0.8)],
            transport_rows, st, font_size=8,
        ),
    ))
    story.append(Spacer(1, 16))

    # severity model — how findings are assigned, scored, and gate acceptance
    sev_rows = [
        [Pill("HIGH · P1", "red"), "Required value missing, or a HIGH-severity format rule fails",
         "−6 points each", "Blocks acceptance; grade capped at ACTION REQUIRED"],
        [Pill("MEDIUM · P2", "amber"), "A MEDIUM-severity format or domain rule fails",
         "−1 point each", "Fix within the 7-day cycle"],
        [Pill("LOW · P3", "blue"), "Low-impact or cosmetic rule fails",
         "−1 point each", "Tracked; does not gate"],
    ]
    story.append(section(
        "Severity model — assignment, scoring, acceptance", st,
        table_block(
            [("Severity", 1.0), ("Assigned when", 2.4), ("Score impact", 1.1), ("Acceptance effect", 2.2)],
            sev_rows, st, font_size=8,
        ),
        Spacer(1, 5),
        Paragraph(
            "<b>Score:</b> start at 100; subtract 6 per Critical finding and 1 per Medium or Low "
            "finding; floor at 0. Formula: Score = max(0, 100 − (6 × critical) − (1 × medium) − (1 × low)).",
            st["small"],
        ),
        Paragraph(
            "<b>Worked example:</b> 1 Critical + 2 Medium → 100 − 6 − 1 − 1 = <b>92</b>, but the open "
            "Critical caps the grade at ACTION REQUIRED. Fix the Critical and re-run: "
            "100 − 0 − 1 − 1 = <b>98</b> → <b>HEALTHY</b>.",
            st["small"],
        ),
        Paragraph(
            "Severities come from the preset schema per field — never heuristics — so the same data "
            "always grades the same. Cross-reference: the inspection preset grades an unknown condition "
            "value (e.g. \"utmarkt\") HIGH and a malformed date MEDIUM, every run, deterministically.",
            st["small"],
        ),
    ))
    story.append(Spacer(1, 16))

    # execution / mental model
    story.append(_model_panels(st))
    story.append(Spacer(1, 16))

    # performance envelope (measured, not estimated)
    story.append(section(
        "Performance envelope & deployment footprint (measured)", st,
        panel([
            Paragraph("• Validate a 1,000-row catalog: <b>~60 ms</b>. A 100-row take: <b>~7 ms</b>.", st["small"]),
            Paragraph("• Bounce a 100-row branded PDF master: <b>&lt;100 ms</b>; CSV / XLSX faster still.", st["small"]),
            Paragraph("• Production service footprint: <b>~70 MB RSS</b> (measured live), cold start under 2 s, one CPU core per request.", st["small"]),
            Paragraph("• Scaling path: <b>single worker → N uvicorn workers → N hosts</b>, partitioned by Run ID. Runs share nothing, so there is no state to migrate and no coordination layer to add.", st["small"]),
            Paragraph("• Dependencies: 8 pinned, pure-Python packages (FastAPI, uvicorn, pandas, openpyxl, reportlab, pydantic, numpy, python-multipart). Deploys as one systemd unit behind nginx; containerizes trivially.", st["small"]),
        ]),
    ))
    story.append(Spacer(1, 16))

    # extensibility — the #1 diligence question
    story.append(section(
        "Extending the engine — new domain presets", st,
        panel([
            Paragraph("<b>1. Drop a schema.</b> One JSON file: required columns, regex patterns, severities, messages (schemas/&lt;domain&gt;_schema.json).", st["small"]),
            Paragraph("<b>2. Add a rule pack (optional).</b> Domain-specific checks beyond format — same JSON convention (rules/&lt;domain&gt;_rules.json).", st["small"]),
            Paragraph("<b>3. Done.</b> The preset appears across the API, dashboard and every report — zero engine-code changes. The pytest suite covers the validate → correct → export round trip.", st["small"]),
            Paragraph("<b>Rule-set isolation:</b> presets are self-contained JSON. Adding or editing one cannot change the behavior of any other domain — integration risk stays local.", st["small"]),
        ]),
    ))
    story.append(Spacer(1, 16))

    # versioning + governance
    story.append(section(
        "Preset versioning & ruleset governance", st,
        panel([
            Paragraph("<b>Versioning.</b> Every schema and rule pack carries a <b>version</b> field (year.month.rev, e.g. 2026.06.1) and lives in git. Additive changes bump the revision; breaking changes bump year.month. Every report stamps the preset + schema + rules versions it ran with, so historical artifacts stay reproducible against their exact ruleset.", st["small"]),
            Paragraph("<b>Adding a rule.</b> A rule change is a pull request: the JSON edit + a seeded demo take that exercises it + the pytest round trip (validate → correct → export). Nothing ships untested.", st["small"]),
            Paragraph("<b>Deploying.</b> Rules deploy as files with a service restart; rollback is a git revert. No migrations, no downtime windows.", st["small"]),
            Paragraph("<b>Deprecating.</b> Retired presets stay in git history; artifacts produced under them remain verifiable forever.", st["small"]),
        ]),
    ))
    story.append(Spacer(1, 16))

    # determinism + failure modes
    story.append(section(
        "Deterministic replay & error model", st,
        panel([
            Paragraph("<b>Replay.</b> Same take + same preset version = identical findings, worksheet and master. Schemas and rule packs are versioned JSON in git; every artifact carries its Run ID, so any past result can be reproduced and audited.", st["small"]),
            Paragraph("<b>Post-remediation.</b> Fix the flagged rows and re-run the same file: the score recalculates automatically and cleared findings drop from the report. No manual clearing, no state to reset.", st["small"]),
            Paragraph("<b>Malformed upload</b> → HTTP 400 with the parse error — never a crash.", st["small"]),
            Paragraph("<b>Missing required columns</b> → reported as HIGH findings in the run, not an exception.", st["small"]),
            Paragraph("<b>Unknown domain</b> → falls back to the base schema and still validates structure.", st["small"]),
            Paragraph("<b>Correction conflicts</b> → HTTP 400 with the reason; the original take is never modified in place.", st["small"]),
            Paragraph("<b>Telemetry.</b> Every request, latency and error is tracked and visible live on the dashboard.", st["small"]),
        ]),
    ))
    story.append(Spacer(1, 16))

    # architecture overview — literal, component by component
    arch_rows = [
        ["API layer", Paragraph("api/ — FastAPI", mono_s), "4 endpoints, multipart in, JSON / file out; telemetry middleware on every request"],
        ["Services", Paragraph("services/", mono_s), "validate · generate_worksheet · apply_corrections · export — thin orchestration over core"],
        ["Validators", Paragraph("core/validators/", mono_s), "schema-driven required + format checks; domain validators add vertical logic (e.g. royalty gaps)"],
        ["Correctors", Paragraph("core/correctors/", mono_s), "merge reviewed worksheet corrections onto the take; original never modified in place"],
        ["Exporters", Paragraph("core/exporters/", mono_s), "csv / xlsx / branded PDF on a shared report kit (pure reportlab)"],
        ["Presets", Paragraph("schemas/ + rules/", mono_s), "versioned JSON, one pair per domain; loaded per request, isolated per domain"],
        ["Runtime", Paragraph("systemd + nginx", mono_s), "one uvicorn unit behind TLS (Let's Encrypt); console behind basic auth"],
    ]
    story.append(section(
        "Architecture overview (literal)", st,
        table_block(
            [("Component", 1.0), ("Where", 1.3), ("Responsibility", 3.4)],
            arch_rows, st, font_size=8,
        ),
    ))
    story.append(Spacer(1, 16))

    # security & compliance posture
    story.append(section(
        "Security & compliance posture", st,
        panel([
            Paragraph("• <b>No external calls</b> during validation, correction or export — the chain runs entirely in-process.", st["small"]),
            Paragraph("• <b>No customer data retained.</b> Uploads are processed in memory per request; artifacts are returned to the caller, not stored.", st["small"]),
            Paragraph("• <b>Telemetry, precisely:</b> request counts, latency and error rate per endpoint — no row-level data, no PII, held in memory only until process restart. Disable entirely with TELEMETRY_ENABLED=false.", st["small"]),
            Paragraph("• <b>Data residency by construction.</b> The engine runs entirely on your infrastructure; nothing leaves the host. GDPR-friendly: no PII storage means no retention schedule to manage.", st["small"]),
            Paragraph("• <b>Transport & access.</b> TLS via nginx + Let's Encrypt; the console and API sit behind HTTP basic auth; the marketing surface is the only public path.", st["small"]),
            Paragraph("• <b>Auditability.</b> Run ID + preset/schema/rules versions on every artifact — any result can be traced to the exact code and rules that produced it.", st["small"]),
            Paragraph("• <b>Supply chain.</b> 8 pinned, widely-audited pure-Python dependencies; no browser, no GPU, no queue, no database.", st["small"]),
        ]),
    ))
    story.append(Spacer(1, 16))

    # why this is hard to build
    story.append(section(
        "Why this is hard to build", st,
        panel([
            Paragraph("• <b>The artifact chain is the product.</b> Validation is easy; a deterministic, procurement-grade evidence chain (report → worksheet → corrected master, all version-stamped and replayable) is what compliance teams actually accept — and what takes the engineering discipline.", st["small"]),
            Paragraph("• <b>The rule packs are distilled domain knowledge.</b> Five presets encode the working vocabulary of five live vertical products: ISRC/ISWC/IPI and §507(b) statute logic (music), CARC/RARC/NPI/CPT (healthcare claims), CIP channel findings (comms), SIE/BAS double-entry conventions (Swedish accounting), besiktningsprotokoll condition scales (inspection). That's operator knowledge, not just code.", st["small"]),
            Paragraph("• <b>Print-grade branded PDFs without a browser.</b> The report kit renders score rings, gauges and finding cards in pure reportlab — no headless Chrome fleet to babysit, which is what makes per-request rendering on a 70 MB service possible.", st["small"]),
            Paragraph("• <b>Determinism is a constraint, not a feature flag.</b> No model calls, no clocks in the logic, no hidden state — kept honest across every preset by the test suite.", st["small"]),
        ]),
    ))
    story.append(Spacer(1, 16))

    # integration plan
    story.append(section(
        "Integration plan (30–60 days)", st,
        panel([
            Paragraph("<b>Days 1–7 — Deploy & smoke.</b> Stand up the unit (VPS or container), run the bundled demo kit: all five presets through the full chain in one command, artifacts compared against known-good output.", st["small"]),
            Paragraph("<b>Days 8–21 — Map your data.</b> Point your catalog exports at an existing preset, or author your own schema + rule pack (JSON only). Pilot on real files; tune severities with your compliance owner.", st["small"]),
            Paragraph("<b>Days 22–45 — Wire the pipeline.</b> Integrate the four endpoints into your intake flow; stand up the operator worksheet loop for corrections that need human review.", st["small"]),
            Paragraph("<b>Days 46–60 — Gate & monitor.</b> Make the score an acceptance gate in your procurement/release workflow; schedule re-scans; watch the dashboard telemetry.", st["small"]),
            Paragraph("Typical effort: one engineer, part-time. There is no data migration — the engine is stateless by design.", st["small"]),
        ]),
    ))
    story.append(Spacer(1, 16))

    # why teams buy it
    story.append(section(
        "Why teams buy it", st,
        panel([
            Paragraph("• <b>Deterministic.</b> Same take in, same master out — no model drift, no surprises in re-runs.", st["small"]),
            Paragraph("• <b>Evidence on every run.</b> Validation report, fix worksheet, corrected master and audit trail — each carrying the Run ID.", st["small"]),
            Paragraph("• <b>Preset-extensible.</b> A new vertical is a new schema + rule pack, not a rewrite — five presets shipped, more on request.", st["small"]),
            Paragraph("• <b>Light footprint, real scale.</b> Pure Python, stateless — one VPS today, horizontal scale by adding processes, because runs share nothing.", st["small"]),
        ]),
    ))

    subtitle = f"engine reference · studio metaphor · {now_utc()}"
    return build_document("Engine Reference", subtitle, story)
