# Codi que funciona per 4 imatges que extreu com a frames espaiats del video:
from openai import OpenAI 
import base64 
import cv2
import os

client = OpenAI( base_url="https://router.huggingface.co/v1", api_key="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", ) 

def load_image_as_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def extract_frames(video_path, output_dir="frames", max_frames=4, padding_ratio=0.05):
    """
    Extract up to max_frames frames evenly spaced through the video,
    avoiding using the very first and very last frames by adding padding.
    Saves frames as videoframe_0001.jpg, ..., videoframe_0004.jpg.
    """
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if frame_count == 0:
        cap.release()
        return []

    # Apply padding to avoid the first and last frames
    pad = int(frame_count * padding_ratio)
    start = pad
    end = max(frame_count - pad, start + 1)   # ensure valid range

    # Limit number of frames (max 4)
    num_frames = min(max_frames, max(1, end - start))

    # Compute evenly spaced frame indices inside the padded region
    if num_frames == 1:
        indices = [start]
    else:
        indices = [
            int(start + i * (end - start - 1) / (num_frames - 1))
            for i in range(num_frames)]

    saved = []
    for i, frame_no in enumerate(indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        ret, frame = cap.read()
        if not ret:
            continue
        out_name = os.path.join(output_dir, f"videoframe_{i+1:04d}.jpg")
        cv2.imwrite(out_name, frame)
        saved.append(out_name)

    cap.release()
    return saved

video_path = r"video\\man_approaching.mp4"
saved_frames = extract_frames(video_path)
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

completion = client.chat.completions.create(
    model="Qwen/Qwen2.5-VL-7B-Instruct:hyperbolic",
    messages=messages,)

print(completion.choices[0].message.content)