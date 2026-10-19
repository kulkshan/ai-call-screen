CREATE TABLE IF NOT EXISTS scenarios (
  scenario_id TEXT PRIMARY KEY, archetype TEXT NOT NULL, subtype TEXT NOT NULL,
  difficulty TEXT NOT NULL, label TEXT NOT NULL, malicious_from_turn INTEGER,
  variant_of TEXT, corpus_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS turns (
  turn_id TEXT PRIMARY KEY, scenario_id TEXT, call_id TEXT, turn_index INTEGER NOT NULL,
  speaker TEXT NOT NULL, text TEXT NOT NULL, turn_label TEXT, expected_signals_json TEXT
);
CREATE TABLE IF NOT EXISTS calls (
  call_id TEXT PRIMARY KEY, scenario_id TEXT, source TEXT NOT NULL, started_at TEXT,
  final_tier TEXT, label TEXT
);
CREATE TABLE IF NOT EXISTS signals (
  signal_id TEXT PRIMARY KEY, call_id TEXT NOT NULL, turn_id TEXT NOT NULL, signal_type TEXT NOT NULL,
  present INTEGER NOT NULL, confidence REAL NOT NULL, evidence TEXT, extractor_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reporters (
  reporter_id TEXT PRIMARY KEY, reliability_a REAL NOT NULL, reliability_b REAL NOT NULL,
  activity REAL NOT NULL, split TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reports (
  report_id TEXT PRIMARY KEY, reporter_id TEXT NOT NULL, number_profile TEXT NOT NULL,
  verdict INTEGER NOT NULL, reported_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
  decision_id TEXT PRIMARY KEY, call_id TEXT NOT NULL, turn_index INTEGER NOT NULL,
  p_scam REAL NOT NULL, tier TEXT NOT NULL, tier_costs_json TEXT NOT NULL,
  escalated INTEGER NOT NULL, policy_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS adjudications (
  adjudication_id TEXT PRIMARY KEY, call_id TEXT NOT NULL, predicted_tier TEXT NOT NULL,
  reviewer_label TEXT, corrected_label TEXT, timestamp TEXT NOT NULL, reviewer TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS metric_runs (
  run_id TEXT PRIMARY KEY, git_sha TEXT NOT NULL, timestamp TEXT NOT NULL,
  fusion_version TEXT NOT NULL, config_json TEXT NOT NULL, metrics_json TEXT NOT NULL
);
