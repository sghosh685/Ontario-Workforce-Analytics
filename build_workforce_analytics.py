from __future__ import annotations

import math
import re
import textwrap
import zipfile
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


PROJECT_DIR = Path(__file__).resolve().parent
RAW_LABOUR = PROJECT_DIR / "1410028701_databaseLoadingData.csv"
RAW_INDUSTRY = PROJECT_DIR / "1410035501_databaseLoadingData.csv"
DATA_DIR = PROJECT_DIR / "data_clean"
CHART_DIR = PROJECT_DIR / "charts"
DOCS_DIR = PROJECT_DIR / "docs"
ZIP_PATH = PROJECT_DIR / "ontario_workforce_analytics_starter_package.zip"

ROLLUP_INDUSTRIES = {
    "Total employed, all industries",
    "Goods-producing sector",
    "Services-producing sector",
}

LABOUR_RENAMES = {
    "Population": "population_thousands",
    "Labour force": "labour_force_thousands",
    "Employment": "employment_thousands",
    "Unemployment": "unemployment_thousands",
    "Unemployment rate": "unemployment_rate_percent",
    "Participation rate": "participation_rate_percent",
    "Employment rate": "employment_rate_percent",
    "Full-time employment": "full_time_employment_thousands",
    "Part-time employment": "part_time_employment_thousands",
}

CHART_FILES = [
    "01_ontario_employment_trend.png",
    "02_ontario_unemployment_rate_trend.png",
    "03_employment_and_participation_rates.png",
    "04_top_industries_latest_month.png",
    "05_industry_employment_change_since_2021.png",
    "06_industry_yoy_change_latest_month.png",
]

BLUE = "#2563eb"
ORANGE = "#f59e0b"
RED = "#dc2626"
GREEN = "#0f9f6e"
INK = "#18222f"
MUTED = "#5e6b78"
GRID = "#d9e0e8"
AXIS = "#9aa6b2"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    CHART_DIR.mkdir(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf" if bold else "",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


FONT_TITLE = font(36, bold=True)
FONT_SUBTITLE = font(22)
FONT_AXIS = font(22)
FONT_TICK = font(18)
FONT_LABEL = font(20)
FONT_LABEL_BOLD = font(20, bold=True)
FONT_NOTE = font(16)


def strip_naics_codes(label: str) -> str:
    return re.sub(r"\s+\[[^\]]+\]\s*$", "", label).strip()


def month_label(month: pd.Timestamp) -> str:
    return month.strftime("%B %Y")


def format_thousands(value: float) -> str:
    return f"{value:,.0f}"


def format_signed(value: float) -> str:
    return f"{value:+,.0f}"


def format_percent(value: float) -> str:
    return f"{value:.0f}%"


def text_width(draw: ImageDraw.ImageDraw, text: str, selected_font) -> int:
    box = draw.textbbox((0, 0), text, font=selected_font)
    return box[2] - box[0]


def text_height(draw: ImageDraw.ImageDraw, text: str, selected_font) -> int:
    box = draw.textbbox((0, 0), text, font=selected_font)
    return box[3] - box[1]


def draw_right_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    selected_font,
    fill: str = INK,
) -> None:
    x, y = xy
    draw.text((x - text_width(draw, text, selected_font), y), text, font=selected_font, fill=fill)


def draw_center_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    selected_font,
    fill: str = INK,
) -> None:
    x, y = xy
    draw.text(
        (x - text_width(draw, text, selected_font) / 2, y),
        text,
        font=selected_font,
        fill=fill,
    )


def nice_ticks(vmin: float, vmax: float, count: int = 5) -> list[float]:
    if vmin == vmax:
        return [vmin]
    span = abs(vmax - vmin)
    raw_step = span / max(count - 1, 1)
    magnitude = 10 ** math.floor(math.log10(raw_step))
    step = 10 * magnitude
    for multiplier in [1, 2, 2.5, 5, 10]:
        candidate = multiplier * magnitude
        if candidate >= raw_step:
            step = candidate
            break
    start = math.floor(vmin / step) * step
    end = math.ceil(vmax / step) * step
    ticks = []
    current = start
    while current <= end + step * 0.5:
        ticks.append(round(current, 8))
        current += step
    return ticks


def draw_source_note(draw: ImageDraw.ImageDraw, width: int, height: int, text: str) -> None:
    wrapped = textwrap.wrap(text, width=150)
    y = height - 46
    for line in wrapped[:2]:
        draw.text((45, y), line, font=FONT_NOTE, fill=MUTED)
        y += 19


def draw_line_chart(
    data: pd.DataFrame,
    y_cols: list[str],
    labels: list[str],
    colors: list[str],
    title: str,
    ylabel: str,
    output_path: Path,
    formatter,
) -> None:
    width, height = 1800, 990
    left, right, top, bottom = 155, 75, 155, 140
    plot_w = width - left - right
    plot_h = height - top - bottom

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((45, 40), title, font=FONT_TITLE, fill=INK)

    all_values = pd.concat([data[col] for col in y_cols]).dropna()
    vmin = float(all_values.min())
    vmax = float(all_values.max())
    pad = (vmax - vmin) * 0.08 if vmax != vmin else 1
    y_min = vmin - pad
    y_max = vmax + pad
    ticks = nice_ticks(y_min, y_max, 6)
    y_min = min(ticks)
    y_max = max(ticks)

    def x_at(index: int) -> float:
        if len(data) == 1:
            return left
        return left + index * plot_w / (len(data) - 1)

    def y_at(value: float) -> float:
        return bottom + plot_h - (value - y_min) / (y_max - y_min) * plot_h

    for tick in ticks:
        y = y_at(tick)
        draw.line([(left, y), (width - right, y)], fill=GRID, width=1)
        draw_right_text(draw, (left - 16, int(y - 10)), formatter(tick), FONT_TICK, MUTED)

    draw.line([(left, top), (left, bottom + plot_h)], fill=AXIS, width=2)
    draw.line([(left, bottom + plot_h), (width - right, bottom + plot_h)], fill=AXIS, width=2)
    draw.text((left, top - 42), ylabel, font=FONT_AXIS, fill=MUTED)

    tick_indexes = [i for i, month in enumerate(data["month"]) if month.month == 1]
    if len(data) - 1 not in tick_indexes:
        tick_indexes.append(len(data) - 1)
    for index in tick_indexes:
        x = x_at(index)
        label = str(data["month"].iloc[index].year)
        if index == len(data) - 1:
            label = data["month"].iloc[index].strftime("%Y-%m")
        draw.line([(x, bottom + plot_h), (x, bottom + plot_h + 8)], fill=AXIS, width=2)
        draw_center_text(draw, (int(x), bottom + plot_h + 18), label, FONT_TICK, MUTED)

    for y_col, color in zip(y_cols, colors):
        series = data[y_col].tolist()
        points = [(x_at(i), y_at(float(value))) for i, value in enumerate(series)]
        draw.line(points, fill=color, width=6, joint="curve")
        last_x, last_y = points[-1]
        draw.ellipse((last_x - 8, last_y - 8, last_x + 8, last_y + 8), fill=color)

    if len(y_cols) > 1:
        legend_x = width - right - 430
        legend_y = top + 5
        for offset, (label, color) in enumerate(zip(labels, colors)):
            y = legend_y + offset * 34
            draw.rounded_rectangle((legend_x, y + 8, legend_x + 28, y + 20), radius=4, fill=color)
            draw.text((legend_x + 40, y), label, font=FONT_LABEL, fill=INK)

    draw_source_note(
        draw,
        width,
        height,
        "Source: Statistics Canada Tables 14-10-0287-01 and 14-10-0355-01. Values are seasonally adjusted.",
    )
    image.save(output_path)


def wrap_label(label: str, max_chars: int = 44) -> list[str]:
    lines = textwrap.wrap(label, width=max_chars)
    return lines[:2] if lines else [label]


def draw_bar_chart(
    data: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str,
    xlabel: str,
    output_path: Path,
    diverging: bool = False,
    top_n: int | None = None,
) -> None:
    plot_data = data.copy()
    if top_n:
        plot_data = plot_data.nlargest(top_n, value_col)
    plot_data = plot_data.sort_values(value_col, ascending=True).reset_index(drop=True)

    rows = len(plot_data)
    width = 1800
    height = max(920, 255 + rows * 62)
    left, right, top, bottom = 610, 110, 125, 145
    plot_w = width - left - right
    plot_h = height - top - bottom

    values = plot_data[value_col].astype(float)
    if diverging:
        x_min = min(float(values.min()), 0.0)
        x_max = max(float(values.max()), 0.0)
        span = x_max - x_min
        x_min -= span * 0.08
        x_max += span * 0.08
    else:
        x_min = 0
        x_max = float(values.max()) * 1.1
    ticks = nice_ticks(x_min, x_max, 6)
    x_min = min(ticks)
    x_max = max(ticks)

    def x_at(value: float) -> float:
        return left + (value - x_min) / (x_max - x_min) * plot_w

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((45, 40), title, font=FONT_TITLE, fill=INK)
    draw.text((left, height - 92), xlabel, font=FONT_AXIS, fill=MUTED)

    axis_y = height - bottom
    for tick in ticks:
        x = x_at(tick)
        draw.line([(x, top), (x, axis_y)], fill=GRID, width=1)
        draw_center_text(draw, (int(x), axis_y + 18), format_thousands(tick), FONT_TICK, MUTED)
    zero_x = x_at(0)
    draw.line([(zero_x, top), (zero_x, axis_y)], fill=AXIS, width=2)
    draw.line([(left, axis_y), (width - right, axis_y)], fill=AXIS, width=2)

    row_gap = plot_h / rows
    bar_h = min(38, row_gap * 0.55)
    for idx, row in plot_data.iterrows():
        value = float(row[value_col])
        y_mid = top + row_gap * idx + row_gap / 2
        y1 = y_mid - bar_h / 2
        y2 = y_mid + bar_h / 2
        color = BLUE
        if diverging:
            color = GREEN if value >= 0 else RED
        x0 = x_at(0)
        x1 = x_at(value)
        draw.rounded_rectangle(
            (min(x0, x1), y1, max(x0, x1), y2),
            radius=8,
            fill=color,
        )

        label_lines = wrap_label(str(row[label_col]))
        label_height = len(label_lines) * 22
        label_y = int(y_mid - label_height / 2 - 2)
        for line in label_lines:
            draw_right_text(draw, (left - 22, label_y), line, FONT_LABEL, INK)
            label_y += 22

        value_label = format_signed(value) if diverging else format_thousands(value)
        if value >= 0:
            draw.text((max(x0, x1) + 10, y_mid - 11), value_label, font=FONT_TICK, fill=MUTED)
        else:
            draw_right_text(draw, (min(x0, x1) - 10, int(y_mid - 11)), value_label, FONT_TICK, MUTED)

    draw_source_note(
        draw,
        width,
        height,
        "Source: Statistics Canada Table 14-10-0355-01. Values are seasonally adjusted and shown in thousands.",
    )
    image.save(output_path)


def create_contact_sheet() -> None:
    thumbs = []
    for filename in CHART_FILES:
        path = CHART_DIR / filename
        with Image.open(path) as image:
            thumb_w = 820
            thumb_h = int(image.height * thumb_w / image.width)
            thumbs.append((filename, image.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)))

    padding = 34
    label_h = 28
    cols = 2
    rows = math.ceil(len(thumbs) / cols)
    cell_w = 820
    cell_h = max(thumb.height for _, thumb in thumbs) + label_h
    sheet_w = padding * (cols + 1) + cell_w * cols
    sheet_h = padding * (rows + 1) + cell_h * rows
    sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
    draw = ImageDraw.Draw(sheet)

    for index, (filename, thumb) in enumerate(thumbs):
        row = index // cols
        col = index % cols
        x = padding + col * (cell_w + padding)
        y = padding + row * (cell_h + padding)
        draw.text((x, y), filename, font=FONT_NOTE, fill=MUTED)
        sheet.paste(thumb, (x, y + label_h))

    sheet.save(CHART_DIR / "chart_contact_sheet.png")


def clean_labour_indicators() -> pd.DataFrame:
    labour = pd.read_csv(RAW_LABOUR, encoding="utf-8-sig")
    labour["VALUE"] = pd.to_numeric(labour["VALUE"], errors="coerce")
    labour["month"] = pd.to_datetime(labour["REF_DATE"] + "-01")

    filtered = labour[
        (labour["GEO"] == "Ontario")
        & (labour["Gender"] == "Total - Gender")
        & (labour["Age group"] == "15 years and over")
        & (labour["Statistics"] == "Estimate")
        & (labour["Data type"] == "Seasonally adjusted")
        & (labour["VALUE"].notna())
    ].copy()

    pivot = (
        filtered.pivot_table(
            index="month",
            columns="Labour force characteristics",
            values="VALUE",
            aggfunc="first",
        )
        .sort_index()
        .rename(columns=LABOUR_RENAMES)
        .reset_index()
    )

    pivot["ref_date"] = pivot["month"].dt.strftime("%Y-%m")
    pivot["employment_yoy_change_thousands"] = pivot["employment_thousands"].diff(12)
    pivot["employment_yoy_change_percent"] = (
        pivot["employment_thousands"].pct_change(12) * 100
    )
    pivot["employment_mom_change_thousands"] = pivot["employment_thousands"].diff(1)
    pivot["unemployment_rate_yoy_change_pp"] = pivot[
        "unemployment_rate_percent"
    ].diff(12)
    pivot["unemployment_rate_mom_change_pp"] = pivot[
        "unemployment_rate_percent"
    ].diff(1)

    ordered = [
        "ref_date",
        "month",
        "population_thousands",
        "labour_force_thousands",
        "employment_thousands",
        "unemployment_thousands",
        "full_time_employment_thousands",
        "part_time_employment_thousands",
        "unemployment_rate_percent",
        "participation_rate_percent",
        "employment_rate_percent",
        "employment_mom_change_thousands",
        "employment_yoy_change_thousands",
        "employment_yoy_change_percent",
        "unemployment_rate_mom_change_pp",
        "unemployment_rate_yoy_change_pp",
    ]
    return pivot[ordered]


def clean_industry_employment() -> pd.DataFrame:
    industry = pd.read_csv(RAW_INDUSTRY, encoding="utf-8-sig")
    industry["VALUE"] = pd.to_numeric(industry["VALUE"], errors="coerce")
    industry["month"] = pd.to_datetime(industry["REF_DATE"] + "-01")
    industry["industry"] = industry[
        "North American Industry Classification System (NAICS)"
    ]
    industry["industry_display"] = industry["industry"].map(strip_naics_codes)
    industry["is_rollup"] = industry["industry"].isin(ROLLUP_INDUSTRIES)

    cleaned = industry[
        (industry["GEO"] == "Ontario")
        & (industry["Statistics"] == "Estimate")
        & (industry["Data type"] == "Seasonally adjusted")
        & (industry["VALUE"].notna())
    ].copy()

    cleaned = cleaned.sort_values(["industry_display", "month"])
    cleaned["employment_thousands"] = cleaned["VALUE"]
    cleaned["employment_mom_change_thousands"] = cleaned.groupby("industry_display")[
        "employment_thousands"
    ].diff(1)
    cleaned["employment_yoy_change_thousands"] = cleaned.groupby("industry_display")[
        "employment_thousands"
    ].diff(12)
    cleaned["employment_yoy_change_percent"] = (
        cleaned.groupby("industry_display")["employment_thousands"].pct_change(12)
        * 100
    )
    cleaned["ref_date"] = cleaned["month"].dt.strftime("%Y-%m")

    ordered = [
        "ref_date",
        "month",
        "industry",
        "industry_display",
        "is_rollup",
        "employment_thousands",
        "employment_mom_change_thousands",
        "employment_yoy_change_thousands",
        "employment_yoy_change_percent",
    ]
    return cleaned[ordered]


def build_dashboard_kpis(labour: pd.DataFrame) -> pd.DataFrame:
    latest = labour.sort_values("month").iloc[-1]
    latest_month = latest["month"]
    prior_year_month = latest_month - pd.DateOffset(years=1)
    prior_year = labour[labour["month"] == prior_year_month].iloc[0]

    rows = [
        {
            "metric": "Latest Ontario employment",
            "value": latest["employment_thousands"],
            "unit": "persons_thousands",
            "latest_month": latest["ref_date"],
            "comparison_month": "",
            "note": "Multiply by 1,000 for persons.",
        },
        {
            "metric": "Latest unemployment rate",
            "value": latest["unemployment_rate_percent"],
            "unit": "percent",
            "latest_month": latest["ref_date"],
            "comparison_month": "",
            "note": "Seasonally adjusted.",
        },
        {
            "metric": "Latest labour force",
            "value": latest["labour_force_thousands"],
            "unit": "persons_thousands",
            "latest_month": latest["ref_date"],
            "comparison_month": "",
            "note": "Multiply by 1,000 for persons.",
        },
        {
            "metric": "Latest participation rate",
            "value": latest["participation_rate_percent"],
            "unit": "percent",
            "latest_month": latest["ref_date"],
            "comparison_month": "",
            "note": "Seasonally adjusted.",
        },
        {
            "metric": "Employment year-over-year change",
            "value": latest["employment_thousands"] - prior_year["employment_thousands"],
            "unit": "persons_thousands",
            "latest_month": latest["ref_date"],
            "comparison_month": prior_year["ref_date"],
            "note": "Latest month minus same month one year earlier.",
        },
        {
            "metric": "Employment year-over-year change rate",
            "value": (
                latest["employment_thousands"] / prior_year["employment_thousands"] - 1
            )
            * 100,
            "unit": "percent",
            "latest_month": latest["ref_date"],
            "comparison_month": prior_year["ref_date"],
            "note": "Same-month year-over-year percent change.",
        },
    ]
    return pd.DataFrame(rows)


def build_industry_summaries(industry: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    detail = industry[~industry["is_rollup"]].copy()
    latest_month = detail["month"].max()
    base_month = pd.Timestamp("2021-01-01")
    prior_year_month = latest_month - pd.DateOffset(years=1)

    latest = detail[detail["month"] == latest_month][
        ["industry_display", "employment_thousands"]
    ].rename(columns={"employment_thousands": "latest_employment_thousands"})
    base = detail[detail["month"] == base_month][
        ["industry_display", "employment_thousands"]
    ].rename(columns={"employment_thousands": "jan2021_employment_thousands"})
    since_base = latest.merge(base, on="industry_display", how="inner")
    since_base["change_thousands"] = (
        since_base["latest_employment_thousands"]
        - since_base["jan2021_employment_thousands"]
    )
    since_base["change_percent"] = (
        since_base["change_thousands"]
        / since_base["jan2021_employment_thousands"]
        * 100
    )
    since_base["base_month"] = base_month.strftime("%Y-%m")
    since_base["latest_month"] = latest_month.strftime("%Y-%m")
    since_base = since_base.sort_values("change_thousands", ascending=False)

    prior_year = detail[detail["month"] == prior_year_month][
        ["industry_display", "employment_thousands"]
    ].rename(columns={"employment_thousands": "prior_year_employment_thousands"})
    yoy = latest.merge(prior_year, on="industry_display", how="inner")
    yoy["yoy_change_thousands"] = (
        yoy["latest_employment_thousands"]
        - yoy["prior_year_employment_thousands"]
    )
    yoy["yoy_change_percent"] = (
        yoy["yoy_change_thousands"] / yoy["prior_year_employment_thousands"] * 100
    )
    yoy["prior_year_month"] = prior_year_month.strftime("%Y-%m")
    yoy["latest_month"] = latest_month.strftime("%Y-%m")
    yoy = yoy.sort_values("yoy_change_thousands", ascending=False)

    return since_base, yoy


def build_charts(
    labour: pd.DataFrame, industry: pd.DataFrame, since_base: pd.DataFrame, yoy: pd.DataFrame
) -> None:
    latest_month = industry["month"].max()
    detail_latest = industry[
        (~industry["is_rollup"]) & (industry["month"] == latest_month)
    ].copy()

    draw_line_chart(
        labour,
        ["employment_thousands"],
        ["Employment"],
        [BLUE],
        "Ontario Employment Trend",
        "Employment (thousands)",
        CHART_DIR / "01_ontario_employment_trend.png",
        format_thousands,
    )
    draw_line_chart(
        labour,
        ["unemployment_rate_percent"],
        ["Unemployment rate"],
        [RED],
        "Ontario Unemployment Rate Trend",
        "Unemployment rate",
        CHART_DIR / "02_ontario_unemployment_rate_trend.png",
        format_percent,
    )
    draw_line_chart(
        labour,
        ["participation_rate_percent", "employment_rate_percent"],
        ["Participation rate", "Employment rate"],
        [BLUE, ORANGE],
        "Ontario Employment and Participation Rates",
        "Rate",
        CHART_DIR / "03_employment_and_participation_rates.png",
        format_percent,
    )
    draw_bar_chart(
        detail_latest,
        "industry_display",
        "employment_thousands",
        f"Top Ontario Industries by Employment, {month_label(latest_month)}",
        "Employment (thousands)",
        CHART_DIR / "04_top_industries_latest_month.png",
        top_n=10,
    )
    draw_bar_chart(
        since_base,
        "industry_display",
        "change_thousands",
        f"Industry Employment Change Since January 2021 to {month_label(latest_month)}",
        "Change in employment (thousands)",
        CHART_DIR / "05_industry_employment_change_since_2021.png",
        diverging=True,
    )
    draw_bar_chart(
        yoy,
        "industry_display",
        "yoy_change_thousands",
        f"Latest Year-over-Year Industry Employment Change, {month_label(latest_month)}",
        "Change in employment (thousands)",
        CHART_DIR / "06_industry_yoy_change_latest_month.png",
        diverging=True,
    )
    create_contact_sheet()


def build_zip() -> None:
    include_paths = [
        PROJECT_DIR / "build_workforce_analytics.py",
        DATA_DIR,
        CHART_DIR,
        DOCS_DIR,
        PROJECT_DIR / "README.md",
    ]
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in include_paths:
            if path.is_file():
                archive.write(path, path.relative_to(PROJECT_DIR))
            else:
                for file_path in sorted(path.rglob("*")):
                    if file_path.is_file():
                        archive.write(file_path, file_path.relative_to(PROJECT_DIR))


def main() -> None:
    ensure_dirs()
    labour = clean_labour_indicators()
    industry = clean_industry_employment()
    dashboard_kpis = build_dashboard_kpis(labour)
    since_base, yoy = build_industry_summaries(industry)

    labour.to_csv(
        DATA_DIR / "clean_labour_indicators_ontario_2021_2026.csv",
        index=False,
        float_format="%.1f",
    )
    industry.to_csv(
        DATA_DIR / "clean_industry_employment_ontario_2021_2026.csv",
        index=False,
        float_format="%.1f",
    )
    dashboard_kpis.to_csv(
        DATA_DIR / "summary_dashboard_kpis.csv", index=False, float_format="%.1f"
    )
    since_base.to_csv(
        DATA_DIR / "summary_industry_change_jan2021_to_latest.csv",
        index=False,
        float_format="%.1f",
    )
    yoy.to_csv(
        DATA_DIR / "summary_industry_yoy_change_latest_month.csv",
        index=False,
        float_format="%.1f",
    )

    build_charts(labour, industry, since_base, yoy)
    build_zip()

    print(f"Latest month: {labour['ref_date'].iloc[-1]}")
    print(f"Cleaned labour rows: {len(labour)}")
    print(f"Cleaned industry rows: {len(industry)}")
    print(f"Package: {ZIP_PATH}")


if __name__ == "__main__":
    main()
