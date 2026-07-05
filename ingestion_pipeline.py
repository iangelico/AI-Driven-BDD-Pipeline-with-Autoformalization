import os
import re
import hashlib
import random
import config
from spanner_client import SpannerGraphClient

def generate_embedding(text: str) -> list[float]:
    """
    Generates a 768-dimensional text embedding vector.
    Uses Gemini's text-embedding-004 model if API key is set,
    otherwise falls back to generating a mock random vector.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and not api_key.startswith("AIzaSy_placeholder"):
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.embed_content(
                model="text-embedding-004",
                contents=text
            )
            if response.embeddings and len(response.embeddings) > 0:
                return response.embeddings[0].values
        except Exception as e:
            print(f"Warning: Live embedding call failed ({e}). Falling back to mock vector.")
            
    # Mock fallback (768-dimensional vector)
    random.seed(hashlib.md5(text.encode()).digest())
    return [random.uniform(-0.1, 0.1) for _ in range(768)]


def ingest_all_assets():
    """Reads ecosystem directories, generates embeddings, and inserts into Spanner Graph."""
    print("=" * 60)
    print("STARTING GRAPH INGESTION PIPELINE")
    print("=" * 60)
    
    # Initialize Spanner client
    db = SpannerGraphClient()
    
    # 1. Ingest User Stories (Stories directory)
    stories_dir = config.STORIES_DIR
    dataset_dir = os.path.join(stories_dir, "dataset")
    
    # Check if directory exists
    if not os.path.exists(dataset_dir):
        print(f"Error: Dataset directory {dataset_dir} does not exist. Run generate_stories.py first.")
        return
        
    story_files = [f for f in os.listdir(dataset_dir) if f.endswith(".txt")]
    print(f"Found {len(story_files)} user stories for ingestion...")
    
    for filename in story_files:
        path = os.path.join(dataset_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        story_id = filename
        title = filename.replace(".txt", "").replace("_", " ").title()
        
        # Generate embedding for story description
        emb = generate_embedding(content)
        
        properties = {
            "title": title,
            "description": content
        }
        if filename == "banking_02_deposit.txt":
            properties["verified_spec"] = (
                "class Account {\n"
                "  var balance: int\n"
                "  constructor(initialBalance: int)\n"
                "    requires initialBalance >= 0\n"
                "    ensures balance == initialBalance\n"
                "  {\n"
                "    balance := initialBalance;\n"
                "  }\n"
                "  method deposit(amount: int)\n"
                "    requires amount > 0\n"
                "    ensures balance == old(balance) + amount\n"
                "    modifies this\n"
                "  {\n"
                "    balance := balance + amount;\n"
                "  }\n"
                "}"
            )
            
        # Save node
        db.insert_node(
            label="UserStory",
            node_id=story_id,
            properties=properties,
            embedding=emb
        )
        print(f"Ingested UserStory node: {story_id}")

    # 2. Ingest Ruby Cucumber Step Definitions (step_definitions/ directory)
    ruby_defs_dir = "step_definitions"
    ruby_files = []
    if os.path.exists(ruby_defs_dir):
        ruby_files = [os.path.join(ruby_defs_dir, f) for f in os.listdir(ruby_defs_dir) if f.endswith(".rb")]
        
    print(f"\nFound {len(ruby_files)} Ruby step definition files...")
    
    # Regex parser to extract Given/When/Then definitions
    # Example: Given(/^the account balance is (\d+)$/) do |balance|
    pattern = re.compile(r"(Given|When|Then)\(\/\^(.*?)\$\/\) do( \|.*?\|)?\n(.*?)\nend", re.DOTALL)
    
    ruby_defs_cache = []
    
    for path in ruby_files:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        matches = pattern.finditer(content)
        for match in matches:
            step_type = match.group(1)
            expression = match.group(2)
            code_block = match.group(0)
            
            # Generate a unique hash id based on expression
            def_hash = hashlib.md5(expression.encode()).hexdigest()[:12]
            definition_id = f"ruby_def_{def_hash}"
            
            emb = generate_embedding(expression)
            
            db.insert_node(
                label="RubyDefinition",
                node_id=definition_id,
                properties={
                    "expression": expression,
                    "code_block": code_block
                },
                embedding=emb
            )
            print(f"Ingested RubyDefinition node: {definition_id} (Pattern: /{expression}/)")
            
            ruby_defs_cache.append({
                "id": definition_id,
                "expression": expression,
                "regex": re.compile(expression)
            })

    # 3. Ingest Gherkin Features & Steps (features/ directory)
    features_dir = config.FEATURES_DIR
    feature_files = []
    if os.path.exists(features_dir):
        feature_files = [os.path.join(features_dir, f) for f in os.listdir(features_dir) if f.endswith(".feature")]
        
    print(f"\nFound {len(feature_files)} Gherkin feature files...")
    
    for path in feature_files:
        filename = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Try to map back to a User Story (if matching file exists)
        # e.g. withdraw.feature maps to banking_01_withdrawal.txt
        story_id = None
        if "withdraw" in filename.lower():
            story_id = "banking_01_withdrawal.txt"
        elif "atm" in filename.lower():
            story_id = "banking_04_daily_limit.txt"
            
        # Parse scenarios and Given/When/Then steps
        lines = content.split("\n")
        for line in lines:
            line_strip = line.strip()
            match_step = re.match(r"^(Given|When|Then)\s+(.*)$", line_strip)
            
            if match_step:
                step_type = match_step.group(1)
                step_text = match_step.group(2)
                
                step_hash = hashlib.md5(step_text.encode()).hexdigest()[:12]
                step_id = f"gherkin_step_{step_hash}"
                
                emb = generate_embedding(step_text)
                
                # Insert GherkinStep Node
                db.insert_node(
                    label="GherkinStep",
                    node_id=step_id,
                    properties={
                        "step_type": step_type,
                        "text": step_text
                    },
                    embedding=emb
                )
                print(f"Ingested GherkinStep node: {step_id} ({step_type} {step_text})")
                
                # If we mapped it to a User Story, link them using StoryImplementsStep Edge
                if story_id:
                    db.insert_edge(
                        label="IMPLEMENTS",
                        source_id=story_id,
                        destination_id=step_id
                    )
                    print(f"  Created Edge: ({story_id}) --[IMPLEMENTS]--> ({step_id})")
                    
                # Check for regex bindings in Ruby definitions to link them using StepBindsDefinition Edge
                for r_def in ruby_defs_cache:
                    if r_def["regex"].match(step_text):
                        db.insert_edge(
                            label="BINDS",
                            source_id=step_id,
                            destination_id=r_def["id"]
                        )
                        print(f"  Created Edge: ({step_id}) --[BINDS]--> ({r_def['id']})")
                        break

    print("=" * 60)
    print("INGESTION PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    ingest_all_assets()
