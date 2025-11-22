import os
import cv2
import base64
import numpy as np

from datetime import datetime
from openai import OpenAI

#  QWEN2 VL CLIENT SETUP
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key="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",  
)

#  HELPER: Base64 encode an image
def load_image_as_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

#  EXTRACT FRAMES FROM RECORDED VIDEO
def extract_frames(video_path, output_dir="frames", max_frames=4, padding_ratio=0.05):
    """
    Extract up to max_frames evenly spaced frames from a video,
    avoiding the very first and very last frames using padding.
    Returns list of saved frame paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video for frame extraction: {video_path}")
        return []
    
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if frame_count == 0:
        cap.release()
        return []

    pad = int(frame_count * padding_ratio)
    start = pad
    end = max(frame_count - pad, start + 1)

    num_frames = min(max_frames, max(1, end - start))

    # Compute evenly spaced frame indices
    if num_frames == 1:
        indices = [start]
    else:
        indices = [
            int(start + i * (end - start - 1) / (num_frames - 1))
            for i in range(num_frames)
        ]

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

#  SEND FRAMES TO QWEN2 VL FOR ANALYSIS
def analyze_video_with_qwen(video_path):
    print(f"Extracting frames from: {video_path}")

    saved_frames = extract_frames(video_path)
    if not saved_frames:
        print("No frames extracted, skipping analysis.")
        return None

    frame_images = [load_image_as_base64(path) for path in saved_frames]

    messages = [{"role": "user",
                "content": [
                    {
                        "type": "text",
                        "text":"You are a security assistant analyzing images from a home camera. Describe only what is relevant to the property owner: people, animals, vehicles, or objects interacting with the property, and any unusual or noteworthy activity. Do NOT describe the camera, the property itself, or give suggestions or opinions. Keep your description concise, clear, and suitable for a quick alert. Consider all images together as frames from the same event, and interpret the activity based on the event as a whole."
                    }
                ] + [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpg;base64,{img}"}} 
                    for img in frame_images
                ]}]

    print("Using Qwen2 VL to analyze the video...")
    try:
        completion = client.chat.completions.create(
            model="Qwen/Qwen2.5-VL-7B-Instruct:hyperbolic",
            messages=messages,
        )
        result = completion.choices[0].message.content
        print("SECURITY FOOTAGE SUMMARY:\n",result,"\n")
        return result

    except Exception as e:
        print("[ERROR]", e)
        return None

#  CAMERA + MOTION DETECTION + RECORDING
def run_camera_monitor():
    RECORDINGS_DIR = "recordings"
    os.makedirs(RECORDINGS_DIR, exist_ok=True)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Cannot open webcam.")

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    fps    = int(cap.get(cv2.CAP_PROP_FPS)) or 20

    print("Camera initialized:", width, height, "fps:", fps)

    last_mean = 0
    recording = False
    frame_rec_count = 0
    max_frames_per_clip = 240  # ~12 seconds at 20 fps

    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    out = None
    current_video_path = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Simple motion detection by mean brightness change
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        current_mean = np.mean(gray)
        difference = abs(current_mean - last_mean)
        last_mean = current_mean

        # Trigger recording
        if not recording and difference > 0.3:
            print("Motion detected! Starting new recording...")

            recording = True
            frame_rec_count = 0

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_video_path = os.path.join(RECORDINGS_DIR, f"rec_{timestamp}.avi")

            out = cv2.VideoWriter(current_video_path, fourcc, fps, (width, height))
            print(f"Saving to: {current_video_path}")

        # Write frames if recording 
        if recording:
            out.write(frame)
            frame_rec_count += 1

            # Stop recording after max frames
            if frame_rec_count >= max_frames_per_clip:
                print("Recording stopped.")
                recording = False
                out.release()
                out = None

                # Call Qwen2 analysis here
                analyze_video_with_qwen(current_video_path)

        # Show preview
        cv2.imshow("Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    if out:
        out.release()
    cv2.destroyAllWindows()

#  MAIN ENTRY POINT
if __name__ == "__main__":
    run_camera_monitor()
