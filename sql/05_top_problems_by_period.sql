-- Q5. How does the share of the main problems change between periods?
-- Why: counts rise and fall with total volume; the share (% of reports in the period) is comparable.
-- Periods: before 2014, 2014-2019 (reporting peak), 2020-2026.
WITH periods AS (
    SELECT mdr_report_key,
           CASE WHEN year < 2014 THEN '1_before_2014'
                WHEN year <= 2019 THEN '2_2014_2019'
                ELSE '3_2020_2026' END AS period
    FROM report_features
),
totals AS (SELECT period, COUNT(*) AS n_period FROM periods GROUP BY period),
top AS (SELECT problem FROM report_problems GROUP BY problem ORDER BY COUNT(*) DESC LIMIT 10)
SELECT p.period,
       rp.problem,
       COUNT(*) AS n_reports,
       t.n_period,
       ROUND(100.0 * COUNT(*) / t.n_period, 1) AS pct_of_period
FROM report_problems rp
JOIN periods p USING (mdr_report_key)
JOIN totals t USING (period)
WHERE rp.problem IN (SELECT problem FROM top)
GROUP BY p.period, rp.problem
ORDER BY rp.problem, p.period;
