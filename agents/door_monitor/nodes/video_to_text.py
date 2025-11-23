import os
import cv2
import base64

from openai import OpenAI
from dotenv import load_dotenv
import os



from agents.door_monitor.state import VLMState

load_dotenv() 

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.getenv("HF_TOKEN"),  
)

# Base64 encode an image
def load_image_as_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
    

# Extract frames from the recorded video
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
    

# CHECK THE RETURN: IT MUST BE A STATE
def analyze_video(state: VLMState):
    # print(f"Extracting frames from: {state['video_path']}")
    saved_frames = extract_frames(state['video_path'])

    if not saved_frames:
        print("No frames extracted, skipping analysis.")
        return None

    frame_images = [load_image_as_base64(path) for path in saved_frames]
    # IS A PERSON APPROACHING THE DOOR/CLOSE TO THE CAMERA
    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "You are a security assistant analyzing home camera footage.\n\n"
                        "Classify what is approaching the camera into EXACTLY one of the following categories:\n"
                        "• person — if a person is approaching the door or very close to the camera\n"
                        "• other — animals, objects, vehicles, nothing in sight, or anything that is NOT a person\n\n"
                        "STRICT RULES:\n"
                        "• Output only ONE category, all lowercase.\n"
                        "• No explanations. No descriptions.\n"
                        "• If multiple frames disagree, choose 'person' if any frame contains a person, otherwise 'other'."
                    )
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpg;base64,{img}"}
                }
                for img in frame_images
            ]
        }
    ]

    print("[INFO] Using Qwen2 VL to analyze the video...")
    try:
        completion = client.chat.completions.create(
            model="Qwen/Qwen2.5-VL-7B-Instruct:hyperbolic",
            messages=messages,
        )
        result = completion.choices[0].message.content
        
        if result == 'person':
            person = True
        else:
            person = False
        return {"description": result, "video_path": state['video_path'], "person": person}

    except Exception as e:
        print("[ERROR]", e)
        return None