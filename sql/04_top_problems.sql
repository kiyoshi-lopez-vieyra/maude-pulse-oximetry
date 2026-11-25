-- Q4. Which FDA product problem terms are reported most often (all years)?
-- Why: first answer to "which failure types appear most", using FDA's own coding.
-- Caveat: one report can have several problems, so the percentages add up to more than 100.
SELECT problem,
       COUNT(*) AS n_reports,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM reports), 1) AS pct_of_reports
FROM report_problems
GROUP BY problem
ORDER BY n_reports DESC
LIMIT 15;
