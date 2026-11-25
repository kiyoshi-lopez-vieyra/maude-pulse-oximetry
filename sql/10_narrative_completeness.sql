-- Q10. How complete and how long are the event descriptions each year?
-- Why: the classifier needs text; years with short or missing descriptions will be harder.
SELECT year,
       COUNT(*) AS n_reports,
       SUM(description IS NULL) AS missing_description,
       ROUND(AVG(CASE WHEN description IS NOT NULL THEN description_chars END), 0) AS avg_chars
FROM report_features
GROUP BY year
ORDER BY year;
