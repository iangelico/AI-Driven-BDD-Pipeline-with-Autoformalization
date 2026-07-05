---
name: ruby-step-scaffolder
description: Generates Ruby Cucumber step definition stubs from Gherkin step strings.
---
# Ruby Step Scaffolder Skill

This skill guides the agent in writing standard Ruby step definition stubs for Cucumber scenarios.

## 🎯 Goal
Auto-generate a Ruby step definition stub matching a specific Gherkin step string (Given, When, Then).

## 🛠️ Ruby Cucumber Patterns

### 1. Simple Step Mapping
Gherkin: `Given the user is logged in`
Ruby:
```ruby
Given(/^the user is logged in$/) do
  # TODO: Implement step logic
  pending
end
```

### 2. Parameter Matching (Regex)
Gherkin: `Given the account balance is 100`
Ruby:
```ruby
Given(/^the account balance is (\d+)$/) do |balance|
  @balance = balance.to_i
end
```

Gherkin: `When the customer withdraws 50 dollars`
Ruby:
```ruby
When(/^the customer withdraws (\d+) dollars$/) do |amount|
  @withdrawal_result = @account.withdraw(amount.to_i)
end
```
