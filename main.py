import os
import argparse
import sys
import config
from pipeline import run_pipeline

def parse_args():
    parser = argparse.ArgumentParser(
        description="AI-Driven BDD Pipeline with Formal Verification (Dafny -> Cucumber/Gherkin)"
    )
    parser.add_argument(
        "--story",
        type=str,
        required=True,
        help="The natural language User Story. Can be a text string or a path to a file containing the story."
    )
    parser.add_argument(
        "--output",
        type=str,
        default=os.path.join("features", "output_test.feature"),
        help="Path where the final Gherkin .feature file will be saved. Default: features/output_test.feature"
    )
    parser.add_argument(
        "--spec",
        type=str,
        default=os.path.join("specs", "verified_spec.dfy"),
        help="Path where the proven Dafny specification (.dfy) will be saved. Default: specs/verified_spec.dfy"
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=5,
        help="Max number of self-correction attempts in the agent loop if verification fails. Default: 5"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Ensure target output directories exist
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.spec)), exist_ok=True)
    
    # Check if --story is a file path
    user_story = args.story
    if os.path.exists(user_story):
        print(f"Reading user story from file: {user_story}")
        with open(user_story, "r", encoding="utf-8") as f:
            user_story = f.read()
            
    # Validate LLM credentials
    try:
        config.validate_config()
    except Exception as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        print("Please check your .env file or environment variables.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Starting BDD pipeline...")
    provider_info = config.get_llm_info()
    print(f"Provider: {provider_info['provider'].upper()}")
    print(f"Model: {provider_info['model']}")
    print(f"Target Gherkin output: {args.output}")
    print(f"Target Dafny specification: {args.spec}")
    print("-" * 60)
    
    success = run_pipeline(
        user_story=user_story,
        output_feature_path=args.output,
        output_spec_path=args.spec,
        max_attempts=args.attempts
    )
    
    if success:
        print("\nPipeline execution completed successfully!")
        sys.exit(0)
    else:
        print("\nPipeline execution completed with verification failures.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
