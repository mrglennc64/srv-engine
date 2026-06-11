"""
One-command sales demo: run every domain preset's dirty take through the full
signal chain and drop the complete artifact set per domain into demo/out/.

    python demo/demo.py            # all five presets
    python demo/demo.py music      # one preset

Per domain it produces:
    01-validation-report.pdf   the console pass (branded PDF)
    02-worksheet.csv           the fix worksheet, corrections pre-filled
    03-corrected.csv           the corrected take
    04-master.pdf              the bounced master (branded PDF)

and prints the before/after score so the lift is visible in the terminal.
"""

import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_DIR))

import pandas as pd

from services.validate import validate_file
from services.generate_worksheet import generate_worksheet
from services.apply_corrections import apply_corrections
from services.export_file import export_corrected
from core.exporters.pdf_exporter import export_validation_pdf

TAKES_DIR = ENGINE_DIR / "demo" / "takes"
OUT_DIR = ENGINE_DIR / "demo" / "out"

# operator corrections per take: (row, field) -> corrected value
FIXES = {
    "music": {
        (1, "isrc"): "SEABC2600002",
        (2, "isrc"): "SEABC2600003",
        (3, "iswc"): "T-987.654.321-0",
        (4, "title"): "Northern Lights",
        (5, "release_date"): "2026-05-01",
        (7, "ipi"): "00198765432",
    },
    "healthcare": {
        (1, "denial_code"): "CO-45",
        (2, "provider_npi"): "1234567890",
        (3, "cpt_code"): "99214",
        (4, "billed_amount"): "100.00",
        (5, "payer"): "Cigna",
        (6, "date_of_service"): "2026-02-11",
    },
    "comms": {
        (1, "url"): "https://bad-url-demo.com",
        (2, "channel"): "ivr",
        (3, "severity"): "issue",
        (4, "score"): "100",
        (5, "label"): "About-page scan",
    },
    "accounting": {
        (1, "account"): "1930",
        (2, "amount"): "12.50",
        (3, "voucher_series"): "A",
        (4, "voucher_date"): "2026-01-15",
        (5, "vat_code"): "SE25",
    },
    "inspection": {
        (1, "condition"): "under_normalt",
        (2, "section"): "Fasad",
        (3, "inspection_date"): "2026-04-02",
        (4, "validated_by_user"): "true",
        (5, "photo_count"): "2",
    },
}


def _score(issues) -> int:
    real = [i for i in issues if i.get("severity") != "INFO" and i.get("field") != "__health__"]
    high = sum(1 for i in real if i.get("severity") == "HIGH")
    rest = len(real) - high
    return max(0, min(100, 100 - 6 * high - rest))


def run_domain(domain: str) -> dict:
    take_path = TAKES_DIR / f"{domain}_take.csv"
    out = OUT_DIR / domain
    out.mkdir(parents=True, exist_ok=True)

    take = pd.read_csv(take_path, dtype=str)

    # 1. console pass — validate + branded report
    issues = validate_file(take, domain=domain)
    (out / "01-validation-report.pdf").write_bytes(export_validation_pdf(take, domain, issues))

    # 2. mix — worksheet with operator corrections filled in
    ws = generate_worksheet(take, issues)
    fixes = FIXES.get(domain, {})
    if not ws.empty:
        ws["correction"] = [
            fixes.get((int(r) if pd.notna(r) else -1, f), "")
            for r, f in zip(ws["row"], ws["field"])
        ]
    ws.to_csv(out / "02-worksheet.csv", index=False)

    # 3. rack — apply the corrections
    corrected = apply_corrections(take, ws, domain=domain)
    corrected.to_csv(out / "03-corrected.csv", index=False)

    # 4. bounce — the master, with the before-score so the delta shows
    (out / "04-master.pdf").write_bytes(
        export_corrected(corrected, fmt="pdf", domain=domain, baseline_score=_score(issues))
    )

    after_issues = validate_file(corrected, domain=domain)
    return {
        "domain": domain,
        "rows": len(take),
        "issues_before": len(issues),
        "issues_after": len(after_issues),
        "score_before": _score(issues),
        "score_after": _score(after_issues),
        "out": out,
    }


def main():
    domains = sys.argv[1:] or list(FIXES)
    print(f"NgineAgent demo — full signal chain, artifacts in {OUT_DIR}\n")
    print(f"{'PRESET':<12} {'ROWS':>4}  {'ISSUES':>13}  {'SCORE':>11}")
    for domain in domains:
        if domain not in FIXES:
            print(f"{domain:<12} unknown preset (choose from: {', '.join(FIXES)})")
            continue
        r = run_domain(domain)
        print(
            f"{r['domain']:<12} {r['rows']:>4}  "
            f"{r['issues_before']:>5} -> {r['issues_after']:<4}  "
            f"{r['score_before']:>4} -> {r['score_after']:<4}"
        )
    print("\nPer preset: 01-validation-report.pdf · 02-worksheet.csv · 03-corrected.csv · 04-master.pdf")


if __name__ == "__main__":
    main()
