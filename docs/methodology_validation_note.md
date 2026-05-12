# Methodology and Validation Note

## Scope

This project analyzes Ontario labour market conditions from January 2021 through the latest month available in the two source files. It focuses on headline labour force indicators and employment by industry.

## Source Data

The project uses two Statistics Canada CSV extracts:

- Table 14-10-0287-01 for labour force characteristics
- Table 14-10-0355-01 for employment by industry

Both files are filtered to Ontario, seasonally adjusted values, and estimate rows.

## Preparation Steps

For labour indicators, the script filters to:

- `GEO = Ontario`
- `Gender = Total - Gender`
- `Age group = 15 years and over`
- `Statistics = Estimate`
- `Data type = Seasonally adjusted`

The labour indicators are reshaped from long format to one monthly row per period, with separate columns for employment, labour force, unemployment, participation rate, employment rate, and unemployment rate.

For industry employment, the script filters to Ontario, estimates, and seasonally adjusted values. It keeps the full industry history and flags aggregate rollups separately. Industry-ranking summaries exclude these rollups:

- Total employed, all industries
- Goods-producing sector
- Services-producing sector

## Validation Checks

The build script validates that:

- Date coverage runs from January 2021 through the latest available month in the source files.
- Labour market values are numeric after import.
- Industry values are numeric after import.
- Year-over-year comparisons use the same calendar month one year earlier.
- Industry growth summaries compare the latest month with January 2021.
- The labour market employment total reconciles with the industry table's `Total employed, all industries` row within rounding. The maximum absolute difference observed is approximately 0.1 thousand.

## Data Model

The professional build creates a simple star-style model for Power BI:

- `dim_date.csv`
- `dim_industry.csv`
- `fact_labour_market_monthly.csv`
- `fact_industry_employment_monthly.csv`

The industry dimension adds sector type and policy theme fields so the dashboard can support analyst-style filtering without changing the source data.

## Limitations

Employment values are reported in thousands. The dashboard should label units clearly to avoid overstating or understating counts.

This is a descriptive dashboard. It identifies employment trends and sector differences, but it does not prove why those changes occurred. Economic interpretation should be paired with qualitative context, employer demand data, job postings, immigration, training capacity, and policy/program information where available.

## Policy Interpretation

The dashboard is best used to identify where workforce planning questions may be needed. Strong growth sectors may require talent pipeline support. Weak or volatile sectors may require closer monitoring, targeted retraining, or program review.
