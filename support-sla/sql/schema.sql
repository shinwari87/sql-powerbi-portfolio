CREATE TABLE response_targets (
  priority TEXT PRIMARY KEY,
  target_minutes INTEGER NOT NULL CHECK (target_minutes > 0)
);
CREATE TABLE snapshot (cutoff_utc TEXT PRIMARY KEY);
CREATE TABLE tickets (
  ticket_id TEXT PRIMARY KEY,
  queue TEXT NOT NULL,
  priority TEXT NOT NULL REFERENCES response_targets(priority),
  opened_utc TEXT NOT NULL
);
CREATE TABLE events (
  event_id TEXT PRIMARY KEY,
  ticket_id TEXT NOT NULL REFERENCES tickets(ticket_id),
  event_type TEXT NOT NULL CHECK (event_type IN ('auto_ack','internal_note','agent_reply')),
  event_utc TEXT NOT NULL
);
