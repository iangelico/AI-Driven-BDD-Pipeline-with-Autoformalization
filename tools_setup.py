import os
import sys
import urllib.request
import zipfile
import subprocess
import shutil

# Configurations
DAFNY_VERSION = "4.11.0"
DAFNY_URL = f"https://github.com/dafny-lang/dafny/releases/download/v{DAFNY_VERSION}/dafny-{DAFNY_VERSION}-x64-windows-2022.zip"
TOOLS_DIR = os.path.abspath("tools")
ZIP_PATH = os.path.join(TOOLS_DIR, f"dafny-{DAFNY_VERSION}.zip")
DAFNY_DIR = os.path.join(TOOLS_DIR, "dafny")
DAFNY_EXE = os.path.join(DAFNY_DIR, "dafny.exe")

def download_file(url, dest_path):
    print(f"Downloading Dafny v{DAFNY_VERSION} from {url}...")
    
    # Custom headers to resemble a browser request and avoid GitHub blocks
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    
    # Download with a simple progress tracker
    with urllib.request.urlopen(req) as response, open(dest_path, 'wb') as out_file:
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        chunk_size = 1024 * 1024  # 1MB
        
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                percent = (downloaded / total_size) * 100
                print(f"Progress: {percent:.1f}% ({downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB)", end='\r')
            else:
                print(f"Downloaded: {downloaded // (1024*1024)}MB...", end='\r')
        print("\nDownload completed successfully.")

def main():
    # 1. Create tools directory
    if not os.path.exists(TOOLS_DIR):
        os.makedirs(TOOLS_DIR)
        print(f"Created tools directory: {TOOLS_DIR}")

    # 2. Download Dafny zip if not already downloaded/extracted
    if not os.path.exists(DAFNY_EXE):
        if not os.path.exists(ZIP_PATH):
            try:
                download_file(DAFNY_URL, ZIP_PATH)
            except Exception as e:
                print(f"Error downloading file: {e}")
                sys.exit(1)
        
        # 3. Extract the ZIP
        print("Extracting Dafny zip file...")
        try:
            with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
                zip_ref.extractall(TOOLS_DIR)
            print(f"Extracted to {TOOLS_DIR}")
        except Exception as e:
            print(f"Error extracting zip: {e}")
            sys.exit(1)
            
        # Clean up zip file to save space
        try:
            os.remove(ZIP_PATH)
            print("Cleaned up download zip file.")
        except Exception as e:
            print(f"Warning: could not clean up zip: {e}")
    else:
        print("Dafny is already installed locally.")

    # 4. Verify Dafny runs
    print(f"Verifying Dafny installation via {DAFNY_EXE}...")
    if not os.path.exists(DAFNY_EXE):
        print(f"Error: Dafny executable not found at {DAFNY_EXE}")
        sys.exit(1)
        
    try:
        # Run dafny --version
        result = subprocess.run(
            [DAFNY_EXE, "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print("Dafny execution SUCCESS!")
        print(f"Version output: {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"Dafny failed to execute. Exit code: {e.returncode}")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"Error running Dafny: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
