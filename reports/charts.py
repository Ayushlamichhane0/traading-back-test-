"""Matplotlib -> base64 chart generator helpers."""
from __future__ import annotations

import base64
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def fig_to_base64(fig: plt.Figure) -> str:
    """Convert a matplotlib Figure into a base64 encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def equity_chart(equity: pd.Series) -> str:
    """Generate base64 encoded equity curve chart."""
    if equity is None or equity.empty:
        return ""

    fig, ax = plt.subplots(figsize=(11, 4))
    equity.plot(ax=ax, color="#1f4e79", lw=1.6)
    ax.set_title("Portfolio Equity Curve", fontsize=12, fontweight="bold", pad=10)
    ax.set_ylabel("Account Balance ($)", fontsize=10)
    ax.set_xlabel("Date", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.yaxis.set_major_formatter("${x:,.0f}")
    return fig_to_base64(fig)


def drawdown_chart(equity: pd.Series) -> str:
    """Generate base64 encoded underwater drawdown chart."""
    if equity is None or equity.empty:
        return ""

    peak = equity.cummax()
    dd = (equity - peak) / peak.replace(0, np.nan) * 100.0

    fig, ax = plt.subplots(figsize=(11, 3))
    dd.plot(ax=ax, color="#c00000", lw=1.2)
    ax.fill_between(dd.index, dd, 0, color="#c00000", alpha=0.25)
    ax.set_title("Underwater Drawdown (%)", fontsize=11, fontweight="bold", pad=8)
    ax.set_ylabel("Drawdown %", fontsize=10)
    ax.set_xlabel("Date", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.yaxis.set_major_formatter("{x:.1f}%")
    return fig_to_base64(fig)


def monthly_heatmap(monthly: pd.DataFrame) -> str:
    """Generate monthly PnL heatmap matrix."""
    if monthly is None or monthly.empty:
        return ""

    m = monthly.copy()
    m["year"] = m["month"].str[:4]
    m["mon"] = m["month"].str[5:7]
    pivot = m.pivot(index="year", columns="mon", values="net_pnl").fillna(0.0)

    fig, ax = plt.subplots(figsize=(10, max(2.5, len(pivot) * 0.7)))
    vmax = max(abs(pivot.values.min()), abs(pivot.values.max()), 1.0)
    im = ax.imshow(pivot.values, cmap="RdYlGn", aspect="auto", vmin=-vmax, vmax=vmax)

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)

    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.values[i, j]
            text_color = "black" if abs(val) < 0.6 * vmax else "white"
            ax.text(
                j,
                i,
                f"{val:,.0f}",
                ha="center",
                va="center",
                fontsize=8,
                color=text_color,
                fontweight="semibold",
            )

    fig.colorbar(im, ax=ax, label="Net PnL ($)", shrink=0.8)
    ax.set_title("Monthly Net PnL Heatmap", fontsize=11, fontweight="bold", pad=8)
    return fig_to_base64(fig)
