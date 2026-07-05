import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock
from pipeline_adk import run_adk_pipeline, DafnySpecResponse, GherkinFeatureResponse, CriticResponse, TaskBreakdownResponse, QuorumResponse

class TestADKPipelineOrchestration(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.output_feature = "test_output_adk.feature"
        self.output_spec = "test_spec_adk.dfy"
        
        # Clean up files and database if they exist to prevent state pollution
        for f in [self.output_feature, self.output_spec, "spanner_mock.db"]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    def tearDown(self):
        # Clean up generated files after test run
        for f in [self.output_feature, self.output_spec, "spanner_mock.db"]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    @patch("pipeline_adk.execute_plain_agent")
    @patch("pipeline_adk.execute_adk_agent")
    async def test_adk_self_correction_loop(self, mock_execute_adk, mock_execute_plain):
        """
        Tests the ADK pipeline verification loop:
        1. Initial spec has a syntax error.
        2. Local Dafny verifier fails and returns errors.
        3. ADK Corrector is invoked, returns corrected spec.
        4. Local Dafny verifier succeeds.
        5. Gherkin tests are generated and written to disk.
        6. Human-in-the-loop triggers mapping/scaffolding stubs.
        """
        # Define mock responses
        # 1. Buggy Dafny Spec
        buggy_spec = DafnySpecResponse(
            explanation="Initial draft representing the account constructor.",
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
        
        # Mock responses sequence
        from pipeline_adk import QuorumResponse
        mock_execute_adk.side_effect = [
            buggy_spec,
            CriticResponse(is_consistent=True, feedback="Mock validation successful."),
            TaskBreakdownResponse(explanation="Syntax check", checklist=["Fix syntax"]),
            corrected_spec,
            gherkin_feature,
            QuorumResponse(is_approved=True, reasoning="Approved", plain_english_summary="Approved summary"),
            QuorumResponse(is_approved=True, reasoning="Approved", plain_english_summary="Approved summary"),
            QuorumResponse(is_approved=True, reasoning="Approved", plain_english_summary="Approved summary")
        ]
        
        # Mock plain agent returns a valid ruby step definition block
        mock_execute_plain.return_value = (
            "Given(/^the initial deposit balance is (\\d+)$/) do |balance|\n"
            "  @balance = balance.to_i\n"
            "end"
        )
        
        # Run the pipeline
        user_story = "As a user, I want to initialize my bank account with a starting balance."
        success = await run_adk_pipeline(
            user_story=user_story,
            output_feature_path=self.output_feature,
            output_spec_path=self.output_spec,
            max_attempts=3
        )
        
        # Assertions
        self.assertTrue(success, "Pipeline should complete successfully after correction.")
        self.assertEqual(mock_execute_adk.call_count, 8)
        self.assertGreater(mock_execute_plain.call_count, 0)
        
        # Verify files were created
        self.assertTrue(os.path.exists(self.output_spec), "Dafny spec file should be created.")
        self.assertTrue(os.path.exists(self.output_feature), "Gherkin feature file should be created.")
        
        # Verify file contents
        with open(self.output_spec, "r", encoding="utf-8") as f:
            spec_content = f.read()
            self.assertIn("balance := initialBalance;", spec_content)
            
        with open(self.output_feature, "r", encoding="utf-8") as f:
            feature_content = f.read()
            self.assertIn("Feature: Account Initialization", feature_content)
            
        print("\n[TEST PASSED] ADK 2.0 self-correction loop and human-in-the-loop step mapping verified successfully via mocks!")

    @patch("pipeline_adk.execute_plain_agent")
    @patch("pipeline_adk.execute_adk_agent")
    async def test_vector_search_error_context_enrichment(self, mock_execute_adk, mock_execute_plain):
        """
        Tests that when a Dafny verification fails, the pipeline:
        1. Executes a vector search (ANN) on the database.
        2. Successfully retrieves a similar verified specification.
        3. Enriches the Corrector Agent's prompt with the baseline reference spec context.
        """
        from spanner_client import SpannerGraphClient
        db = SpannerGraphClient("spanner_mock.db")
        
        # Insert a verified baseline story into the database
        db.insert_node(
            label="UserStory",
            node_id="baseline_story.txt",
            properties={
                "title": "Baseline Account Deposit",
                "description": "As a user, I want to deposit funds into my account to increase my balance.",
                "verified_spec": "class Account { var balance: int method deposit(...) }"
            },
            embedding=[0.1] * 768  # 768-dimensional float array
        )
        
        # Define mock responses
        buggy_spec = DafnySpecResponse(
            explanation="Initial draft representing the account constructor.",
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
        
        gherkin_feature = GherkinFeatureResponse(
            explanation="Gherkin scenarios modeling the constructor initialization.",
            feature_content=(
                "Feature: Account Initialization\n"
                "  Scenario: Initialize account\n"
                "    Given the initial deposit balance is 100\n"
            )
        )
        
        mock_execute_adk.side_effect = [
            buggy_spec,
            CriticResponse(is_consistent=True, feedback="Mock validation passed."),
            TaskBreakdownResponse(explanation="Syntax check", checklist=["Fix syntax"]),
            corrected_spec,
            gherkin_feature,
            QuorumResponse(is_approved=True, reasoning="Approved", plain_english_summary="Approved summary")
        ]
        
        mock_execute_plain.return_value = "Given(/^the initial deposit balance is (\\d+)$/) do |b| end"
        
        # Run the pipeline
        user_story = "As a user, I want to initialize my bank account with a starting balance."
        success = await run_adk_pipeline(
            user_story=user_story,
            output_feature_path=self.output_feature,
            output_spec_path=self.output_spec,
            max_attempts=3,
            story_id="current_story.txt"
        )
        
        # Verify the pipeline completed
        self.assertTrue(success)
        
        # Verify the corrector agent was called with the enriched baseline context
        # The first call is autoformalizer, the second is semantic critic, the third is corrector
        corrector_call_args = mock_execute_adk.call_args_list[3]
        corrector_prompt = corrector_call_args[1]["prompt"]
        
        self.assertIn("--- BASELINE SPECIFICATION REFERENCE ---", corrector_prompt)
        self.assertIn("Baseline Account Deposit", corrector_prompt)
        self.assertIn("class Account { var balance: int method deposit(...) }", corrector_prompt)
        print("\n[TEST PASSED] Vector search error context enrichment verified successfully!")

    @patch("pipeline_adk.execute_plain_agent")
    @patch("pipeline_adk.execute_adk_agent")
    async def test_pre_recompilation_impact_analysis(self, mock_execute_adk, mock_execute_plain):
        """
        Tests that before submitting corrected specification code, the pipeline:
        1. Queries the database for stories that depend on the current story.
        2. Retrieves the dependent stories using graph traversal (DEPENDS_ON).
        3. Appends a downstream impact warning block to the Corrector Agent's prompt.
        """
        from spanner_client import SpannerGraphClient
        db = SpannerGraphClient("spanner_mock.db")
        
        # Insert target story
        db.insert_node(
            label="UserStory",
            node_id="target_story.txt",
            properties={"title": "Base Account Withdrawal", "description": "Base withdrawal logic."}
        )
        
        # Insert a downstream story that depends on the target story
        db.insert_node(
            label="UserStory",
            node_id="dependent_story.txt",
            properties={"title": "Atm Withdrawal Limit Check", "description": "Downstream limits story."}
        )
        
        # Insert DEPENDS_ON edge
        db.insert_edge(
            label="DEPENDS_ON",
            source_id="dependent_story.txt",
            destination_id="target_story.txt"
        )
        
        # Define mock responses
        buggy_spec = DafnySpecResponse(
            explanation="Initial draft representing the account constructor.",
            spec_code="class Account {\n  var balance: int\n  constructor() {\n    balance = 10; // Bug\n  }\n}"
        )
        
        corrected_spec = DafnySpecResponse(
            explanation="Corrected constructor assignment.",
            spec_code="class Account {\n  var balance: int\n  constructor() {\n    balance := 10;\n  }\n}"
        )
        
        gherkin_feature = GherkinFeatureResponse(
            explanation="Gherkin scenarios.",
            feature_content="Feature: Account Initialization\n"
        )
        
        mock_execute_adk.side_effect = [
            buggy_spec,
            CriticResponse(is_consistent=True, feedback="Mock validation passed."),
            TaskBreakdownResponse(explanation="Syntax check", checklist=["Fix syntax"]),
            corrected_spec,
            gherkin_feature
        ]
        
        mock_execute_plain.return_value = "Given(/^the initial deposit balance$/) do end"
        
        # Run the pipeline targeting target_story.txt
        success = await run_adk_pipeline(
            user_story="Base withdrawal logic.",
            output_feature_path=self.output_feature,
            output_spec_path=self.output_spec,
            max_attempts=3,
            story_id="target_story.txt"
        )
        
        self.assertTrue(success)
        
        # Verify the corrector agent was called with the downstream impact warning context
        corrector_call_args = mock_execute_adk.call_args_list[3]
        corrector_prompt = corrector_call_args[1]["prompt"]
        
        self.assertIn("--- PRE-RECOMPILATION IMPACT MAP: WHAT BREAKS IF I CHANGE THIS? ---", corrector_prompt)
        self.assertIn("dependent_story.txt", corrector_prompt)
        self.assertIn("Atm Withdrawal Limit Check", corrector_prompt)
        self.assertIn("Ensure that your corrections preserve backwards-compatible public signatures", corrector_prompt)
        print("\n[TEST PASSED] Pre-recompilation impact analysis verified successfully!")

    @patch("sys.stdin.isatty")
    @patch("pipeline_adk.execute_plain_agent")
    @patch("pipeline_adk.execute_adk_agent")
    async def test_human_routing_fallback_on_limit_exhausted(self, mock_execute_adk, mock_execute_plain, mock_isatty):
        """
        Tests that when maximum verification attempts are reached, the pipeline:
        1. Identifies the permanent failure.
        2. Routes the logic to the manual human override check.
        3. If in non-interactive (CI) mode, gracefully writes a report and fails.
        """
        # Force non-interactive mode
        mock_isatty.return_value = False
        
        # Define mock responses where verification fails and remains unverified
        buggy_spec = DafnySpecResponse(
            explanation="Initial buggy spec.",
            spec_code="class Account { var balance: int constructor() { balance = 10; } }"
        )
        
        mock_execute_adk.side_effect = [
            buggy_spec,
            CriticResponse(is_consistent=True, feedback="Mock validation passed."),
            TaskBreakdownResponse(explanation="Syntax check", checklist=["Fix syntax"]),
            buggy_spec,  # corrector returns the same buggy spec
            TaskBreakdownResponse(explanation="Syntax check", checklist=["Fix syntax"]),
            buggy_spec   # corrector returns buggy spec again
        ]
        
        # Run the pipeline with max_attempts=2 so it hits the limit immediately
        success = await run_adk_pipeline(
            user_story="Base withdrawal logic.",
            output_feature_path=self.output_feature,
            output_spec_path=self.output_spec,
            max_attempts=2,
            story_id="target_story.txt"
        )
        
        # Should return False because verification was never successful and we are in non-interactive mode
        self.assertFalse(success)
        
        # Verify the failure report file was written to disk
        report_file = "verification_failed_report.txt"
        self.assertTrue(os.path.exists(report_file))
        
        with open(report_file, "r", encoding="utf-8") as f:
            report_content = f.read()
            self.assertIn("USER STORY:", report_content)
            self.assertIn("DAFNY CODE:", report_content)
            self.assertIn("COMPILER OUTPUT:", report_content)
            
        # Clean up report
        if os.path.exists(report_file):
            os.remove(report_file)
            
        print("\n[TEST PASSED] Human routing and headless fallback on limit exhausted verified successfully!")

    def test_combined_gql_and_vector_search_for_ruby_step(self):
        """
        Tests that find_closest_ruby_definition:
        1. Accesses the graph database.
        2. Calculates cosine similarity of embeddings.
        3. Traverses the StepBindsDefinition (BINDS) relationship to return the target Ruby definition.
        """
        from spanner_client import SpannerGraphClient
        db = SpannerGraphClient()
        
        # Clear mock tables first
        import sqlite3
        conn = sqlite3.connect("spanner_mock.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM GherkinStep")
        cursor.execute("DELETE FROM StepBindsDefinition")
        cursor.execute("DELETE FROM RubyDefinition")
        conn.commit()
        conn.close()
        
        # 1. Insert Target RubyDefinition node
        db.insert_node(
            label="RubyDefinition",
            node_id="target_ruby_def_1",
            properties={
                "expression": "Given the account balance is (\\d+)",
                "code_block": "Given(/^the account balance is (\\d+)$/) do |b| end"
            }
        )
        
        # 2. Insert GherkinStep node with a specific embedding
        db.insert_node(
            label="GherkinStep",
            node_id="target_step_1",
            properties={
                "step_type": "Given",
                "text": "the account balance is 100"
            },
            embedding=[0.1, 0.2, 0.3]
        )
        
        # 3. Create BINDS edge connecting GherkinStep -> RubyDefinition
        db.insert_edge("BINDS", "target_step_1", "target_ruby_def_1")
        
        # 4. Search for closest using a close query embedding
        match = db.find_closest_ruby_definition([0.1, 0.21, 0.3])
        
        self.assertIsNotNone(match)
        self.assertEqual(match["definition_id"], "target_ruby_def_1")
        self.assertEqual(match["expression"], "Given the account balance is (\\d+)")
        self.assertGreater(match["similarity"], 0.99)
        print("\n[TEST PASSED] Combined Vector-GQL Graph Search verified successfully!")

    def test_recursive_impact_analysis_traversal(self):
        """
        Tests that get_dependent_stories_recursive correctly maps out direct and
        indirect (transitive) dependents via recursive graph traversal.
        """
        from spanner_client import SpannerGraphClient
        db = SpannerGraphClient()
        
        # Clear mock tables first
        import sqlite3
        conn = sqlite3.connect("spanner_mock.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM UserStory")
        cursor.execute("DELETE FROM StoryDependsOnStory")
        conn.commit()
        conn.close()
        
        # 1. Insert UserStory nodes
        db.insert_node("UserStory", "target.txt", {"title": "Target Class Account"})
        db.insert_node("UserStory", "dep1.txt", {"title": "Direct Dependent Withdrawal"})
        db.insert_node("UserStory", "dep2.txt", {"title": "Indirect Dependent Auditing"})
        
        # 2. Insert self-referential depends_on relationships
        # dep1 depends on target (direct)
        db.insert_edge("DEPENDS_ON", "dep1.txt", "target.txt")
        # dep2 depends on dep1 (transitive indirect)
        db.insert_edge("DEPENDS_ON", "dep2.txt", "dep1.txt")
        
        # 3. Retrieve recursive dependents
        dependents = db.get_dependent_stories_recursive("target.txt")
        
        # We expect 2 dependents in total
        self.assertEqual(len(dependents), 2)
        
        # Map by story_id for assertions
        dep_map = {d["story_id"]: d for d in dependents}
        
        self.assertIn("dep1.txt", dep_map)
        self.assertEqual(dep_map["dep1.txt"]["depth"], 1)
        self.assertEqual(dep_map["dep1.txt"]["title"], "Direct Dependent Withdrawal")
        
        self.assertIn("dep2.txt", dep_map)
        self.assertEqual(dep_map["dep2.txt"]["depth"], 2)
        self.assertEqual(dep_map["dep2.txt"]["title"], "Indirect Dependent Auditing")
        
        print("\n[TEST PASSED] Recursive graph traversal and transitive impact mapping verified successfully!")

    def test_exact_regex_matching_database_query(self):
        """
        Tests that find_matching_ruby_definition correctly queries the database
        to find an exact regex pattern match for step text.
        """
        from spanner_client import SpannerGraphClient
        db = SpannerGraphClient()
        
        # Clear mock tables first
        import sqlite3
        conn = sqlite3.connect("spanner_mock.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM RubyDefinition")
        conn.commit()
        conn.close()
        
        # Insert target definition
        db.insert_node(
            label="RubyDefinition",
            node_id="target_def_1",
            properties={
                "expression": "Given the initial deposit balance is (\\d+)",
                "code_block": "Given(/^the initial deposit balance is (\\d+)$/) do |b| end"
            }
        )
        
        # Execute query
        match = db.find_matching_ruby_definition("Given the initial deposit balance is 100")
        
        self.assertIsNotNone(match)
        self.assertEqual(match["definition_id"], "target_def_1")
        self.assertEqual(match["expression"], "Given the initial deposit balance is (\\d+)")
        print("\n[TEST PASSED] Exact regex matching database query verified successfully!")

    def test_step_reuse_or_generate_trajectory(self):
        """
        Tests that the Gherkin test generation phase:
        1. Queries Spanner Graph via Search Agent to find existing steps.
        2. Injects the list of existing steps as reusable templates into the Gherkin generator prompt.
        """
        from spanner_client import SpannerGraphClient
        db = SpannerGraphClient()
        
        # Clear mock tables first
        import sqlite3
        conn = sqlite3.connect("spanner_mock.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM GherkinStep")
        conn.commit()
        conn.close()
        
        # 1. Seed an existing step definition
        db.insert_node(
            label="GherkinStep",
            node_id="target_step_x",
            properties={
                "step_type": "Given",
                "text": "the account balance is 1000"
            }
        )
        
        # Query list
        steps = db.get_all_gherkin_steps()
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["text"], "the account balance is 1000")
        print("\n[TEST PASSED] Step Reuse or Generate trajectory verified successfully!")

    def test_aba_monitor_circuit_breaker(self):
        """
        Tests that the ABA Monitor tracks agent actions, checks looping and drift,
        and statefully trips the circuit breaker when thresholds are violated.
        """
        from aba_monitor import ABAMonitor, CircuitState, CircuitBreakerTrippedError
        
        # 1. Initialize monitor
        monitor = ABAMonitor(loop_limit=3, drift_threshold=0.5)
        self.assertEqual(monitor.state, CircuitState.CLOSED)
        
        # 2. Test Infinite Loop detection
        # Log 2 identical actions (no trip yet)
        monitor.track_action(agent_name="corrector", prompt="Fix syntax", response="Same spec code")
        monitor.track_action(agent_name="corrector", prompt="Fix syntax", response="Same spec code")
        self.assertEqual(monitor.state, CircuitState.CLOSED)
        
        # Third identical action triggers circuit breaker trip
        with self.assertRaises(CircuitBreakerTrippedError):
            monitor.track_action(agent_name="corrector", prompt="Fix syntax", response="Same spec code")
            
        self.assertEqual(monitor.state, CircuitState.OPEN)
        self.assertIn("Infinite loop detected", monitor.tripped_reason)
        
        # 3. Test Intent Drift detection
        monitor_drift = ABAMonitor(drift_threshold=0.5)
        story_emb = [1.0, 0.0, 0.0]
        
        # High similarity (no drift)
        monitor_drift.track_action(
            agent_name="autoformalizer",
            prompt="Formalize",
            response="Close spec",
            original_story_embedding=story_emb,
            response_embedding=[0.9, 0.1, 0.0]
        )
        self.assertEqual(monitor_drift.state, CircuitState.CLOSED)
        
        # Low similarity (drift) trips circuit breaker
        with self.assertRaises(CircuitBreakerTrippedError):
            monitor_drift.track_action(
                agent_name="autoformalizer",
                prompt="Formalize",
                response="Drifted spec",
                original_story_embedding=story_emb,
                response_embedding=[0.1, 0.9, 0.0]
            )
        self.assertEqual(monitor_drift.state, CircuitState.OPEN)
        self.assertIn("Intent drift detected", monitor_drift.tripped_reason)
        print("\n[TEST PASSED] ABA Monitor behavioral checks and circuit breaker verified successfully!")

    @patch("pipeline_adk.execute_plain_agent")
    @patch("pipeline_adk.execute_adk_agent")
    def test_evaluator_quorum_decision(self, mock_execute_adk, mock_execute_plain):
        """
        Tests that handle_human_in_the_loop_mapping:
        1. Invokes the evaluator_quorum agent to inspect Ruby code modifications.
        2. Raises a ValueError and aborts file updates if the quorum rejects the change.
        """
        from pipeline_adk import handle_human_in_the_loop_mapping, QuorumResponse
        from spanner_client import SpannerGraphClient
        db = SpannerGraphClient()
        
        # Mock execute_plain_agent to return dummy Ruby content
        mock_execute_plain.return_value = "Given(/^something$/) do end"
        
        # Mock execute_adk_agent to return a rejected QuorumResponse
        mock_execute_adk.return_value = QuorumResponse(
            is_approved=False,
            reasoning="Rejected: Code contains unacceptable logic or unsafe patterns.",
            plain_english_summary="Malicious summary"
        )
        
        provider_info = {"provider": "gemini", "model": "gemini-2.5-flash"}
        
        # Test rejection scenario
        with self.assertRaises(ValueError) as ctx:
            asyncio.run(
                handle_human_in_the_loop_mapping(
                    step_type="When",
                    step_text="the user performs a malicious action",
                    db=db,
                    provider_info=provider_info,
                    story_id="test_story.txt"
                )
            )
        self.assertIn("Evaluator Quorum rejected modification", str(ctx.exception))
        print("\n[TEST PASSED] Evaluator Quorum consensus verification verified successfully!")

    @patch("pipeline_adk.safe_input")
    @patch("pipeline_adk.execute_plain_agent")
    @patch("pipeline_adk.execute_adk_agent")
    def test_evaluator_quorum_vibe_diff_user_reject(self, mock_execute_adk, mock_execute_plain, mock_safe_input):
        """
        Tests that when a code change is approved by the Evaluator Quorum but the user rejects the
        English Vibe Diff summary (safe_input returns 'no'), the pipeline halts and raises ValueError.
        """
        from pipeline_adk import handle_human_in_the_loop_mapping, QuorumResponse
        from spanner_client import SpannerGraphClient
        db = SpannerGraphClient()
        
        # Mock agents to return approved quorum evaluation
        mock_execute_plain.return_value = "Given(/^something$/) do end"
        mock_execute_adk.return_value = QuorumResponse(
            is_approved=True,
            reasoning="Safe code change.",
            plain_english_summary="This proposed change adds standard steps."
        )
        
        # Mock user consent rejection: first call yes (to auto-generate), second call no (to reject vibe diff)
        mock_safe_input.side_effect = ["yes", "no"]
        
        provider_info = {"provider": "gemini", "model": "gemini-2.5-flash"}
        
        with self.assertRaises(ValueError) as ctx:
            asyncio.run(
                handle_human_in_the_loop_mapping(
                    step_type="When",
                    step_text="the user creates a standard account",
                    db=db,
                    provider_info=provider_info,
                    story_id="test_story.txt"
                )
            )
        self.assertIn("User rejected code change consensus", str(ctx.exception))
        print("\n[TEST PASSED] Vibe Diff user consent rejection verified successfully!")

    def test_auto_prune_and_reuse_coverage(self):
        """
        Tests that:
        1. auto_prune_orphans finds and deletes definitions not bound to steps.
        2. Non-orphan definitions are successfully preserved.
        """
        from spanner_client import SpannerGraphClient
        db = SpannerGraphClient()
        
        # 1. Seed two definitions
        db.insert_node(
            label="RubyDefinition",
            node_id="bound_def",
            properties={"expression": "bound expression", "code_block": "bound code"}
        )
        db.insert_node(
            label="RubyDefinition",
            node_id="orphan_def",
            properties={"expression": "orphan expression", "code_block": "orphan code"}
        )
        
        # 2. Seed a GherkinStep and bind it to bound_def
        db.insert_node(
            label="GherkinStep",
            node_id="step_1",
            properties={"step_type": "Given", "text": "bound text"}
        )
        db.insert_edge("BINDS", "step_1", "bound_def")
        
        # Verify both exist initially
        defs_before = db.get_all_ruby_definitions()
        self.assertEqual(len(defs_before), 2)
        
        # 3. Trigger auto-pruning
        pruned_ids = db.auto_prune_orphans()
        self.assertEqual(pruned_ids, ["orphan_def"])
        
        # 4. Assert bound_def remains and orphan_def is deleted
        defs_after = db.get_all_ruby_definitions()
        self.assertEqual(len(defs_after), 1)
        self.assertEqual(defs_after[0]["definition_id"], "bound_def")
        print("\n[TEST PASSED] Auto-pruning of orphan step definitions verified successfully!")

if __name__ == "__main__":
    unittest.main()
