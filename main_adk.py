import os
import argparse
import asyncio
import sys
import config
from pipeline_adk import run_adk_pipeline

def parse_args():
    parser = argparse.ArgumentParser(
        description="ADK 2.0 BDD Pipeline with Autoformalization (Dafny -> Cucumber/Gherkin)"
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
        default=os.path.join(config.FEATURES_DIR, "output_test.feature"),
        help=f"Path where the final Gherkin .feature file will be saved. Default: {config.FEATURES_DIR}/output_test.feature"
    )
    parser.add_argument(
        "--spec",
        type=str,
        default=os.path.join(config.SPECS_DIR, "verified_spec.dfy"),
        help=f"Path where the proven Dafny specification (.dfy) will be saved. Default: {config.SPECS_DIR}/verified_spec.dfy"
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=5,
        help="Max number of self-correction attempts in the agent loop if verification fails. Default: 5"
    )
    return parser.parse_args()

async def main():
    args = parse_args()
    
    # Ensure target output directories exist
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.spec)), exist_ok=True)
    
    # Check if --story is a file path
    user_story = args.story
    story_id = "ad_hoc_story.txt"
    if os.path.exists(user_story):
        story_id = os.path.basename(user_story)
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
        
    print("Starting BDD pipeline (Google ADK 2.0 Engine)...")
    provider_info = config.get_llm_info()
    print(f"Provider: {provider_info['provider'].upper()}")
    print(f"Model: {provider_info['model']}")
    print(f"Target Gherkin output: {args.output}")
    print(f"Target Dafny specification: {args.spec}")
    print("-" * 60)
    
    success = await run_adk_pipeline(
        user_story=user_story,
        output_feature_path=args.output,
        output_spec_path=args.spec,
        max_attempts=args.attempts,
        story_id=story_id
    )
    
    if success:
        print("\nPipeline execution completed successfully!")
        sys.exit(0)
    else:
        print("\nPipeline execution completed with verification failures.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
