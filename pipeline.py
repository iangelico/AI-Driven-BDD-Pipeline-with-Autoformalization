import os
from pydantic import BaseModel, Field
import config
from verifier import verify_dafny_spec, VerificationResult

# 1. Define Pydantic response models for structured outputs
class DafnySpecResponse(BaseModel):
    explanation: str = Field(description="A brief explanation of how the user story states, preconditions, and invariants are mapped to Dafny.")
    spec_code: str = Field(description="The complete self-contained Dafny source code block containing classes, methods, and formal specifications.")

class GherkinFeatureResponse(BaseModel):
    explanation: str = Field(description="Brief explanation of how the Dafny states and transitions map to Given/When/Then scenarios.")
    feature_content: str = Field(description="The complete Gherkin feature file content starting with 'Feature:' and containing Cucumber scenarios.")


def generate_structured_output(prompt: str, response_schema: type, system_instruction: str = None):
    """
    Unified function to request structured output from Gemini or OpenAI.
    """
    config.validate_config()
    provider_info = config.get_llm_info()
    
    if provider_info["provider"] == "gemini":
        from google import genai
        from google.genai import types
        
        client = config.get_gemini_client()
        
        # Prepare GenAI config with native Pydantic schema
        gen_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.1  # Low temperature for logical reasoning
        )
        
        response = client.models.generate_content(
            model=provider_info["model"],
            contents=prompt,
            config=gen_config
        )
        
        # Google GenAI SDK automatically parses response to response_schema and stores in .parsed
        if hasattr(response, "parsed") and response.parsed:
            return response.parsed
        else:
            raise ValueError(f"Failed to get structured output from Gemini. Raw text: {response.text}")
            
    elif provider_info["provider"] == "openai":
        client = config.get_openai_client()
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        
        completion = client.beta.chat.completions.parse(
            model=provider_info["model"],
            messages=messages,
            response_format=response_schema,
            temperature=0.1
        )
        
        if completion.choices[0].message.parsed:
            return completion.choices[0].message.parsed
        else:
            raise ValueError(f"Failed to get structured output from OpenAI. Message content: {completion.choices[0].message.content}")


def run_pipeline(user_story: str, output_feature_path: str, output_spec_path: str, max_attempts: int = 5):
    """
    Orchestrates the entire BDD pipeline:
    Phase 1: Autoformalization (NL -> Dafny)
    Phase 2: Verification Loop (Dafny -> Verifier -> Self-Correct)
    Phase 3: Gherkin Generation (Verified Spec -> Cucumber Gherkin)
    """
    print("=" * 60)
    print("PHASE 1: AUTOFORMALIZATION (NL -> Dafny)")
    print("=" * 60)
    
    phase1_system = (
        "You are a QA Architect and Formal Verification Expert.\n"
        "Your task is to translate an informal natural language User Story into a formal specification in Dafny.\n"
        "Instructions:\n"
        "1. Identify the system state variables, class fields, preconditions, and postconditions.\n"
        "2. Create a clean, self-contained Dafny class or set of methods modeling the behaviors.\n"
        "3. Include constructors to initialize the state.\n"
        "4. Define logical postconditions (ensures) and preconditions (requires) for each operation.\n"
        "5. Keep the code simple and focus on provability. Avoid overly complex proof constructs if basic ones suffice.\n"
        "CRITICAL DAFNY SYNTAX RULE:\n"
        "Dafny does NOT support the 'invariant' keyword directly inside a class body (this causes 'rbrace expected' parse errors).\n"
        "To enforce class invariants (e.g. balance >= 0), you must either:\n"
        "  a) Define them as standard preconditions ('requires') and postconditions ('ensures') on all constructors and methods (e.g. requires balance >= 0, ensures balance >= 0). This is the simplest and recommended approach.\n"
        "  b) Define a validity predicate 'predicate Valid() reads this { balance >= 0 }' and require/ensure Valid() on every constructor/method.\n"
        "NEVER use the 'invariant' keyword outside of a loop block."
    )
    
    phase1_prompt = (
        f"Translate the following User Story into a formal Dafny specification.\n\n"
        f"User Story:\n{user_story}\n\n"
        f"Provide the complete, self-contained Dafny source code in the 'spec_code' field."
    )
    
    print(f"Requesting initial Dafny specification...")
    parsed_spec = generate_structured_output(
        prompt=phase1_prompt,
        response_schema=DafnySpecResponse,
        system_instruction=phase1_system
    )
    
    current_spec_code = parsed_spec.spec_code
    explanation = parsed_spec.explanation
    
    print("\nInitial specification generated.")
    print(f"Explanation:\n{explanation}\n")
    
    print("=" * 60)
    print("PHASE 2: AGENTIC VERIFICATION LOOP")
    print("=" * 60)
    
    attempt = 1
    verified = False
    verification_log = ""
    
    while attempt <= max_attempts:
        print(f"Verification Attempt {attempt}/{max_attempts}...")
        
        # Run local verifier
        result: VerificationResult = verify_dafny_spec(current_spec_code, file_path=output_spec_path)
        
        if result.success:
            print(f"SUCCESS: Dafny specification successfully verified in attempt {attempt}!")
            verified = True
            verification_log = result.compiler_output
            break
        else:
            print(f"FAILED: Verification issues detected:")
            print("-" * 40)
            print(result.status_message)
            print(result.compiler_output)
            print("-" * 40)
            
            if attempt == max_attempts:
                break
                
            # Self-Correction Step
            print(f"Triggering self-correction loop...")
            phase2_system = (
                "You are an expert Dafny developer. The Dafny verifier has compiled the code and reported errors.\n"
                "You must analyze the code and the errors carefully, identify where safety conditions or preconditions fail, "
                "and correct the specification. Do not change the original logic or rules of the user story; instead, "
                "fix the specifications (e.g. preconditions, postconditions, modifies clauses, or invariants) so that it compiles and proves successfully.\n"
                "CRITICAL DAFNY SYNTAX RULE:\n"
                "If the compiler reports 'rbrace expected' on an 'invariant' line, it is because Dafny does NOT allow the 'invariant' keyword directly inside a class body.\n"
                "To implement class invariants (like balance >= 0), you must:\n"
                "  1. Remove the class-level 'invariant' declaration.\n"
                "  2. Add standard preconditions ('requires') and postconditions ('ensures') representing the invariant to all constructors and methods.\n"
                "  Never use the 'invariant' keyword outside of loop blocks."
            )
            
            phase2_prompt = (
                f"The following Dafny specification code failed verification. Please correct the code based on the compiler output.\n\n"
                f"--- INCORRECT DAFNY CODE ---\n"
                f"{current_spec_code}\n\n"
                f"--- COMPILER ERRORS ---\n"
                f"{result.compiler_output}\n\n"
                f"Analyze the errors, fix the code, and return the complete corrected specification in the 'spec_code' field."
            )
            
            parsed_correction = generate_structured_output(
                prompt=phase2_prompt,
                response_schema=DafnySpecResponse,
                system_instruction=phase2_system
            )
            
            current_spec_code = parsed_correction.spec_code
            print(f"Self-correction received from LLM. Correction explanation: {parsed_correction.explanation}")
            attempt += 1

    if not verified:
        print(f"\nERROR: Max verification attempts ({max_attempts}) reached. Verification failed.")
        print("Please check the generated spec file manually to resolve errors.")
        # We will still output the failing spec so the user can debug
        return False
        
    print("=" * 60)
    print("PHASE 3: GHERKIN TEST GENERATION")
    print("=" * 60)
    
    phase3_system = (
        "You are a QA Lead and BDD specialist. Your job is to translate a mathematically verified Dafny formal specification "
        "into a Cucumber/Gherkin feature file (.feature).\n"
        "Instructions:\n"
        "1. Map class fields/states to Given preconditions (e.g., Given the account balance is 100).\n"
        "2. Map Dafny methods to When actions (e.g., When the customer withdraws 50).\n"
        "3. Map method postconditions, success states, and updates to Then assertions.\n"
        "4. Create scenarios showing both successful paths (preconditions satisfied) and failure paths (preconditions violated or boundaries crossed).\n"
        "5. Output valid, standard Cucumber feature file syntax in the 'feature_content' field."
    )
    
    phase3_prompt = (
        f"Please translate the following mathematically verified Dafny specification into Cucumber Gherkin test cases.\n\n"
        f"Verified Dafny Specification:\n"
        f"{current_spec_code}\n\n"
        f"Verification Compiler Output:\n"
        f"{verification_log}\n"
    )
    
    print("Requesting Gherkin feature file generation...")
    parsed_feature = generate_structured_output(
        prompt=phase3_prompt,
        response_schema=GherkinFeatureResponse,
        system_instruction=phase3_system
    )
    
    # Save the Gherkin feature file
    print(f"Saving final Gherkin tests to {output_feature_path}...")
    with open(output_feature_path, "w", encoding="utf-8") as f:
        f.write(parsed_feature.feature_content)
        
    print("\nBDD Feature file successfully generated!")
    print(f"Gherkin Explanation:\n{parsed_feature.explanation}")
    print("-" * 60)
    print(parsed_feature.feature_content)
    print("=" * 60)
    return True
