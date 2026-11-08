-- Pass rate for each assistant version over the same scenario set.
CREATE VIEW version_pass_rate AS
SELECT v.version, v.label,
       COUNT(j.scenario_id) AS scenarios,
       SUM(j.result = 'Pass') AS passed,
       SUM(j.result = 'Fail') AS failed,
       ROUND(100.0 * SUM(j.result = 'Pass') / COUNT(j.scenario_id), 1) AS pass_pct
FROM versions v LEFT JOIN judgments j USING (version)
GROUP BY v.version, v.label;

-- One row per scenario with both versions side by side. A scenario is an
-- improvement when B fixed an A failure and a regression when B broke an
-- answer A got right. Pivoting on the primary key keeps the grain at one row
-- per scenario, so counts never double.
CREATE VIEW scenario_comparison AS
SELECT s.scenario_id, s.topic, s.customer_message, s.expected_answer,
       ra.response_text AS a_response, rb.response_text AS b_response,
       ja.result AS a_result, jb.result AS b_result,
       ja.failure_type AS a_failure_type, jb.failure_type AS b_failure_type,
       ja.reviewer_note AS a_note, jb.reviewer_note AS b_note,
       CASE WHEN ja.result = 'Fail' AND jb.result = 'Pass' THEN 'Improved'
            WHEN ja.result = 'Pass' AND jb.result = 'Fail' THEN 'Regressed'
            WHEN ja.result = 'Pass' THEN 'Both pass'
            ELSE 'Both fail' END AS change
FROM scenarios s
JOIN judgments ja ON ja.scenario_id = s.scenario_id AND ja.version = 'A'
JOIN judgments jb ON jb.scenario_id = s.scenario_id AND jb.version = 'B'
JOIN responses ra ON ra.scenario_id = s.scenario_id AND ra.version = 'A'
JOIN responses rb ON rb.scenario_id = s.scenario_id AND rb.version = 'B';

-- How many scenarios moved in each direction.
CREATE VIEW change_summary AS
SELECT change, COUNT(*) AS scenarios
FROM scenario_comparison GROUP BY change;

-- Pass rates by topic for both versions, with the net movement. Topics where
-- B lost ground show a negative change even when the overall rate improved.
CREATE VIEW topic_scorecard AS
SELECT topic, COUNT(*) AS scenarios,
       SUM(a_result = 'Pass') AS a_passed,
       SUM(b_result = 'Pass') AS b_passed,
       ROUND(100.0 * SUM(a_result = 'Pass') / COUNT(*), 1) AS a_pass_pct,
       ROUND(100.0 * SUM(b_result = 'Pass') / COUNT(*), 1) AS b_pass_pct,
       SUM(change = 'Improved') AS improved,
       SUM(change = 'Regressed') AS regressed,
       SUM(b_result = 'Pass') - SUM(a_result = 'Pass') AS net_change
FROM scenario_comparison GROUP BY topic;

-- Failures by topic and failure type for each version.
CREATE VIEW failure_breakdown AS
SELECT s.topic, j.version, j.failure_type, COUNT(*) AS failures
FROM judgments j JOIN scenarios s USING (scenario_id)
WHERE j.result = 'Fail'
GROUP BY s.topic, j.version, j.failure_type;

-- The regressions a reviewer should read first: A passed, B failed, with the
-- customer message, the expected answer, and both replies side by side.
CREATE VIEW regressions AS
SELECT scenario_id, topic, b_failure_type, b_note, customer_message,
       expected_answer, a_response, b_response
FROM scenario_comparison WHERE change = 'Regressed';

-- Re-grade every response from the rubric so recorded judgments can be
-- audited. A reply fails if it contains any forbidden phrase or lacks any
-- required phrase. This view must agree with the judgments table.
CREATE VIEW rubric_audit AS
SELECT r.scenario_id, r.version,
       CASE WHEN EXISTS (SELECT 1 FROM rubric_checks c
                         WHERE c.scenario_id = r.scenario_id
                           AND ((c.check_kind = 'forbidden' AND instr(r.response_text, c.phrase) > 0)
                             OR (c.check_kind = 'required' AND instr(r.response_text, c.phrase) = 0)))
            THEN 'Fail' ELSE 'Pass' END AS rubric_result,
       j.result AS recorded_result
FROM responses r JOIN judgments j USING (scenario_id, version);
