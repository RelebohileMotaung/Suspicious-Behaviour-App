# Suspicious Behaviour Detection System - MongoDB Edition

A comprehensive AI-powered surveillance system that detects suspicious behavior using computer vision and machine learning, with MongoDB as the primary database for storing telemetry, chat history, and configuration data.

## 🚀 Features

- **Real-time Video Analysis**: Continuous monitoring with frame-by-frame analysis
- **AI-Powered Detection**: Advanced ML models for suspicious behavior identification
- **MongoDB Integration**: Scalable NoSQL database for telemetry and chat storage
- **LangChain Integration**: Conversational AI with memory persistence
- **Google Drive Integration**: Automatic backup and file management
- **Web Dashboard**: Real-time monitoring interface
- **Docker Support**: Containerized deployment ready
- **Render Deployment**: One-click deployment to cloud

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Deployment on Render](#deployment-on-render)
- [Monitoring & Telemetry](#monitoring--telemetry)
- [Troubleshooting](#troubleshooting)

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Web Interface                   │
├─────────────────────────────────────────────────────────────┤
│                    Flask API Layer                          │
├─────────────────────────────────────────────────────────────┤
│                  MongoDB Database                           │
│  ├─ observations (telemetry data)                          │
│  ├─ chat_history (conversational AI)                      │
│  ├─ alerts (system notifications)                          │
│  └─ configuration (system settings)                        │
├─────────────────────────────────────────────────────────────┤
│                  AI Processing Layer                        │
│  ├─ Google Gemini AI (behavior analysis)                   │
│  ├─ Computer Vision (frame processing)                     │
│  └─ LangChain (<thinking>
I have received the full content of app_mongodb.py which is the main application file. It contains the core logic for video processing, MongoDB integration, telemetry, AI model interaction, and feedback system. This file alone provides a comprehensive overview of the app's functionality.

Next, I need to understand the MongoDB configuration and handler to explain database setup and connection details. The relevant files appear to be app/db/mongo_config.py and app/db/langchain_mongodb_manager.py.

I also want to check the Dockerfile and render.yaml to understand containerization and deployment configuration for Render.

I will proceed to read app/db/mongo_config.py next to understand the MongoDB connection setup.
</thinking>

<read_file>
<path>app/db/mongo_config.py</path>
</read_file>
