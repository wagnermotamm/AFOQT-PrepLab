-- Banco de treino do AFOQT. Questões originais. Não é material oficial da USAF.

CREATE TABLE sources (
  source_key TEXT PRIMARY KEY,
  institution TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  published TEXT,
  updated TEXT,
  accessed TEXT NOT NULL,
  doc_type TEXT NOT NULL,
  license_notes TEXT NOT NULL,
  relevant TEXT NOT NULL,
  verification TEXT NOT NULL,
  role TEXT NOT NULL
);

CREATE TABLE topics (
  topic_key TEXT PRIMARY KEY,
  subtest TEXT NOT NULL,
  name TEXT NOT NULL,
  competency TEXT NOT NULL,
  level_notes TEXT NOT NULL,
  source_keys TEXT NOT NULL,
  official_basis TEXT NOT NULL
);

CREATE TABLE questions (
  question_id TEXT PRIMARY KEY,
  subtest TEXT NOT NULL,
  topic TEXT NOT NULL,
  subtopic TEXT NOT NULL,
  difficulty TEXT NOT NULL,
  stem TEXT NOT NULL,
  explanation_pt TEXT NOT NULL,
  why_correct_pt TEXT NOT NULL,
  concept_ref TEXT NOT NULL,
  source_key TEXT NOT NULL,
  source_url TEXT NOT NULL,
  estimated_seconds INTEGER NOT NULL,
  tags TEXT NOT NULL,
  figure_svg TEXT,
  validation_status TEXT NOT NULL,
  check_kind TEXT,
  check_value TEXT,
  scored INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE options (
  question_id TEXT NOT NULL,
  position INTEGER NOT NULL,
  label TEXT NOT NULL,
  text TEXT NOT NULL,
  is_correct INTEGER NOT NULL,
  why_wrong_pt TEXT NOT NULL,
  PRIMARY KEY (question_id, position),
  FOREIGN KEY (question_id) REFERENCES questions(question_id)
);

CREATE TABLE glossary (
  question_id TEXT NOT NULL,
  word TEXT NOT NULL,
  meaning_pt TEXT NOT NULL,
  PRIMARY KEY (question_id, word),
  FOREIGN KEY (question_id) REFERENCES questions(question_id)
);

CREATE TABLE validation_results (
  question_id TEXT PRIMARY KEY,
  passed INTEGER NOT NULL,
  checks TEXT NOT NULL,
  FOREIGN KEY (question_id) REFERENCES questions(question_id)
);

CREATE TABLE exam_blueprints (
  blueprint_key TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  section_json TEXT NOT NULL
);

CREATE INDEX idx_questions_subtest ON questions(subtest);
CREATE INDEX idx_questions_topic ON questions(topic);
CREATE INDEX idx_questions_status ON questions(validation_status);
