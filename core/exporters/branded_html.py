"""
Branded HTML for the engine's PDF artifacts, in the CIP / HeyRoya house style
(light theme, score ring, severity distribution, finding cards, per-row status).

Two builders, one shared stylesheet:
  - build_validation_report_html(df, domain, issues)  -> the rich "what's wrong" report
  - build_export_html(df, domain)                     -> the corrected-data export

Pure string building (only pandas). The HTML is handed to a headless browser
(see pdf_render.render_html_to_pdf) to produce the print-ready PDF.
"""

import html as _html
from datetime import datetime, timezone

import pandas as pd

from ..utils.health_score import get_risk_status

BRAND = "NgineAgent"
URL = "engine.usesmpt.com"

# severity (validator vocab) -> semantic class
_SEV = {"HIGH": "red", "MEDIUM": "amber", "LOW": "blue"}

# corrected-data token -> semantic class (export pills)
_GREEN = {"ok", "pass", "passing", "healthy", "clean", "done", "valid", "present"}
_AMBER = {"warn", "warning", "watch", "needs work", "medium", "review", "partial"}
_RED = {"issue", "critical", "fail", "failed", "error", "blocking", "high", "missing"}


def _esc(x) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return _html.escape(str(x))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _grade(score: float) -> str:
    return "green" if score >= 90 else "amber" if score >= 70 else "red"


BASE_CSS = """
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  color:#0c1a1f; background:#fff; line-height:1.5; font-size:13px; }
.page { max-width:1040px; margin:0 auto; padding:26px 30px 52px; }
.runhead { display:flex; justify-content:space-between; align-items:center;
  font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:#6b7b80;
  border-bottom:1px solid #e0e9eb; padding-bottom:10px; margin-bottom:22px; font-weight:700; }
.runhead .url { color:#0c1a1f; }
.hero { display:flex; justify-content:space-between; align-items:center; gap:24px;
  border:1px solid #e0e9eb; border-radius:16px; padding:24px 28px; margin-bottom:20px;
  background:linear-gradient(135deg,#f4f9f9 0%,#eef5f4 100%); }
.pre-tag { display:inline-block; background:rgba(15,184,156,.14); color:#0b6f5e;
  border:1px solid #0fb89c; border-radius:999px; padding:3px 12px; font-size:10px;
  font-weight:700; text-transform:uppercase; letter-spacing:.07em; margin-bottom:10px; }
.hero h1 { font-size:24px; font-weight:800; margin-bottom:5px; }
.hero .sub { color:#52646a; font-size:13px; }
.ring { flex:0 0 auto; width:112px; height:112px; border-radius:999px; display:flex;
  flex-direction:column; align-items:center; justify-content:center; border:6px solid #0fb89c; }
.ring.amber { border-color:#d9892a; } .ring.red { border-color:#e0524e; } .ring.gray { border-color:#9fb0b4; }
.ring-num { font-size:36px; font-weight:800; line-height:1; }
.ring.amber .ring-num { color:#b06a16; } .ring.red .ring-num { color:#c23a36; }
.ring.green .ring-num { color:#0b6f5e; } .ring.gray .ring-num { color:#52646a; }
.ring-cap { font-size:9px; color:#6b7b80; margin-top:4px; text-transform:uppercase; letter-spacing:.06em; }
.ring-status { font-size:10px; font-weight:800; margin-top:3px; letter-spacing:.04em; }
.summary { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:22px; }
.card { border:1px solid #e0e9eb; border-radius:12px; padding:14px 16px; background:#fff; }
.card-label { font-size:10px; color:#6b7b80; text-transform:uppercase; letter-spacing:.06em; margin-bottom:6px; font-weight:700; }
.card-value { font-size:25px; font-weight:800; }
.card-sub { font-size:11px; color:#8a979b; margin-top:2px; }
.card.red .card-value { color:#c23a36; } .card.amber .card-value { color:#b06a16; } .card.green .card-value { color:#0b6f5e; }
.section { margin-bottom:22px; }
.section-h { font-size:13px; font-weight:800; color:#0b6f5e; text-transform:uppercase; letter-spacing:.08em; margin-bottom:10px; }
.distro { display:flex; height:14px; border-radius:999px; overflow:hidden; border:1px solid #e0e9eb; }
.distro span { display:block; height:100%; }
.distro .red { background:#e0524e; } .distro .amber { background:#d9892a; } .distro .blue { background:#0b8c77; } .distro .green { background:#15936b; }
.distro-key { margin-top:8px; font-size:11px; color:#52646a; display:flex; gap:16px; }
.distro-key b { font-weight:800; }
.panel { border:1px solid #e0e9eb; border-radius:12px; padding:16px 20px; background:#fff; }
.panel ul { list-style:none; }
.panel li { padding:7px 0 7px 22px; position:relative; color:#243238; font-size:13px; border-bottom:1px solid #f1f5f6; }
.panel li:last-child { border-bottom:0; }
.panel li::before { content:'✕'; position:absolute; left:0; color:#e0524e; font-weight:800; }
.panel li.amber::before { content:'!'; color:#d9892a; } .panel li.blue::before { content:'•'; color:#0b8c77; }
.panel li strong { color:#0c1a1f; }
.finding { border:1px solid #e0e9eb; border-left-width:4px; border-radius:10px; padding:12px 16px; margin-bottom:10px; }
.finding.red { border-left-color:#e0524e; background:#fdf3f3; }
.finding.amber { border-left-color:#d9892a; background:#fdf8f0; }
.finding.blue { border-left-color:#0b8c77; background:#f1faf8; }
.finding .ftop { display:flex; justify-content:space-between; align-items:center; gap:10px; margin-bottom:3px; }
.finding .ftitle { font-weight:700; color:#0c1a1f; font-size:13px; }
.finding .ffix { font-size:12px; color:#52646a; margin-top:4px; }
.finding .ffix b { color:#0b6f5e; }
.tablewrap { border:1px solid #e0e9eb; border-radius:12px; overflow:hidden; }
table { width:100%; border-collapse:collapse; font-size:12px; }
th { text-align:left; padding:10px 12px; background:#0c1a1f; color:#fff; font-size:10px; text-transform:uppercase; letter-spacing:.05em; font-weight:700; }
td { padding:9px 12px; border-bottom:1px solid #eef2f3; color:#243238; vertical-align:top; }
tr:nth-child(even) td { background:#f7fafa; }
tr:last-child td { border-bottom:0; }
.pill { display:inline-block; padding:2px 9px; border-radius:999px; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.03em; white-space:nowrap; }
.pill.green { background:rgba(15,147,107,.12); color:#0b6f5e; border:1px solid rgba(15,147,107,.4); }
.pill.amber { background:rgba(217,137,42,.14); color:#b06a16; border:1px solid rgba(217,137,42,.45); }
.pill.red { background:rgba(224,82,78,.12); color:#c23a36; border:1px solid rgba(224,82,78,.4); }
.pill.blue { background:rgba(11,140,119,.12); color:#0b6f5e; border:1px solid rgba(11,140,119,.4); }
.score { font-weight:800; } .score.green { color:#0b6f5e; } .score.amber { color:#b06a16; } .score.red { color:#c23a36; }
.foot { text-align:center; color:#8a979b; font-size:11px; margin-top:26px; }
@page { size:A4 landscape; margin:13mm 11mm; }
"""


def _doc(title: str, body: str) -> str:
    return (
        f'<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        f"<title>{_esc(title)}</title><style>{BASE_CSS}</style></head>"
        f'<body><div class="page">{body}'
        f'<div class="foot">Generated by {_esc(BRAND)} · {_esc(URL)}</div>'
        f"</div></body></html>"
    )


def _runhead(left: str) -> str:
    return f'<div class="runhead"><span>{_esc(left)}</span><span class="url">{_esc(URL)}</span></div>'


# ── Validation report ────────────────────────────────────────────────────────

def _summarize(issues):
    """Collapse raw issues into report-ready aggregates."""
    real = [i for i in issues if i.get("severity") != "INFO" and i.get("field") != "__health__"]
    blocking = sum(1 for i in real if i.get("severity") == "HIGH")
    medium = sum(1 for i in real if i.get("severity") == "MEDIUM")
    low = sum(1 for i in real if i.get("severity") == "LOW")
    resolvable = medium + low
    score = max(0, min(100, 100 - 6 * blocking - 1 * resolvable))
    return {
        "real": real,
        "blocking": blocking,
        "medium": medium,
        "low": low,
        "resolvable": resolvable,
        "score": score,
        "status": get_risk_status(score),
    }


def _finding_card(i) -> str:
    cls = _SEV.get(i.get("severity", "LOW"), "blue")
    title = _esc(i.get("field", "—"))
    if i.get("row") is not None:
        title += f" · row {i.get('row')}"
    fix = ""
    if i.get("fix"):
        fix = f'<div class="ffix"><b>Fix:</b> {_esc(i.get("fix"))}</div>'
    return (
        f'<div class="finding {cls}"><div class="ftop">'
        f'<span class="ftitle">{title}</span>'
        f'<span class="pill {cls}">{_esc(i.get("severity",""))}</span></div>'
        f'<div>{_esc(i.get("message",""))}</div>{fix}</div>'
    )


def build_validation_report_html(df: pd.DataFrame, domain: str, issues) -> str:
    s = _summarize(issues)
    domain_label = (domain or "dataset").strip()
    n_rows = len(df)
    grade = _grade(s["score"])

    # severity distribution bar
    total = max(s["blocking"] + s["medium"] + s["low"], 1)
    seg = lambda n, cls: (f'<span class="{cls}" style="width:{round(100 * n / total, 2)}%"></span>' if n else "")
    distro = seg(s["blocking"], "red") + seg(s["medium"], "amber") + seg(s["low"], "blue")

    cards = (
        f'<div class="card"><div class="card-label">Rows analyzed</div><div class="card-value">{n_rows}</div><div class="card-sub">{_esc(domain_label)} domain</div></div>'
        f'<div class="card"><div class="card-label">Total issues</div><div class="card-value">{len(s["real"])}</div><div class="card-sub">across the dataset</div></div>'
        f'<div class="card red"><div class="card-label">Blocking</div><div class="card-value">{s["blocking"]}</div><div class="card-sub">prevent acceptance</div></div>'
        f'<div class="card amber"><div class="card-label">Resolvable</div><div class="card-value">{s["resolvable"]}</div><div class="card-sub">fixable with confirmation</div></div>'
    )

    # issues grouped by field
    by_field = {}
    for i in s["real"]:
        by_field.setdefault(i.get("field", "—"), []).append(i)
    field_items = "".join(
        f'<li class="{_SEV.get(max(g, key=lambda x: ["LOW","MEDIUM","HIGH"].index(x.get("severity","LOW"))).get("severity","LOW"), "blue")}">'
        f'<strong>{_esc(field)}</strong> — {len(g)} issue(s): {_esc(g[0].get("message",""))}</li>'
        for field, g in sorted(by_field.items(), key=lambda kv: -len(kv[1]))
    ) or '<li class="blue">No issues detected — dataset is clean.</li>'

    # top findings (cards, HIGH first)
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    top = sorted(s["real"], key=lambda i: order.get(i.get("severity", "LOW"), 3))[:8]
    finding_cards = "".join(_finding_card(i) for i in top) or (
        '<div class="finding blue"><div class="ftitle">No findings</div>'
        "<div>The dataset passed all schema and domain checks.</div></div>"
    )

    # per-row status
    rows_with_issues = {}
    for i in s["real"]:
        r = i.get("row")
        if r is not None:
            rows_with_issues.setdefault(r, set()).add(i.get("field", "—"))
    body_rows = []
    for idx in range(n_rows):
        if idx in rows_with_issues:
            fields = ", ".join(sorted(rows_with_issues[idx]))
            body_rows.append(f'<tr><td>{idx}</td><td><span class="pill red">Issues</span></td><td>{_esc(fields)}</td></tr>')
        else:
            body_rows.append(f'<tr><td>{idx}</td><td><span class="pill green">Clean</span></td><td>—</td></tr>')
    per_row = "".join(body_rows) or '<tr><td colspan="3">No rows.</td></tr>'

    body = (
        _runhead("Validation Report")
        + '<div class="hero"><div>'
        + f'<span class="pre-tag">{_esc(domain_label)} · validation scan</span>'
        + "<h1>Validation Report</h1>"
        + f'<div class="sub">{n_rows} rows analyzed · {len(s["real"])} issues · {s["blocking"]} blocking · {s["resolvable"]} resolvable · generated {_now()}</div>'
        + "</div>"
        + f'<div class="ring {grade}"><div class="ring-num">{s["score"]}</div><div class="ring-cap">/ 100</div><div class="ring-status">{_esc(s["status"])}</div></div>'
        + "</div>"
        + f'<div class="summary">{cards}</div>'
        + f'<div class="section"><div class="section-h">Severity distribution</div><div class="distro">{distro}</div>'
        + f'<div class="distro-key"><span><b style="color:#c23a36">{s["blocking"]}</b> High</span>'
        + f'<span><b style="color:#b06a16">{s["medium"]}</b> Medium</span>'
        + f'<span><b style="color:#0b6f5e">{s["low"]}</b> Low</span></div></div>'
        + f'<div class="section"><div class="section-h">Issues by field</div><div class="panel"><ul>{field_items}</ul></div></div>'
        + f'<div class="section"><div class="section-h">Top findings</div>{finding_cards}</div>'
        + f'<div class="section"><div class="section-h">Per-row status</div><div class="tablewrap"><table>'
        + "<thead><tr><th>Row</th><th>Status</th><th>Fields with issues</th></tr></thead>"
        + f"<tbody>{per_row}</tbody></table></div></div>"
    )
    return _doc("Validation Report", body)


# ── Corrected-data export ────────────────────────────────────────────────────

def _sev_class(value) -> str:
    t = str(value).strip().lower()
    if t in _RED:
        return "red"
    if t in _AMBER:
        return "amber"
    if t in _GREEN:
        return "green"
    return ""


def _find_col(df, *names):
    lower = {c.lower(): c for c in df.columns}
    for n in names:
        if n in lower:
            return lower[n]
    return None


def build_export_html(df: pd.DataFrame, domain: str | None = None) -> str:
    domain_label = (domain or "dataset").strip()
    n_rows, n_cols = len(df), len(df.columns)
    sev_col = _find_col(df, "severity", "status", "result", "condition")
    score_col = _find_col(df, "score")

    if score_col is not None:
        scores = pd.to_numeric(df[score_col], errors="coerce").dropna()
        avg = round(scores.mean()) if len(scores) else 0
        g = "green" if avg >= 80 else "amber" if avg >= 60 else "red"
        ring = f'<div class="ring {g}"><div class="ring-num">{avg}</div><div class="ring-cap">avg / 100</div></div>'
    else:
        ring = f'<div class="ring gray"><div class="ring-num">{n_rows}</div><div class="ring-cap">rows</div></div>'

    cards = (
        f'<div class="card"><div class="card-label">Rows</div><div class="card-value">{n_rows}</div><div class="card-sub">corrected records</div></div>'
        f'<div class="card"><div class="card-label">Columns</div><div class="card-value">{n_cols}</div><div class="card-sub">fields per row</div></div>'
        f'<div class="card green"><div class="card-label">Status</div><div class="card-value">Clean</div><div class="card-sub">corrections applied</div></div>'
        f'<div class="card"><div class="card-label">Domain</div><div class="card-value" style="font-size:18px">{_esc(domain_label)}</div><div class="card-sub">validated schema</div></div>'
    )

    head_cells = "".join(f"<th>{_esc(c)}</th>" for c in df.columns)
    body = []
    for row in df.itertuples(index=False, name=None):
        tds = []
        for col, val in zip(df.columns, row):
            if sev_col is not None and col == sev_col and _sev_class(val):
                tds.append(f'<td><span class="pill {_sev_class(val)}">{_esc(val)}</span></td>')
            else:
                tds.append(f"<td>{_esc(val)}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    body_html = "".join(body) or f'<tr><td colspan="{n_cols}">No rows.</td></tr>'

    inner = (
        _runhead("Corrected Data Export")
        + '<div class="hero"><div>'
        + f'<span class="pre-tag">{_esc(domain_label)} domain</span>'
        + "<h1>Corrected Data Export</h1>"
        + f'<div class="sub">{n_rows} rows × {n_cols} columns · generated {_now()}</div>'
        + "</div>" + ring + "</div>"
        + f'<div class="summary">{cards}</div>'
        + '<div class="section-h">Corrected records</div>'
        + f'<div class="tablewrap"><table><thead><tr>{head_cells}</tr></thead><tbody>{body_html}</tbody></table></div>'
    )
    return _doc("Corrected Data Export", inner)
