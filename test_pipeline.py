import os
import unittest
from unittest.mock import patch, MagicMock
from pipeline import run_pipeline, DafnySpecResponse, GherkinFeatureResponse

class TestPipelineOrchestration(unittest.TestCase):
    
    def setUp(self):
        self.output_feature = "test_output.feature"
        self.output_spec = "test_spec.dfy"
        
        # Clean up files if they exist
        for f in [self.output_feature, self.output_spec]:
            if os.path.exists(f):
                os.remove(f)

    def tearDown(self):
        # Clean up generated files after test run
        for f in [self.output_feature, self.output_spec]:
            if os.path.exists(f):
                os.remove(f)

    @patch("pipeline.generate_structured_output")
    def test_successful_self_correction_loop(self, mock_generate):
        """
        Tests the pipeline verification loop when:
        1. Initial spec is generated but has a syntax error (using '=' instead of ':=').
        2. Local Dafny verifier fails and returns errors.
        3. LLM is invoked again with errors, returns corrected spec (using ':=').
        4. Local Dafny verifier succeeds.
        5. Gherkin tests are generated and written to disk.
        """
        # Define mock responses
        # 1. Buggy Dafny Spec (using '=' instead of ':=' in constructor)
        buggy_spec = DafnySpecResponse(
            explanation="Initial draft representing the ATM account withdrawal state.",
            spec_code=(
                "class Account {\n"
                "  var balance: int\n"
                "  constructor(initialBalance: int)\n"
                "    requires initialBalance >= 0\n"
                "    ensures balance == initialBalance\n"
                "  {\n"
                "    balance = initialBalance; // Bug: '=' instead of ':='\n"
                "  }\n"
                "}\n"
            )
        )
        
        # 2. Corrected Dafny Spec
        corrected_spec = DafnySpecResponse(
            explanation="Corrected constructor assignment to use Dafny's ':=' operator.",
            spec_code=(
                "class Account {\n"
                "  var balance: int\n"
                "  constructor(initialBalance: int)\n"
                "    requires initialBalance >= 0\n"
                "    ensures balance == initialBalance\n"
                "  {\n"
                "    balance := initialBalance;\n"
                "  }\n"
                "}\n"
            )
        )
        
        # 3. Final Gherkin Feature
        gherkin_feature = GherkinFeatureResponse(
            explanation="Gherkin scenarios modeling the constructor initialization.",
            feature_content=(
                "Feature: Account Initialization\n"
                "  Scenario: Initialize account with positive balance\n"
                "    Given the initial deposit balance is 100\n"
                "    When the account is created\n"
                "    Then the account balance should be 100\n"
            )
        )
        
        # Mock responses sequence: Initial Spec -> Corrected Spec -> Gherkin Feature
        mock_generate.side_effect = [buggy_spec, corrected_spec, gherkin_feature]
        
        # Run the pipeline
        user_story = "As a user, I want to initialize my bank account with a starting balance."
        success = run_pipeline(
            user_story=user_story,
            output_feature_path=self.output_feature,
            output_spec_path=self.output_spec,
            max_attempts=3
        )
        
        # Assertions
        self.assertTrue(success, "Pipeline should complete successfully after correction.")
        
        # Verify call counts (should be exactly 3: draft spec, correction spec, gherkin generation)
        self.assertEqual(mock_generate.call_count, 3)
        
        # Verify files were created
        self.assertTrue(os.path.exists(self.output_spec), "Dafny spec file should be created.")
        self.assertTrue(os.path.exists(self.output_feature), "Gherkin feature file should be created.")
        
        # Verify file content
        with open(self.output_spec, "r", encoding="utf-8") as f:
            spec_content = f.read()
            self.assertIn("balance := initialBalance;", spec_content)
            
        with open(self.output_feature, "r", encoding="utf-8") as f:
            feature_content = f.read()
            self.assertIn("Feature: Account Initialization", feature_content)
            
        print("\n[TEST PASSED] Pipeline self-correction loop verified successfully via mocks!")

if __name__ == "__main__":
    unittest.main()
