"""
Shared reportlab components for NgineAgent's branded PDF reports.

Every PDF gets the same house chrome (ink letterhead band, teal accent rule,
ruled footer with "Page X of Y") plus CIP-grade building blocks: score rings,
gauge bars, severity-distribution bars, status pills, stat cards, finding
cards and bordered panels.

Pure reportlab (no headless browser) so reports render per-request on the VPS.
"""

import io
import json
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as _pdfcanvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ── Branding (white-label) ────────────────────────────────────────────────────
# Optional branding.json at the engine root overrides name, URL, accent colors
# and logo on every artifact. See branding.example.json. Defaults: house style.
_BRANDING_PATH = Path(__file__).resolve().parents[2] / "branding.json"


def _load_branding() -> dict:
    try:
        return json.loads(_BRANDING_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


_BRANDING = _load_branding()
BRAND = _BRANDING.get("name", "NgineAgent")
URL = _BRANDING.get("url", "engine.usesmpt.com")
_LOGO = _BRANDING.get("logo_path")
LOGO_PATH = str(_BRANDING_PATH.parent / _LOGO) if _LOGO else None

# ── House palette ─────────────────────────────────────────────────────────────
INK = colors.HexColor("#0c1a1f")
SLATE = colors.HexColor("#52646a")
MUTED = colors.HexColor("#6b7b80")
FAINT = colors.HexColor("#8a979b")
TEAL = colors.HexColor(_BRANDING.get("accent", "#0fb89c"))
TEAL_DK = colors.HexColor(_BRANDING.get("accent_dark", "#0b6f5e"))
GREEN = colors.HexColor("#15936b")
GREEN_DK = colors.HexColor("#0b6f5e")
GREEN_BG = colors.HexColor("#f1faf8")
AMBER = colors.HexColor("#d9892a")
AMBER_DK = colors.HexColor("#b06a16")
AMBER_BG = colors.HexColor("#fdf8f0")
RED = colors.HexColor("#e0524e")
RED_DK = colors.HexColor("#c23a36")
RED_BG = colors.HexColor("#fdf3f3")
BLUE = colors.HexColor("#0b8c77")
GRIDC = colors.HexColor("#e0e9eb")
ZEBRA = colors.HexColor("#f7fafa")
HERO_BG = colors.HexColor("#f2f8f7")
TRACK = colors.HexColor("#e6ecee")

# scheme name -> (accent, dark text, tint background)
SCHEMES = {
    "red": (RED, RED_DK, RED_BG),
    "amber": (AMBER, AMBER_DK, AMBER_BG),
    "green": (GREEN, GREEN_DK, GREEN_BG),
    "blue": (BLUE, TEAL_DK, GREEN_BG),
    "gray": (colors.HexColor("#9fb0b4"), SLATE, ZEBRA),
}

PAGE_SIZE = letter
MARGIN = 0.55 * inch
CONTENT_W = PAGE_SIZE[0] - 2 * MARGIN


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def kit_styles() -> dict:
    return {
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=INK),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=9, leading=13, textColor=SLATE),
        "section": ParagraphStyle(
            "section", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=TEAL_DK, spaceBefore=4
        ),
        "label": ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=6.5, leading=9, textColor=MUTED),
        "value": ParagraphStyle("value", fontName="Helvetica-Bold", fontSize=19, leading=22, textColor=INK),
        "valuesub": ParagraphStyle("valuesub", fontName="Helvetica", fontSize=7.5, leading=10, textColor=FAINT),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9, leading=12.5, textColor=INK),
        "small": ParagraphStyle("small", fontName="Helvetica", fontSize=8, leading=11, textColor=SLATE),
        "fine": ParagraphStyle("fine", fontName="Helvetica", fontSize=7.5, leading=10.5, textColor=MUTED),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=INK),
        "cellhead": ParagraphStyle("cellhead", fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=colors.white),
        "ftitle": ParagraphStyle("ftitle", fontName="Helvetica-Bold", fontSize=9.5, leading=12.5, textColor=INK),
        "fbody": ParagraphStyle("fbody", fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=SLATE),
    }


# ── Page chrome ───────────────────────────────────────────────────────────────

class NumberedCanvas(_pdfcanvas.Canvas):
    """Two-pass canvas so the footer can show 'Page X of Y'."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_states = []

    def showPage(self):
        self._saved_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_states)
        for state in self._saved_states:
            self.__dict__.update(state)
            self._draw_page_count(total)
            super().showPage()
        super().save()

    def _draw_page_count(self, total):
        w, _ = self._pagesize
        self.setFont("Helvetica", 7.5)
        self.setFillColor(MUTED)
        self.drawRightString(w - MARGIN, 0.38 * inch, f"Page {self._pageNumber} of {total}")


class PageChrome:
    """Draws the letterhead band and ruled footer on every page."""

    def __init__(self, title: str, subtitle: str):
        self.title = title
        self.subtitle = subtitle

    def __call__(self, canvas, doc):
        w, h = doc.pagesize
        band_h = 0.62 * inch

        # header band + teal accent rule
        canvas.setFillColor(INK)
        canvas.rect(0, h - band_h, w, band_h, stroke=0, fill=1)
        canvas.setFillColor(TEAL)
        canvas.rect(0, h - band_h - 2.5, w, 2.5, stroke=0, fill=1)

        # brand mark: custom logo from branding.json, else the teal dot pair
        cy = h - band_h / 2
        title_x = MARGIN + 26
        if LOGO_PATH and Path(LOGO_PATH).exists():
            try:
                canvas.drawImage(LOGO_PATH, MARGIN, cy - 12, width=60, height=24,
                                 preserveAspectRatio=True, anchor="w", mask="auto")
                title_x = MARGIN + 68
            except Exception:
                pass
        else:
            canvas.setFillColor(TEAL)
            canvas.circle(MARGIN + 9, cy, 9, stroke=0, fill=1)
            canvas.setFillColor(TEAL_DK)
            canvas.circle(MARGIN + 11.5, cy - 2.5, 4.5, stroke=0, fill=1)

        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 12.5)
        canvas.drawString(title_x, cy - 1, self.title)
        canvas.setFillColor(TEAL)
        canvas.setFont("Helvetica-Bold", 8.5)
        canvas.drawRightString(w - MARGIN, cy + 4, URL)
        canvas.setFillColor(colors.HexColor("#9fb0b4"))
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(w - MARGIN, cy - 7, self.subtitle)

        # footer rule + credits ('Page X of Y' is drawn by NumberedCanvas)
        canvas.setStrokeColor(GRIDC)
        canvas.setLineWidth(0.6)
        canvas.line(MARGIN, 0.52 * inch, w - MARGIN, 0.52 * inch)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(MARGIN, 0.38 * inch, f"Generated by {BRAND}")
        canvas.setFont("Helvetica", 6.5)
        canvas.setFillColor(FAINT)
        canvas.drawCentredString(w / 2, 0.38 * inch, f"{URL.upper()} · CONFIDENTIAL")


def build_document(title: str, subtitle: str, story: list) -> bytes:
    """Lay the story out under the house chrome and return PDF bytes."""
    buf = io.BytesIO()
    doc = BaseDocTemplate(
        buf,
        pagesize=PAGE_SIZE,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=1.0 * inch,
        bottomMargin=0.75 * inch,
        title=title,
        author=BRAND,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=PageChrome(title, subtitle))])
    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()


# ── Drawing flowables ─────────────────────────────────────────────────────────

class ScoreRing(Flowable):
    """Donut score ring with the number, '/ 100' caption and status inside."""

    def __init__(self, score: int, status: str = "", scheme: str = "green", size: float = 96):
        super().__init__()
        self.score = max(0, min(100, int(round(score))))
        self.status = status
        self.scheme = scheme
        self.size = size

    def wrap(self, availWidth, availHeight):
        return self.size, self.size

    def draw(self):
        c = self.canv
        s = self.size
        cx = cy = s / 2
        r = s / 2 - 5
        accent, dark, _ = SCHEMES.get(self.scheme, SCHEMES["green"])

        c.setLineWidth(7)
        c.setLineCap(1)
        c.setStrokeColor(TRACK)
        c.circle(cx, cy, r, stroke=1, fill=0)
        if self.score > 0:
            c.setStrokeColor(accent)
            c.arc(cx - r, cy - r, cx + r, cy + r, 90, -360 * self.score / 100)

        c.setFillColor(dark)
        c.setFont("Helvetica-Bold", 26)
        c.drawCentredString(cx, cy - 4, str(self.score))
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(cx, cy - 15, "/ 100")
        if self.status:
            c.setFillColor(dark)
            c.setFont("Helvetica-Bold", 6.5)
            c.drawCentredString(cx, cy - 25, self.status.upper())


class GaugeBar(Flowable):
    """Zoned 0-100 gauge (red / amber / green bands) with a marker at the score."""

    BAR_H = 9
    LABEL_H = 12

    def __init__(self, score: int):
        super().__init__()
        self.score = max(0, min(100, int(round(score))))
        self.width = CONTENT_W

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        return availWidth, self.BAR_H + self.LABEL_H + 6

    def draw(self):
        c = self.canv
        w, bh = self.width, self.BAR_H
        y = self.LABEL_H

        c.saveState()
        path = c.beginPath()
        path.roundRect(0, y, w, bh, bh / 2)
        c.clipPath(path, stroke=0)
        for x0, x1, col in (
            (0.0, 0.60, colors.HexColor("#f6d7d6")),
            (0.60, 0.80, colors.HexColor("#f8e8cd")),
            (0.80, 1.0, colors.HexColor("#d9f0e3")),
        ):
            c.setFillColor(col)
            c.rect(w * x0, y, w * (x1 - x0), bh, stroke=0, fill=1)
        c.restoreState()
        c.setStrokeColor(GRIDC)
        c.setLineWidth(0.7)
        c.roundRect(0, y, w, bh, bh / 2, stroke=1, fill=0)

        # marker tick + dot
        mx = w * self.score / 100
        c.setStrokeColor(INK)
        c.setLineWidth(1.4)
        c.line(mx, y - 3, mx, y + bh + 3)
        c.setFillColor(INK)
        c.circle(mx, y - 5, 2.6, stroke=0, fill=1)

        c.setFillColor(MUTED)
        c.setFont("Helvetica", 6.5)
        for v in (0, 60, 80, 100):
            x = min(max(w * v / 100, 4), w - 8)
            c.drawCentredString(x, 0, str(v))


class DistroBar(Flowable):
    """Proportional severity-distribution bar; segments = [(count, scheme)]."""

    def __init__(self, segments, height: float = 12):
        super().__init__()
        self.segments = [(n, s) for n, s in segments if n > 0]
        self.height = height
        self.width = CONTENT_W

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        return availWidth, self.height

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        total = sum(n for n, _ in self.segments)

        c.saveState()
        path = c.beginPath()
        path.roundRect(0, 0, w, h, h / 2)
        c.clipPath(path, stroke=0)
        if total:
            x = 0.0
            for n, scheme in self.segments:
                seg_w = w * n / total
                c.setFillColor(SCHEMES.get(scheme, SCHEMES["gray"])[0])
                c.rect(x, 0, seg_w, h, stroke=0, fill=1)
                x += seg_w
        else:
            c.setFillColor(TRACK)
            c.rect(0, 0, w, h, stroke=0, fill=1)
        c.restoreState()
        c.setStrokeColor(GRIDC)
        c.setLineWidth(0.7)
        c.roundRect(0, 0, w, h, h / 2, stroke=1, fill=0)


class Pill(Flowable):
    """Rounded status chip, e.g. HIGH / P1 · FIX 48H / CLEAN."""

    def __init__(self, text: str, scheme: str = "gray", font_size: float = 6.5, pad_x: float = 6, pad_y: float = 2.5):
        super().__init__()
        self.text = str(text).upper()
        self.scheme = scheme
        self.font_size = font_size
        self.pad_x = pad_x
        self.pad_y = pad_y
        self.w = stringWidth(self.text, "Helvetica-Bold", font_size) + 2 * pad_x
        self.h = font_size + 2 * pad_y

    def wrap(self, availWidth, availHeight):
        return self.w, self.h

    def draw(self):
        c = self.canv
        accent, dark, bg = SCHEMES.get(self.scheme, SCHEMES["gray"])
        c.setFillColor(bg)
        c.setStrokeColor(accent)
        c.setLineWidth(0.8)
        c.roundRect(0, 0, self.w, self.h, self.h / 2, stroke=1, fill=1)
        c.setFillColor(dark)
        c.setFont("Helvetica-Bold", self.font_size)
        c.drawCentredString(self.w / 2, self.pad_y + 0.6, self.text)


# ── Composite builders ────────────────────────────────────────────────────────

def hero_block(chip_text, chip_scheme, title, sub_lines, ring: ScoreRing | None, st: dict) -> Table:
    """Rounded hero panel: status chip, H1, subtitle lines, optional score ring at right."""
    left = [Pill(chip_text, chip_scheme, font_size=7, pad_x=8, pad_y=3), Spacer(1, 7), Paragraph(title, st["h1"])]
    for line in sub_lines:
        left.append(Paragraph(line, st["sub"]))
    if ring is not None:
        ring_w = ring.size + 16
        t = Table([[left, ring]], colWidths=[CONTENT_W - ring_w - 40, ring_w])
        align = [("ALIGN", (1, 0), (1, 0), "RIGHT"), ("RIGHTPADDING", (1, 0), (1, 0), 18)]
    else:
        t = Table([[left]], colWidths=[CONTENT_W])
        align = [("RIGHTPADDING", (0, 0), (0, 0), 18)]
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HERO_BG),
        ("BOX", (0, 0), (-1, -1), 0.8, GRIDC),
        ("ROUNDEDCORNERS", [10, 10, 10, 10]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 18),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        *align,
    ]))
    return t


def stat_cards(cards, st: dict) -> Table:
    """Row of stat cards; cards = [(label, value, sub, scheme_or_None)]."""
    n = len(cards)
    gap = 8
    card_w = (CONTENT_W - gap * (n - 1)) / n
    cells, widths = [], []
    for i, (label, value, sub, scheme) in enumerate(cards):
        val_color = SCHEMES[scheme][1] if scheme else INK
        vstyle = ParagraphStyle(f"v{i}", parent=st["value"], textColor=val_color)
        inner = Table(
            [[Paragraph(str(label).upper(), st["label"])],
             [Paragraph(str(value), vstyle)],
             [Paragraph(str(sub), st["valuesub"])]],
            colWidths=[card_w - 20],
        )
        inner.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        card = Table([[inner]], colWidths=[card_w])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.8, GRIDC),
            ("ROUNDEDCORNERS", [8, 8, 8, 8]),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        cells.append(card)
        widths.append(card_w)
        if i < n - 1:
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
    return row


def section(title: str, st: dict, *flowables) -> KeepTogether:
    return KeepTogether([Paragraph(title.upper(), st["section"]), Spacer(1, 6), *flowables])


def finding_card(number, title, message, chip_text, scheme, st: dict, fix: str | None = None) -> Table:
    """Numbered, tinted finding card with severity chip and optional fix line."""
    accent, dark, bg = SCHEMES.get(scheme, SCHEMES["gray"])
    body = [Paragraph(title, st["ftitle"])]
    if message:
        body.append(Paragraph(message, st["fbody"]))
    if fix:
        body.append(Paragraph(f'<font color="#0b6f5e"><b>Fix:</b></font> {fix}', st["fbody"]))
    num_style = ParagraphStyle("fnum", parent=st["ftitle"], textColor=dark, fontSize=11)
    chip = Pill(chip_text, scheme, font_size=6.5, pad_x=7, pad_y=3)
    t = Table([[Paragraph(str(number), num_style), body, chip]],
              colWidths=[30, CONTENT_W - 30 - chip.w - 30, chip.w + 14])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.8, GRIDC),
        ("LINEBEFORE", (0, 0), (0, -1), 2.6, accent),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (0, 0), 12),
        ("RIGHTPADDING", (0, 0), (0, 0), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (2, 0), (2, 0), 8),
    ]))
    return t


def panel(flowables, bg=colors.white, accent=None, rounded: bool = True) -> Table:
    """Bordered content panel; optional left accent bar and tinted background."""
    t = Table([[flowables]], colWidths=[CONTENT_W])
    cmds = [
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.8, GRIDC),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]
    if rounded:
        cmds.append(("ROUNDEDCORNERS", [8, 8, 8, 8]))
    if accent is not None:
        cmds.append(("LINEBEFORE", (0, 0), (0, -1), 2.6, accent))
    t.setStyle(TableStyle(cmds))
    return t


def table_block(col_defs, rows, st: dict, font_size: float = 7.5) -> Table:
    """Styled data table. col_defs = [(header, weight)]; rows hold str/Flowable cells."""
    headers = [Paragraph(str(h).upper(), st["cellhead"]) for h, _ in col_defs]
    weights = [max(w, 0.1) for _, w in col_defs]
    total_w = sum(weights)
    col_widths = [CONTENT_W * w / total_w for w in weights]

    # never let a column get narrower than its header text — instead shrink the
    # flexible (wider-than-minimum) columns proportionally
    minima = [stringWidth(str(h).upper(), "Helvetica-Bold", 7) + 12 for h, _ in col_defs]
    col_widths = [max(w, m) for w, m in zip(col_widths, minima)]
    excess = sum(col_widths) - CONTENT_W
    if excess > 0:
        slack = [w - m for w, m in zip(col_widths, minima)]
        total_slack = sum(slack)
        if total_slack > 0:
            col_widths = [w - excess * s / total_slack for w, s in zip(col_widths, slack)]

    cell_style = ParagraphStyle("cellsz", parent=st["cell"], fontSize=font_size, leading=font_size + 2.2)
    body = []
    for row in rows:
        cells = []
        for v in row:
            if isinstance(v, (Flowable, list)):
                cells.append(v)
            else:
                text = "" if v is None else str(v)
                if len(text) > 300:
                    text = text[:299] + "…"
                cells.append(Paragraph(text.replace("&", "&amp;").replace("<", "&lt;"), cell_style))
        body.append(cells)
    if not body:
        body = [[Paragraph("(no rows)", cell_style)] + [""] * (len(headers) - 1)]

    t = Table([headers] + body, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("LINEBELOW", (0, 0), (-1, 0), 1.4, TEAL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
        ("GRID", (0, 0), (-1, -1), 0.4, GRIDC),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def distro_legend(items, st: dict) -> Paragraph:
    """Legend under a DistroBar; items = [(count, label, scheme)]."""
    parts = []
    for count, label, scheme in items:
        dark = SCHEMES.get(scheme, SCHEMES["gray"])[1]
        hex_color = "#" + dark.hexval()[2:]
        parts.append(f'<font color="{hex_color}"><b>{count}</b></font> {label}')
    return Paragraph(" &nbsp;&nbsp;·&nbsp;&nbsp; ".join(parts), st["small"])
