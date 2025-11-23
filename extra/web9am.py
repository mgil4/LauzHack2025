# app.py
import os
import cv2
import threading
import time
from flask import Flask, Response, render_template_string, request
from agents.door_monitor.nodes.video_to_text import analyze_video
from agents.door_monitor.nodes.send_notification import send_telegram_notification
from agents.door_monitor.state import VLMState

# ---------------- CONFIG ---------------- #
VIDEO_DIR = "recordings"
MANUAL_DIR = "messages"
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(MANUAL_DIR, exist_ok=True)

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
RECORD_SECONDS = 5  # length of auto-recorded clip
FPS = 20

# Simple HTML template for the webpage
HTML_PAGE = """
<html>
<head>
<title>Door Monitor</title>
</head>
<body>
<h1>Door Monitor Live Feed</h1>
<img src="{{ url_for('video_feed') }}" width="640" height="480"/>
<form action="/toggle_manual" method="POST">
<button type="submit">{{ 'Stop Recording' if recording else 'Start Manual Recording' }}</button>
</form>
</body>
</html>
"""

# ---------------- GLOBALS ---------------- #
app = Flask(__name__)
camera = cv2.VideoCapture(0)
output_frame = None
lock = threading.Lock()
motion_detected = False
manual_recording = False

# ---------------- MOTION DETECTION ---------------- #
def detect_motion(frame, threshold=5000):
    """Simple frame differencing motion detection"""
    if not hasattr(detect_motion, "last_frame"):
        detect_motion.last_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return False
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(detect_motion.last_frame, gray)
    detect_motion.last_frame = gray
    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    count = cv2.countNonZero(thresh)
    return count > threshold

# ---------------- RECORDING FUNCTION ---------------- #
def record_clip(filename, duration=RECORD_SECONDS):
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out = cv2.VideoWriter(filename, fourcc, FPS, (FRAME_WIDTH, FRAME_HEIGHT))
    start_time = time.time()
    while time.time() - start_time < duration:
        ret, frame = camera.read()
        if not ret:
            break
        out.write(frame)
        time.sleep(1 / FPS)
    out.release()
    print(f"[INFO] Saved recording: {filename}")
    return filename

# ---------------- BACKGROUND THREAD ---------------- #
def camera_loop():
    global output_frame, motion_detected, manual_recording
    while True:
        ret, frame = camera.read()
        if not ret:
            continue
        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

        # Motion detection for auto-recording
        if detect_motion(frame):
            if not motion_detected:
                motion_detected = True
                video_path = os.path.join(VIDEO_DIR, f"recording_{int(time.time())}.avi")
                print("[INFO] Motion detected! Recording video...")
                record_clip(video_path)
                
                # Analyze the video and send Telegram if needed
                state: VLMState = {"video_path": video_path, "description": ""}
                analyzed_state = analyze_video(state)
                if analyzed_state:
                    if analyzed_state["description"] != "other":
                        send_telegram_notification(analyzed_state)
                motion_detected = False

        # Manual recording
        if manual_recording:
            video_path = os.path.join(MANUAL_DIR, f"manual_{int(time.time())}.avi")
            print("[INFO] Manual recording started...")
            record_clip(video_path)
            manual_recording = False

        # Update output frame for MJPEG streaming
        with lock:
            output_frame = frame.copy()

# ---------------- FLASK ROUTES ---------------- #
@app.route("/")
def index():
    return render_template_string(HTML_PAGE, recording=manual_recording)

def generate_mjpeg():
    global output_frame
    while True:
        with lock:
            if output_frame is None:
                continue
            ret, jpeg = cv2.imencode(".jpg", output_frame)
            if not ret:
                continue
        frame = jpeg.tobytes()
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n\r\n")

@app.route("/video_feed")
def video_feed():
    return Response(generate_mjpeg(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/toggle_manual", methods=["POST"])
def toggle_manual():
    global manual_recording
    manual_recording = not manual_recording
    return render_template_string(HTML_PAGE, recording=manual_recording)

# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    # Start background thread
    t = threading.Thread(target=camera_loop, daemon=True)
    t.start()
    app.run(host="localhost", port=5000, debug=False)
