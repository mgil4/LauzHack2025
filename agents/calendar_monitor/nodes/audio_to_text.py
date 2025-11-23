import subprocess
import base64
import tempfile
import os
import requests
import base64
from dotenv import load_dotenv
import os

from agents.calendar_monitor.state import LLMState

load_dotenv()

def video_to_audio_base64(video_path, audio_format="flac"):
    """
    Convert a video file to base64-encoded audio.
    
    Args:
        video_path (str): Path to the video file.
        audio_format (str): Audio format to extract (e.g., "flac", "wav", "mp3").
        
    Returns:
        str: Base64-encoded audio string.
    """
    # Create a temporary file to store audio
    with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as tmp_audio:
        audio_path = tmp_audio.name

    try:
        # Use ffmpeg to extract audio
        subprocess.run([
            "ffmpeg",
            "-y",  # overwrite if exists
            "-i", video_path,
            "-vn",  # no video
            "-acodec", "flac",  # you can change to pcm_s16le for wav
            audio_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Read audio file as bytes
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        # Convert to Base64
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        return audio_b64
    finally:
        # Clean up temporary audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)

def query(payload):
	headers = {
		"Accept" : "application/json",
		"Authorization": f"Bearer {os.getenv("HF_TOKEN")}",
		"Content-Type": "application/json"
	}
	response = requests.post(
		"https://i4d7elpjedi309k3.us-east-1.aws.endpoints.huggingface.cloud",
		headers=headers,
		json=payload
	)
	return response.json()


def transcript_audio_to_text(state: LLMState):
    audio_base64 = video_to_audio_base64(state["video_path"])
    output = query({
        "inputs": audio_base64,
        "parameters": {}
    }) 

    return {"video_path": state["video_path"], "transcript": output}

