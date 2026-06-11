"""
CIP-grade branded PDF reports for the engine.

Two builders on top of the shared report kit (core/exporters/report_kit.py):

  - export_pdf(df, title, domain)            -> corrected-data export report
  - export_validation_pdf(df, domain, issues) -> validation "what's wrong" report

Both produce a multi-section, procurement-ready document: letterhead chrome,
hero with score ring and status chip, zoned gauge bar, stat cards, severity
distribution, numbered finding cards, remediation plan, styled records table
and an audit trail — in the NgineAgent ink + teal house style.

Pure reportlab (no headless browser) so the PDFs render per-request on the VPS.
"""

import uuid

import pandas as pd
from reportlab.platypus import Paragraph, Spacer

from .report_kit import (
    AMBER,
    RED,
    SCHEMES,
    DistroBar,
    GaugeBar,
    Pill,
    ScoreRing,
    build_document,
    distro_legend,
    finding_card,
    hero_block,
    kit_styles,
    now_iso,
    now_utc,
    panel,
    section,
    stat_cards,
    table_block,
)

# severity vocabulary -> bucket
_HIGH = {"high", "critical", "fail", "failed", "error", "blocking", "urgent"}
_MED = {"medium", "med", "warn", "warning", "watch", "needs work", "review", "partial"}
_LOW = {"low", "info", "minor", "note"}
_OK = {"ok", "pass", "passing", "healthy", "clean", "done", "valid", "present", "resolved", "fixed"}

_BUCKET_SCHEME = {"high": "red", "medium": "amber", "low": "blue", "ok": "green"}
_BUCKET_CHIP = {"high": "P1 · FIX 48H", "medium": "P2 · FIX 7D", "low": "P3 · TRACK"}


def _bucket(value) -> str | None:
    t = str(value).strip().lower()
    if t in _HIGH:
        return "high"
    if t in _MED:
        return "medium"
    if t in _LOW:
        return "low"
    if t in _OK:
        return "ok"
    return None


def _find_col(df: pd.DataFrame, *names) -> str | None:
    lower = {str(c).lower(): c for c in df.columns}
    for n in names:
        if n in lower:
            return lower[n]
    return None


def _score(high: int, med: int, low: int) -> int:
    return max(0, min(100, 100 - 6 * high - 1 * (med + low)))


def _status_for(score: int, blocking: int = 0) -> tuple[str, str]:
    """(score, blocking count) -> (status label, scheme). Blocking findings cap the grade."""
    if score >= 90 and blocking == 0:
        return "HEALTHY", "green"
    if score >= 70:
        return "NEEDS WORK", "amber"
    return "CRITICAL", "red"


def _run_id() -> str:
    return uuid.uuid4().hex[:12]


def _cell_text(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value)


def _severity_sections(high: int, med: int, low: int, ok: int, st: dict) -> list:
    """Shared 'severity distribution' section (bar + legend)."""
    bar = DistroBar([(high, "red"), (med, "amber"), (low, "blue"), (ok, "green")])
    legend = distro_legend(
        [(high, "Critical", "red"), (med, "Watch", "amber"), (low, "Low", "blue"), (ok, "Passing", "green")],
        st,
    )
    return [section("Severity distribution", st, bar, Spacer(1, 5), legend), Spacer(1, 14)]


def _audit_sections(run_id: str, st: dict) -> list:
    how = panel([
        Paragraph("HOW TO READ THIS", st["section"]),
        Spacer(1, 4),
        Paragraph(
            "Each finding carries a severity (Critical / Watch / Low) and a fix priority "
            "(P1 / P2 / P3). P1 items are blocking and should be remediated within 48 hours; "
            "P2 items within the next 7-day cycle; P3 items are tracked. Re-run the scan after "
            "remediation to confirm score lift and resolved-finding count.",
            st["small"],
        ),
    ])
    audit = panel([
        Paragraph("AUDIT TRAIL", st["section"]),
        Spacer(1, 4),
        Paragraph(f"Run ID: {run_id} · Generated: {now_iso()} · NgineAgent validation/correction pipeline", st["small"]),
        Paragraph("Findings derived from structured, repeatable checks. Operator review pending.", st["fine"]),
    ])
    return [how, Spacer(1, 10), audit]


# ── Corrected-data export ─────────────────────────────────────────────────────

def export_pdf(df: pd.DataFrame, title: str = "Corrected Data Export", domain: str | None = None) -> bytes:
    st = kit_styles()
    run_id = _run_id()
    domain_label = (domain or "dataset").strip()
    n_rows, n_cols = len(df), len(df.columns)

    sev_col = _find_col(df, "severity", "status", "result", "condition")
    high = med = low = ok = 0
    if sev_col is not None:
        for v in df[sev_col]:
            b = _bucket(v)
            if b == "high":
                high += 1
            elif b == "medium":
                med += 1
            elif b == "low":
                low += 1
            elif b == "ok":
                ok += 1
    score = _score(high, med, low)
    status, scheme = _status_for(score, high)

    story = []

    # hero
    sub = (
        f"{n_rows} record(s) × {n_cols} columns · {high} critical · {med} watch · "
        f"{low} low · generated {now_utc()}"
    )
    story.append(hero_block(
        f"{domain_label} · corrected dataset", "blue",
        title,
        [sub, f"Run ID: {run_id}"],
        ScoreRing(score, status, scheme),
        st,
    ))
    story.append(Spacer(1, 14))

    # gauge band
    if high:
        impact = (
            "Remaining critical fields block downstream acceptance. Apply the required "
            "actions below, then re-export to confirm a clean run."
        )
    elif med or low:
        impact = (
            "No blocking fields remain. Clear the watch-list items within the next "
            "7-day cycle, then re-export to confirm a clean run."
        )
    else:
        impact = "All corrections applied cleanly — dataset is release-ready."
    story.append(section(
        "Data quality score", st,
        GaugeBar(score),
        Spacer(1, 6),
        Paragraph(impact, st["small"]),
    ))
    story.append(Spacer(1, 14))

    # stat cards
    story.append(stat_cards([
        ("Rows", n_rows, "corrected records", None),
        ("Columns", n_cols, "fields per row", None),
        ("Critical", high, "fix within 48 hours", "red" if high else "green"),
        ("Watch", med + low, "fix within 7 days", "amber" if (med + low) else "green"),
    ], st))
    story.append(Spacer(1, 16))

    # severity distribution
    if high + med + low + ok > 0:
        story.extend(_severity_sections(high, med, low, ok, st))

    # top findings
    field_col = _find_col(df, "field", "column", "attribute")
    row_col = _find_col(df, "row", "line", "index")
    msg_col = _find_col(df, "message", "issue", "detail", "description")
    orig_col = _find_col(df, "original", "value", "input")
    fix_col = _find_col(df, "fix", "correction", "suggestion", "remedy")

    findings = []
    if sev_col is not None and msg_col is not None:
        order = {"high": 0, "medium": 1, "low": 2}
        flagged = [
            (order[_bucket(r[sev_col])], r) for _, r in df.iterrows()
            if _bucket(r[sev_col]) in order
        ]
        flagged.sort(key=lambda x: x[0])
        for i, (_, r) in enumerate(flagged[:8], start=1):
            b = _bucket(r[sev_col])
            ftitle = _cell_text(r[field_col]) if field_col else "finding"
            if row_col is not None and _cell_text(r[row_col]):
                ftitle += f" · row {_cell_text(r[row_col])}"
            msg = _cell_text(r[msg_col])
            if orig_col is not None and _cell_text(r[orig_col]):
                msg += f' — original value: "{_cell_text(r[orig_col])}"'
            fix = _cell_text(r[fix_col]) if fix_col is not None else None
            findings.append(finding_card(
                i, ftitle, msg, _BUCKET_CHIP[b], _BUCKET_SCHEME[b], st, fix=fix or None,
            ))
            findings.append(Spacer(1, 7))
    if findings:
        story.append(section("Top findings (blocking first)", st, *findings))
        story.append(Spacer(1, 8))

    # corrected records table
    weights = []
    for c in df.columns:
        cl = str(c).lower()
        if cl in ("message", "issue", "detail", "description", "notes"):
            weights.append(3.2)
        elif cl in ("original", "value", "input", "correction", "fix", "url"):
            weights.append(1.8)
        elif cl in ("row", "line", "index", "priority"):
            weights.append(0.6)
        else:
            weights.append(1.0)

    rows = []
    for tup in df.itertuples(index=False, name=None):
        cells = []
        for col, val in zip(df.columns, tup):
            b = _bucket(val) if sev_col is not None and col == sev_col else None
            if b:
                cells.append(Pill(_cell_text(val), _BUCKET_SCHEME[b]))
            else:
                cells.append(_cell_text(val))
        rows.append(cells)

    story.append(section(
        "Corrected records", st,
        table_block(list(zip(df.columns, weights)), rows, st),
    ))
    story.append(Spacer(1, 16))

    story.extend(_audit_sections(run_id, st))

    subtitle = f"{domain_label} · corrected dataset · {now_utc()}"
    return build_document(title, subtitle, story)


# ── Validation report ─────────────────────────────────────────────────────────

def export_validation_pdf(df: pd.DataFrame, domain: str, issues) -> bytes:
    st = kit_styles()
    run_id = _run_id()
    domain_label = (domain or "dataset").strip()
    n_rows = len(df)

    real = [i for i in issues if i.get("severity") != "INFO" and i.get("field") != "__health__"]
    high = sum(1 for i in real if i.get("severity") == "HIGH")
    med = sum(1 for i in real if i.get("severity") == "MEDIUM")
    low = sum(1 for i in real if i.get("severity") == "LOW")
    score = _score(high, med, low)
    status, scheme = _status_for(score, high)

    sev_scheme = {"HIGH": "red", "MEDIUM": "amber", "LOW": "blue"}
    sev_chip = {"HIGH": "P1 · FIX 48H", "MEDIUM": "P2 · FIX 7D", "LOW": "P3 · TRACK"}

    story = []

    # hero
    story.append(hero_block(
        f"{domain_label} · validation scan", "blue",
        "Validation Report",
        [
            f"{n_rows} rows analyzed · {len(real)} issues · {high} blocking · "
            f"{med + low} resolvable · generated {now_utc()}",
            f"Run ID: {run_id}",
        ],
        ScoreRing(score, status, scheme),
        st,
    ))
    story.append(Spacer(1, 14))

    # gauge + impact statement
    if not real:
        impact = "Dataset passed all schema and domain checks — release-ready."
    elif high:
        impact = (
            "Blocking findings prevent acceptance of this dataset. Remediate P1 items, apply "
            "the correction pass, then re-validate to confirm the score lift."
        )
    else:
        impact = (
            "No blocking findings. Resolve the watch-list items within the next 7-day cycle "
            "and re-validate to confirm a clean run."
        )
    story.append(section("Data health score", st, GaugeBar(score), Spacer(1, 6), Paragraph(impact, st["small"])))
    story.append(Spacer(1, 14))

    # stat cards
    story.append(stat_cards([
        ("Rows analyzed", n_rows, f"{domain_label} domain", None),
        ("Total issues", len(real), "across the dataset", None),
        ("Blocking", high, "prevent acceptance", "red" if high else "green"),
        ("Resolvable", med + low, "fixable with confirmation", "amber" if (med + low) else "green"),
    ], st))
    story.append(Spacer(1, 16))

    # severity distribution
    clean_rows = n_rows - len({i.get("row") for i in real if i.get("row") is not None})
    story.extend(_severity_sections(high, med, low, max(clean_rows, 0), st))

    # issues by field
    by_field = {}
    for i in real:
        by_field.setdefault(str(i.get("field", "—")), []).append(i)
    if by_field:
        rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        lines = []
        for field, group in sorted(by_field.items(), key=lambda kv: -len(kv[1])):
            worst = min(group, key=lambda x: rank.get(x.get("severity", "LOW"), 3))
            color = {"HIGH": "#c23a36", "MEDIUM": "#b06a16", "LOW": "#0b6f5e"}[worst.get("severity", "LOW")]
            lines.append(Paragraph(
                f'<font color="{color}"><b>✕</b></font> <b>{field}</b> — {len(group)} issue(s): '
                f"{group[0].get('message', '')}",
                st["small"],
            ))
        story.append(section("Issues by field", st, panel(lines)))
        story.append(Spacer(1, 14))

    # top findings
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    top = sorted(real, key=lambda i: order.get(i.get("severity", "LOW"), 3))[:8]
    cards = []
    for n, i in enumerate(top, start=1):
        sev = i.get("severity", "LOW")
        ftitle = str(i.get("field", "—"))
        if i.get("row") is not None:
            ftitle += f" · row {i.get('row')}"
        cards.append(finding_card(
            n, ftitle, str(i.get("message", "")),
            sev_chip.get(sev, "P3 · TRACK"), sev_scheme.get(sev, "blue"), st,
            fix=i.get("fix") or None,
        ))
        cards.append(Spacer(1, 7))
    if cards:
        story.append(section("Top findings (blocking first)", st, *cards))
        story.append(Spacer(1, 8))

    # remediation plan
    p1 = [i for i in real if i.get("severity") == "HIGH"]
    p2 = [i for i in real if i.get("severity") in ("MEDIUM", "LOW")]

    def _plan_panel(title_text, items, accent, bg_scheme):
        _, dark, bg = SCHEMES[bg_scheme]
        head = st["section"].clone("planhead", textColor=dark)
        lines = [Paragraph(title_text, head), Spacer(1, 4)]
        for i in items[:12]:
            fix = i.get("fix") or i.get("message", "")
            lines.append(Paragraph(f"• <b>{i.get('field', '—')}</b>: {fix}", st["small"]))
        if len(items) > 12:
            lines.append(Paragraph(f"… and {len(items) - 12} more.", st["fine"]))
        return panel(lines, bg=bg, accent=accent)

    if p1 or p2:
        plan = []
        if p1:
            plan.append(_plan_panel(f"CRITICAL · P1 — 48-HOUR PLAN ({len(p1)})", p1, RED, "red"))
            plan.append(Spacer(1, 8))
        if p2:
            plan.append(_plan_panel(f"WATCH · P2 — 7-DAY PLAN ({len(p2)})", p2, AMBER, "amber"))
        story.append(section("Remediation plan", st, *plan))
        story.append(Spacer(1, 14))

    # per-row status
    rows_with_issues = {}
    for i in real:
        r = i.get("row")
        if r is not None:
            rows_with_issues.setdefault(r, set()).add(str(i.get("field", "—")))
    status_rows = []
    for idx in range(n_rows):
        if idx in rows_with_issues:
            status_rows.append([str(idx), Pill("Issues", "red"), ", ".join(sorted(rows_with_issues[idx]))])
        else:
            status_rows.append([str(idx), Pill("Clean", "green"), "—"])
    story.append(section(
        "Per-row status", st,
        table_block([("Row", 0.5), ("Status", 0.8), ("Fields with issues", 4.0)], status_rows, st, font_size=8),
    ))
    story.append(Spacer(1, 16))

    story.extend(_audit_sections(run_id, st))

    subtitle = f"{domain_label} · validation scan · {now_utc()}"
    return build_document("Validation Report", subtitle, story)
