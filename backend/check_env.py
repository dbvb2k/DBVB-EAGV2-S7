#!/usr/bin/env python3
"""
Script to check .env file configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / '.env'

print("=" * 80)
print("Checking .env file configuration")
print("=" * 80)
print(f"\nExpected location: {env_path}")
print(f"File exists: {env_path.exists()}")

if env_path.exists():
    print("\n[OK] .env file found")
    
    # Load and check
    load_dotenv(env_path)
    
    nomic_key = os.getenv('NOMIC_API_KEY')
    gemini_key = os.getenv('GEMINI_API_KEY')
    secret_key = os.getenv('SECRET_KEY')
    
    print("\nConfiguration values:")
    print("-" * 80)
    
    if nomic_key:
        if nomic_key.strip() == '':
            print("ERROR: NOMIC_API_KEY: EMPTY (contains only whitespace)")
        else:
            print(f"OK: NOMIC_API_KEY: Set (length: {len(nomic_key)} chars)")
            print(f"  First 4 chars: {nomic_key[:4]}...")
    else:
        print("ERROR: NOMIC_API_KEY: NOT SET")
    
    if gemini_key:
        if gemini_key.strip() == '':
            print("NOTE: GEMINI_API_KEY: EMPTY (optional)")
        else:
            print(f"OK: GEMINI_API_KEY: Set (length: {len(gemini_key)} chars)")
    else:
        print("NOTE: GEMINI_API_KEY: NOT SET (optional)")
    
    if secret_key:
        print("OK: SECRET_KEY: Set")
    else:
        print("WARNING: SECRET_KEY: NOT SET (using default)")
    
    print("\n" + "-" * 80)
    
    if not nomic_key or nomic_key.strip() == '':
        print("\n[ERROR] NOMIC_API_KEY is missing or empty!")
        print("\nTo fix this:")
        print("1. Open the .env file in a text editor")
        print("2. Add this line (replace with your actual key):")
        print("   NOMIC_API_KEY=your-actual-api-key-here")
        print("3. Get your API key from: https://atlas.nomic.ai/")
        print("4. Save the file and restart the server")
    else:
        print("\n[OK] Configuration looks good!")
        print("\nNote: If you're still getting errors, make sure:")
        print("- There are no extra quotes around the API key")
        print("- There are no spaces before or after the '=' sign")
        print("- The key is all on one line (no line breaks)")
    
else:
    print("\n[ERROR] .env file NOT FOUND!")
    print("\nTo create it:")
    print("1. Create a new file named '.env' in the backend directory")
    print("2. Add this content:")
    print("\n   NOMIC_API_KEY=your-actual-api-key-here")
    print("   GEMINI_API_KEY=your-gemini-key-here  # Optional")
    print("   SECRET_KEY=dev-key-please-change-in-production")
    print("\n3. Get your API keys:")
    print("   - Nomic: https://atlas.nomic.ai/")
    print("   - Gemini: https://makersuite.google.com/app/apikey")

print("\n" + "=" * 80)

