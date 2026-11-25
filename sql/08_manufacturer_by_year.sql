-- Q8. How much of each year's volume comes from the largest manufacturer group?
-- Why: explains peaks in Q1 (for example 2014-2016).
WITH yearly AS (
    SELECT year, manufacturer_group, COUNT(*) AS n
    FROM report_features GROUP BY year, manufacturer_group
),
ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY year ORDER BY n DESC) AS rk,
              SUM(n) OVER (PARTITION BY year) AS year_total
    FROM yearly
)
SELECT year, manufacturer_group AS top_group, n AS top_group_reports, year_total,
       ROUND(100.0 * n / year_total, 1) AS top_group_pct
FROM ranked
WHERE rk = 1 AND year >= 2005
ORDER BY year;
