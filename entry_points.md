# Entry Points - AI-Driven BDD Pipeline with Autoformalization

This file lists the entry points and commands required to configure, test, and run the formal BDD verification pipeline.

---

## 1. Setup & Environment Configuration

To download and extract the local Dafny verifier binary and configure dependencies:
```bash
# Install package requirements (including google-adk)
pip install -r requirements.txt

# Run setup to download and extract Dafny v4.11.0 to /tools
python tools_setup.py
```

---

## 2. Test Verification

To run the mock-based asynchronous test suite which validates the ADK agents, self-correction loop, and Gherkin file generation:
```bash
python test_pipeline_adk.py
```

---

## 3. Running Pipeline Execution

To run the formal verification pipeline on a natural language User Story:

### A. Directly from a text string:
```bash
python main_adk.py --story "As a bank customer, I want to withdraw cash. The balance must never go below 0." --output features/output_test.feature --spec specs/verified_spec.dfy
```

### B. Using a User Story text file:
```bash
python main_adk.py --story stories/sample_story.txt --output features/atm_withdrawal.feature --spec specs/atm_verified.dfy
```
*(All input and output paths are resolved dynamically using `SETTINGS.json`)*
