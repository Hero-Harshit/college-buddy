import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Reconfigure stdout/stderr to utf-8 for Windows terminals
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from google import genai

# Load environment variables
env_path = Path(__file__).resolve().parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


def list_flash_models():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env file.")
        sys.exit(1)

    print("Querying Google GenAI API for available models...\n")
    client = genai.Client(api_key=api_key)

    flash_models = []
    for model in client.models.list():
        name = getattr(model, "name", "")
        display_name = getattr(model, "display_name", "")
        if "flash" in name.lower() or "flash" in display_name.lower():
            flash_models.append(name)

    print("=== Available Flash Models ===")
    if flash_models:
        for model_name in sorted(flash_models):
            print(f"- {model_name}")
    else:
        print("No Flash models found.")


if __name__ == "__main__":
    list_flash_models()
