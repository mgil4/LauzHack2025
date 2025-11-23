# web_camera_pipeline.py
import os
import uuid
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse

# Import your existing project modules
from agents.door_monitor.state import VLMState
from agents.door_monitor.nodes.video_to_text import analyze_video
from agents.door_monitor.edges.handle_video_description import classify_video
from agents.door_monitor.nodes.send_notification import send_telegram_notification

# Directory to store recordings
UPLOAD_DIR = "recordings"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()

# Simple HTML page with camera + manual recording
HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>Camera + Microphone</title>
</head>
<body>
    <h2>Camera + Microphone Live</h2>
    <video id="camera" autoplay muted style="width: 640px; height: 480px; border: 1px solid black;"></video>
    <br>
    <button id="start">Start Recording</button>
    <button id="stop" disabled>Stop Recording</button>

    <script>
        const video = document.getElementById('camera');
        const startBtn = document.getElementById('start');
        const stopBtn = document.getElementById('stop');

        let mediaRecorder;
        let recordedChunks = [];

        startBtn.onclick = async () => {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            video.srcObject = stream;

            recordedChunks = [];
            mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) recordedChunks.push(e.data);
            };

            mediaRecorder.onstop = async () => {
                const blob = new Blob(recordedChunks, { type: 'video/webm' });
                const formData = new FormData();
                formData.append('file', blob, 'recording.webm');

                await fetch('/upload', { method: 'POST', body: formData });
            };

            mediaRecorder.start(1000); // chunk every 1 second
            startBtn.disabled = true;
            stopBtn.disabled = false;
        };

        stopBtn.onclick = () => {
            mediaRecorder.stop();
            startBtn.disabled = false;
            stopBtn.disabled = true;
        };
    </script>
</body>
</html>
"""

@app.get("/")
async def index():
    return HTMLResponse(HTML_CONTENT)


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    # Save the uploaded video
    unique_name = f"{uuid.uuid4()}.webm"
    save_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(save_path, "wb") as f:
        f.write(await file.read())
    print(f"[INFO] Saved recording: {save_path}")

    # Create initial state for AI analysis
    state: VLMState = {"video_path": save_path, "description": ""}

    # Call your existing pipeline: frame extraction + AI analysis
    analyzed_state = analyze_video(state)
    if analyzed_state:
        # Check if notification is needed
        next_step = classify_video(analyzed_state)
        if next_step != "END":
            send_telegram_notification(analyzed_state)

    return {"status": "success", "file_path": save_path, "analysis": analyzed_state}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
# http://localhost:8000/