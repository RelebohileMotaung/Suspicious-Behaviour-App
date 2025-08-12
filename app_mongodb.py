"""
Robust Cash Counter Monitoring with MongoDB and Gemini Telemetry
Enhanced version using MongoDB instead of SQLite for better scalability
"""

import cv2
import numpy as np
import os
import time
import base64
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import streamlit as st
import tempfile
from dotenv import load_dotenv
import tiktoken

# Import MongoDB handler and telemetry systems
from app.db.mongo_handler import get_mongo_handler
from app.utils.file_handler import FileHandler
from telemetry_manager_mongodb import get_telemetry_manager_mongodb as get_telemetry_manager
import telemetry as basic_telemetry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set up Gemini AI
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    logger.warning("GOOGLE_API_KEY not found - AI features will be disabled")
    gemini_model = None
else:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
    gemini_model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

# Create folder for saving full-frame images
FRAME_FOLDER = "full_frames"
FileHandler.ensure_directory_exists(FRAME_FOLDER)

# Initialize MongoDB handler
mongo_handler = get_mongo_handler()

def count_tokens(text: str) -> int:
    """Count tokens using tiktoken."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text)) if text else 0
    except Exception as e:
        logger.error(f"Token counting failed: {e}")
        return 0

def save_observation_mongo(timestamp: str, observation: str, image_path: str, 
                          telemetry_data: Dict[str, Any], theft_detected: bool) -> str:
    """Save observation to MongoDB with comprehensive telemetry data."""
    try:
        observation_data = {
            "timestamp": datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp,
            "observation": observation,
            "image_path": image_path,
            "latency_ms": telemetry_data.get('latency_ms', 0),
            "tokens_in": telemetry_data.get('tokens_in', 0),
            "tokens_out": telemetry_data.get('tokens_out', 0),
            "cost_usd": telemetry_data.get('cost_usd', 0),
            "theft_detected": bool(theft_detected),
            "model_version": "gemini-2.0-flash",
            "created_at": datetime.utcnow()
        }
        
        observation_id = mongo_handler.save_observation(observation_data)
        logger.info(f"Observation saved to MongoDB: {observation_id}")
        return str(observation_id)
        
    except Exception as e:
        logger.error(f"Failed to save observation to MongoDB: {e}")
        raise

def update_observation_eval_mongo(observation_id: str, eval_result: str) -> bool:
    """Update observation with evaluation result in MongoDB."""
    try:
        success = mongo_handler.update_observation(
            str(observation_id), 
            {"eval_result": eval_result, "updated_at": datetime.utcnow()}
        )
        if success:
            logger.info(f"Updated observation {observation_id} with eval: {eval_result}")
        return success
        
    except Exception as e:
        logger.error(f"Failed to update observation: {e}")
        return False

def get_observations_mongo(limit: int = 100, filter_dict: Optional[Dict] = None) -> list:
    """Get observations from MongoDB with flexible filtering."""
    try:
        return mongo_handler.get_observations(limit=limit, filter_dict=filter_dict)
    except Exception as e:
        logger.error(f"Failed to get observations from MongoDB: {e}")
        return []

def image_to_base64(image_path: str) -> str:
    """Convert image to base64 string."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to convert image to base64: {e}")
        return ""

def log_event(event_type: str, data: Dict[str, Any]) -> None:
    """Log events for monitoring and alerts."""
    logger.info(f"EVENT: {event_type} - {data}")
    
    # Also save to MongoDB alerts collection
    try:
        severity = "warning" if "alert" in event_type.lower() else "info"
        mongo_handler.save_alert(event_type, severity, data)
    except Exception as e:
        logger.error(f"Failed to save alert: {e}")

def evaluate_response(image_path: str, model_response: str) -> str:
    """Evaluate the model response using LLM self-evaluation."""
    if gemini_model is None:
        return "DISABLED"
    
    try:
        prompt = f"""
        You are an LLM evaluator. Given the image and the previous model answer below, output ONLY one word: CORRECT or INCORRECT.
        Model answer: {model_response}
        """
        
        base64_image = image_to_base64(image_path)
        if not base64_image:
            return "ERROR"
        
        eval_msg = HumanMessage(content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ])
        
        eval_resp = gemini_model.invoke([eval_msg]).content.strip()
        return eval_resp.upper()
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return "ERROR"

def save_observation_with_eval_mongo(timestamp: str, observation: str, image_path: str,
                                   telemetry_data: Dict[str, Any], theft_detected: bool,
                                   eval_result: Optional[str] = None) -> str:
    """Save observation with telemetry data and evaluation result to MongoDB."""
    try:
        observation_data = {
            "timestamp": datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp,
            "observation": observation,
            "image_path": image_path,
            "latency_ms": telemetry_data.get('latency_ms', 0),
            "tokens_in": telemetry_data.get('tokens_in', 0),
            "tokens_out": telemetry_data.get('tokens_out', 0),
            "cost_usd": telemetry_data.get('cost_usd', 0),
            "theft_detected": bool(theft_detected),
            "eval_result": eval_result,
            "model_version": "gemini-2.0-flash",
            "created_at": datetime.utcnow()
        }
        
        observation_id = mongo_handler.save_observation(observation_data)
        logger.info(f"Observation with eval saved to MongoDB: {observation_id}")
        return str(observation_id)
        
    except Exception as e:
        logger.error(f"Failed to save observation with eval: {e}")
        return ""

def analyze_image_mongo(image_path: str, timestamp: str) -> tuple:
    """Analyze image with Gemini and track telemetry using MongoDB."""
    start_time = time.time()
    
    if gemini_model is None:
        return "AI analysis disabled - no API key", {}
    
    try:
        # Check if file exists and is readable
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return "Error: Image file not found", {}
        
        if not os.access(image_path, os.R_OK):
            logger.error(f"Image file not readable: {image_path}")
            return "Error: Image file not readable", {}

        with open(image_path, "rb") as img_file:
            base64_image = base64.b64encode(img_file.read()).decode("utf-8")

        prompt = """
         Observe the **cash counter area** and respond in a structured format.
                If money theft is detected (**"Yes"**), provide details of the **suspect**.
                NO More Details  
                | Suspicious Activity at Cash Counter | Observed? (Yes/No) | Suspect Description (If Yes) |
                |--------------------------------------|--------------------|-----------------------------|
                | Money theft from cash counter?      |                    |                             |

                If theft is detected, describe the **clothing, appearance, and any identifiable features** of the suspect.
                Otherwise, leave the details column empty.
        """

        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        )

        response = gemini_model.invoke([message])
        processing_time = time.time() - start_time
        
        observation = response.content.strip()
        theft_detected = any(word in observation.lower() for word in ['theft', 'steal', 'rob', 'suspicious'])
        
        # Calculate telemetry
        tokens_in = count_tokens(prompt)
        tokens_out = count_tokens(observation)
        cost_usd = (tokens_in + tokens_out) * 0.0005
        
        telemetry_data = {
            'latency_ms': processing_time * 1000,
            'tokens_in': tokens_in,
            'tokens_out': tokens_out,
            'cost_usd': cost_usd
        }
        
        # Check for cost and latency alerts
        if cost_usd > 0.005:
            log_event("high_cost_alert", {"cost": cost_usd, "image_path": image_path})
        if telemetry_data['latency_ms'] > 3000:
            log_event("high_latency_alert", {"latency": telemetry_data['latency_ms'], "image_path": image_path})
        
        if theft_detected:
            # Save observation first to get ID
            observation_id = save_observation_with_eval_mongo(
                datetime.utcnow().isoformat(),
                observation, 
                image_path, 
                telemetry_data, 
                theft_detected
            )
            
            # Perform LLM self-evaluation if "Yes" detected
            if "Yes" in observation:
                eval_label = evaluate_response(image_path, observation)
                update_observation_eval_mongo(observation_id, eval_label)
                log_event("llm_eval", {"id": observation_id, "eval": eval_label})
        
        return observation, telemetry_data
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return f"Error: {str(e)}", {}

def process_video_safe_mongo(video_path: str) -> bool:
    """Process video with comprehensive error handling using MongoDB."""
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            st.error("Cannot open video file")
            return False

        st_frame = st.empty()
        frame_count = 0
        
        while cap.isOpened() and st.session_state.get('processing', False):
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.resize(frame, (800, 450))
            frame_count += 1
            
            if frame_count % 30 == 0:  # Process every 30th frame
                timestamp = datetime.utcnow().isoformat()
                safe_filename = FileHandler.get_safe_filename(timestamp)
                image_path = os.path.join(FRAME_FOLDER, safe_filename)
                
                try:
                    if FileHandler.ensure_directory_exists(FRAME_FOLDER):
                        cv2.imwrite(image_path, frame)
                        thread = threading.Thread(
                            target=analyze_image_mongo, 
                            args=(image_path, timestamp)
                        )
                        thread.daemon = True
                        thread.start()
                    else:
                        logger.error(f"Frame folder not accessible: {FRAME_FOLDER}")
                except Exception as e:
                    logger.error(f"Frame processing failed: {e}")

            # Display frame
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            st_frame.image(frame_rgb, channels="RGB", use_column_width=True)
            
            time.sleep(0.1)

        cap.release()
        return True
        
    except Exception as e:
        logger.error(f"Video processing failed: {e}")
        st.error(f"Video processing error: {str(e)}")
        return False

def feedback_system_mongo():
    """Human-in-the-loop feedback system with MongoDB integration."""
    st.header("🔍 Feedback & Correction")
    
    # Use session state to manage feedback submission
    if 'feedback_submitted' not in st.session_state:
        st.session_state.feedback_submitted = False
    
    try:
        # Get observations that need feedback from MongoDB
        filter_dict = {
            "theft_detected": True,
            "$or": [
                {"human_feedback": {"$exists": False}},
                {"human_feedback": None},
                {"human_feedback": ""}
            ]
        }
        
        observations = mongo_handler.get_observations(limit=10, filter_dict=filter_dict)
        
        if observations:
            # Create display options
            display_options = [
                f"{obs['timestamp']} - {obs['observation'][:50]}..." 
                for obs in observations
            ]
            
            selected_display = st.selectbox(
                "Select detection to review",
                display_options,
                key="feedback_select"
            )
            
            selected_index = display_options.index(selected_display)
            selected_obs = observations[selected_index]
            
            col1, col2 = st.columns(2)
            with col1:
                if os.path.exists(selected_obs['image_path']):
                    st.image(selected_obs['image_path'], caption="Captured Frame")
                else:
                    st.warning("Image not found")
            
            with col2:
                # Create a form to handle submission properly
                with st.form("feedback_form", clear_on_submit=True):
                    feedback = st.radio(
                        "Was this detection correct?",
                        ("Correct", "False Positive", "Insufficient Details"),
                        key="feedback_radio"
                    )
                    
                    st.write("Review the detection above and provide feedback")
                    submitted = st.form_submit_button("Submit Feedback")
                    
                    if submitted and not st.session_state.feedback_submitted:
                        try:
                            # Update the observation with feedback in MongoDB
                            success = mongo_handler.update_observation(
                                str(selected_obs['_id']),
                                {"human_feedback": feedback, "updated_at": datetime.utcnow()}
                            )
                            
                            if success:
                                # Log feedback for model improvement
                                telemetry_manager = get_telemetry_manager()
                                if telemetry_manager:
                                    try:
                                        telemetry_manager.record_metric(
                                            "human_feedback",
                                            1,
                                            {
                                                "observation_id": str(selected_obs['_id']),
                                                "verdict": str(feedback),
                                                "image_path": str(selected_obs['image_path'])
                                            }
                                        )
                                    except Exception as e:
                                        logger.error(f"Telemetry logging failed: {e}")
                                
                                st.session_state.feedback_submitted = True
                                st.success("✅ Feedback submitted successfully!")
                            else:
                                st.error("❌ Failed to save feedback")
                                
                        except Exception as e:
                            st.error(f"❌ Failed to save feedback: {str(e)}")
                            logger.error(f"Feedback save error: {e}")
        else:
            st.info("No observations requiring feedback found")
            
    except Exception as e:
        st.error(f"Error loading feedback system: {str(e)}")
        logger.error(f"Feedback system error: {e}")

def main():
    """Main application with MongoDB integration."""
    st.set_page_config(page_title="Cash Counter Monitoring - MongoDB", layout="wide")
    
    st.title("🎥 Cash Counter Monitoring with MongoDB & Gemini Telemetry")
    st.markdown("Enhanced monitoring system with MongoDB for better scalability")
    
    # Initialize session state
    if 'processing' not in st.session_state:
        st.session_state['processing'] = False
    
    # Sidebar for telemetry
    with st.sidebar:
        st.header("📊 MongoDB Telemetry Dashboard")
        
        # Get observations from MongoDB
        observations = get_observations_mongo()
        st.metric("Total Observations", len(observations))
        
        # Model Metrics Dashboard
        st.subheader("Model Metrics")
        
        # Get performance summary from MongoDB
        performance_summary = mongo_handler.get_performance_summary(hours=24)
        
        total_theft = performance_summary.get('theft_detections', 0)
        correct_evals = performance_summary.get('correct_evaluations', 0)
        
        st.metric("Total Theft Alerts", total_theft)
        if total_theft > 0:
            accuracy = correct_evals / total_theft
            st.metric("Self-Reported Accuracy", f"{accuracy:.0%}")
        else:
            st.metric("Self-Reported Accuracy", "N/A")
        
        # Recent analysis from MongoDB
        if observations:
            st.subheader("Recent Analysis")
            for obs in observations[:5]:
                try:
                    timestamp = obs.get('timestamp', 'N/A')
                    if isinstance(timestamp, datetime):
                        timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    
                    observation_text = obs.get('observation', 'N/A')
                    latency = obs.get('latency_ms', 0)
                    cost = obs.get('cost_usd', 0)
                    theft = obs.get('theft_detected', False)
                    eval_result = obs.get('eval_result')
                    human_feedback = obs.get('human_feedback')
                    
                    status = "🚨 Theft" if theft else "✅ Normal"
                    st.write(f"**{timestamp}** - {status}")
                    st.write(f"Latency: {latency:.1f}ms | Cost: ${cost:.6f}")
                    if eval_result:
                        st.write(f"Eval: {eval_result}")
                    if human_feedback:
                        st.write(f"Feedback: {human_feedback}")
                except Exception as e:
                    st.error(f"Error displaying observation: {e}")
                    continue
        
        st.header("🎛️ Controls")
        
        # Enhanced file upload
        st.subheader("📹 Video Upload")
        
        video_file = st.file_uploader(
            "Upload Video File", 
            type=["mp4", "avi", "mov", "mkv"],
            help="Upload a video file to analyze",
            key="video_uploader"
        )
        
        if video_file is not None:
            file_size_mb = video_file.size / (1024 * 1024)
            st.write(f"📊 File: {video_file.name} ({file_size_mb:.1f} MB)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("▶️ Start Monitoring", disabled=video_file is None):
                if video_file is not None:
                    try:
                        # Enhanced file handling with progress
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        status_text.text("📤 Saving uploaded file...")
                        
                        # Save uploaded file to temp location
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                            chunk_size = 8192
                            total_size = video_file.size
                            bytes_written = 0
                            
                            while True:
                                chunk = video_file.read(chunk_size)
                                if not chunk:
                                    break
                                tmp.write(chunk)
                                bytes_written += len(chunk)
                                progress = min(bytes_written / total_size, 1.0)
                                progress_bar.progress(progress)
                            
                            tmp_path = tmp.name
                        
                        status_text.text("🔄 Processing video...")
                        progress_bar.progress(0.8)
                        
                        st.session_state['processing'] = True
                        
                        if process_video_safe_mongo(tmp_path):
                            progress_bar.progress(1.0)
                            status_text.text("✅ Video processing completed!")
                            st.success("Analysis complete!")
                        else:
                            st.error("❌ Failed to process video")
                            
                        # Clean up temp file
                        try:
                            os.unlink(tmp_path)
                            progress_bar.empty()
                            status_text.empty()
                        except:
                            pass
                            
                    except Exception as e:
                        st.error(f"❌ File handling error: {str(e)}")
                        logger.error(f"Upload error: {e}", exc_info=True)
                else:
                    st.error("Please select a video file first")
        
        with col2:
            if st.button("⏹️ Stop"):
                st.session_state['processing'] = False
                st.info("Monitoring stopped")

    # Main content area with tabs
    tab1, tab2, tab3 = st.tabs(["📈 Performance Metrics", "🔍 Feedback & Correction", "📊 Analytics"])
    
    with tab1:
        st.header("📈 Performance Metrics")
        
        # Display telemetry summary from MongoDB
        observations = get_observations_mongo()
        if observations:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Analyses", len(observations))
            
            with col2:
                avg_latency = sum(obs.get('latency_ms', 0) for obs in observations) / len(observations) if observations else 0
                st.metric("Avg Latency", f"{avg_latency:.1f}ms")
            
            with col3:
                total_cost = sum(obs.get('cost_usd', 0) for obs in observations)
                st.metric("Total Cost", f"${total_cost:.6f}")
            
            with col4:
                theft_count = sum(1 for obs in observations if obs.get('theft_detected', False))
                st.metric("Theft Detections", theft_count)
    
    with tab2:
        feedback_system_mongo()
    
    with tab3:
        st.header("📊 Advanced Analytics")
        
        # MongoDB aggregation examples
        st.subheader("📊 MongoDB Analytics")
        
        try:
            # Get performance summary
            performance_summary = mongo_handler.get_performance_summary(hours=24)
            
            if performance_summary:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("24h Total Analyses", performance_summary.get('total_observations', 0))
                
                with col2:
                    avg_latency = performance_summary.get('avg_latency', 0)
                    st.metric("24h Avg Latency", f"{avg_latency:.1f}ms")
                
                with col3:
                    total_cost = performance_summary.get('total_cost', 0)
                    st.metric("24h Total Cost", f"${total_cost:.6f}")
            
            # Collection statistics
            st.subheader("📈 Collection Statistics")
            
            collections = ['observations', 'telemetry', 'alerts']
            for collection in collections:
                stats = mongo_handler.get_collection_stats(collection)
                if stats['document_count'] > 0:
                    st.write(f"**{collection}**: {stats['document_count']} documents, {stats['size']} bytes")
            
        except Exception as e:
            st.error(f"Error loading analytics: {str(e)}")
            logger.error(f"Analytics error: {e}")

if __name__ == "__main__":
    main()
