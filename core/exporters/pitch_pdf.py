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
    ("MASTER", "Bounce", "CSV · XLSX · branded PDF"),
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
    ("Record", "Load a take", "POST /validation/validate", "Active"),
    ("Mix", "Build the fix worksheet", "POST /validation/worksheet", "Active"),
    ("Process", "Run the take through the rack", "POST /correction/apply", "Active"),
    ("Bounce", "Render the master", "POST /export/file (csv · xlsx · pdf)", "Active"),
    ("Print", "Branded validation report", "POST /validation/report", "Active"),
    ("A/B", "Original vs corrected, side by side", "original + correction columns", "Active"),
    ("Loop", "Scheduled re-scan + drift detection", "recurring runs", "Planned"),
    ("Punch-in", "Re-validate only the rows you touched", "row-scoped runs", "Planned"),
]

_EXEC_MODEL = [
    ("Ordering", "Deterministic per run"),
    ("State", "Stateless HTTP · per-run artifacts"),
    ("Concurrency", "Parallel runs, isolated Run IDs"),
    ("Footprint", "Pure Python on a single VPS"),
]

_MENTAL_MODEL = [
    ("You get", "A mastering studio for data"),
    ("Scale", "Any CSV / XLSX catalog"),
    ("Extension", "New domain presets"),
    ("Output", "Procurement-ready masters"),
]


class SignalChain(Flowable):
    """The four-stage studio signal chain with arrows between stages."""

    BOX_H = 58
    ARROW_W = 24

    def __init__(self):
        super().__init__()
        self.width = CONTENT_W

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        return availWidth, self.BOX_H

    def draw(self):
        c = self.canv
        n = len(_STAGES)
        box_w = (self.width - self.ARROW_W * (n - 1)) / n
        x = 0.0
        for i, (title, mid, caption) in enumerate(_STAGES):
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
            "NgineAgent runs your catalog through a studio-grade signal chain: load the raw take, "
            "scan it on the console, process it through the correction rack, and bounce a "
            "procurement-ready master.",
            f"5 domain presets · HTTP API · branded PDF artifacts · generated {now_utc()}",
        ],
        None, st,
    ))
    story.append(Spacer(1, 16))

    # signal chain
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

    # execution / mental model
    story.append(_model_panels(st))
    story.append(Spacer(1, 16))

    # why teams buy it
    story.append(section(
        "Why teams buy it", st,
        panel([
            Paragraph("• <b>Deterministic.</b> Same take in, same master out — no model drift, no surprises in re-runs.", st["small"]),
            Paragraph("• <b>Evidence on every run.</b> Validation report, fix worksheet, corrected master and audit trail — each carrying the Run ID.", st["small"]),
            Paragraph("• <b>Preset-extensible.</b> A new vertical is a new schema + rule pack, not a rewrite — five presets shipped, more on request.", st["small"]),
            Paragraph("• <b>Light footprint.</b> Pure Python behind a plain HTTP API; runs on a single VPS, no browser, no GPU, no queue to operate.", st["small"]),
        ]),
    ))

    subtitle = f"engine reference · studio metaphor · {now_utc()}"
    return build_document("Engine Reference", subtitle, story)
