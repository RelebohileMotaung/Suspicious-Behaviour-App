# 🚀 Deployment Guide for HR & Tech Teams
## Suspicious Behaviour Detection System - MongoDB Edition

### 📋 Executive Summary for Leadership

This guide provides **step-by-step instructions** for HR and Tech teams to deploy the Suspicious Behaviour Detection System from scratch to production on Render. All commands, configurations, and architecture decisions are documented for seamless deployment.

---

## 🎯 Quick Start Checklist for Teams

### ✅ Pre-Deployment Requirements
| Team | Responsibility | Status |
|------|----------------|--------|
| **HR** | MongoDB Atlas account setup | ⏳ |
| **Tech** | Git repository access | ⏳ |
| **Tech** | Render account creation | ⏳ |
| **Tech** | Environment variables configuration | ⏳ |

---

## 🏗️ Architecture Overview for Leadership

```
┌─────────────────────────────────────────────────────────────┐
│                    Production Architecture                    │
├─────────────────────────────────────────────────────────────┤
│  🌐 Render Cloud Platform                                   │
│  ├─ Web Service: Streamlit App (Port 10000)                │
│  ├─ Background Worker: Video Processing                      │
│  └─ MongoDB Atlas (Managed Database)                       │
├─────────────────────────────────────────────────────────────┤
│  📊 Data Flow:                                              │
│  Video Upload → AI Analysis → MongoDB Storage → Dashboard  │
├─────────────────────────────────────────────────────────────┤
│  🔐 Security Layers:                                        │
│  - HTTPS/TLS encryption                                    │
│  - MongoDB connection encryption                          │
│  - Environment variable protection                        │
│  - Access logging & monitoring                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📥 Step 1: Repository Setup & Cloning

### For Tech Team Lead:

```bash
# 1. Clone the repository
git clone https://github.com/your-org/suspicious-behaviour-mongodb.git
cd suspicious-behaviour-mongodb

# 2. Verify repository structure
ls -la
# Expected output:
# - app_mongodb.py (main application)
# - app/ (source code)
# - requirements.txt
# - Dockerfile
# - render.yaml
# - README.md
```

---

## 🔧 Step 2: Environment Configuration

### For Tech Team:

Create `.env` file in project root:
```bash
# Copy template
cp .env.example .env

# Edit with your credentials
nano .env
```

### Required Environment Variables:
```bash
# MongoDB Configuration (HR Team provides)
MONGODB_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/cash_monitor
MONGODB_DATABASE=cash_monitor

# Google API (HR Team provides)
GOOGLE_API_KEY=your-gemini-api-key-here

# Application Settings
PORT=10000
STREAMLIT_SERVER_PORT=10000
```

---

## 🗄️ Step 3: MongoDB Atlas Setup (HR Team)

### For HR Team Lead:

1. **Create MongoDB Atlas Account**
   - Visit: https://www.mongodb.com/cloud/atlas
   - Create free tier cluster (M0)
   - Whitelist IP: `0.0.0.0/0` (for Render deployment)

2. **Create Database User**
   ```bash
   Username: cash_monitor_user
   Password: [generate-secure-password]
   Database: cash_monitor
   ```

3. **Get Connection String**
   ```bash
   # Format: mongodb+srv://<username>:<password>@cluster.mongodb.net/cash_monitor
   ```

---

## 🐳 Step 4: Local Testing (Tech Team)

### For Tech Lead:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Test MongoDB connection
python -c "from app.db.mongo_config import check_mongodb_connection; check_mongodb_connection()"

# 3. Run local development server
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```

**Expected Output:**
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
Network URL: http://192.168.x.x:8501
```

---

## 🚀 Step 5: Render Deployment (Tech Team)

### For Tech Lead:

#### Option A: One-Click Deploy (Recommended)
1. **Click the Deploy Button:**
   [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/your-org/suspicious-behaviour-mongodb)

#### Option B: Manual Deployment

1. **Create Render Account**
   - Visit: https://render.com
   - Connect GitHub account

2. **Create New Web Service**
   ```bash
   # Service Configuration:
   Name: suspicious-behavior-detector
   Environment: Python 3.9
   Build Command: pip install -r requirements.txt
   Start Command: streamlit run app.py --server.port=10000 --server.address=0.0.0.0
   ```

3. **Environment Variables Configuration**
   ```bash
   # In Render Dashboard → Environment → Add Variables:
   MONGODB_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/cash_monitor
   GOOGLE_API_KEY=your-gemini-api-key
   PORT=10000
   ```

---

## 🔍 Step 6: Post-Deployment Verification

### For Tech Team:

```bash
# 1. Check deployment status
curl https://your-app.onrender.com/health

# 2. Test video upload functionality
# Upload a test video through the web interface

# 3. Verify MongoDB data
python -c "
from app.db.mongo_config import get_mongo_client
client = get_mongo_client()
print('Connected to MongoDB:', client.admin.command('ping'))
"
```

---

## 📊 Step 7: Monitoring & Maintenance

### For Tech Team Lead:

#### Daily Monitoring Commands:
```bash
# Check application logs
render logs suspicious-behavior-detector

# Monitor MongoDB performance
python -c "
from app.db.mongo_config import get_performance_metrics
get_performance_metrics()
"
```

#### Weekly Maintenance:
```bash
# Clean up old telemetry data
python -c "
from app.db.mongo_config import cleanup_old_data
cleanup_old_data(days=30)
"
```

---

## 🚨 Troubleshooting Quick Reference

### Common Issues & Solutions:

| Issue | Solution | Team |
|-------|----------|------|
| **MongoDB Connection Failed** | Check MONGODB_URI format and credentials | Tech |
| **Streamlit Port Error** | Ensure PORT=10000 in environment | Tech |
| **Video Upload Fails** | Check file permissions and disk space | Tech |
| **AI Analysis Disabled** | Verify GOOGLE_API_KEY is set | HR |
| **Memory Issues** | Monitor via Render dashboard | Tech |

---

## 📞 Emergency Contacts

| Role | Contact | Responsibility |
|------|---------|----------------|
| **Tech Lead** | [tech-lead@company.com] | Deployment issues |
| **HR Manager** | [hr@company.com] | MongoDB credentials |
| **System Admin** | [admin@company.com] | Infrastructure issues |

---

## 🔄 Continuous Deployment Pipeline

### For DevOps Team:

```bash
# 1. GitHub Actions Setup (Optional)
# Create .github/workflows/deploy.yml for automated deployments

# 2. Staging Environment
# Create separate Render service for staging: suspicious-behavior-staging

# 3. Production Deployment
# Use GitHub Actions to deploy to production on tag releases
```

---

## 📈 Success Metrics

### For Leadership Review:

- **Deployment Time**: < 30 minutes from clone to live
- **Uptime Target**: 99.9% availability
- **Response Time**: < 3 seconds for video analysis
- **Cost Efficiency**: <$5/month for basic usage

---

## 🎉 Next Steps After Deployment

1. **Week 1**: Monitor performance and user feedback
2. **Week 2**: Scale MongoDB cluster if needed
3. **Week 3**: Implement additional security features
4. **Month 1**: Performance optimization based on usage

**Deployment Status**: ✅ Ready for Production
</result>
</attempt_completion>
</attempt_completion>
