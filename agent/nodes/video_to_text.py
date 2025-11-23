import os
import cv2
import base64

from openai import OpenAI

from agent.state import VLMState


client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key="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",  
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
    print(f"Extracting frames from: {state['video_path']}")
    saved_frames = extract_frames(state['video_path'])

    if not saved_frames:
        print("No frames extracted, skipping analysis.")
        return None

    frame_images = [load_image_as_base64(path) for path in saved_frames]

    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "You are a security assistant analyzing images from a home camera. "
                        "Describe **only the type of entity approaching the camera**: if it is a person, specify the type (e.g., kid, mailman, suspicious person). "
                        "If it is not a person, respond with 'other'. "
                        "Do NOT describe animals, vehicles, objects, the camera, or the property. "
                        "Do NOT give suggestions, opinions, or extra commentary. "
                        "Keep the description concise and suitable for a quick alert."
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

    print("Using Qwen2 VL to analyze the video...")
    try:
        completion = client.chat.completions.create(
            model="Qwen/Qwen2.5-VL-7B-Instruct:hyperbolic",
            messages=messages,
        )
        result = completion.choices[0].message.content
        print("SECURITY FOOTAGE SUMMARY:\n",result,"\n")
        return {"description": result, "video_path": state['video_path']}

    except Exception as e:
        print("[ERROR]", e)
        return None