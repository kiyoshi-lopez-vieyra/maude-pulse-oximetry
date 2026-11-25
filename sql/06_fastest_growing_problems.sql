-- Q6. Which problems grew the most in share: 2023-2025 versus 2020-2022?
-- Why: second research question ("which grow fastest"), using complete years only (2026 is partial).
-- Caveat: share changes can come from coding practice or one manufacturer's reporting; this is a signal to investigate, not proof.
-- Only problems with at least 20 reports across both windows, to avoid noise from tiny counts.
WITH win AS (
    SELECT mdr_report_key,
           CASE WHEN year BETWEEN 2020 AND 2022 THEN 'before'
                WHEN year BETWEEN 2023 AND 2025 THEN 'after' END AS w
    FROM report_features
    WHERE year BETWEEN 2020 AND 2025
),
totals AS (
    SELECT SUM(w = 'before') AS n_before, SUM(w = 'after') AS n_after FROM win
),
counts AS (
    SELECT rp.problem,
           SUM(win.w = 'before') AS k_before,
           SUM(win.w = 'after')  AS k_after
    FROM report_problems rp JOIN win USING (mdr_report_key)
    GROUP BY rp.problem
)
SELECT problem, k_before, k_after,
       ROUND(100.0 * k_before / n_before, 1) AS pct_before,
       ROUND(100.0 * k_after  / n_after, 1)  AS pct_after,
       ROUND(100.0 * k_after / n_after - 100.0 * k_before / n_before, 1) AS change_pp
FROM counts, totals
WHERE k_before + k_after >= 20
ORDER BY change_pp DESC;
