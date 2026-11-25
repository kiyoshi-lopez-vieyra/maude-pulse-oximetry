-- Q7. Which manufacturer groups submit the most reports?
-- Why: if one company dominates, trends may describe that company's reporting, not oximeters in general.
-- Caveat: more reports usually mean more devices sold, not a worse device. Usage data is not available.
SELECT manufacturer_group,
       COUNT(*) AS n_reports,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM report_features), 1) AS pct
FROM report_features
GROUP BY manufacturer_group
ORDER BY n_reports DESC
LIMIT 10;
