-- Q1. How many DQA reports did FDA receive each year?
-- Why: baseline volume; every later count must be read against it.
-- Caveat: counts are reports, not failures in the population. 2026 is partial (data until the download date).
SELECT year,
       COUNT(*) AS n_reports
FROM report_features
GROUP BY year
ORDER BY year;
