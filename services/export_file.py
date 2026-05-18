import pandas as pd

from core.exporters.csv_exporter import export_csv
from core.exporters.xlsx_exporter import export_xlsx


def export_corrected(df: pd.DataFrame, fmt: str = "csv") -> bytes:
    fmt = (fmt or "csv").lower()
    if fmt in ("xlsx", "excel"):
        return export_xlsx(df)
    return export_csv(df)


def media_type_for(fmt: str) -> str:
    if fmt and fmt.lower() in ("xlsx", "excel"):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return "text/csv"


def filename_for(fmt: str, stem: str = "corrected") -> str:
    if fmt and fmt.lower() in ("xlsx", "excel"):
        return f"{stem}.xlsx"
    return f"{stem}.csv"
