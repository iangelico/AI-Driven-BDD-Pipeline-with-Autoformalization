import os
import subprocess
from pydantic import BaseModel

import config

# Configuration for local Dafny path
DEFAULT_DAFNY_PATH = os.path.abspath(os.path.join(config.TOOLS_DIR, "dafny", "dafny.exe"))

class VerificationResult(BaseModel):
    success: bool
    status_message: str
    compiler_output: str
    file_path: str

def verify_dafny_spec(spec_code: str, file_path: str = "temp_spec.dfy", dafny_path: str = DEFAULT_DAFNY_PATH) -> VerificationResult:
    """
    Saves the provided Dafny specification code to a file and runs the Dafny verifier.
    Returns a VerificationResult object.
    """
    # Ensure parent directories exist
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    
    # Save the Dafny spec to file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(spec_code)
    
    if not os.path.exists(dafny_path):
        return VerificationResult(
            success=False,
            status_message=f"Dafny executable not found at: {dafny_path}. Please run tools_setup.py first.",
            compiler_output="",
            file_path=file_path
        )
        
    try:
        # Run dafny verify <file_path>
        result = subprocess.run(
            [dafny_path, "verify", file_path],
            capture_output=True,
            text=True
        )
        
        # In Dafny 4, verification success is signaled by exit code 0
        if result.returncode == 0:
            return VerificationResult(
                success=True,
                status_message="SUCCESS: The specification is mathematically sound.",
                compiler_output=result.stdout + result.stderr,
                file_path=file_path
            )
        else:
            return VerificationResult(
                success=False,
                status_message="VERIFICATION FAILED: The compiler found logical errors or syntax violations.",
                compiler_output=result.stdout + result.stderr,
                file_path=file_path
            )
            
    except Exception as e:
        return VerificationResult(
            success=False,
            status_message=f"System error executing Dafny verifier: {str(e)}",
            compiler_output="",
            file_path=file_path
        )
