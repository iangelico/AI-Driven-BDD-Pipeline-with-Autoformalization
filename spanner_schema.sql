-- DDL Schema for BDD Ecosystem Property Graph (Spanner Graph compliant)

-- 1. Create Node Tables
CREATE TABLE UserStory (
  story_id STRING(MAX) NOT NULL,
  title STRING(MAX),
  description STRING(MAX),
  embedding ARRAY<FLOAT64>,
  verified_spec STRING(MAX),
) PRIMARY KEY (story_id);

CREATE TABLE GherkinStep (
  step_id STRING(MAX) NOT NULL,
  step_type STRING(10), -- Given, When, Then
  text STRING(MAX),
  embedding ARRAY<FLOAT64>,
) PRIMARY KEY (step_id);

CREATE TABLE RubyDefinition (
  definition_id STRING(MAX) NOT NULL,
  expression STRING(MAX), -- Regex or string matcher
  code_block STRING(MAX),
  embedding ARRAY<FLOAT64>,
) PRIMARY KEY (definition_id);

-- 2. Create Edge Tables
CREATE TABLE StoryImplementsStep (
  story_id STRING(MAX) NOT NULL,
  step_id STRING(MAX) NOT NULL,
  PRIMARY KEY (story_id, step_id),
  CONSTRAINT fk_story FOREIGN KEY (story_id) REFERENCES UserStory (story_id),
  CONSTRAINT fk_step FOREIGN KEY (step_id) REFERENCES GherkinStep (step_id)
);

CREATE TABLE StepBindsDefinition (
  step_id STRING(MAX) NOT NULL,
  definition_id STRING(MAX) NOT NULL,
  PRIMARY KEY (step_id, definition_id),
  CONSTRAINT fk_bind_step FOREIGN KEY (step_id) REFERENCES GherkinStep (step_id),
  CONSTRAINT fk_bind_def FOREIGN KEY (definition_id) REFERENCES RubyDefinition (definition_id)
);

CREATE TABLE StoryDependsOnStory (
  story_id STRING(MAX) NOT NULL,
  depends_on_story_id STRING(MAX) NOT NULL,
  PRIMARY KEY (story_id, depends_on_story_id),
  CONSTRAINT fk_story_dep FOREIGN KEY (story_id) REFERENCES UserStory (story_id),
  CONSTRAINT fk_depends_on_story FOREIGN KEY (depends_on_story_id) REFERENCES UserStory (story_id)
);

-- 3. Declare Property Graph
CREATE OR REPLACE PROPERTY GRAPH BddGraph
  NODE TABLES (
    UserStory,
    GherkinStep,
    RubyDefinition
  )
  EDGE TABLES (
    StoryImplementsStep
      SOURCE KEY (story_id) REFERENCES UserStory (story_id)
      DESTINATION KEY (step_id) REFERENCES GherkinStep (step_id)
      LABEL IMPLEMENTS,
    StepBindsDefinition
      SOURCE KEY (step_id) REFERENCES GherkinStep (step_id)
      DESTINATION KEY (definition_id) REFERENCES RubyDefinition (definition_id)
      LABEL BINDS,
    StoryDependsOnStory
      SOURCE KEY (story_id) REFERENCES UserStory (story_id)
      DESTINATION KEY (depends_on_story_id) REFERENCES UserStory (story_id)
      LABEL DEPENDS_ON
  );
