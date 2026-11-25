-- Q3. Who submits the reports?
-- Why: a system dominated by manufacturer reports reflects manufacturers' complaint handling.
SELECT report_source_code,
       COUNT(*) AS n_reports,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM reports), 1) AS pct
FROM reports
GROUP BY report_source_code
ORDER BY n_reports DESC;
