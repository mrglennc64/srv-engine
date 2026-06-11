import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from services.export_file import export_corrected
from core.exporters.ddex_exporter import DDEXGenerator, validate_ern, validate_release_data


def test_export_csv():
    df = pd.DataFrame([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}])
    data = export_corrected(df, fmt="csv")
    assert b"a,b" in data
    assert b"1,x" in data


def test_export_xlsx_starts_with_zip_magic():
    df = pd.DataFrame([{"a": 1}])
    data = export_corrected(df, fmt="xlsx")
    assert data[:2] == b"PK"  # XLSX is a ZIP archive


def test_export_pdf_branded_report():
    df = pd.DataFrame([
        {"row": 9, "field": "url", "original": "ftp://bad-url-demo.com", "correction": "",
         "severity": "HIGH", "priority": 25, "message": "URGENT: url must start with http:// or https://",
         "fix": "", "notes": ""},
        {"row": 10, "field": "channel", "original": "telephony", "correction": "",
         "severity": "MEDIUM", "priority": 10, "message": "channel must be one of: audit, seo, funnel",
         "fix": "Use 'audit'", "notes": ""},
    ])
    data = export_corrected(df, fmt="pdf", domain="comms")
    assert data[:5] == b"%PDF-"
    assert len(data) > 2000  # multi-section report, not a bare table


def test_export_pdf_handles_empty_and_plain_frames():
    assert export_corrected(pd.DataFrame(columns=["a", "b"]), fmt="pdf")[:5] == b"%PDF-"
    assert export_corrected(pd.DataFrame([{"a": 1, "b": "x"}]), fmt="pdf")[:5] == b"%PDF-"


def test_export_validation_pdf():
    from core.exporters.pdf_exporter import export_validation_pdf

    df = pd.DataFrame([{"title": "Song", "isrc": ""}, {"title": "", "isrc": "USRC12345678"}])
    issues = [
        {"row": 0, "field": "isrc", "severity": "HIGH", "message": "ISRC is missing.", "fix": "Add the ISRC."},
        {"row": 1, "field": "title", "severity": "MEDIUM", "message": "Title is empty."},
        {"row": None, "field": "__health__", "severity": "INFO", "message": "health row"},
    ]
    data = export_validation_pdf(df, "music", issues)
    assert data[:5] == b"%PDF-"


def test_pitch_pdf_builds():
    from core.exporters.pitch_pdf import build_pitch_pdf

    data = build_pitch_pdf()
    assert data[:5] == b"%PDF-"
    assert len(data) > 2000


def test_ddex_generate_and_validate_round_trip():
    data = {
        "id": "REL001",
        "title": "Test Single",
        "artist": "Test Artist",
        "artist_id": "001",
        "label_name": "Test Label",
        "label_id": "002",
        "release_date": "2025-06-01",
        "tracks": [
            {"title": "Test Single", "isrc": "USRC12345678", "duration": "PT3M00S"},
        ],
    }
    ok, errs = validate_release_data(data)
    assert ok, errs

    gen = DDEXGenerator(version="4.3")
    result = gen.generate(data)
    assert "<NewReleaseMessage" in result["xml"]
    assert result["hash"]

    is_valid, errors = validate_ern(result["xml"])
    assert is_valid, errors


def test_ddex_missing_required_caught_by_release_validator():
    data = {"artist": "X"}  # missing title, release_date, label_name
    ok, errs = validate_release_data(data)
    assert not ok
    assert any("title" in e for e in errs)
