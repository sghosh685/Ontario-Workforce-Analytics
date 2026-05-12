-- Reconciliation checks for the Ontario workforce dashboard.

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
