"""Static chart rendering (matplotlib -> base64 PNG) for embedding in reports.

Separate from the interactive Plotly charts used in the UI (app/analytics/charts.py):
WeasyPrint renders static HTML/CSS only, no JavaScript, so Plotly's interactive
output can't appear in a PDF. Matplotlib avoids a Plotly-to-static-image
conversion dependency (kaleido), which has known packaging/runtime fragility.

Light theme throughout — this is a printable document, not the app's dark
dashboard UI, so it follows normal report/print conventions instead.
"""
from __future__ import annotations

import base64
from io import BytesIO

import matplotlib

matplotlib.use("Agg")  # non-interactive backend, safe for server-side rendering

import matplotlib.pyplot as plt  # noqa: E402

BG = "#ffffff"
FG = "#1e293b"
ACCENT = "#2563eb"
GRID = "#e2e8f0"


def _style_ax(fig, ax) -> None:
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.tick_params(colors=FG, labelsize=8)
    ax.xaxis.label.set_color(FG)
    ax.yaxis.label.set_color(FG)
    ax.title.set_color(FG)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.grid(True, color=GRID, alpha=0.7, linewidth=0.6)


def _to_base64(fig) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def render_histogram(values: list[float], title: str) -> str:
    fig, ax = plt.subplots(figsize=(6, 3.2))
    _style_ax(fig, ax)
    ax.hist(values, bins=20, color=ACCENT, edgecolor=BG)
    ax.set_title(title, fontsize=10)
    return _to_base64(fig)


def render_bar(categories: list[str], values: list[float], title: str, ylabel: str = "") -> str:
    fig, ax = plt.subplots(figsize=(6, 3.2))
    _style_ax(fig, ax)
    ax.bar([str(c) for c in categories], values, color=ACCENT)
    ax.set_title(title, fontsize=10)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    return _to_base64(fig)


def render_line(x: list[str], y: list[float], title: str, ylabel: str = "") -> str:
    fig, ax = plt.subplots(figsize=(6, 3.2))
    _style_ax(fig, ax)
    ax.plot(x, y, color=ACCENT, marker="o", markersize=3)
    ax.set_title(title, fontsize=10)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    return _to_base64(fig)


def render_heatmap(columns: list[str], matrix: list[list[float | None]], title: str) -> str:
    n = len(columns)
    fig, ax = plt.subplots(figsize=(min(5.5, 1.2 + 0.6 * n), min(5, 1.2 + 0.6 * n)))
    _style_ax(fig, ax)
    arr = [[v if v is not None else 0.0 for v in row] for row in matrix]
    im = ax.imshow(arr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(n))
    ax.set_xticklabels(columns, rotation=45, ha="right", fontsize=7)
    ax.set_yticks(range(n))
    ax.set_yticklabels(columns, fontsize=7)
    for i in range(n):
        for j in range(n):
            val = matrix[i][j]
            if val is not None:
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                         color="white" if abs(val) > 0.5 else FG, fontsize=6)
    ax.set_title(title, fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    return _to_base64(fig)
