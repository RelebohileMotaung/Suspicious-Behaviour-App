#!/usr/bin/env python3
"""
MongoDB Setup Script
Helps configure MongoDB connection for the Cash Counter Monitoring System
"""

import os
import sys
from pathlib import Path

def setup_mongodb():
    """Interactive setup for MongoDB configuration"""
    print("=== MongoDB Setup for Cash Counter Monitoring System ===\n")
    
    print("Choose your MongoDB setup:")
    print("1. MongoDB Atlas (Cloud)")
    print("2. Local MongoDB")
    print("3. In-memory storage (development only)")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        setup_atlas()
    elif choice == "2":
        setup_local()
    elif choice == "3":
        setup_memory()
    else:
        print("Invalid choice. Using in-memory storage.")
        setup_memory()

def setup_atlas():
    """Setup MongoDB Atlas connection"""
    print("\n=== MongoDB Atlas Setup ===")
    print("Please provide your MongoDB Atlas connection details:")
    
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    cluster = input("Cluster URL (e.g., cluster0.mongodb.net): ").strip()
    db_name = input("Database name [cash_counter]: ").strip() or "cash_counter"
    
    connection_string = f"mongodb+srv://{username}:{password}@{cluster}/{db_name}?retryWrites=true&w=majority"
    
    # Test connection
    try:
        from pymongo import MongoClient
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB Atlas!")
        
        # Save to .env file
        with open('.env', 'w') as f:
            f.write(f"MONGO_URI={connection_string}\n")
            f.write(f"MONGO_DB_NAME={db_name}\n")
        print("✅ Configuration saved to .env file")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("Please check your credentials and try again.")

def setup_local():
    """Setup local MongoDB connection"""
    print("\n=== Local MongoDB Setup ===")
    
    host = input("Host [localhost]: ").strip() or "localhost"
    port = input("Port [27017]: ").strip() or "27017"
    db_name = input("Database name [cash_counter]: ").strip() or "cash_counter"
    
    connection_string = f"mongodb://{host}:{port}"
    
    # Test connection
    try:
        from pymongo import MongoClient
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("✅ Successfully connected to local MongoDB!")
        
        # Save to .env file
        with open('.env', 'w') as f:
            f.write(f"MONGO_URI={connection_string}\n")
            f.write(f"MONGO_DB_NAME={db_name}\n")
        print("✅ Configuration saved to .env file")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("Please ensure MongoDB is running locally and try again.")

def setup_memory():
    """Setup in-memory storage for development"""
    print("\n=== In-Memory Storage Setup ===")
    print("Using in-memory storage for development (no MongoDB required)")
    
    # Save configuration for in-memory storage
    with open('.env', 'w') as f:
        f.write("# Using in-memory storage for development\n")
        f.write("MONGO_URI=memory\n")
        f.write("MONGO_DB_NAME=memory\n")
    print("✅ In-memory storage configured")

if __name__ == "__main__":
    setup_mongodb()
