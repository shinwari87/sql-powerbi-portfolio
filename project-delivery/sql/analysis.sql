-- A completion recorded after the reporting date still counts as open at that date.
CREATE VIEW milestone_status AS
SELECT m.*, s.as_of,
       CASE WHEN completed_on <= as_of THEN 'Complete'
            WHEN due_on < as_of THEN 'Overdue'
            WHEN due_on = as_of THEN 'Due today'
            ELSE 'Upcoming' END AS status_at_cutoff
FROM milestones AS m CROSS JOIN report_settings AS s;

-- Each fact table has a different grain. Aggregate each before joining to projects.
CREATE VIEW portfolio AS
WITH spend AS (
    SELECT project_id, SUM(amount_usd) AS spend_usd
    FROM costs CROSS JOIN report_settings WHERE posted_on <= as_of
    GROUP BY project_id
), schedule AS (
    SELECT project_id, COUNT(*) AS milestones,
           SUM(status_at_cutoff = 'Complete') AS completed,
           SUM(status_at_cutoff = 'Overdue') AS overdue
    FROM milestone_status GROUP BY project_id
)
SELECT p.*, COALESCE(spend_usd, 0) AS spend_usd,
       COALESCE(spend_usd, 0) - budget_usd AS variance_usd,
       COALESCE(milestones, 0) AS milestones, COALESCE(completed, 0) AS completed,
       COALESCE(overdue, 0) AS overdue
FROM projects AS p
LEFT JOIN spend USING (project_id) LEFT JOIN schedule USING (project_id);
