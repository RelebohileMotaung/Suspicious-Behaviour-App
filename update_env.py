#!/usr/bin/env python3
"""
Script to update your .env file with secure MongoDB and Google API credentials
"""

import os

# Check if .env already exists
if os.path.exists('.env'):
    print("⚠️  .env file already exists. Creating backup...")
    import shutil
    shutil.copy('.env', '.env.backup')

# MongoDB configuration - using environment variables
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
MONGODB_CONNECTION_STRING = os.getenv('MONGODB_CONNECTION_STRING', MONGO_URI)

# Google API configuration
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')

# Create comprehensive .env file
env_content = f"""# MongoDB Configuration
MONGO_URI={MONGO_URI}
MONGODB_CONNECTION_STRING={MONGODB_CONNECTION_STRING}

# MongoDB Database Settings
MONGODB_DATABASE_NAME=cash_counter
MONGODB_COLLECTION_NAME=suspicious_behavior_chat_history

# Google API Configuration
GOOGLE_API_KEY={GOOGLE_API_KEY}

# Application Settings
DEBUG=True
ALERT_WEBHOOK=

# Security Settings
# Never commit actual credentials to version control
# Use these environment variables in your applications
# Set GOOGLE_API_KEY to enable AI features
"""

with open('.env', 'w') as f:
    f.write(env_content)

print("✅ .env file updated with secure MongoDB and Google API configuration")
print("🔒 Remember to add .env to your .gitignore file")
print("You can now run: python test_mongodb_connection.py")
print("🤖 Set GOOGLE_API_KEY to enable AI features and avoid quota errors")
