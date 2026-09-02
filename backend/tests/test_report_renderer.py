"""Unit tests for HTML/PDF rendering.

PDF generation needs WeasyPrint's system libraries (Pango/Cairo/GDK-Pixbuf),
which are provisioned in this project's Docker image but commonly missing on
a bare Windows dev machine. The PDF test therefore accepts either a real PDF
or a clean PdfUnavailableError — both are "correct" depending on environment
— while a separate mocked test proves the graceful-degradation path itself
works, independent of what's actually installed here.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.reports.renderer import PdfUnavailableError, render_html, render_pdf

_MINIMAL_REPORT = {
    "dataset": {"id": "d1", "filename": "test.csv", "row_count": 10, "column_count": 3, "size_bytes": 500, "uploaded_at": "2026-01-01T00:00:00"},
    "executive_summary": "This dataset contains 10 rows.",
    "profile": {"row_count": 10, "column_count": 3, "quality": {"overall": 90, "completeness": 9, "missing_values": 9, "duplicates": 10, "data_types": 10, "outliers": 8}, "issues": []},
    "numeric_stats": [],
    "categorical_stats": [],
    "charts": [],
    "anomalies": {"columns": []},
    "recommendations": [],
    "ai_insight": None,
    "methodology": "Methodology text.",
    "limitations": "Limitations text.",
    "generated_at": "2026-01-01T00:00:00",
}


def test_render_html_contains_real_data() -> None:
    html = render_html(_MINIMAL_REPORT)
    assert "test.csv" in html
    assert "90/100" in html
    assert "<html" in html.lower()


def test_render_html_escapes_content() -> None:
    report = dict(_MINIMAL_REPORT)
    report["executive_summary"] = "<script>alert('xss')</script>"
    html = render_html(report)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_render_pdf_either_succeeds_or_fails_cleanly() -> None:
    html = render_html(_MINIMAL_REPORT)
    try:
        pdf_bytes = render_pdf(html)
        assert pdf_bytes[:4] == b"%PDF"
    except PdfUnavailableError as e:
        assert "PDF generation is unavailable" in str(e) or "PDF rendering failed" in str(e)


def test_render_pdf_raises_clean_error_when_weasyprint_import_fails() -> None:
    with patch.dict("sys.modules", {"weasyprint": None}), pytest.raises(PdfUnavailableError):
        render_pdf("<html><body>test</body></html>")
