import cv2
import numpy as np
import os
import time
import base64
import threading
import sqlite3
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import streamlit as st
from PIL import Image
import tempfile
from dotenv import load_dotenv

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
DB_NAME = "observations.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS observations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 timestamp TEXT,
                 observation TEXT,
                 image_path TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Timer settings
last_sent_time = 0
SEND_INTERVAL = 4  # Send an image every 4 seconds

# Streamlit state management
if 'observations' not in st.session_state:
    st.session_state.observations = []
if 'processing' not in st.session_state:
    st.session_state.processing = False

def save_observation(timestamp, observation, image_path):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO observations (timestamp, observation, image_path) VALUES (?, ?, ?)",
              (timestamp, observation, image_path))
    conn.commit()
    conn.close()
    st.session_state.observations.append(f"{timestamp} - {observation}")
    st.rerun()

def get_all_observations():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT timestamp, observation FROM observations ORDER BY timestamp DESC")
    observations = c.fetchall()
    conn.close()
    return observations

def analyze_with_gemini(image_path, timestamp):
    """Sends the full frame to Gemini AI to check for money theft at the cash counter."""
    try:
        with open(image_path, "rb") as img_file:
            base64_image = base64.b64encode(img_file.read()).decode("utf-8")

        message = HumanMessage(
            content=[
                {"type": "text", "text": """
                Observe the **cash counter area** and respond in a structured format.
                If money theft is detected (**"Yes"**), provide details of the **suspect**.
                NO More Details  
                | Suspicious Activity at Cash Counter | Observed? (Yes/No) | Suspect Description (If Yes) |
                |--------------------------------------|--------------------|-----------------------------|
                | Money theft from cash counter?      |                    |                             |

                If theft is detected, describe the **clothing, appearance, and any identifiable features** of the suspect.
                Otherwise, leave the details column empty.
                """},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        )

        response = gemini_model.invoke([message])
        observation = response.content.strip()

        # Only save observations where theft is confirmed
        if "Yes" in observation:
            save_observation(timestamp, observation, image_path)
            print(f"✅ Observation Saved: {observation}")

    except Exception as e:
        print(f"❌ Error analyzing image: {e}")

def process_frame(frame):
    """Saves the full frame and starts a thread for AI analysis every 4 seconds."""
    global last_sent_time

    if frame is None or frame.size == 0:
        print("⚠️ Warning: Empty frame received, skipping...")
        return

    current_time = time.time()
    if current_time - last_sent_time >= SEND_INTERVAL:
        last_sent_time = current_time

        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        image_filename = os.path.join(FRAME_FOLDER, f"frame_{timestamp}.jpg")
        cv2.imwrite(image_filename, frame)

        # Run Gemini AI analysis in a separate thread
        ai_thread = threading.Thread(target=analyze_with_gemini, args=(image_filename, timestamp))
        ai_thread.daemon = True
        ai_thread.start()

def start_monitoring(video_file):
    """Reads video frames and monitors the cash counter area."""
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        st.error("❌ Error: Could not open video file.")
        return

    st_frame = st.empty()
    st.session_state.processing = True

    while cap.isOpened() and st.session_state.processing:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (1020, 500))  # Resize for better display
        process_frame(frame)

        # Convert the frame to RGB for Streamlit
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        st_frame.image(frame_rgb, channels="RGB", use_column_width=True)

        time.sleep(0.03)  # Control the playback speed

    cap.release()
    st.session_state.processing = False
    st.success("✅ Monitoring Completed.")

def main():
    st.title("Cash Counter Monitoring System")
    st.markdown("""
    This application monitors video footage for suspicious activity at cash counters using Gemini AI.
    Upload a video file to begin monitoring.
    """)

    # Sidebar for controls
    with st.sidebar:
        st.header("Controls")
        video_file = st.file_uploader("Upload Video File", type=["mp4", "avi", "mov"])
        
        if st.button("Start Monitoring") and video_file is not None:
            # Save uploaded file to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                tmp_file.write(video_file.read())
                tmp_file_path = tmp_file.name
            
            # Start monitoring in a separate thread
            monitoring_thread = threading.Thread(
                target=start_monitoring, 
                args=(tmp_file_path,)
            )
            monitoring_thread.daemon = True
            monitoring_thread.start()

        if st.button("Stop Monitoring"):
            st.session_state.processing = False

        st.header("Historical Observations")
        observations = get_all_observations()
        if observations:
            for obs in observations:
                timestamp, observation = obs
                with st.expander(f"{timestamp}"):
                    st.warning(observation)
        else:
            st.info("No suspicious activity detected yet.")

    # Display live observations
    st.header("Live Observations")
    if st.session_state.observations:
        for obs in st.session_state.observations:
            st.warning(obs)
    else:
        st.info("No suspicious activity detected in current session.")

if __name__ == "__main__":
    main()