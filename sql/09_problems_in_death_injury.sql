-- Q9. Which problems appear most in reports classified as Death or Injury?
-- Why: post-market risk management (ISO 14971-inspired) prioritizes problems linked to harm.
-- Caveat: association within reports only; it does not show the device caused the harm.
SELECT rp.problem,
       SUM(r.event_type = 'Death')  AS death,
       SUM(r.event_type = 'Injury') AS injury,
       COUNT(*) AS total_harm_reports
FROM report_problems rp
JOIN reports r USING (mdr_report_key)
WHERE r.event_type IN ('Death', 'Injury')
GROUP BY rp.problem
ORDER BY total_harm_reports DESC
LIMIT 15;
