"""Unit tests for static (matplotlib) chart rendering used in reports."""
from __future__ import annotations

import base64

from app.reports.chart_renderer import render_bar, render_heatmap, render_histogram, render_line


def _is_valid_png_base64(s: str) -> bool:
    raw = base64.b64decode(s)
    return raw[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_histogram_produces_valid_png() -> None:
    img = render_histogram([1, 2, 3, 4, 5, 4, 3, 2], "Test histogram")
    assert _is_valid_png_base64(img)


def test_render_bar_produces_valid_png() -> None:
    img = render_bar(["A", "B", "C"], [10, 20, 15], "Test bar")
    assert _is_valid_png_base64(img)


def test_render_line_produces_valid_png() -> None:
    img = render_line(["2025-01-01", "2025-01-02", "2025-01-03"], [10, 15, 12], "Test line")
    assert _is_valid_png_base64(img)


def test_render_heatmap_produces_valid_png() -> None:
    img = render_heatmap(["a", "b"], [[1.0, 0.5], [0.5, 1.0]], "Test heatmap")
    assert _is_valid_png_base64(img)


def test_render_heatmap_handles_none_values() -> None:
    img = render_heatmap(["a", "b"], [[1.0, None], [None, 1.0]], "Test heatmap with nulls")
    assert _is_valid_png_base64(img)
