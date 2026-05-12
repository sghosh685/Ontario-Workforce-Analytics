# Ontario Workforce Analytics Dashboard

**Live Dashboard:** [View Interactive Snapshot](https://sghosh685.github.io/Ontario-Workforce-Analytics/)

## Portfolio Case Study

**Ontario Workforce Snapshot, 2021-2026** is a compact labour market analytics project built from public Statistics Canada data. It cleans monthly Ontario labour force and industry employment data, creates a Power BI-ready model layer, produces validation checks, and translates the analysis into dashboard and policy-brief deliverables.

This project is designed to support Senior Analyst, BI analyst, and data/reporting applications by showing the full workflow:

```text
public source data -> Python cleaning -> model tables -> DAX measures -> dashboard -> policy insight
```

## Executive Summary

Latest available month: **April 2026**

- Ontario employment: **8,247.9 thousand**, or about **8.25 million people**
- Ontario unemployment rate: **7.5%**
- Ontario labour force: **8,920.8 thousand**, or about **8.92 million people**
- Ontario participation rate: **64.8%**
- Employment year-over-year change: **+54.3 thousand**, or **+0.7%**

Sector story:

- The largest employment gains since January 2021 are in health care and social assistance, professional/scientific/technical services, accommodation and food services, wholesale and retail trade, and information/culture/recreation.
- The latest year-over-year gains are led by transportation and warehousing, health care and social assistance, and information/culture/recreation.
- The latest year-over-year soft spots are educational services, public administration, professional/scientific/technical services, accommodation and food services, and manufacturing.

## Source Data

- Statistics Canada Table 14-10-0287-01: Labour force characteristics
- Statistics Canada Table 14-10-0355-01: Employment by industry

Both files are filtered to Ontario, estimates, and seasonally adjusted monthly values.

## Project Structure

```text
Ontario-Workforce-Analytics-Dashboard
├── build_workforce_analytics.py
├── build_professional_assets.py
├── data_clean
├── data_model
├── dashboard
├── charts
├── docs
└── sql
```

## Key Outputs

Cleaned CSVs:

- `data_clean/clean_labour_indicators_ontario_2021_2026.csv`
- `data_clean/clean_industry_employment_ontario_2021_2026.csv`
- `data_clean/summary_dashboard_kpis.csv`
- `data_clean/summary_industry_change_jan2021_to_latest.csv`
- `data_clean/summary_industry_yoy_change_latest_month.csv`

Power BI-ready model:

- `data_model/dim_date.csv`
- `data_model/dim_industry.csv`
- `data_model/fact_labour_market_monthly.csv`
- `data_model/fact_industry_employment_monthly.csv`
- `data_model/measure_catalog.csv`
- `data_model/analysis_summary.json`

Dashboard and visuals:

- `dashboard/index.html`
- `dashboard/dashboard_data.json`
- `charts/chart_contact_sheet.png`
- Six PNG chart exports in `charts/`

Documentation:

- `docs/methodology_validation_note.md`
- `docs/policy_brief.md`
- `docs/powerbi_build_guide.md`
- `docs/executive_deck_storyboard.md`
- `docs/resume_application_snippets.md`

Validation:

- `sql/schema.sql`
- `sql/validation_queries.sql`

## Rebuild

Run the base data build:

```bash
python3 build_workforce_analytics.py
```

Then run the professional portfolio build:

```bash
python3 build_professional_assets.py
```

The professional ZIP package is created at:

```text
ontario_workforce_analytics_professional_package.zip
```

## Suggested Power BI Page

Build one dashboard page with:

- KPI cards: employment, unemployment rate, labour force, participation rate, employment YoY change
- Employment trend line chart
- Unemployment rate trend line chart
- Participation and employment rate trend chart
- Industry change since January 2021 bar chart
- Latest year-over-year industry change bar chart
- A short text box with 2-3 policy implications

## Notes

Employment values are reported in thousands. For example, `8247.9` means `8,247,900` people.

This is a descriptive labour market dashboard. It identifies trends and monitoring areas, but it does not claim causality.
