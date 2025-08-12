#!/usr/bin/env python3
"""
Script to verify that environment variables are properly loaded from .env file
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Environment Variables Check:")
print("=" * 40)

# Check MongoDB configuration
mongo_uri = os.getenv('MONGO_URI')
mongo_db_name = os.getenv('MONGO_DB_NAME')
google_api_key = os.getenv('GOOGLE_API_KEY')

print(f"MONGO_URI: {'✓ Loaded' if mongo_uri else '✗ Missing'}")
print(f"MONGO_DB_NAME: {'✓ Loaded' if mongo_db_name else '✗ Missing'}")
print(f"GOOGLE_API_KEY: {'✓ Loaded' if google_api_key else '✗ Missing'}")

# Show masked values for verification
if mongo_uri:
    print(f"MONGO_URI (masked): {mongo_uri[:20]}...{mongo_uri[-10:]}")
if mongo_db_name:
    print(f"MONGO_DB_NAME: {mongo_db_name}")
if google_api_key:
    print(f"GOOGLE_API_KEY (masked): {google_api_key[:10]}...{google_api_key[-4:]}")

print("\nIf any variables show '✗ Missing', please check your .env file.")
