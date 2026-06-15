#!/usr/bin/env python3
"""
KrishiMitra — Custom LLM Application Loader (v2 FIXED)
=======================================================
Automates loading your fine-tuned GGUF model into Ollama and
configuring the FastAPI/Django application to use it.

Usage:
    python3 load_custom_model.py [--gguf-path /path/to/model.gguf]
"""

import os
import sys
import subprocess
import shutil
import argparse
import urllib.request
import urllib.error
from typing import Optional

# ── Path resolution ────────────────────────────────────────────────────────────
try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_DIR = os.path.abspath(os.getcwd())

PARENT_DIR = os.path.dirname(SCRIPT_DIR)
if not os.path.exists(os.path.join(PARENT_DIR, "phase1")):
    PARENT_DIR = SCRIPT_DIR

OLLAMA_SERVICE_PATH = os.path.join(PARENT_DIR, "phase1", "services", "ollama_service.py")
MODEL_ALIAS         = "krishimitra-llm"
OLLAMA_BASE_URL     = "http://localhost:11434"

# FIX 1: Unsloth saves GGUF as uppercase Q4_K_M inside a named subdirectory.
# We search for the file rather than hardcode the path.
GGUF_SEARCH_CANDIDATES = [
    # Unsloth default nested output
    os.path.join(SCRIPT_DIR, "krishimitra-model", "krishimitra-model-Q4_K_M.gguf"),
    # Flat variants (lowercase/uppercase)
    os.path.join(SCRIPT_DIR, "krishimitra-model-Q4_K_M.gguf"),
    os.path.join(SCRIPT_DIR, "krishimitra-model-q4_k_m.gguf"),
    # Kaggle working dir (if running post-training)
    "/kaggle/working/krishimitra-model/krishimitra-model-Q4_K_M.gguf",
    "/kaggle/working/krishimitra-model-Q4_K_M.gguf",
    "/kaggle/working/krishimitra-model-q4_k_m.gguf",
]


def find_gguf() -> Optional[str]:
    """Search known locations for the GGUF file. Returns path or None."""
    for path in GGUF_SEARCH_CANDIDATES:
        if os.path.exists(path):
            return path
    # Broader glob search as last resort
    import glob
    patterns = [
        os.path.join(SCRIPT_DIR, "**", "*.gguf"),
        os.path.join(PARENT_DIR, "**", "*.gguf"),
        "/kaggle/working/**/*.gguf",
    ]
    for pattern in patterns:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            return matches[0]
    return None


def check_ollama() -> bool:
    """FIX 2: Properly verify Ollama is running and responsive."""
    try:
        req  = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/version")
        resp = urllib.request.urlopen(req, timeout=5)
        if resp.status == 200:
            import json
            data = json.loads(resp.read().decode())
            print(f"✅ Ollama is running (version: {data.get('version', 'unknown')}).")
            return True
        return False
    except urllib.error.URLError as e:
        print(f"❌ Ollama is not reachable: {e.reason}")
        return False
    except Exception as e:
        print(f"❌ Ollama check failed: {e}")
        return False


def create_ollama_model(gguf_path: str, modelfile_dir: str) -> bool:
    """FIX 3: Stream ollama create output so user sees progress, not silence."""

    # Generate a Modelfile on the fly if one doesn't exist
    modelfile_path = os.path.join(modelfile_dir, "Modelfile")
    if not os.path.exists(modelfile_path):
        print(f"⚠️  Modelfile not found. Generating one automatically...")
        # Use relative filename so Ollama resolves it from cwd (modelfile_dir)
        gguf_filename = os.path.basename(gguf_path)
        # If gguf is in a subdirectory relative to modelfile_dir, use relative path
        try:
            gguf_rel = os.path.relpath(gguf_path, modelfile_dir)
        except ValueError:
            gguf_rel = gguf_path  # On Windows relpath can fail across drives

        modelfile_content = f"""\
FROM ./{gguf_rel}

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 4096

SYSTEM \"\"\"You are KrishiMitra AI, an expert agricultural advisor for Indian farmers. \
Provide accurate, practical, and actionable advice in the language the farmer uses \
(Hindi, English, or regional languages). Always prioritize locally available solutions.\"\"\"\
"""
        try:
            with open(modelfile_path, "w", encoding="utf-8") as mf:
                mf.write(modelfile_content)
            print(f"✅ Modelfile generated at: {modelfile_path}")
        except Exception as e:
            print(f"❌ Failed to write Modelfile: {e}")
            return False
    else:
        print(f"✅ Using existing Modelfile: {modelfile_path}")

    print(f"\n📦 Registering '{MODEL_ALIAS}' in Ollama (this may take 1–3 minutes)...")
    print("   Streaming progress output:")
    print("   " + "─" * 50)

    try:
        # FIX 3: Do NOT use capture_output=True — stream directly to terminal
        result = subprocess.run(
            ["ollama", "create", MODEL_ALIAS, "-f", "Modelfile"],
            cwd=modelfile_dir,
            text=True,
            # stdout/stderr inherit from parent process → user sees live progress
        )
        print("   " + "─" * 50)
        if result.returncode == 0:
            print(f"✅ Model '{MODEL_ALIAS}' registered successfully in Ollama.")
            return True
        else:
            print(f"❌ 'ollama create' exited with code {result.returncode}.")
            return False
    except FileNotFoundError:
        print("❌ 'ollama' command not found. Install from https://ollama.ai and add to PATH.")
        return False
    except Exception as e:
        print(f"❌ Unexpected error running ollama: {e}")
        return False


def patch_ollama_service() -> bool:
    """Update DEFAULT_MODEL in ollama_service.py."""
    if not os.path.exists(OLLAMA_SERVICE_PATH):
        print(f"\n⚠️  ollama_service.py not found at:\n   {OLLAMA_SERVICE_PATH}")
        print(f"   Manually set DEFAULT_MODEL = \"{MODEL_ALIAS}\" in your service file.")
        return True  # Non-fatal

    print(f"\n🔧 Patching: {OLLAMA_SERVICE_PATH}")
    try:
        with open(OLLAMA_SERVICE_PATH, "r", encoding="utf-8") as f:
            code = f.read()

        # Handle multiple possible existing values
        import re
        pattern = r'(DEFAULT_MODEL\s*=\s*)["\']([^"\']+)["\']'
        new_line = f'DEFAULT_MODEL = "{MODEL_ALIAS}"'
        match    = re.search(pattern, code)

        if match:
            current_val = match.group(2)
            if current_val == MODEL_ALIAS:
                print(f"ℹ️  Already configured to use '{MODEL_ALIAS}'. No change needed.")
                return True
            # Make a backup before editing
            backup_path = OLLAMA_SERVICE_PATH + ".bak"
            shutil.copy(OLLAMA_SERVICE_PATH, backup_path)
            print(f"   Backup saved: {backup_path}")

            code = re.sub(pattern, new_line, code)
            with open(OLLAMA_SERVICE_PATH, "w", encoding="utf-8") as f:
                f.write(code)
            print(f"✅ DEFAULT_MODEL updated: '{current_val}' → '{MODEL_ALIAS}'")
            return True
        else:
            print(f"⚠️  Could not find DEFAULT_MODEL in the service file.")
            print(f"   Please add this line manually:\n   {new_line}")
            return True  # Non-fatal

    except Exception as e:
        print(f"❌ Failed to patch service file: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="KrishiMitra LLM Loader")
    parser.add_argument("--gguf-path", help="Explicit path to the GGUF model file", default=None)
    parser.add_argument("--skip-ollama-check", action="store_true",
                        help="Skip Ollama connectivity check (useful for pre-staging)")
    args = parser.parse_args()

    print("═" * 55)
    print("  KrishiMitra — Custom LLM Loader & Configurator v2")
    print("═" * 55 + "\n")

    # ── 1. Locate GGUF ─────────────────────────────────────────────────────────
    gguf_path = args.gguf_path
    if gguf_path and not os.path.exists(gguf_path):
        print(f"❌ Specified GGUF path does not exist: {gguf_path}")
        sys.exit(1)

    if not gguf_path:
        print("🔍 Searching for GGUF model file...")
        gguf_path = find_gguf()

    if not gguf_path:
        print("❌ Could not locate the GGUF model file.")
        print("   Expected locations:")
        for p in GGUF_SEARCH_CANDIDATES:
            print(f"     {p}")
        print("\n   Options:")
        print("   1. Re-run with --gguf-path /path/to/your/model.gguf")
        print("   2. Download the GGUF from Kaggle Output tab and place it here:")
        print(f"      {SCRIPT_DIR}/")
        sys.exit(1)

    file_size_gb = os.path.getsize(gguf_path) / 1e9
    print(f"✅ Found model: {gguf_path}  ({file_size_gb:.2f} GB)")

    # ── 2. Check Ollama ────────────────────────────────────────────────────────
    if not args.skip_ollama_check:
        print("\n🔌 Checking Ollama service...")
        if not check_ollama():
            print("\n   To start Ollama:")
            print("     Linux/Mac : ollama serve")
            print("     Windows   : Open the Ollama Desktop app")
            sys.exit(1)

    # ── 3. Register model in Ollama ────────────────────────────────────────────
    modelfile_dir = os.path.dirname(gguf_path)
    if not create_ollama_model(gguf_path, modelfile_dir):
        sys.exit(1)

    # ── 4. Patch application config ────────────────────────────────────────────
    if not patch_ollama_service():
        sys.exit(1)

    # ── 5. Quick smoke test ────────────────────────────────────────────────────
    print("\n🧪 Running smoke test (asking the model a quick question)...")
    try:
        test_result = subprocess.run(
            ["ollama", "run", MODEL_ALIAS, "Say hello in one sentence as KrishiMitra AI."],
            capture_output=True, text=True, timeout=60
        )
        if test_result.returncode == 0 and test_result.stdout.strip():
            print(f"✅ Model response: {test_result.stdout.strip()[:200]}")
        else:
            print(f"⚠️  Smoke test produced no output (model may still be loading).")
    except subprocess.TimeoutExpired:
        print("⚠️  Smoke test timed out (60s). Model may need more warmup time.")
    except Exception as e:
        print(f"⚠️  Smoke test skipped: {e}")

    print(f"\n{'═'*55}")
    print("🎉  KrishiMitra LLM is ready!")
    print(f"{'═'*55}")
    print(f"  Model alias : {MODEL_ALIAS}")
    print(f"  GGUF file   : {gguf_path}")
    print(f"  Ollama API  : {OLLAMA_BASE_URL}")
    print(f"\n  Next steps:")
    print(f"    cd {PARENT_DIR}/phase1")
    print(f"    bash start.sh")
    print(f"{'═'*55}")


if __name__ == "__main__":
    main()
