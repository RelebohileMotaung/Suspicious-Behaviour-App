"""
Robust Cash Counter Monitoring with Gemini Telemetry
Handles file permissions and provides comprehensive error handling
"""

import cv2
import numpy as np
import os
import time
import base64
import threading
import sqlite3
import pandas as pd
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import streamlit as st
import tempfile
from dotenv import load_dotenv
import tiktoken
import logging

# Import telemetry systems
from telemetry_manager import get_telemetry_manager
import telemetry as basic_telemetry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set up Gemini AI
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    st.error("Please set GOOGLE_API_KEY in your .env file")
    st.stop()

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
gemini_model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

# Create folder for saving full-frame images
FRAME_FOLDER = "full_frames"
os.makedirs(FRAME_FOLDER, exist_ok=True)

# SQLite database setup
DB_NAME = "robust_telemetry.db"

def upgrade_database():
    """Upgrade database schema for enhanced monitoring"""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # Add columns if they don't exist
        c.execute("PRAGMA table_info(observations)")
        columns = [col[1] for col in c.fetchall()]
        
        if 'human_feedback' not in columns:
            c.execute("ALTER TABLE observations ADD COLUMN human_feedback TEXT")
            logger.info("Added human_feedback column")
        
        if 'model_version' not in columns:
            c.execute("ALTER TABLE observations ADD COLUMN model_version TEXT")
            logger.info("Added model_version column")
            
        if 'latency_ms' not in columns:
            c.execute("ALTER TABLE observations ADD COLUMN latency_ms REAL")
            logger.info("Added latency_ms column")
            
        if 'tokens_in' not in columns:
            c.execute("ALTER TABLE observations ADD COLUMN tokens_in INTEGER")
            logger.info("Added tokens_in column")
            
        if 'tokens_out' not in columns:
            c.execute("ALTER TABLE observations ADD COLUMN tokens_out INTEGER")
            logger.info("Added tokens_out column")
            
        if 'cost_usd' not in columns:
            c.execute("ALTER TABLE observations ADD COLUMN cost_usd REAL")
            logger.info("Added cost_usd column")
            
        if 'theft_detected' not in columns:
            c.execute("ALTER TABLE observations ADD COLUMN theft_detected BOOLEAN")
            logger.info("Added theft_detected column")
            
        if 'eval_result' not in columns:
            c.execute("ALTER TABLE observations ADD COLUMN eval_result TEXT")
            logger.info("Added eval_result column")

        # Create monitoring table
        c.execute("""
        CREATE TABLE IF NOT EXISTS performance_metrics (
            timestamp TEXT PRIMARY KEY,
            avg_latency REAL,
            total_cost REAL,
            detection_rate REAL,
            error_rate REAL
        )
        """)
        logger.info("Created performance_metrics table")
        
        conn.commit()
        logger.info("Database schema upgraded successfully")
    except Exception as e:
        logger.error(f"Database upgrade failed: {e}")
    finally:
        conn.close()

def init_db():
    """Initialize database with telemetry columns."""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS observations
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     timestamp TEXT,
                     observation TEXT,
                     image_path TEXT,
                     latency_ms REAL,
                     tokens_in INTEGER,
                     tokens_out INTEGER,
                     cost_usd REAL,
                     theft_detected BOOLEAN,
                     eval_result TEXT,
                     human_feedback TEXT,
                     model_version TEXT)''')
        conn.commit()
        
        # Check if eval_result column exists, if not add it
        c.execute("PRAGMA table_info(observations)")
        columns = [column[1] for column in c.fetchall()]
        
        # Add any missing columns
        missing_columns = ['human_feedback', 'model_version', 'latency_ms', 'tokens_in', 'tokens_out', 'cost_usd', 'theft_detected', 'eval_result']
        for col in missing_columns:
            if col not in columns:
                c.execute(f"ALTER TABLE observations ADD COLUMN {col} TEXT")
                logger.info(f"Added {col} column to observations table")
        
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

# Call upgrade during initialization
upgrade_database()
init_db()

def count_tokens(text):
    """Count tokens using tiktoken."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text)) if text else 0
    except Exception as e:
        logger.error(f"Token counting failed: {e}")
        return 0

def save_observation(timestamp, observation, image_path, telemetry_data, theft_detected):
    """Save observation with telemetry data."""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""INSERT INTO observations 
                     (timestamp, observation, image_path, latency_ms, tokens_in, tokens_out, cost_usd, theft_detected) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (timestamp, observation, image_path, 
                   telemetry_data.get('latency_ms', 0),
                   telemetry_data.get('tokens_in', 0),
                   telemetry_data.get('tokens_out', 0),
                   telemetry_data.get('cost_usd', 0),
                   theft_detected))
        conn.commit()
        conn.close()
        logger.info(f"Observation saved: {timestamp}")
    except Exception as e:
        logger.error(f"Failed to save observation: {e}")

def get_observations():
    """Get all observations with column names."""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # Get column names first
        c.execute("PRAGMA table_info(observations)")
        columns_info = c.fetchall()
        column_names = [col[1] for col in columns_info]
        
        # Get data
        c.execute("SELECT * FROM observations ORDER BY timestamp DESC")
        rows = c.fetchall()
        
        # Convert to list of dictionaries to avoid unpacking issues
        observations = []
        for row in rows:
            obs_dict = dict(zip(column_names, row))
            observations.append(obs_dict)
        
        conn.close()
        return observations
    except Exception as e:
        logger.error(f"Failed to get observations: {e}")
        return []

def image_to_base64(image_path):
    """Convert image to base64 string."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to convert image to base64: {e}")
        return ""

def log_event(event_type, data):
    """Log events for monitoring and alerts."""
    logger.info(f"EVENT: {event_type} - {data}")

def evaluate_response(image_path, model_response):
    """Evaluate the model response using LLM self-evaluation."""
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

def save_observation_with_eval(timestamp, observation, image_path, telemetry_data, theft_detected, eval_result=None):
    """Save observation with telemetry data and evaluation result."""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""INSERT INTO observations 
                     (timestamp, observation, image_path, latency_ms, tokens_in, tokens_out, cost_usd, theft_detected, eval_result) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (timestamp, observation, image_path, 
                   telemetry_data.get('latency_ms', 0),
                   telemetry_data.get('tokens_in', 0),
                   telemetry_data.get('tokens_out', 0),
                   telemetry_data.get('cost_usd', 0),
                   theft_detected,
                   eval_result))
        
        rowid = c.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"Observation saved: {timestamp} with eval: {eval_result}")
        return rowid
    except Exception as e:
        logger.error(f"Failed to save observation: {e}")
        return None

def update_observation_eval(rowid, eval_result):
    """Update observation with evaluation result."""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE observations SET eval_result=? WHERE id=?", (eval_result, rowid))
        conn.commit()
        conn.close()
        logger.info(f"Updated observation {rowid} with eval: {eval_result}")
    except Exception as e:
        logger.error(f"Failed to update observation: {e}")

def analyze_image(image_path, timestamp):
    """Analyze image with Gemini and track telemetry."""
    start_time = time.time()
    
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
            # Save observation first to get row ID
            rowid = save_observation_with_eval(time.strftime("%Y-%m-%d %H:%M:%S"), 
                                             observation, image_path, telemetry_data, theft_detected)
            
            # Perform LLM self-evaluation if "Yes" detected
            if "Yes" in observation:
                eval_label = evaluate_response(image_path, observation)
                update_observation_eval(rowid, eval_label)
                log_event("llm_eval", {"id": rowid, "eval": eval_label})
        
        return observation, telemetry_data
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return f"Error: {str(e)}", {}

def process_video_safe(video_path):
    """Process video with comprehensive error handling."""
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
                timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
                image_path = os.path.join(FRAME_FOLDER, f"frame_{timestamp}.jpg")
                
                try:
                    cv2.imwrite(image_path, frame)
                    thread = threading.Thread(target=analyze_image, args=(image_path, timestamp))
                    thread.daemon = True
                    thread.start()
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

def feedback_system():
    """Human-in-the-loop feedback system with improved error handling"""
    st.header("🔍 Feedback & Correction")
    
    # Use session state to manage feedback submission
    if 'feedback_submitted' not in st.session_state:
        st.session_state.feedback_submitted = False
    
    try:
        conn = sqlite3.connect(DB_NAME)
        
        # Get observations that need feedback
        c = conn.cursor()
        c.execute("""
            SELECT id, timestamp, observation, image_path 
            FROM observations 
            WHERE theft_detected = 1 AND (human_feedback IS NULL OR human_feedback = '')
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        
        observations = c.fetchall()
        conn.close()
        
        if observations:
            # Create display options
            display_options = [f"{obs[1]} - {obs[2][:50]}..." for obs in observations]
            
            selected_display = st.selectbox(
                "Select detection to review",
                display_options,
                key="feedback_select"
            )
            
            selected_index = display_options.index(selected_display)
            selected_id, selected_timestamp, selected_obs, selected_img = observations[selected_index]
            
            col1, col2 = st.columns(2)
            with col1:
                if os.path.exists(selected_img):
                    st.image(selected_img, caption="Captured Frame")
                else:
                    st.warning("Image not found")
            
            with col2:
                feedback = st.radio(
                    "Was this detection correct?",
                    ("Correct", "False Positive", "Insufficient Details"),
                    key="feedback_radio"
                )
                
                # Create a form to handle submission properly
                with st.form("feedback_form"):
                    st.write("Review the detection above and provide feedback")
                    submitted = st.form_submit_button("Submit Feedback")
                    
                    if submitted and not st.session_state.feedback_submitted:
                        try:
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            
                            # Update the observation with feedback
                            c.execute("""
                                UPDATE observations 
                                SET human_feedback = ? 
                                WHERE id = ?
                            """, (feedback, selected_id))
                            conn.commit()
                            
                            # Log feedback for model improvement
                            telemetry_manager = get_telemetry_manager()
                            if telemetry_manager:
                                try:
                                    telemetry_manager.record_metric(
                                        "human_feedback",
                                        1,
                                        {
                                            "observation_id": int(selected_id),
                                            "verdict": str(feedback),
                                            "image_path": str(selected_img)
                                        }
                                    )
                                except Exception as e:
                                    logger.error(f"Telemetry logging failed: {e}")
                            
                            st.session_state.feedback_submitted = True
                            st.success("✅ Feedback submitted successfully!")
                            
                            # Use experimental rerun to avoid issues
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Failed to save feedback: {str(e)}")
                            logger.error(f"Feedback save error: {e}")
                        finally:
                            conn.close()
                
                # Reset button to allow new feedback
                if st.session_state.feedback_submitted:
                    if st.button("Submit Another Feedback"):
                        st.session_state.feedback_submitted = False
                        st.rerun()
        else:
            st.info("No detections available for review")
            
    except Exception as e:
        st.error(f"Error loading feedback data: {str(e)}")
        logger.error(f"Feedback system error: {e}")

def main():
    st.set_page_config(page_title="Cash Counter Monitoring", layout="wide")
    
    st.title("🎥 Cash Counter Monitoring with Gemini Telemetry")
    st.markdown("Monitor video footage with AI-powered analysis and performance tracking")
    
    # Initialize session state
    if 'processing' not in st.session_state:
        st.session_state['processing'] = False
    
    # Sidebar for telemetry
    with st.sidebar:
        st.header("📊 Telemetry Dashboard")
        
        observations = get_observations()
        st.metric("Total Observations", len(observations))
        
        # Model Metrics Dashboard
        st.subheader("Model Metrics")
        conn = sqlite3.connect(DB_NAME)
        total_y = conn.execute("SELECT COUNT(*) FROM observations WHERE observation LIKE '%Yes%'").fetchone()[0]
        correct = conn.execute("SELECT COUNT(*) FROM observations WHERE eval_result='CORRECT'").fetchone()[0]
        conn.close()
        
        st.metric("Total Theft Alerts", total_y)
        if total_y > 0:
            st.metric("Self-Reported Accuracy", f"{correct/max(total_y,1):.0%}")
        else:
            st.metric("Self-Reported Accuracy", "N/A")
        
        if observations:
            st.subheader("Recent Analysis")
            for obs in observations[:5]:
                try:
                    # Access dictionary keys directly since observations are now dictionaries
                    timestamp = obs.get('timestamp', 'N/A')
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
        
        # Enhanced file upload with better error handling
        st.subheader("📹 Video Upload")
        
        # File size warning
        st.info("💡 Tip: Large files may take time to upload. Max recommended: 200MB")
        
        video_file = st.file_uploader(
            "Upload Video File", 
            type=["mp4", "avi", "mov", "mkv"],
            help="Upload a video file to analyze (max 200MB)",
            key="video_uploader"
        )
        
        if video_file is not None:
            file_size_mb = video_file.size / (1024 * 1024)
            st.write(f"📊 File: {video_file.name} ({file_size_mb:.1f} MB)")
            
            if file_size_mb > 100:
                st.warning("⚠️ Large file detected - upload may take time")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("▶️ Start Monitoring", disabled=video_file is None):
                if video_file is not None:
                    try:
                        # Enhanced file handling with progress
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        status_text.text("📤 Saving uploaded file...")
                        
                        # Save uploaded file to temp location with progress
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                            # Read in chunks for large files
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
                        
                        if process_video_safe(tmp_path):
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
                        st.error(f"Error type: {type(e).__name__}")
                        logger.error(f"Upload error: {e}", exc_info=True)
                else:
                    st.error("Please select a video file first")
        
        with col2:
            if st.button("⏹️ Stop"):
                st.session_state['processing'] = False
                st.info("Monitoring stopped")
                
        # Upload troubleshooting info
        with st.expander("🛠️ Upload Issues?"):
            st.markdown("""
            **Common solutions for 403 errors:**
            1. **Check file size** - Ensure file is under 200MB
            2. **Try different browser** - Chrome/Firefox recommended
            3. **Clear browser cache** - Ctrl+Shift+Delete
            4. **Disable browser extensions** - Ad blockers may interfere
            5. **Check network** - Corporate firewalls may block uploads
            """)

    # Main content area with tabs
    tab1, tab2, tab3 = st.tabs(["📈 Performance Metrics", "🔍 Feedback & Correction", "📊 Analytics"])
    
    with tab1:
        st.header("📈 Performance Metrics")
        
        # Display telemetry summary
        observations = get_observations()
        if observations:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Analyses", len(observations))
            with col2:
                avg_latency = sum(obs.get('latency_ms', 0) for obs in observations) / len(observations) if observations else 0
                st.metric("Avg Latency", f"{avg_latency:.1f}ms")
            with col3:
                total_cost = sum(obs.get('cost_usd', 0) for obs in observations)
                st.metric("Total Cost", f"${total_cost:.6f}")
    
    with tab2:
        # Use the robust feedback system with RerunData error fix
        try:
            from feedback_rerun_fix import get_feedback_form
            feedback_form = get_feedback_form()
            feedback_form()
        except ImportError as e:
            st.error(f"Failed to load feedback system: {e}")
            feedback_system()
    
    with tab3:
        st.header("📊 Analytics")
        st.info("Analytics dashboard coming soon...")

if __name__ == "__main__":
    main()
