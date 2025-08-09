# 🚨 Suspicious-Behaviour-App

**AI-Powered Cash Counter Monitoring with Real-Time Theft Detection**

A robust video surveillance system that uses Google Gemini AI to detect suspicious behavior and potential theft at cash counters, with comprehensive telemetry and performance monitoring.

## 🎯 Overview

This application provides intelligent monitoring of cash counter areas using computer vision and AI analysis. It processes video footage in real-time, detects suspicious activities, and provides detailed analytics with human-in-the-loop feedback capabilities.

### Key Features
- **Real-time video analysis** with frame-by-frame processing
- **AI-powered theft detection** using Google Gemini 2.0 Flash
- **Comprehensive telemetry** with performance metrics and cost tracking
- **Human feedback system** for continuous model improvement
- **Database integration** for storing observations and analytics
- **Alert system** for immediate notifications
- **Web-based dashboard** with Streamlit interface

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Google API Key (Gemini 2.0 Flash)
- OpenCV-compatible video files (MP4, AVI, MOV, MKV)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-repo/Suspicious-Behaviour-App.git
cd Suspicious-Behaviour-App
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
# Create .env file
echo "GOOGLE_API_KEY=your_api_key_here" > .env
```

4. **Run the application**
```bash
streamlit run app.py
```

## 📋 Configuration

### Environment Variables
Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_api_key
TELEMETRY_WEBHOOK_URL=https://your-webhook-url.com/alerts
```

### File Structure
```
Suspicious-Behaviour-App/
├── app.py                          # Main Streamlit application
├── telemetry.py                    # Basic telemetry logging
├── telemetry_manager.py            # Enhanced telemetry with DB
├── telemetry_manager.py            # Telemetry management system
├── Dockerfile                      # Container configuration
├── render.yaml                     # Render deployment config
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables
├── telemetry/                      # Telemetry data directory
│   ├── events.jsonl               # Event logs
│   ├── metrics.jsonl              # Performance metrics
│   └── telemetry_manager.db       # SQLite database
├── full_frames/                   # Captured frame images
├── robust_telemetry.db            # Main observations database
└── README.md                      # This file
```

## 🎥 Usage Guide

### 1. Upload Video
- Click "Browse files" or drag-and-drop video files
- Supported formats: MP4, AVI, MOV, MKV
- Recommended file size: < 200MB

### 2. Start Monitoring
- Click "Start Monitoring" to begin analysis
- The system processes every 30th frame for efficiency
- Real-time frame display shows processing progress

### 3. Review Results
- **Observations**: AI-generated analysis of each frame
- **Theft Detection**: Highlighted suspicious activities
- **Performance Metrics**: Processing time and cost per frame

### 4. Provide Feedback
- Use the feedback system to validate AI detections
- Mark detections as "Correct", "False Positive", or "Insufficient Details"
- Feedback improves future model performance

## 🔧 Advanced Configuration

### Docker Deployment
```bash
# Build container
docker build -t suspicious-behaviour-app .

# Run container
docker run -p 8501:8501 -e GOOGLE_API_KEY=your_key suspicious-behaviour-app
```

### Render Deployment
The app is configured for Render deployment via `render.yaml`:
- Automatic scaling based on traffic
- Environment variable management
- Health check endpoints

### Custom Alert Webhooks
Configure webhook notifications:
```bash
export ALERT_WEBHOOK_URL=https://your-slack-webhook-url
```

## 📊 Telemetry & Monitoring

### Performance Metrics
- **Latency**: Processing time per frame (target: < 3s)
- **Cost**: API usage cost per operation (target: < $0.005)
- **Accuracy**: Self-reported model accuracy
- **Error Rate**: Failed operations percentage

### Alert Thresholds
- High latency: > 3000ms
- High cost: > $0.005 USD
- High error rate: > 10%
- High CPU usage: > 80%
- High memory usage: > 85%

### Database Schema
The system uses SQLite databases:
- **robust_telemetry.db**: Main observations storage
- **telemetry_manager.db**: Enhanced telemetry data
- **observations.db**: Legacy observations (if exists)

## 🔄 Data Flow

1. **Video Input** → Frame extraction
2. **Frame Analysis** → Gemini AI processing
3. **Result Storage** → SQLite database
4. **Telemetry Logging** → JSONL files + SQLite
5. **Alert Generation** → Webhook notifications
6. **Feedback Collection** → Human validation

## 🧪 Testing

### Manual Testing
1. Upload test video with known suspicious behavior
2. Verify theft detection accuracy
3. Check performance metrics
4. Test feedback system
5. Validate alert notifications

### Automated Testing
```bash
# Run basic functionality tests
python -c "import app; print('App loaded successfully')"

# Test telemetry
python -c "from telemetry import log_event; log_event('test', {'status': 'ok'})"
```

## 📈 Performance Optimization

### Tips for Better Performance
- Use shorter videos for faster processing
- Process during off-peak hours
- Monitor cost usage regularly
- Provide feedback to improve accuracy
- Use appropriate video quality (not too high resolution)

### Scaling Considerations
- **Horizontal**: Multiple instances with load balancer
- **Vertical**: Higher CPU/memory instances
- **Cost**: Batch processing vs. real-time

## 🔒 Security

### Data Protection
- API keys stored in environment variables
- No sensitive data in logs
- Secure webhook endpoints
- HTTPS-only communications

### Access Control
- Streamlit authentication (if configured)
- Environment variable restrictions
- File upload size limits

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Check code style
flake8 .
```

## 📞 Support

### Troubleshooting
- **403 errors**: Check API key validity
- **Memory issues**: Reduce video file size
- **Slow processing**: Check system resources
- **No detections**: Verify video quality

### Contact
- GitHub Issues: [Create an issue](https://github.com/your-repo/Suspicious-Behaviour-App/issues)
- Email: support@your-domain.com

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Google Gemini AI for providing the vision capabilities
- Streamlit for the web framework
- OpenCV for video processing
- The open-source community for various dependencies

---

**Built with ❤️ for safer cash handling environments**
