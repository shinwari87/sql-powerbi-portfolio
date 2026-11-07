-- Find the first human response visible at the snapshot. Joining a single row
-- per ticket prevents repeat replies, acknowledgments or notes multiplying counts.
CREATE VIEW ticket_outcomes AS
WITH first_human AS (
    SELECT e.ticket_id, MIN(e.event_utc) AS first_reply_utc
    FROM events e JOIN tickets t USING (ticket_id) CROSS JOIN snapshot s
    WHERE e.event_type = 'agent_reply'
      AND e.event_utc BETWEEN t.opened_utc AND s.cutoff_utc
    GROUP BY e.ticket_id
), timing AS (
    SELECT t.*, s.cutoff_utc, target_minutes, f.first_reply_utc,
           CAST((strftime('%s',f.first_reply_utc)-strftime('%s',t.opened_utc))/60 AS INTEGER) AS wait_minutes,
           CAST((strftime('%s',s.cutoff_utc)-strftime('%s',t.opened_utc))/60 AS INTEGER) AS age_minutes,
           datetime(t.opened_utc, '+' || target_minutes || ' minutes') AS due_utc
    FROM tickets t JOIN response_targets USING (priority) CROSS JOIN snapshot s
    LEFT JOIN first_human f USING (ticket_id)
    WHERE t.opened_utc <= s.cutoff_utc
)
SELECT *, CASE WHEN first_reply_utc <= due_utc THEN 'Met'
               WHEN first_reply_utc IS NOT NULL OR due_utc < cutoff_utc THEN 'Missed'
               ELSE 'Pending' END AS outcome
FROM timing;

CREATE VIEW queue_scorecard AS
WITH ordered AS (
    SELECT queue, wait_minutes,
           ROW_NUMBER() OVER (PARTITION BY queue ORDER BY wait_minutes, ticket_id) AS rn,
           COUNT(*) OVER (PARTITION BY queue) AS n
    FROM ticket_outcomes WHERE wait_minutes IS NOT NULL
), p90 AS (
    -- Nearest-rank percentile: ceil(0.9*n), using integer arithmetic.
    SELECT queue, wait_minutes AS p90_minutes FROM ordered WHERE rn=(9*n+9)/10
)
SELECT t.queue, COUNT(*) AS tickets, SUM(outcome='Met') AS met,
       SUM(outcome='Missed') AS missed, SUM(outcome='Pending') AS pending,
       ROUND(100.0*SUM(outcome='Met')/NULLIF(SUM(outcome<>'Pending'),0),1) AS met_pct,
       SUM(outcome='Missed' AND first_reply_utc IS NULL) AS overdue_unanswered,
       MAX(p90_minutes) AS p90_minutes
FROM ticket_outcomes t LEFT JOIN p90 USING(queue) GROUP BY t.queue;
