-- Q2. How are reports split by event type (Malfunction, Injury, Death, Other) each year?
-- Why: shows whether the severity mix changes over time.
-- Caveat: event_type is assigned by the reporter; a "Death" report does not mean the device caused the death.
SELECT f.year,
       SUM(r.event_type = 'Malfunction') AS malfunction,
       SUM(r.event_type = 'Injury')      AS injury,
       SUM(r.event_type = 'Death')       AS death,
       SUM(r.event_type = 'Other' OR r.event_type IS NULL OR r.event_type = '') AS other_or_missing,
       COUNT(*) AS total
FROM reports r
JOIN report_features f USING (mdr_report_key)
GROUP BY f.year
ORDER BY f.year;
