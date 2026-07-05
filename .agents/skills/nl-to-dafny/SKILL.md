---
name: nl-to-dafny
description: Translates a natural language user story into a formal Dafny specification class. Enforces class invariants via pre/postconditions.
---
# NL-to-Dafny Formalizer Skill

This skill guides the agent in translating natural language User Stories into mathematically sound and compiler-verifiable Dafny specifications.

## 🎯 Goal
Translate informal requirements into a state machine representation in Dafny where operations are guarded by logical preconditions (`requires`) and postconditions (`ensures`).

## 🛠️ Dafny Syntax Constraints

### 🚨 Critical Class Invariant Rule
*   Dafny **does not support** the `invariant` keyword directly inside a class body (doing so throws a `rbrace expected` parse error).
*   Invariants must be represented by either:
    1.  Adding standard preconditions (`requires`) and postconditions (`ensures`) to all methods.
    2.  Defining a predicate `predicate Valid() reads this { state_variable >= 0 }` and requiring/ensuring `Valid()` on every constructor and method.

### 📝 Example Schema
```dafny
class Account {
  var balance: int

  constructor(initialBalance: int)
    requires initialBalance >= 0
    ensures balance == initialBalance
  {
    balance := initialBalance;
  }

  method Withdraw(amount: int)
    requires amount > 0
    requires balance >= amount
    ensures balance == old(balance) - amount
    modifies this
  {
    balance := balance - amount;
  }
}
```

## 🔄 Self-Correction Strategy
If the verifier fails:
1.  Read the compiler output file.
2.  If the compiler reports syntax errors, resolve symbol mismatches (e.g. use `:=` instead of `=` for assignment).
3.  If the verifier reports that a postcondition might not hold, strengthen the preconditions of the corresponding method.
