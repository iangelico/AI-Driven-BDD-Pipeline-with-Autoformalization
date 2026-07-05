---
name: step-definition-manager
description: Manages Cucumber/Gherkin step definition files, expanding regex patterns and inserting new stubs without breaking existing code.
---

# Step Definition Manager Skill

Use this skill to inspect, modify, expand, or insert Cucumber step definitions in Ruby files.

## Instructions
1. When asked to expand a regex expression (e.g. from `/Given the account balance is (\d+)/` to `/Given the account balance is (?:\$)?(\d+)/`):
   - Locate the exact line containing the old expression.
   - Replace it with the new expression.
   - Do NOT modify any other step definitions, methods, or blocks in the file.
2. When asked to insert a new step definition block:
   - Append it cleanly to the end of the file with double empty lines separating it from previous blocks.
   - Maintain the standard Cucumber format:
     ```ruby
     Given(/^expression$/) do |args|
       # implementation
     end
     ```
3. Return the entire updated file content. Do NOT wrap the response in markdown blocks unless explicitly requested; output only the plain Ruby code.
