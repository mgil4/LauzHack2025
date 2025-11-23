# QUAN EXECUTES GRAVA VIDEOS QUAN DETECTA MOVIMENT I ENVIA NOTIFICACIONS, TAMBÉ PERMET GRAVAR MISSATGES D'ÀUDIO MANUALMENT
import os
import cv2
import threading
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
from flask import Flask, Response, render_template_string

from agents.door_monitor.graph import door_graph
from agents.calendar_monitor.graph import calendar_graph
# ---------------- CONFIG ---------------- #
VIDEO_DIR = "recordings"
MANUAL_DIR = "messages"
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(MANUAL_DIR, exist_ok=True)

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 20
AUDIO_RATE = 44100  # Sample rate for audio

# HTML template
HTML_PAGE = """
<html>
<head>
<title>SNEAK PEEK</title>
<style>
    body {
        background-image: url('background.jpg'); /* or use static too */
        background-size: cover;
        background-position: center;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 100vh;
        margin: 0;
        font-family: Arial, sans-serif;
        color: white;
        text-align: center;
        overflow: hidden;
    }
    img.logo {
        width: 100px;
        height: auto;
        margin-bottom: 10px;
    }
    h1 {
        margin: 10px 0;
        text-shadow: none;
        font-size: 24px;
    }
    img.video-feed {
        border: 3px solid white;
        width: 480px;
        height: 360px;
        margin-bottom: 20px;
    }
    button {
        padding: 10px 20px;
        font-size: 16px;
        cursor: pointer;
        background-color: black;
        border: none;
        color: white;
        border-radius: 5px;
    }
    button:hover {
        background-color: #333;
    }
    p {
        margin-top: 10px;
        font-weight: bold;
    }
</style>
</head>
<body>
<img src="{{ url_for('static', filename='image.jpeg') }}" class="logo"/> <!-- Correct reference -->
<h1 style="color: black;">SNEAK PEEK Live footage</h1>
<img src="{{ url_for('video_feed') }}" class="video-feed"/>
<form action="/toggle_manual" method="POST">
<button type="submit">{{ 'Stop Recording Message' if recording else 'Start Recording Message' }}</button>
</form>
{% if recording %}
<p>Recording...</p>
{% endif %}
</body>
</html>
"""

# ---------------- GLOBALS ---------------- #
app = Flask(__name__)
camera = cv2.VideoCapture(0)
output_frame = None
lock = threading.Lock()
motion_detected = False

# Manual audio recording
manual_recording = False
manual_thread = None
manual_stop_flag = False

# ---------------- MOTION DETECTION ---------------- #
def detect_motion(frame, threshold=5000):
    if not hasattr(detect_motion, "last_frame"):
        detect_motion.last_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return False
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(detect_motion.last_frame, gray)
    detect_motion.last_frame = gray
    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    count = cv2.countNonZero(thresh)
    return count > threshold

# ---------------- BACKGROUND CAMERA LOOP ---------------- #
def camera_loop():
    global output_frame, motion_detected
    while True:
        ret, frame = camera.read()
        if not ret:
            continue
        frame_resized = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        with lock:
            output_frame = frame_resized.copy()
        # Motion detection for automatic video recording
        if detect_motion(frame_resized) and not motion_detected:
            motion_detected = True
            video_path = os.path.join(VIDEO_DIR, f"recording_{int(time.time())}.avi")
            print("[INFO] Motion detected! Recording video...")
            threading.Thread(target=record_and_analyze_video, args=(video_path,), daemon=True).start()

# ---------------- VIDEO RECORD + ANALYZE ---------------- #
def record_clip(filename, duration=5):
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out = cv2.VideoWriter(filename, fourcc, FPS, (FRAME_WIDTH, FRAME_HEIGHT))
    start_time = time.time()
    while time.time() - start_time < duration:
        ret, frame = camera.read()
        if not ret:
            continue
        frame_resized = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        out.write(frame_resized)
    out.release()
    print(f"[INFO] Saved recording: {filename}")
    return filename

def record_and_analyze_video(video_path):
    record_clip(video_path, duration=5)
    
    door_graph.invoke({"video_path": video_path})

    global motion_detected
    motion_detected = False

# ---------------- AUDIO RECORDING ---------------- #
def manual_audio_record_loop(stop_flag):
    filename = os.path.join(MANUAL_DIR, f"manual_{int(time.time())}.wav")
    print("[INFO] Manual audio recording started...")
    frames = []

    def callback(indata, frames_count, time_info, status):
        if stop_flag():
            raise sd.CallbackStop()
        frames.append(indata.copy())

    with sd.InputStream(channels=1, samplerate=AUDIO_RATE, callback=callback):
        while not stop_flag():
            sd.sleep(100)

    if frames:
        audio_data = np.concatenate(frames, axis=0)
        sf.write(filename, audio_data, AUDIO_RATE)
        print(f"[INFO] Manual audio saved: {filename}")

    calendar_graph.invoke({"video_path": filename})

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
            ret, jpeg = cv2.imencode(".jpeg", output_frame)
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
    global manual_recording, manual_thread, manual_stop_flag
    if not manual_recording:
        # Start audio recording
        manual_stop_flag = False
        manual_thread = threading.Thread(
            target=manual_audio_record_loop,
            args=(lambda: manual_stop_flag,),
            daemon=True
        )
        manual_thread.start()
        manual_recording = True
    else:
        # Stop audio recording
        manual_stop_flag = True
        manual_recording = False
    return render_template_string(HTML_PAGE, recording=manual_recording)

# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    t = threading.Thread(target=camera_loop, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5001, debug=False)
