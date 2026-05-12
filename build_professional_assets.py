from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data_clean"
MODEL_DIR = PROJECT_DIR / "data_model"
DASHBOARD_DIR = PROJECT_DIR / "dashboard"
DOCS_DIR = PROJECT_DIR / "docs"
SQL_DIR = PROJECT_DIR / "sql"
ZIP_PATH = PROJECT_DIR / "ontario_workforce_analytics_professional_package.zip"


GOODS_INDUSTRIES = {
    "Agriculture",
    "Forestry, fishing, mining, quarrying, oil and gas",
    "Utilities",
    "Construction",
    "Manufacturing",
}

THEME_MAP = {
    "Agriculture": "Primary industries",
    "Forestry, fishing, mining, quarrying, oil and gas": "Primary industries",
    "Utilities": "Infrastructure",
    "Construction": "Infrastructure",
    "Manufacturing": "Industrial base",
    "Wholesale and retail trade": "Consumer and distribution",
    "Transportation and warehousing": "Supply chain",
    "Finance, insurance, real estate, rental and leasing": "Business services",
    "Professional, scientific and technical services": "Knowledge economy",
    "Business, building and other support services": "Business services",
    "Educational services": "Public service workforce",
    "Health care and social assistance": "Care economy",
    "Information, culture and recreation": "Creative and digital economy",
    "Accommodation and food services": "Consumer services",
    "Other services (except public administration)": "Consumer services",
    "Public administration": "Public service workforce",
}


def ensure_dirs() -> None:
    MODEL_DIR.mkdir(exist_ok=True)
    DASHBOARD_DIR.mkdir(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)
    SQL_DIR.mkdir(exist_ok=True)


def load_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    labour = pd.read_csv(DATA_DIR / "clean_labour_indicators_ontario_2021_2026.csv")
    industry = pd.read_csv(DATA_DIR / "clean_industry_employment_ontario_2021_2026.csv")
    since_base = pd.read_csv(DATA_DIR / "summary_industry_change_jan2021_to_latest.csv")
    yoy = pd.read_csv(DATA_DIR / "summary_industry_yoy_change_latest_month.csv")
    labour["month"] = pd.to_datetime(labour["month"])
    industry["month"] = pd.to_datetime(industry["month"])
    return labour, industry, since_base, yoy


def make_dim_date(labour: pd.DataFrame) -> pd.DataFrame:
    months = pd.date_range(labour["month"].min(), labour["month"].max(), freq="MS")
    latest = months.max()
    dim_date = pd.DataFrame({"month": months})
    dim_date["month_key"] = dim_date["month"].dt.strftime("%Y%m").astype(int)
    dim_date["ref_date"] = dim_date["month"].dt.strftime("%Y-%m")
    dim_date["year"] = dim_date["month"].dt.year
    dim_date["quarter"] = "Q" + dim_date["month"].dt.quarter.astype(str)
    dim_date["month_number"] = dim_date["month"].dt.month
    dim_date["month_name"] = dim_date["month"].dt.month_name()
    dim_date["year_month_label"] = dim_date["month"].dt.strftime("%b %Y")
    dim_date["is_latest_month"] = dim_date["month"].eq(latest)
    return dim_date


def make_dim_industry(industry: pd.DataFrame, since_base: pd.DataFrame, yoy: pd.DataFrame) -> pd.DataFrame:
    latest_rank = (
        industry[industry["month"].eq(industry["month"].max())]
        .sort_values("employment_thousands", ascending=False)
        .assign(latest_employment_rank=lambda frame: range(1, len(frame) + 1))
    )
    dim = (
        industry[["industry", "industry_display", "is_rollup"]]
        .drop_duplicates()
        .sort_values(["is_rollup", "industry_display"])
        .reset_index(drop=True)
    )
    dim["industry_key"] = range(1, len(dim) + 1)
    dim["sector_type"] = dim.apply(
        lambda row: "Rollup"
        if bool(row["is_rollup"])
        else ("Goods-producing" if row["industry_display"] in GOODS_INDUSTRIES else "Services-producing"),
        axis=1,
    )
    dim["policy_theme"] = dim["industry_display"].map(THEME_MAP).fillna("Aggregate")
    dim = dim.merge(
        latest_rank[["industry_display", "latest_employment_rank"]],
        on="industry_display",
        how="left",
    )
    dim = dim.merge(
        since_base[["industry_display", "change_thousands"]].rename(
            columns={"change_thousands": "change_since_2021_thousands"}
        ),
        on="industry_display",
        how="left",
    )
    dim = dim.merge(
        yoy[["industry_display", "yoy_change_thousands"]].rename(
            columns={"yoy_change_thousands": "latest_yoy_change_thousands"}
        ),
        on="industry_display",
        how="left",
    )
    dim["portfolio_focus_flag"] = (
        (~dim["is_rollup"].astype(bool))
        & (
            dim["change_since_2021_thousands"].abs().ge(75)
            | dim["latest_yoy_change_thousands"].abs().ge(20)
        )
    )
    return dim[
        [
            "industry_key",
            "industry",
            "industry_display",
            "is_rollup",
            "sector_type",
            "policy_theme",
            "latest_employment_rank",
            "change_since_2021_thousands",
            "latest_yoy_change_thousands",
            "portfolio_focus_flag",
        ]
    ]


def make_fact_tables(
    labour: pd.DataFrame, industry: pd.DataFrame, dim_date: pd.DataFrame, dim_industry: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    date_keys = dim_date[["ref_date", "month_key"]]
    industry_keys = dim_industry[["industry_display", "industry_key"]]
    fact_labour = labour.merge(date_keys, on="ref_date", how="left")
    fact_labour = fact_labour[
        [
            "month_key",
            "ref_date",
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
    ]
    fact_industry = industry.merge(date_keys, on="ref_date", how="left").merge(
        industry_keys, on="industry_display", how="left"
    )
    fact_industry = fact_industry[
        [
            "month_key",
            "industry_key",
            "ref_date",
            "industry_display",
            "is_rollup",
            "employment_thousands",
            "employment_mom_change_thousands",
            "employment_yoy_change_thousands",
            "employment_yoy_change_percent",
        ]
    ]
    return fact_labour, fact_industry


def make_measure_catalog() -> pd.DataFrame:
    rows = [
        {
            "measure_name": "Latest Month",
            "table": "Dim Date",
            "dax_expression": "Latest Month = MAX('Dim Date'[month])",
            "format": "MMM yyyy",
            "purpose": "Shows the latest month included in the model.",
        },
        {
            "measure_name": "Latest Employment (000s)",
            "table": "Fact Labour Market",
            "dax_expression": "Latest Employment (000s) = VAR LatestMonth = [Latest Month] RETURN CALCULATE(SUM('Fact Labour Market'[employment_thousands]), 'Dim Date'[month] = LatestMonth)",
            "format": "#,0.0",
            "purpose": "Headline employment KPI.",
        },
        {
            "measure_name": "Latest Employment",
            "table": "Fact Labour Market",
            "dax_expression": "Latest Employment = [Latest Employment (000s)] * 1000",
            "format": "#,0",
            "purpose": "Employment shown as people rather than thousands.",
        },
        {
            "measure_name": "Latest Labour Force (000s)",
            "table": "Fact Labour Market",
            "dax_expression": "Latest Labour Force (000s) = VAR LatestMonth = [Latest Month] RETURN CALCULATE(SUM('Fact Labour Market'[labour_force_thousands]), 'Dim Date'[month] = LatestMonth)",
            "format": "#,0.0",
            "purpose": "Headline labour force KPI.",
        },
        {
            "measure_name": "Latest Unemployment Rate",
            "table": "Fact Labour Market",
            "dax_expression": "Latest Unemployment Rate = VAR LatestMonth = [Latest Month] RETURN DIVIDE(CALCULATE(AVERAGE('Fact Labour Market'[unemployment_rate_percent]), 'Dim Date'[month] = LatestMonth), 100)",
            "format": "0.0%",
            "purpose": "Headline unemployment pressure KPI.",
        },
        {
            "measure_name": "Latest Participation Rate",
            "table": "Fact Labour Market",
            "dax_expression": "Latest Participation Rate = VAR LatestMonth = [Latest Month] RETURN DIVIDE(CALCULATE(AVERAGE('Fact Labour Market'[participation_rate_percent]), 'Dim Date'[month] = LatestMonth), 100)",
            "format": "0.0%",
            "purpose": "Headline labour market attachment KPI.",
        },
        {
            "measure_name": "Employment YoY Change (000s)",
            "table": "Fact Labour Market",
            "dax_expression": "Employment YoY Change (000s) = VAR LatestMonth = [Latest Month] RETURN CALCULATE(SUM('Fact Labour Market'[employment_yoy_change_thousands]), 'Dim Date'[month] = LatestMonth)",
            "format": "+#,0.0;-#,0.0;0.0",
            "purpose": "Same-month year-over-year employment change.",
        },
        {
            "measure_name": "Industry Employment (000s)",
            "table": "Fact Industry Employment",
            "dax_expression": "Industry Employment (000s) = SUM('Fact Industry Employment'[employment_thousands])",
            "format": "#,0.0",
            "purpose": "Employment by selected industry and date context.",
        },
        {
            "measure_name": "Industry YoY Change (000s)",
            "table": "Fact Industry Employment",
            "dax_expression": "Industry YoY Change (000s) = SUM('Fact Industry Employment'[employment_yoy_change_thousands])",
            "format": "+#,0.0;-#,0.0;0.0",
            "purpose": "Industry year-over-year change for the selected month.",
        },
        {
            "measure_name": "Industry Change Since Jan 2021 (000s)",
            "table": "Fact Industry Employment",
            "dax_expression": "Industry Change Since Jan 2021 (000s) = VAR BaseMonth = DATE(2021,1,1) VAR CurrentEmployment = [Industry Employment (000s)] VAR BaseEmployment = CALCULATE([Industry Employment (000s)], 'Dim Date'[month] = BaseMonth) RETURN CurrentEmployment - BaseEmployment",
            "format": "+#,0.0;-#,0.0;0.0",
            "purpose": "Longer-run industry employment change from the project baseline.",
        },
    ]
    return pd.DataFrame(rows)


def make_analysis_summary(
    labour: pd.DataFrame, since_base: pd.DataFrame, yoy: pd.DataFrame
) -> dict:
    latest = labour.sort_values("month").iloc[-1]
    top_long = since_base.head(5)
    weakest_long = since_base.tail(5).sort_values("change_thousands")
    top_yoy = yoy.head(5)
    weakest_yoy = yoy.tail(5).sort_values("yoy_change_thousands")
    return {
        "title": "Ontario Workforce Snapshot, 2021-2026",
        "latest_month": latest["ref_date"],
        "date_range": f"{labour['ref_date'].min()} to {labour['ref_date'].max()}",
        "headline": (
            "Ontario employment is above its 2021 level, but the latest year-over-year picture "
            "shows mixed pressure across sectors."
        ),
        "kpis": {
            "employment_thousands": round(float(latest["employment_thousands"]), 1),
            "labour_force_thousands": round(float(latest["labour_force_thousands"]), 1),
            "unemployment_rate_percent": round(float(latest["unemployment_rate_percent"]), 1),
            "participation_rate_percent": round(float(latest["participation_rate_percent"]), 1),
            "employment_yoy_change_thousands": round(
                float(latest["employment_yoy_change_thousands"]), 1
            ),
            "employment_yoy_change_percent": round(
                float(latest["employment_yoy_change_percent"]), 1
            ),
        },
        "top_long_term_growth": top_long[
            ["industry_display", "change_thousands", "change_percent"]
        ].to_dict("records"),
        "weakest_long_term_growth": weakest_long[
            ["industry_display", "change_thousands", "change_percent"]
        ].to_dict("records"),
        "top_latest_yoy_growth": top_yoy[
            ["industry_display", "yoy_change_thousands", "yoy_change_percent"]
        ].to_dict("records"),
        "weakest_latest_yoy_growth": weakest_yoy[
            ["industry_display", "yoy_change_thousands", "yoy_change_percent"]
        ].to_dict("records"),
        "policy_implications": [
            "Care economy and professional services show large gains since 2021, supporting workforce pipeline and training relevance.",
            "Transportation, health care, and information/culture/recreation lead the latest year-over-year gains.",
            "Education, public administration, professional services, and accommodation/food services show latest year-over-year softness and should be treated as monitoring areas.",
        ],
        "version_2_roadmap": [
            {
                "title": "Occupation and regional breakdowns",
                "work": "Add occupation-level and Ontario regional views so the project can move beyond province-wide sector summaries.",
                "help": "This makes the analysis look more like applied labour market work because it connects sector shifts to where and for whom workforce pressure is happening.",
            },
            {
                "title": "Demand-side signals",
                "work": "Layer in job vacancies, Job Bank signals, or Ontario labour market context to compare employment outcomes with hiring demand.",
                "help": "This strengthens the policy story by showing not only who is employed, but where demand may still be rising or unmet.",
            },
            {
                "title": "Decision-support dashboard polish",
                "work": "Add slicers, annotations, downloadable summary views, and a stronger briefing section for senior leadership use.",
                "help": "This makes the project feel less like a student chart pack and more like a reporting product that could support real planning conversations.",
            },
        ],
    }


def rows_for_dashboard(
    labour: pd.DataFrame, since_base: pd.DataFrame, yoy: pd.DataFrame, industry: pd.DataFrame
) -> dict:
    latest_month = industry["month"].max()
    latest_industries = (
        industry[(~industry["is_rollup"].astype(bool)) & industry["month"].eq(latest_month)]
        .sort_values("employment_thousands", ascending=False)
        .head(10)
    )
    return {
        "labour": json.loads(
            labour[
                [
                    "ref_date",
                    "employment_thousands",
                    "unemployment_rate_percent",
                    "participation_rate_percent",
                    "employment_rate_percent",
                ]
            ].to_json(orient="records")
        ),
        "sinceBase": json.loads(
            since_base[
                [
                    "industry_display",
                    "latest_employment_thousands",
                    "change_thousands",
                    "change_percent",
                ]
            ].to_json(orient="records")
        ),
        "yoy": json.loads(
            yoy[
                [
                    "industry_display",
                    "latest_employment_thousands",
                    "yoy_change_thousands",
                    "yoy_change_percent",
                ]
            ].to_json(orient="records")
        ),
        "latestIndustries": json.loads(
            latest_industries[
                ["industry_display", "employment_thousands"]
            ].to_json(orient="records")
        ),
    }


def dashboard_html(data: dict, summary: dict) -> str:
    template = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ontario Workforce Snapshot, 2021-2026</title>
  <style>
    :root {
      --bg: #f6f8fb;
      --surface: #ffffff;
      --line: #d9e2ec;
      --ink: #16202d;
      --muted: #596779;
      --blue: #2563eb;
      --green: #0f9f6e;
      --red: #dc2626;
      --amber: #d97706;
      --violet: #7c3aed;
      --shadow: 0 14px 30px rgba(21, 32, 45, 0.08);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
      letter-spacing: 0;
    }

    .app {
      max-width: 1480px;
      margin: 0 auto;
      padding: 28px;
    }

    header {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 24px;
      align-items: end;
      margin-bottom: 20px;
    }

    h1 {
      margin: 0;
      font-size: 34px;
      line-height: 1.15;
      letter-spacing: 0;
    }

    .subtitle {
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 15px;
      max-width: 860px;
    }

    .source-pill {
      border: 1px solid var(--line);
      background: var(--surface);
      color: var(--muted);
      border-radius: 8px;
      padding: 10px 12px;
      font-size: 13px;
      white-space: nowrap;
    }

    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 14px;
    }

    .kpi {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      box-shadow: var(--shadow);
      min-height: 116px;
    }

    .kpi .label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      font-weight: 700;
      line-height: 1.25;
    }

    .kpi .value {
      margin-top: 10px;
      font-size: 28px;
      font-weight: 800;
      line-height: 1.1;
    }

    .kpi .note {
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
    }

    .insight-strip {
      display: grid;
      grid-template-columns: 1.15fr 1fr 1fr;
      gap: 14px;
      margin-bottom: 14px;
    }

    .insight {
      background: var(--surface);
      border: 1px solid var(--line);
      border-left: 5px solid var(--blue);
      border-radius: 8px;
      padding: 14px 16px;
      min-height: 94px;
    }

    .insight:nth-child(2) { border-left-color: var(--green); }
    .insight:nth-child(3) { border-left-color: var(--amber); }

    .insight strong {
      display: block;
      font-size: 14px;
      margin-bottom: 6px;
    }

    .insight span {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.4;
    }

    .main-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(420px, 0.9fr);
      gap: 14px;
      align-items: start;
    }

    .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 16px;
      min-width: 0;
    }

    .panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      margin-bottom: 12px;
    }

    h2 {
      margin: 0;
      font-size: 18px;
      line-height: 1.25;
    }

    .panel-note {
      color: var(--muted);
      font-size: 12px;
      margin: 4px 0 0;
    }

    .chart {
      width: 100%;
      height: 340px;
    }

    .chart.tall {
      height: 610px;
    }

    .stack {
      display: grid;
      gap: 14px;
    }

    .segmented {
      display: inline-grid;
      grid-auto-flow: column;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: #eef3f8;
      min-width: 315px;
    }

    .segmented button {
      appearance: none;
      border: 0;
      background: transparent;
      color: var(--muted);
      font: inherit;
      font-size: 12px;
      font-weight: 700;
      padding: 9px 11px;
      cursor: pointer;
    }

    .segmented button.active {
      background: var(--ink);
      color: white;
    }

    .table-wrap {
      overflow-x: auto;
    }

    .roadmap-section {
      margin-top: 14px;
      display: grid;
      gap: 14px;
    }

    .roadmap-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }

    .roadmap-card {
      background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 16px;
      min-height: 178px;
    }

    .roadmap-kicker {
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      font-weight: 800;
      margin-bottom: 10px;
    }

    .roadmap-card h3 {
      margin: 0 0 10px;
      font-size: 18px;
      line-height: 1.2;
    }

    .roadmap-card p {
      margin: 0 0 10px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }

    .roadmap-card .impact {
      color: var(--ink);
      font-size: 13px;
      line-height: 1.45;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }

    th, td {
      text-align: left;
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }

    th {
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0;
    }

    td.num, th.num { text-align: right; }

    .badge {
      display: inline-block;
      border-radius: 6px;
      padding: 4px 7px;
      font-size: 12px;
      font-weight: 700;
      background: #eaf7f1;
      color: var(--green);
    }

    .badge.negative {
      background: #fdecec;
      color: var(--red);
    }

    footer {
      color: var(--muted);
      font-size: 12px;
      margin-top: 16px;
      line-height: 1.45;
    }

    svg text {
      font-family: inherit;
      letter-spacing: 0;
    }

    @media (max-width: 1100px) {
      .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .insight-strip { grid-template-columns: 1fr; }
      .main-grid { grid-template-columns: 1fr; }
      .roadmap-grid { grid-template-columns: 1fr; }
      header { grid-template-columns: 1fr; }
      .source-pill { white-space: normal; }
    }

    @media (max-width: 640px) {
      .app { padding: 16px; }
      h1 { font-size: 27px; }
      .kpi-grid { grid-template-columns: 1fr; }
      .panel-header { align-items: flex-start; flex-direction: column; }
      .segmented { width: 100%; min-width: 0; }
      .chart { height: 300px; }
      .chart.tall { height: 540px; }
    }
  </style>
</head>
<body>
  <main class="app">
    <header>
      <div>
        <h1>Ontario Workforce Snapshot, 2021-2026</h1>
        <p class="subtitle">A portfolio-ready labour market analytics dashboard using Statistics Canada monthly labour force and industry employment data.</p>
      </div>
      <div class="source-pill">Latest month: __LATEST_MONTH__ | Seasonally adjusted | Values in thousands</div>
    </header>

    <section class="kpi-grid" aria-label="Headline KPIs">
      <article class="kpi">
        <div class="label">Employment</div>
        <div class="value" id="kpi-employment"></div>
        <div class="note">people, converted from thousands</div>
      </article>
      <article class="kpi">
        <div class="label">Unemployment rate</div>
        <div class="value" id="kpi-unemployment"></div>
        <div class="note">April 2026</div>
      </article>
      <article class="kpi">
        <div class="label">Labour force</div>
        <div class="value" id="kpi-labour-force"></div>
        <div class="note">people, converted from thousands</div>
      </article>
      <article class="kpi">
        <div class="label">Participation rate</div>
        <div class="value" id="kpi-participation"></div>
        <div class="note">labour market attachment</div>
      </article>
      <article class="kpi">
        <div class="label">Employment YoY</div>
        <div class="value" id="kpi-yoy"></div>
        <div class="note">same month, prior year</div>
      </article>
    </section>

    <section class="insight-strip" aria-label="Analyst findings">
      <div class="insight">
        <strong>Long-run growth is concentrated.</strong>
        <span>Health care, professional services, accommodation and food, retail, and information/culture account for the strongest sector gains since January 2021.</span>
      </div>
      <div class="insight">
        <strong>Latest growth is mixed.</strong>
        <span>Transportation and health care lead the latest year-over-year increase, while education shows the largest decline.</span>
      </div>
      <div class="insight">
        <strong>Policy use case.</strong>
        <span>The dashboard supports workforce planning conversations about training capacity, sector monitoring, and program targeting.</span>
      </div>
    </section>

    <section class="main-grid">
      <div class="stack">
        <section class="panel">
          <div class="panel-header">
            <div>
              <h2>Employment Trend</h2>
              <p class="panel-note">Employment level, January 2021 to April 2026.</p>
            </div>
          </div>
          <div id="employment-chart" class="chart"></div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div>
              <h2>Unemployment Pressure</h2>
              <p class="panel-note">Unemployment rate, shown separately to avoid mixing units with employment level.</p>
            </div>
          </div>
          <div id="unemployment-chart" class="chart"></div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div>
              <h2>Labour Market Attachment</h2>
              <p class="panel-note">Participation and employment rates show the relationship between population growth and employment absorption.</p>
            </div>
          </div>
          <div id="rates-chart" class="chart"></div>
        </section>
      </div>

      <div class="stack">
        <section class="panel">
          <div class="panel-header">
            <div>
              <h2>Sector Movement</h2>
              <p class="panel-note" id="sector-note"></p>
            </div>
            <div class="segmented" role="tablist" aria-label="Sector view">
              <button type="button" class="active" data-mode="since">Since 2021</button>
              <button type="button" data-mode="yoy">Latest YoY</button>
              <button type="button" data-mode="size">Current size</button>
            </div>
          </div>
          <div id="sector-chart" class="chart tall"></div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div>
              <h2>Watchlist</h2>
              <p class="panel-note">Latest year-over-year sector changes for briefing notes and interview talking points.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Industry</th>
                  <th class="num">YoY change</th>
                  <th class="num">YoY rate</th>
                </tr>
              </thead>
              <tbody id="watchlist-body"></tbody>
            </table>
          </div>
        </section>
      </div>
    </section>

    <section class="roadmap-section" aria-label="Version 2 roadmap">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2>Version 2 Roadmap</h2>
            <p class="panel-note">A visible roadmap helps the project read like an evolving analytics product rather than a one-time portfolio exercise.</p>
          </div>
        </div>
        <div class="roadmap-grid" id="roadmap-grid"></div>
      </section>
    </section>

    <footer>
      Source: Statistics Canada Tables 14-10-0287-01 and 14-10-0355-01. Employment values are shown in thousands in the source data. Dashboard analysis is descriptive and should be paired with job postings, regional evidence, and program context before policy decisions.
    </footer>
  </main>

  <script>
    const dashboardData = __DASHBOARD_DATA__;
    const summary = __SUMMARY_DATA__;

    const colours = {
      blue: "#2563eb",
      green: "#0f9f6e",
      red: "#dc2626",
      amber: "#d97706",
      violet: "#7c3aed",
      ink: "#16202d",
      muted: "#596779",
      line: "#d9e2ec"
    };

    function fmtPeopleFromThousands(value) {
      return Math.round(value * 1000).toLocaleString("en-CA");
    }

    function fmtThousands(value, digits = 1) {
      return Number(value).toLocaleString("en-CA", { maximumFractionDigits: digits, minimumFractionDigits: digits });
    }

    function fmtPct(value, digits = 1) {
      return `${Number(value).toFixed(digits)}%`;
    }

    function fmtSigned(value, digits = 1) {
      const n = Number(value);
      const prefix = n > 0 ? "+" : "";
      return `${prefix}${n.toLocaleString("en-CA", { maximumFractionDigits: digits, minimumFractionDigits: digits })}`;
    }

    function svgEl(name, attrs = {}) {
      const el = document.createElementNS("http://www.w3.org/2000/svg", name);
      Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
      return el;
    }

    function clear(el) {
      while (el.firstChild) el.removeChild(el.firstChild);
    }

    function niceTicks(min, max, count = 5) {
      if (min === max) return [min];
      const span = Math.abs(max - min);
      const raw = span / Math.max(count - 1, 1);
      const mag = Math.pow(10, Math.floor(Math.log10(raw)));
      const steps = [1, 2, 2.5, 5, 10].map(v => v * mag);
      const step = steps.find(v => v >= raw) || steps[steps.length - 1];
      const start = Math.floor(min / step) * step;
      const end = Math.ceil(max / step) * step;
      const ticks = [];
      for (let v = start; v <= end + step * 0.5; v += step) ticks.push(Number(v.toFixed(8)));
      return ticks;
    }

    function lineChart(targetId, rows, series, formatter) {
      const target = document.getElementById(targetId);
      clear(target);
      const width = Math.max(target.clientWidth, 640);
      const height = target.clientHeight || 330;
      const margin = { top: 18, right: 34, bottom: 38, left: 70 };
      const innerW = width - margin.left - margin.right;
      const innerH = height - margin.top - margin.bottom;
      const allValues = series.flatMap(s => rows.map(row => Number(row[s.key])));
      const ticks = niceTicks(Math.min(...allValues), Math.max(...allValues), 5);
      const yMin = Math.min(...ticks);
      const yMax = Math.max(...ticks);
      const x = index => margin.left + (rows.length === 1 ? 0 : index * innerW / (rows.length - 1));
      const y = value => margin.top + innerH - ((value - yMin) / (yMax - yMin)) * innerH;
      const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, width: "100%", height: "100%", role: "img" });

      ticks.forEach(tick => {
        const yy = y(tick);
        svg.appendChild(svgEl("line", { x1: margin.left, y1: yy, x2: width - margin.right, y2: yy, stroke: colours.line, "stroke-width": 1 }));
        const label = svgEl("text", { x: margin.left - 10, y: yy + 4, "text-anchor": "end", fill: colours.muted, "font-size": 12 });
        label.textContent = formatter(tick);
        svg.appendChild(label);
      });

      const yearIndexes = rows.map((row, i) => row.ref_date.endsWith("-01") ? i : -1).filter(i => i >= 0);
      if (!yearIndexes.includes(rows.length - 1)) yearIndexes.push(rows.length - 1);
      yearIndexes.forEach(i => {
        const xx = x(i);
        const label = svgEl("text", { x: xx, y: height - 10, "text-anchor": "middle", fill: colours.muted, "font-size": 12 });
        label.textContent = i === rows.length - 1 ? rows[i].ref_date : rows[i].ref_date.slice(0, 4);
        svg.appendChild(label);
      });

      svg.appendChild(svgEl("line", { x1: margin.left, y1: margin.top, x2: margin.left, y2: height - margin.bottom, stroke: "#9aa6b2", "stroke-width": 1.5 }));
      svg.appendChild(svgEl("line", { x1: margin.left, y1: height - margin.bottom, x2: width - margin.right, y2: height - margin.bottom, stroke: "#9aa6b2", "stroke-width": 1.5 }));

      series.forEach((s, index) => {
        const d = rows.map((row, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(Number(row[s.key])).toFixed(1)}`).join(" ");
        svg.appendChild(svgEl("path", { d, fill: "none", stroke: s.colour, "stroke-width": 3, "stroke-linejoin": "round", "stroke-linecap": "round" }));
        const last = rows[rows.length - 1];
        svg.appendChild(svgEl("circle", { cx: x(rows.length - 1), cy: y(Number(last[s.key])), r: 4, fill: s.colour }));
        const legend = svgEl("text", { x: width - margin.right - 8, y: margin.top + 18 + index * 20, "text-anchor": "end", fill: s.colour, "font-size": 12, "font-weight": 700 });
        legend.textContent = s.label;
        svg.appendChild(legend);
      });
      target.appendChild(svg);
    }

    function barChart(targetId, rows, valueKey, labelKey, mode) {
      const target = document.getElementById(targetId);
      clear(target);
      const width = Math.max(target.clientWidth, 640);
      const height = target.clientHeight || 560;
      const margin = { top: 8, right: 46, bottom: 28, left: Math.min(360, Math.max(285, width * 0.46)) };
      const innerW = width - margin.left - margin.right;
      const innerH = height - margin.top - margin.bottom;
      const values = rows.map(row => Number(row[valueKey]));
      const min = mode === "size" ? 0 : Math.min(0, ...values);
      const max = Math.max(...values);
      const ticks = niceTicks(min, max, 5);
      const xMin = Math.min(...ticks);
      const xMax = Math.max(...ticks);
      const x = value => margin.left + ((value - xMin) / (xMax - xMin)) * innerW;
      const rowH = innerH / rows.length;
      const barH = Math.max(12, Math.min(24, rowH * 0.58));
      const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, width: "100%", height: "100%", role: "img" });

      ticks.forEach(tick => {
        const xx = x(tick);
        svg.appendChild(svgEl("line", { x1: xx, y1: margin.top, x2: xx, y2: height - margin.bottom, stroke: colours.line, "stroke-width": 1 }));
        const label = svgEl("text", { x: xx, y: height - 8, "text-anchor": "middle", fill: colours.muted, "font-size": 11 });
        label.textContent = mode === "size" ? Math.round(tick).toLocaleString("en-CA") : fmtSigned(tick, 0);
        svg.appendChild(label);
      });
      svg.appendChild(svgEl("line", { x1: x(0), y1: margin.top, x2: x(0), y2: height - margin.bottom, stroke: "#8f9bab", "stroke-width": 1.5 }));

      rows.forEach((row, i) => {
        const value = Number(row[valueKey]);
        const yMid = margin.top + rowH * i + rowH / 2;
        const x0 = x(0);
        const x1 = x(value);
        const colour = mode === "size" ? colours.blue : (value >= 0 ? colours.green : colours.red);
        const rect = svgEl("rect", {
          x: Math.min(x0, x1),
          y: yMid - barH / 2,
          width: Math.max(1, Math.abs(x1 - x0)),
          height: barH,
          rx: 4,
          fill: colour
        });
        svg.appendChild(rect);
        const labelLines = wrapSvgLabel(row[labelKey], 35).slice(0, 2);
        labelLines.forEach((line, lineIndex) => {
          const label = svgEl("text", {
            x: margin.left - 10,
            y: yMid - ((labelLines.length - 1) * 6) + lineIndex * 12 + 4,
            "text-anchor": "end",
            fill: colours.ink,
            "font-size": 10.5
          });
          label.textContent = line;
          svg.appendChild(label);
        });
        const valueLabel = svgEl("text", {
          x: value >= 0 ? Math.max(x0, x1) + 6 : Math.min(x0, x1) - 6,
          y: yMid + 4,
          "text-anchor": value >= 0 ? "start" : "end",
          fill: colours.muted,
          "font-size": 11
        });
        valueLabel.textContent = mode === "size" ? fmtThousands(value, 0) : fmtSigned(value, 0);
        svg.appendChild(valueLabel);
      });
      target.appendChild(svg);
    }

    function wrapSvgLabel(text, maxChars) {
      const words = String(text).split(" ");
      const lines = [];
      let current = "";
      words.forEach(word => {
        const next = current ? `${current} ${word}` : word;
        if (next.length > maxChars && current) {
          lines.push(current);
          current = word;
        } else {
          current = next;
        }
      });
      if (current) lines.push(current);
      return lines;
    }

    function renderSector(mode) {
      const note = document.getElementById("sector-note");
      if (mode === "since") {
        const rows = [...dashboardData.sinceBase].sort((a, b) => a.change_thousands - b.change_thousands);
        note.textContent = "Employment change from January 2021 to the latest month.";
        barChart("sector-chart", rows, "change_thousands", "industry_display", mode);
      } else if (mode === "yoy") {
        const rows = [...dashboardData.yoy].sort((a, b) => a.yoy_change_thousands - b.yoy_change_thousands);
        note.textContent = "Same-month year-over-year change for the latest month.";
        barChart("sector-chart", rows, "yoy_change_thousands", "industry_display", mode);
      } else {
        const rows = [...dashboardData.latestIndustries].sort((a, b) => a.employment_thousands - b.employment_thousands);
        note.textContent = "Largest sectors by current employment level.";
        barChart("sector-chart", rows, "employment_thousands", "industry_display", mode);
      }
    }

    function renderWatchlist() {
      const body = document.getElementById("watchlist-body");
      const rows = [...dashboardData.yoy].sort((a, b) => Math.abs(b.yoy_change_thousands) - Math.abs(a.yoy_change_thousands)).slice(0, 8);
      body.innerHTML = rows.map(row => {
        const cls = row.yoy_change_thousands < 0 ? "badge negative" : "badge";
        return `<tr><td>${row.industry_display}</td><td class="num"><span class="${cls}">${fmtSigned(row.yoy_change_thousands, 1)}</span></td><td class="num">${fmtSigned(row.yoy_change_percent, 1)}%</td></tr>`;
      }).join("");
    }

    function renderRoadmap() {
      const grid = document.getElementById("roadmap-grid");
      grid.innerHTML = summary.version_2_roadmap.map((item, index) => `
        <article class="roadmap-card">
          <div class="roadmap-kicker">Version 2 priority ${index + 1}</div>
          <h3>${item.title}</h3>
          <p>${item.work}</p>
          <div class="impact"><strong>Why it helps:</strong> ${item.help}</div>
        </article>
      `).join("");
    }

    function render() {
      document.getElementById("kpi-employment").textContent = fmtPeopleFromThousands(summary.kpis.employment_thousands);
      document.getElementById("kpi-unemployment").textContent = fmtPct(summary.kpis.unemployment_rate_percent, 1);
      document.getElementById("kpi-labour-force").textContent = fmtPeopleFromThousands(summary.kpis.labour_force_thousands);
      document.getElementById("kpi-participation").textContent = fmtPct(summary.kpis.participation_rate_percent, 1);
      document.getElementById("kpi-yoy").textContent = `${fmtSigned(summary.kpis.employment_yoy_change_thousands, 1)}k`;
      lineChart("employment-chart", dashboardData.labour, [
        { key: "employment_thousands", label: "Employment", colour: colours.blue }
      ], value => fmtThousands(value, 0));
      lineChart("unemployment-chart", dashboardData.labour, [
        { key: "unemployment_rate_percent", label: "Unemployment rate", colour: colours.red }
      ], value => fmtPct(value, 0));
      lineChart("rates-chart", dashboardData.labour, [
        { key: "participation_rate_percent", label: "Participation", colour: colours.violet },
        { key: "employment_rate_percent", label: "Employment rate", colour: colours.amber }
      ], value => fmtPct(value, 0));
      renderSector("since");
      renderWatchlist();
      renderRoadmap();
    }

    document.querySelectorAll(".segmented button").forEach(button => {
      button.addEventListener("click", () => {
        document.querySelectorAll(".segmented button").forEach(b => b.classList.remove("active"));
        button.classList.add("active");
        renderSector(button.dataset.mode);
      });
    });

    window.addEventListener("resize", () => render());
    render();
  </script>
</body>
</html>
"""
    return (
        template.replace("__LATEST_MONTH__", summary["latest_month"])
        .replace("__DASHBOARD_DATA__", json.dumps(data, separators=(",", ":")))
        .replace("__SUMMARY_DATA__", json.dumps(summary, separators=(",", ":")))
    )


def write_professional_outputs(
    dim_date: pd.DataFrame,
    dim_industry: pd.DataFrame,
    fact_labour: pd.DataFrame,
    fact_industry: pd.DataFrame,
    measures: pd.DataFrame,
    summary: dict,
    dashboard_data: dict,
) -> None:
    html = dashboard_html(dashboard_data, summary)
    dim_date.to_csv(MODEL_DIR / "dim_date.csv", index=False)
    dim_industry.to_csv(MODEL_DIR / "dim_industry.csv", index=False, float_format="%.1f")
    fact_labour.to_csv(
        MODEL_DIR / "fact_labour_market_monthly.csv", index=False, float_format="%.1f"
    )
    fact_industry.to_csv(
        MODEL_DIR / "fact_industry_employment_monthly.csv",
        index=False,
        float_format="%.1f",
    )
    measures.to_csv(MODEL_DIR / "measure_catalog.csv", index=False)
    (MODEL_DIR / "analysis_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (DASHBOARD_DIR / "dashboard_data.json").write_text(
        json.dumps({"summary": summary, "data": dashboard_data}, indent=2),
        encoding="utf-8",
    )
    # Keep the root site entrypoint and the dashboard copy in sync so GitHub Pages
    # and local preview show the same version of the project.
    (DASHBOARD_DIR / "index.html").write_text(html, encoding="utf-8")
    (PROJECT_DIR / "index.html").write_text(html, encoding="utf-8")


def write_sql_files() -> None:
    (SQL_DIR / "schema.sql").write_text(
        """-- Optional SQLite schema for validating the dashboard model.
CREATE TABLE dim_date (
  month_key INTEGER PRIMARY KEY,
  ref_date TEXT,
  month TEXT,
  year INTEGER,
  quarter TEXT,
  month_number INTEGER,
  month_name TEXT,
  year_month_label TEXT,
  is_latest_month INTEGER
);

CREATE TABLE dim_industry (
  industry_key INTEGER PRIMARY KEY,
  industry TEXT,
  industry_display TEXT,
  is_rollup INTEGER,
  sector_type TEXT,
  policy_theme TEXT,
  latest_employment_rank INTEGER,
  change_since_2021_thousands REAL,
  latest_yoy_change_thousands REAL,
  portfolio_focus_flag INTEGER
);

CREATE TABLE fact_labour_market_monthly (
  month_key INTEGER,
  ref_date TEXT,
  population_thousands REAL,
  labour_force_thousands REAL,
  employment_thousands REAL,
  unemployment_thousands REAL,
  full_time_employment_thousands REAL,
  part_time_employment_thousands REAL,
  unemployment_rate_percent REAL,
  participation_rate_percent REAL,
  employment_rate_percent REAL,
  employment_mom_change_thousands REAL,
  employment_yoy_change_thousands REAL,
  employment_yoy_change_percent REAL,
  unemployment_rate_mom_change_pp REAL,
  unemployment_rate_yoy_change_pp REAL
);

CREATE TABLE fact_industry_employment_monthly (
  month_key INTEGER,
  industry_key INTEGER,
  ref_date TEXT,
  industry_display TEXT,
  is_rollup INTEGER,
  employment_thousands REAL,
  employment_mom_change_thousands REAL,
  employment_yoy_change_thousands REAL,
  employment_yoy_change_percent REAL
);
""",
        encoding="utf-8",
    )
    (SQL_DIR / "validation_queries.sql").write_text(
        """-- Reconciliation checks for the Ontario workforce dashboard.

-- 1. Latest headline labour market values.
SELECT
  ref_date,
  employment_thousands,
  labour_force_thousands,
  unemployment_rate_percent,
  participation_rate_percent
FROM fact_labour_market_monthly
ORDER BY month_key DESC
LIMIT 1;

-- 2. Labour force employment vs industry total employment.
SELECT
  l.ref_date,
  ROUND(l.employment_thousands - i.employment_thousands, 1) AS employment_difference_thousands
FROM fact_labour_market_monthly l
JOIN fact_industry_employment_monthly i
  ON l.month_key = i.month_key
JOIN dim_industry d
  ON i.industry_key = d.industry_key
WHERE d.industry_display = 'Total employed, all industries'
ORDER BY ABS(l.employment_thousands - i.employment_thousands) DESC
LIMIT 10;

-- 3. Top latest year-over-year industry gains, excluding rollups.
SELECT
  d.industry_display,
  i.ref_date,
  i.employment_yoy_change_thousands
FROM fact_industry_employment_monthly i
JOIN dim_industry d
  ON i.industry_key = d.industry_key
WHERE d.is_rollup = 0
  AND i.month_key = (SELECT MAX(month_key) FROM fact_industry_employment_monthly)
ORDER BY i.employment_yoy_change_thousands DESC
LIMIT 10;
""",
        encoding="utf-8",
    )


def build_zip() -> None:
    include_dirs = [DATA_DIR, MODEL_DIR, PROJECT_DIR / "charts", DASHBOARD_DIR, DOCS_DIR, SQL_DIR]
    include_files = [
        PROJECT_DIR / "README.md",
        PROJECT_DIR / "build_workforce_analytics.py",
        PROJECT_DIR / "build_professional_assets.py",
    ]
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in include_files:
            if path.exists():
                archive.write(path, path.relative_to(PROJECT_DIR))
        for directory in include_dirs:
            if not directory.exists():
                continue
            for file_path in sorted(directory.rglob("*")):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(PROJECT_DIR))


def main() -> None:
    ensure_dirs()
    labour, industry, since_base, yoy = load_outputs()
    dim_date = make_dim_date(labour)
    dim_industry = make_dim_industry(industry, since_base, yoy)
    fact_labour, fact_industry = make_fact_tables(labour, industry, dim_date, dim_industry)
    measures = make_measure_catalog()
    summary = make_analysis_summary(labour, since_base, yoy)
    dashboard_data = rows_for_dashboard(labour, since_base, yoy, industry)
    write_professional_outputs(
        dim_date, dim_industry, fact_labour, fact_industry, measures, summary, dashboard_data
    )
    write_sql_files()
    build_zip()
    print(f"Professional package: {ZIP_PATH}")
    print(f"Interactive dashboard: {DASHBOARD_DIR / 'index.html'}")
    print(f"Model tables: {MODEL_DIR}")


if __name__ == "__main__":
    main()
