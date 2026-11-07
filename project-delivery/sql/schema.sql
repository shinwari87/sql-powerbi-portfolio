CREATE TABLE projects (
    project_id TEXT PRIMARY KEY, project TEXT NOT NULL, program TEXT NOT NULL,
    budget_usd INTEGER NOT NULL CHECK (budget_usd > 0)
);
CREATE TABLE costs (
    cost_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects,
    posted_on TEXT NOT NULL, amount_usd INTEGER NOT NULL
);
CREATE TABLE milestones (
    milestone_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects,
    milestone TEXT NOT NULL, due_on TEXT NOT NULL, completed_on TEXT
);
CREATE TABLE report_settings (as_of TEXT PRIMARY KEY);
