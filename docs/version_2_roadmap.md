# Roadmap: Ontario Workforce Analytics 2.0

This document outlines the strategic evolution of the Ontario Workforce Analytics Dashboard from a static data snapshot into a dynamic, production-grade decision support tool.

## Phase 1: Dynamic Data Ingestion (The "Workable" Feature)
**Objective:** Enable the dashboard to process any compatible StatCan dataset without requiring a code update.

*   **Feature: Drag-and-Drop Parser**
    *   Integrate `PapaParse.js` to handle client-side CSV parsing.
    *   Implement a "Schema Mapper" that detects StatCan column headers (Ref_Date, Value, Vector, etc.).
    *   Allow users to drop a raw CSV file from Table 14-10-0287-01 to instantly update the visuals.
*   **Feature: Data Export**
    *   Allow users to download the filtered "Watchlist" or "Sector Movement" data as a clean Excel/CSV file for briefing notes.

## Phase 2: Live API Integration & Demand Signals
**Objective:** Automate data updates and integrate demand-side intelligence.

*   **Feature: StatCan Web Service (WDS)**
    *   Replace embedded JSON with a fetch call to the Statistics Canada Web Data Service.
    *   Implement a "Refresh" button that triggers a live pull of the most recent monthly release.
*   **Feature: Demand-Side Indicators**
    *   Integrate **Job Vacancy and Wage Survey (JVWS)** data to show labor shortages alongside employment levels.
    *   Add Job Bank trend context to highlight high-demand occupations.

## Phase 3: Advanced Analytics & UX
**Objective:** Increase the depth of insight and improve the analytical user experience.

*   **Feature: Regional & Occupation Slicing**
    *   Include data for Ontario Economic Regions and specific 2-digit NOC (Occupation) codes.
    *   Add an interactive SVG map for geographic workforce distribution.
*   **Feature: Demographic Deep-Dives**
    *   Add toggles for Gender, Age Group (15-24, 25-54, 55+), and Education level.
*   **Feature: Executive Polish**
    *   Implement a "Briefing Mode" that generates a one-page executive summary PDF based on the current view.
