# Power BI Build Guide

## Goal

Build a one-page dashboard titled **Ontario Workforce Snapshot, 2021-2026** using the model tables in `data_model/`.

Use the model tables instead of the raw source CSVs. They are cleaner, easier to explain, and closer to a professional BI workflow.

## Import Tables

Load these CSVs into Power BI:

- `data_model/dim_date.csv`
- `data_model/dim_industry.csv`
- `data_model/fact_labour_market_monthly.csv`
- `data_model/fact_industry_employment_monthly.csv`
- `data_model/measure_catalog.csv` as documentation only

## Relationships

Create these relationships:

```text
dim_date[month_key] 1 -> * fact_labour_market_monthly[month_key]
dim_date[month_key] 1 -> * fact_industry_employment_monthly[month_key]
dim_industry[industry_key] 1 -> * fact_industry_employment_monthly[industry_key]
```

Mark `dim_date` as the date table if Power BI recognizes the `month` column as a date.

## Field Formatting

Use these display conventions:

- Employment and labour force: whole people on KPI cards, thousands in charts
- Unemployment, participation, employment rates: percentage with one decimal
- Change values: signed number with one decimal
- Latest month label: `Apr 2026`

## Core DAX Measures

Create these measures in a dedicated table named `Measures`.

```DAX
Latest Month =
MAX('dim_date'[month])
```

```DAX
Latest Employment (000s) =
VAR LatestMonth = [Latest Month]
RETURN
CALCULATE(
    SUM('fact_labour_market_monthly'[employment_thousands]),
    'dim_date'[month] = LatestMonth
)
```

```DAX
Latest Employment =
[Latest Employment (000s)] * 1000
```

```DAX
Latest Labour Force (000s) =
VAR LatestMonth = [Latest Month]
RETURN
CALCULATE(
    SUM('fact_labour_market_monthly'[labour_force_thousands]),
    'dim_date'[month] = LatestMonth
)
```

```DAX
Latest Labour Force =
[Latest Labour Force (000s)] * 1000
```

```DAX
Latest Unemployment Rate =
VAR LatestMonth = [Latest Month]
RETURN
DIVIDE(
    CALCULATE(
        AVERAGE('fact_labour_market_monthly'[unemployment_rate_percent]),
        'dim_date'[month] = LatestMonth
    ),
    100
)
```

```DAX
Latest Participation Rate =
VAR LatestMonth = [Latest Month]
RETURN
DIVIDE(
    CALCULATE(
        AVERAGE('fact_labour_market_monthly'[participation_rate_percent]),
        'dim_date'[month] = LatestMonth
    ),
    100
)
```

```DAX
Employment YoY Change (000s) =
VAR LatestMonth = [Latest Month]
RETURN
CALCULATE(
    SUM('fact_labour_market_monthly'[employment_yoy_change_thousands]),
    'dim_date'[month] = LatestMonth
)
```

```DAX
Industry Employment (000s) =
SUM('fact_industry_employment_monthly'[employment_thousands])
```

```DAX
Industry YoY Change (000s) =
SUM('fact_industry_employment_monthly'[employment_yoy_change_thousands])
```

```DAX
Industry Change Since Jan 2021 (000s) =
VAR BaseMonth = DATE(2021, 1, 1)
VAR CurrentEmployment = [Industry Employment (000s)]
VAR BaseEmployment =
    CALCULATE(
        [Industry Employment (000s)],
        'dim_date'[month] = BaseMonth
    )
RETURN
CurrentEmployment - BaseEmployment
```

## Dashboard Layout

Use a single page with a restrained analyst style:

- Top row: five KPI cards
- Left column: employment trend, unemployment rate trend, participation/employment rates
- Right column: sector movement bar chart and watchlist table
- Bottom note: source, unit caveat, and limitation

Recommended visuals:

- Card: Latest Employment
- Card: Latest Unemployment Rate
- Card: Latest Labour Force
- Card: Latest Participation Rate
- Card: Employment YoY Change
- Line chart: employment over time
- Line chart: unemployment rate over time
- Line chart: participation rate and employment rate
- Bar chart: industry change since January 2021
- Bar chart or table: latest year-over-year industry change

## Filters

Add only useful filters:

- Year
- Sector type
- Policy theme
- Industry

Avoid overloading the page with filters. For a portfolio dashboard, clarity matters more than maximum interactivity.

## Validation Checks

Before taking screenshots:

- Confirm latest month is April 2026.
- Confirm latest employment is 8,247.9 thousand.
- Confirm latest unemployment rate is 7.5%.
- Confirm latest labour force is 8,920.8 thousand.
- Confirm employment YoY change is +54.3 thousand.
- Confirm aggregate industry employment reconciles to labour force employment within rounding.

## Interview Talking Point

Use this wording:

> I treated the project as a small BI product: I cleaned public labour market data with Python, created fact and dimension tables, documented DAX measures, validated headline totals, and translated the dashboard into a policy-style brief.
