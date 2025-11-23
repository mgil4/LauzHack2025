import os
import cv2
import numpy as np

from datetime import datetime

from agents.door_monitor.graph import graph

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

                # analyze_video_with_qwen(current_video_path)
                graph.invoke({"video_path" : current_video_path})
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
