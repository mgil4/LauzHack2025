import cv2
import numpy as np
from insightface.app import FaceAnalysis
from pathlib import Path

from agents.door_monitor.state import VLMState
from agents.door_monitor.nodes.video_to_text import extract_frames, load_image_as_base64

# Initialize model
app = FaceAnalysis(name="buffalo_l")
app.prepare(ctx_id=0, det_size=(640, 640))

family_dir = Path("family")

def get_embedding(img_path):
    img = cv2.imread(img_path)
    faces = app.get(img)
    if len(faces) == 0:
        raise Exception("No face found")
    return faces[0].embedding

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def detect_family_members(state: VLMState):
    print(f"Extracting frames from: {state['video_path']}")
    saved_frames = extract_frames(state['video_path'])

    if not saved_frames:
        print("No frames extracted, skipping analysis.")
        return None
    
    image_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]
    family_frames = sorted([p for p in family_dir.iterdir() if p.suffix.lower() in image_extensions])

    family_images_embeddings = [get_embedding(str(image_path)) for image_path in family_frames]
    frame_images_embeddings = [get_embedding(str(image_path)) for image_path in saved_frames]

    for family_member in family_images_embeddings:
        total_sim = 0
        for frame in frame_images_embeddings:
            total_sim += cosine_similarity(family_member, frame)

        if total_sim/(len(frame_images_embeddings)) > 0.5:
            return {"description": state["description"], "video_path": state['video_path'], "person": state["person"], "family": True}

    return {"description": state["description"], "video_path": state['video_path'], "person": state["person"], "family": False}