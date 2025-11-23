import cv2
import time
import os
import base64
import threading
import numpy as np

from openai import OpenAI
from datetime import datetime
from flask import Flask, render_template, Response, request, jsonify

#  QWEN2 VL CLIENT SETUP
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key="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",
)

RECORDINGS_DIR = "recordings"
os.makedirs(RECORDINGS_DIR, exist_ok=True)

# Shared variable for latest frame
latest_frame = None
frame_lock = threading.Lock()

# Manual recording state
manual_recording = False
manual_out = None
manual_video_path = None
manual_lock = threading.Lock()

MESSAGES_DIR = "messages"
os.makedirs(MESSAGES_DIR, exist_ok=True)


#  CAMERA + MOTION DETECTION + RECORDING
def camera_thread():
    global latest_frame
    cap = cv2.VideoCapture(0)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    fps    = int(cap.get(cv2.CAP_PROP_FPS)) or 20

    last_mean = 0
    recording = False
    frame_rec_count = 0
    max_frames_per_clip = 240
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    out = None
    current_video_path = None

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # Update latest frame for web streaming
        with frame_lock:
            latest_frame = frame.copy()
        
        # Handle manual recording
        with manual_lock:
            if manual_recording and manual_out is not None:
                manual_out.write(frame)

        # Simple motion detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        current_mean = np.mean(gray)
        difference = abs(current_mean - last_mean)
        last_mean = current_mean

        if not recording and difference > 0.3:
            recording = True
            frame_rec_count = 0
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_video_path = os.path.join(RECORDINGS_DIR, f"rec_{timestamp}.avi")
            out = cv2.VideoWriter(current_video_path, fourcc, fps, (width, height))
            print(f"Motion detected. Saving recording to {current_video_path}")

        if recording:
            out.write(frame)
            frame_rec_count += 1
            if frame_rec_count >= max_frames_per_clip:
                print(f"Recording stopped.")
                recording = False
                out.release()
                out = None
                # Call Qwen2 analysis (reuse your function)
                analyze_video_with_qwen(current_video_path)

# Qwen2 Analysis Function
def extract_frames(video_path, output_dir="frames", max_frames=4, padding_ratio=0.05):
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if frame_count == 0:
        cap.release()
        return []
    pad = int(frame_count * padding_ratio)
    start = pad
    end = max(frame_count - pad, start + 1)
    num_frames = min(max_frames, max(1, end - start))
    indices = [int(start + i * (end - start - 1) / (num_frames - 1)) for i in range(num_frames)]
    saved = []
    for i, frame_no in enumerate(indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        ret, frame = cap.read()
        if not ret:
            continue
        out_name = os.path.join(output_dir, f"frame_{i+1:04d}.jpg")
        cv2.imwrite(out_name, frame)
        saved.append(out_name)
    cap.release()
    return saved

def load_image_as_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def analyze_video_with_qwen(video_path):
    saved_frames = extract_frames(video_path)
    if not saved_frames:
        return
    frame_images = [load_image_as_base64(p) for p in saved_frames]
    messages = [{"role": "user",
                "content": [
                    {"type": "text",
                     "text": "You are a security assistant analyzing images from a home camera. Describe only what is relevant to the property owner: people, animals, vehicles, or objects interacting with the property, and any unusual or noteworthy activity. Do NOT describe the camera, the property itself, or give suggestions or opinions. Keep your description concise, clear, and suitable for a quick alert. Consider all images together as frames from the same event, and interpret the activity based on the event as a whole."}
                ] + [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpg;base64,{img}"}} 
                    for img in frame_images
                ]}]
    try:
        completion = client.chat.completions.create(
            model="Qwen/Qwen2.5-VL-7B-Instruct:hyperbolic",
            messages=messages
        )
        result = completion.choices[0].message.content
        print("SECURITY FOOTAGE SUMMARY:\n",result,"\n")
    except Exception as e:
        print("[ERROR]:", e)

# Flask Web Server
from flask import Flask, Response, render_template_string

app = Flask(__name__)

# Live video feed endpoint
def gen_frames():
    global latest_frame
    while True:
        with frame_lock:
            if latest_frame is None:
                continue
            ret, buffer = cv2.imencode('.jpg', latest_frame)
            frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template_string("""
    <html>
    <head>
        <title>HOME SECURITY CAMERA</title>
    </head>
    <body style="text-align:center;">
        <h1>Live Camera Footage</h1>
        <img src="{{ url_for('video_feed') }}" width="540" height="380"><br><br>
        <button id="recordButton" onclick="toggleRecording()">Start Recording</button>
        <script>
            let recording = false;
            function toggleRecording() {
                fetch('/toggle_manual_record', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    recording = !recording;
                    document.getElementById('recordButton').innerText = recording ? 'Stop Recording' : 'Start Recording';                });
            }
        </script>
    </body>
    </html>
    """)


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/toggle_manual_record', methods=['POST'])
def toggle_manual_record():
    global manual_recording, manual_out, manual_video_path
    with manual_lock:
        if not manual_recording:
            # Start manual recording
            manual_recording = True
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            manual_video_path = os.path.join(MESSAGES_DIR, f"message_{timestamp}.avi")
            width  = 640
            height = 480
            fps    = 20
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            manual_out = cv2.VideoWriter(manual_video_path, fourcc, fps, (width, height))
            print(f"Message recording started and saved at {manual_video_path}")
            return jsonify({"status": "recording", "path": manual_video_path})
        else:
            # Stop manual recording
            manual_recording = False
            if manual_out:
                manual_out.release()
                manual_out = None
                print(f"Message recording stopped: {manual_video_path}")
            return jsonify({"status": "stopped", "path": manual_video_path})

# Main
if __name__ == '__main__':
    threading.Thread(target=camera_thread, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False)
