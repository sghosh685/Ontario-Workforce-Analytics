-- Optional SQLite schema for validating the dashboard model.
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
