-- Analytics store schema. All timestamps are UTC. Constraints double as data-quality checks:
-- the build fails if the generator ever produces duplicate keys or missing required values.

CREATE TABLE workspaces (
    workspace_id        BIGINT PRIMARY KEY,
    created_at          TIMESTAMPTZ NOT NULL,
    name                VARCHAR NOT NULL,
    founder_user_id     BIGINT NOT NULL,
    acquisition_channel VARCHAR NOT NULL,
    company_size        VARCHAR NOT NULL
);

CREATE TABLE users (
    user_id             BIGINT PRIMARY KEY,
    workspace_id        BIGINT NOT NULL,
    role                VARCHAR NOT NULL CHECK (role IN ('owner', 'member')),
    signup_at           TIMESTAMPTZ NOT NULL,
    signup_platform     VARCHAR NOT NULL CHECK (signup_platform IN ('web', 'ios', 'android')),
    signup_app_version  VARCHAR NOT NULL,
    browser             VARCHAR,
    country             VARCHAR NOT NULL,
    acquisition_channel VARCHAR NOT NULL
);

CREATE TABLE subscriptions (
    workspace_id BIGINT NOT NULL,
    plan         VARCHAR NOT NULL CHECK (plan IN ('team_trial', 'team', 'free')),
    started_at   TIMESTAMPTZ NOT NULL,
    ended_at     TIMESTAMPTZ,
    CHECK (ended_at IS NULL OR ended_at > started_at)
);

CREATE TABLE sessions (
    session_id  BIGINT PRIMARY KEY,
    user_id     BIGINT NOT NULL,
    platform    VARCHAR NOT NULL,
    app_version VARCHAR NOT NULL,
    started_at  TIMESTAMPTZ NOT NULL,
    ended_at    TIMESTAMPTZ NOT NULL,
    CHECK (ended_at >= started_at)
);

CREATE TABLE events (
    event_id    BIGINT PRIMARY KEY,
    user_id     BIGINT NOT NULL,
    session_id  BIGINT NOT NULL,
    event_name  VARCHAR NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    platform    VARCHAR NOT NULL,
    app_version VARCHAR NOT NULL,
    properties  VARCHAR
);

CREATE TABLE releases (
    platform    VARCHAR NOT NULL,
    version     VARCHAR NOT NULL,
    released_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (platform, version)
);

CREATE TABLE experiments (
    experiment_id         VARCHAR PRIMARY KEY,
    name                  VARCHAR NOT NULL,
    hypothesis            VARCHAR NOT NULL,
    randomization_unit    VARCHAR NOT NULL,
    primary_metric        VARCHAR NOT NULL,
    guardrail_metrics     VARCHAR NOT NULL,
    baseline_rate         DOUBLE NOT NULL,
    mde_abs               DOUBLE NOT NULL,
    planned_units_per_arm BIGINT NOT NULL,
    started_at            TIMESTAMPTZ NOT NULL,
    ended_at              TIMESTAMPTZ NOT NULL
);

CREATE TABLE experiment_assignments (
    experiment_id VARCHAR NOT NULL,
    workspace_id  BIGINT NOT NULL,
    variant       VARCHAR NOT NULL CHECK (variant IN ('control', 'treatment')),
    assigned_at   TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (experiment_id, workspace_id)
);

CREATE TABLE experiment_exposures (
    experiment_id VARCHAR NOT NULL,
    workspace_id  BIGINT NOT NULL,
    exposed_at    TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (experiment_id, workspace_id)
);

CREATE TABLE dataset_info (
    key   VARCHAR PRIMARY KEY,
    value VARCHAR NOT NULL
);
