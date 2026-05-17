# Roadmap: Ontario Workforce Analytics 2.0

This document outlines the next phases for the Ontario Workforce Analytics project.

> Build a reusable StatCan ingestion and profiling engine that can turn selected, compatible public data tables into documented dashboard-ready analytics products.

For the deeper system design, see:

- `docs/cortex_engine_blueprint.md`

## Phase 1: Dataset Profiling

**Objective:** Inspect any candidate StatCan table and report whether it is dashboard-ready.

Features:

- Accept a StatCan table ID or product ID
- Download or read the full-table CSV
- Detect date, value, geography, unit, scalar, and topic dimensions
- Report date range, frequency, table shape, missing values, and candidate dashboard type
- Generate a profile JSON and a human-readable summary

## Phase 2: Config-Driven Builds

**Objective:** Generate clean model tables and summaries from a small config file.

Features:

- Create a draft config from the profile
- Let the analyst define the main geography, category dimension, filters, and metrics
- Generate fact and dimension tables
- Produce validation reports
- Produce summary JSON for the website

## Phase 3: Demand and Regional Labour Market Layer

**Objective:** Strengthen the existing Ontario workforce dashboard with deeper labour market context.

Features:

- Add occupation-level indicators
- Add Ontario regional or census metropolitan area views
- Add job vacancy or wage signals where available
- Compare employment change with demand-side indicators

## Phase 4: Public-Data Monitor Hub

**Objective:** Use the same engine to produce additional monitors.

Candidate projects:

- Ontario Workforce Snapshot
- Ontario Inflation Monitor
- Ontario Housing Affordability Snapshot
- Ontario Workforce Demand Layer

Features:

- One landing page
- Project cards
- Source table metadata
- Dashboard links
- Methodology notes
- Validation reports

## What Not To Build Yet

Avoid these until the core engine works:

- full SaaS authentication
- database deployment
- massive daily delta ingestion
- automatic dashboards for every StatCan table
- AI-written policy claims
- complex SDMX transformations

## Next Sprint

Build the smallest useful engine:

1. `main.py profile <table_id>`
2. CSV ZIP download or local CSV input
3. schema profile JSON
4. readable terminal summary
5. test on the two current labour market tables
6. test on one inflation table
