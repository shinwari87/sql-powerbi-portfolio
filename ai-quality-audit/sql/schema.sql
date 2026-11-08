CREATE TABLE versions (
  version TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  evaluated_on TEXT NOT NULL
);
CREATE TABLE scenarios (
  scenario_id TEXT PRIMARY KEY,
  topic TEXT NOT NULL,
  customer_message TEXT NOT NULL,
  expected_answer TEXT NOT NULL
);
-- The grading rubric: phrases a passing reply must contain (required) or
-- must not contain (forbidden), with the failure type assigned when it trips.
CREATE TABLE rubric_checks (
  scenario_id TEXT NOT NULL REFERENCES scenarios(scenario_id),
  check_id TEXT PRIMARY KEY,
  check_kind TEXT NOT NULL CHECK (check_kind IN ('required','forbidden')),
  phrase TEXT NOT NULL,
  failure_type TEXT NOT NULL
);
CREATE TABLE responses (
  scenario_id TEXT NOT NULL REFERENCES scenarios(scenario_id),
  version TEXT NOT NULL REFERENCES versions(version),
  response_text TEXT NOT NULL,
  PRIMARY KEY (scenario_id, version)
);
-- One reviewer judgment per scenario and version. The primary key makes a
-- second judgment for the same pair impossible to load.
CREATE TABLE judgments (
  scenario_id TEXT NOT NULL REFERENCES scenarios(scenario_id),
  version TEXT NOT NULL REFERENCES versions(version),
  result TEXT NOT NULL CHECK (result IN ('Pass','Fail')),
  failure_type TEXT,
  reviewer_note TEXT,
  PRIMARY KEY (scenario_id, version),
  FOREIGN KEY (scenario_id, version) REFERENCES responses(scenario_id, version)
);
