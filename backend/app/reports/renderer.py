"""Renders report data to HTML (via Jinja2) and, optionally, PDF (via WeasyPrint).

WeasyPrint needs system libraries (Pango/Cairo/GDK-Pixbuf via GObject) that are
present in this project's Docker image (see docker/backend.Dockerfile) but are
a well-known pain point on a bare Windows install without the GTK3 runtime.
Rather than crash with a raw import/OSError, PDF generation fails with a clear,
actionable error — HTML and JSON export are unaffected either way.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.errors import AppError
from app.core.logging import get_logger

log = get_logger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "jinja"]),
)


class PdfUnavailableError(AppError):
    status_code = 503
    code = "pdf_unavailable"


def render_html(report_data: dict[str, Any]) -> str:
    template = _env.get_template("report.html.jinja")
    return template.render(report=report_data)


def render_pdf(html: str) -> bytes:
    try:
        import weasyprint
    except (ImportError, OSError) as e:
        log.error("weasyprint_unavailable", error=str(e))
        raise PdfUnavailableError(
            "PDF generation is unavailable in this environment: WeasyPrint could not load its "
            "system libraries (Pango/Cairo/GDK-Pixbuf). This is a known limitation on a bare "
            "Windows install without the GTK3 runtime — it works in the project's Docker image. "
            "Use format=html or format=json instead."
        ) from e

    try:
        return weasyprint.HTML(string=html).write_pdf()
    except Exception as e:  # noqa: BLE001 - surface any renderer failure as a clean error
        log.error("pdf_render_failed", error=str(e))
        raise PdfUnavailableError(f"PDF rendering failed: {e}") from e
