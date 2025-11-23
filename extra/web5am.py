import os
import cv2
import threading
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, Response, JSONResponse
import asyncio

from agents.door_monitor.state import VLMState
from agents.door_monitor.nodes.video_to_text import analyze_video
from agents.door_monitor.edges.handle_video_description import classify_video
from agents.door_monitor.nodes.send_notification import send_telegram_notification

BASE_DIR = Path(__file__).parent
RECORDINGS_DIR = BASE_DIR / "recordings"
MESSAGES_DIR = BASE_DIR / "messages"
RECORDINGS_DIR.mkdir(exist_ok=True)
MESSAGES_DIR.mkdir(exist_ok=True)

app = FastAPI()

# --- HTML Frontend ---
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>Home Security Camera</title>
</head>
<body style="text-align:center;">
<h2>Live Camera Feed + Manual Recording</h2>
<img id="videoFeed" width="640" height="480" style="border:1px solid #333;" />
<br><br>
<button id="manualBtn">Start Message Recording</button>
<span id="status" style="margin-left:12px;"></span>

<script>
let manualRecorder;
let manualRecording = false;
let stream;

async function startCamera() {
    stream = await navigator.mediaDevices.getUserMedia({video:true, audio:true});
}

manualBtn.onclick = async () => {
    if(!manualRecording) {
        manualRecorder = new MediaRecorder(stream, {mimeType:'video/webm;codecs=vp8,opus'});
        const chunks = [];
        manualRecorder.ondataavailable = e => {if(e.data.size>0) chunks.push(e.data);};
        manualRecorder.onstop = async () => {
            const blob = new Blob(chunks,{type:'video/webm'});
            const fd = new FormData();
            fd.append('file', blob, 'message.webm');
            await fetch('/upload_message',{method:'POST',body:fd});
            document.getElementById('status').innerText='Message saved!';
        };
        manualRecorder.start();
        manualRecording = true;
        manualBtn.innerText='Stop Message Recording';
        document.getElementById('status').innerText='Recording message...';
    } else {
        manualRecorder.stop();
        manualRecording = false;
        manualBtn.innerText='Start Message Recording';
    }
};

async function loadVideoFeed() {
    const img = document.getElementById('videoFeed');
    setInterval(()=>{img.src='/video_feed?'+new Date().getTime();},100);
}

startCamera();
loadVideoFeed();
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML

# --- Video streaming ---
latest_frame = None
frame_lock = threading.Lock()

def camera_thread():
    global latest_frame
    cap = cv2.VideoCapture(0)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
    fps    = int(cap.get(cv2.CAP_PROP_FPS) or 20)

    last_mean = 0
    recording = False
    frame_rec_count = 0
    max_frames_per_clip = fps*8  # 8s por movimiento
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    out = None
    current_video_path = None

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        with frame_lock:
            latest_frame = frame.copy()

        # Detección de movimiento
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        current_mean = gray.mean()
        diff = abs(current_mean - last_mean)
        last_mean = current_mean

        if not recording and diff>2.0:  # umbral de movimiento
            recording = True
            frame_rec_count = 0
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_video_path = RECORDINGS_DIR / f"rec_{timestamp}.avi"
            out = cv2.VideoWriter(str(current_video_path), fourcc, fps, (width,height))
            print(f"[INFO] Motion detected. Recording to {current_video_path}")

        if recording:
            out.write(frame)
            frame_rec_count += 1
            if frame_rec_count >= max_frames_per_clip:
                recording = False
                out.release()
                out = None
                print(f"[INFO] Motion recording finished: {current_video_path}")
                # Lanzar análisis en segundo plano
                asyncio.run(process_uploaded_video(current_video_path))

def gen_frame_bytes():
    global latest_frame
    while True:
        with frame_lock:
            if latest_frame is None:
                continue
            ret, buffer = cv2.imencode('.jpg', latest_frame)
            frame = buffer.tobytes()
        yield frame

@app.get("/video_feed")
def video_feed():
    frame = gen_frame_bytes().__next__()
    return Response(frame, media_type="image/jpeg")

# --- Helpers para guardar y analizar ---
def save_upload(upload: UploadFile, dest_dir: Path, prefix="clip") -> Path:
    ext = Path(upload.filename).suffix or ".webm"
    fname = f"{prefix}_{uuid.uuid4().hex}{ext}"
    path = dest_dir / fname
    with path.open("wb") as f:
        f.write(upload.file.read())
    return path

async def process_uploaded_video(video_path: Path):
    try:
        state: VLMState = {"video_path": str(video_path), "description": ""}
        analyzed = await asyncio.to_thread(analyze_video, state)
        if not analyzed: return
        next_step = await asyncio.to_thread(classify_video, analyzed)
        if next_step != 'END':
            await asyncio.to_thread(send_telegram_notification, analyzed)
    except Exception as e:
        print("[ERROR] processing uploaded video:", e)

# --- Endpoints para manual recording ---
@app.post("/upload_message")
async def upload_message(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    saved_path = save_upload(file, MESSAGES_DIR, prefix="message")
    if background_tasks:
        background_tasks.add_task(asyncio.run, process_uploaded_video(saved_path))
    return JSONResponse({"status":"saved_message","path":str(saved_path)})

@app.get("/health")
async def health():
    return {"status":"ok"}

# --- Main ---
if __name__ == "__main__":
    threading.Thread(target=camera_thread, daemon=True).start()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
