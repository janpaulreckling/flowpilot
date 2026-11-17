-- Derived tables, built once after loading. The metric layer reads only these and the raw
-- tables; every definition here is documented in docs/METRICS.md.

-- One row per signup (workspace owner) with the timestamps of the onboarding milestones.
CREATE TABLE owner_cohort AS
WITH firsts AS (
    SELECT user_id,
           min(occurred_at) FILTER (WHERE event_name = 'project_created') AS project_at,
           min(occurred_at) FILTER (WHERE event_name = 'invite_sent') AS invite_at
    FROM events
    WHERE event_name IN ('project_created', 'invite_sent')
    GROUP BY user_id
),
team AS (
    SELECT workspace_id, min(signup_at) AS first_teammate_at
    FROM users WHERE role = 'member' GROUP BY workspace_id
)
SELECT u.user_id, u.workspace_id, u.signup_at,
       CAST(u.signup_at AS DATE) AS signup_date,
       u.signup_platform, u.signup_app_version, u.acquisition_channel, w.company_size,
       u.country, u.browser,
       f.project_at, f.invite_at, t.first_teammate_at
FROM users u
JOIN workspaces w USING (workspace_id)
LEFT JOIN firsts f USING (user_id)
LEFT JOIN team t USING (workspace_id)
WHERE u.role = 'owner';

-- D25: a user is active on a day when they performed at least one core action.
CREATE TABLE user_active_days AS
SELECT DISTINCT user_id, CAST(occurred_at AS DATE) AS day, platform
FROM events
WHERE event_name IN ('task_created', 'task_completed', 'comment_added', 'timeline_viewed',
                     'integration_used');

-- Outcome of each 14-day trial: the plan that follows it (NULL while the trial is running).
CREATE TABLE trial_outcomes AS
SELECT t.workspace_id, t.started_at AS trial_start, t.ended_at AS trial_end, n.plan AS next_plan
FROM subscriptions t
LEFT JOIN subscriptions n
       ON n.workspace_id = t.workspace_id AND n.started_at = t.ended_at
WHERE t.plan = 'team_trial';

-- Daily volumes for data-quality monitoring.
CREATE TABLE daily_event_counts AS
SELECT CAST(occurred_at AS DATE) AS day, event_name, platform, count(*) AS n
FROM events GROUP BY ALL;

CREATE TABLE daily_sessions AS
SELECT CAST(started_at AS DATE) AS day, platform, count(*) AS n
FROM sessions GROUP BY ALL;
