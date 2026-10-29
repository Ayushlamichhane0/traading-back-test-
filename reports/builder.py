"""Render the analyzer output into professional deliverables (HTML, Excel)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from reports import charts


class ReportBuilder:
    """Delivers polished reports in HTML and Excel formats."""

    def __init__(self, output_dir: Path | str = "reports/output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def to_html(
        self,
        report: dict[str, Any],
        equity: pd.Series,
        filename: str = "report.html",
    ) -> Path:
        """Render performance results to self-contained HTML with embedded base64 charts."""
        template = self.env.get_template("report.html.j2")

        eq_chart = charts.equity_chart(equity)
        dd_chart = charts.drawdown_chart(equity)
        mm_chart = charts.monthly_heatmap(report.get("monthly", pd.DataFrame()))

        html = template.render(
            r=report,
            equity_chart=eq_chart,
            drawdown_chart=dd_chart,
            monthly_heatmap=mm_chart,
            monthly_table=report["monthly"].to_html(index=False, classes="table", float_format=lambda x: f"{x:,.2f}"),
            dow_table=report["day_of_week"].to_html(index=False, classes="table", float_format=lambda x: f"{x:,.2f}"),
            hour_table=report["hour_of_day"].to_html(index=False, classes="table", float_format=lambda x: f"{x:,.2f}"),
            session_table=report["session"].to_html(index=False, classes="table", float_format=lambda x: f"{x:,.2f}"),
            symbol_table=report["symbol"].to_html(index=False, classes="table", float_format=lambda x: f"{x:,.2f}"),
        )

        out_path = self.output_dir / filename
        out_path.write_text(html, encoding="utf-8")
        return out_path

    def to_excel(
        self,
        report: dict[str, Any],
        trades: pd.DataFrame,
        filename: str = "report.xlsx",
    ) -> Path:
        """Export all trades, metrics, and breakdowns into an Excel workbook."""
        out_path = self.output_dir / filename

        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            # 1. Summary sheet
            scalar_items = {
                k: v
                for k, v in report.items()
                if isinstance(v, (int, float, str)) and not isinstance(v, bool)
            }
            summary_df = pd.DataFrame(list(scalar_items.items()), columns=["Metric", "Value"])
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

            # 2. Trades sheet
            if trades is not None and not trades.empty:
                t_export = trades.copy()
                # Format datetime columns as timezone-naive strings for Excel compatibility
                for col in ["entry_time", "exit_time"]:
                    if col in t_export.columns:
                        t_export[col] = t_export[col].dt.strftime("%Y-%m-%d %H:%M:%S")
                t_export.to_excel(writer, sheet_name="Trades", index=False)
            else:
                pd.DataFrame({"Status": ["No trades executed"]}).to_excel(writer, sheet_name="Trades", index=False)

            # 3. Breakdowns
            breakdown_keys = [
                ("monthly", "Monthly"),
                ("day_of_week", "DayOfWeek"),
                ("hour_of_day", "HourOfDay"),
                ("session", "Session"),
                ("symbol", "Symbol"),
                ("distribution", "Distribution"),
            ]
            for key, sheet in breakdown_keys:
                df = report.get(key)
                if isinstance(df, pd.DataFrame) and not df.empty:
                    df_clean = df.copy()
                    # Ensure all object/interval columns are clean strings
                    for col in df_clean.columns:
                        if df_clean[col].dtype == "object" or isinstance(df_clean[col].dtype, pd.CategoricalDtype):
                            df_clean[col] = df_clean[col].astype(str)
                    df_clean.to_excel(writer, sheet_name=sheet, index=False)

        return out_path
