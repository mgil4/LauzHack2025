import cv2
import numpy as np
import os

RECORDINGS_DIR = "recordings"
os.makedirs(RECORDINGS_DIR, exist_ok=True)

cap = cv2.VideoCapture(0)

width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps    = int(cap.get(cv2.CAP_PROP_FPS)) or 20

print("Camera resolution:", width, height, "fps:", fps)

last_mean = 0
recording = False
frame_rec_count = 0
fourcc = cv2.VideoWriter_fourcc(*'MJPG')
out = None

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    current_mean = np.mean(gray)
    result = abs(current_mean - last_mean)
    last_mean = current_mean

    if not recording and result > 0.3:
        print("Motion detected! Starting new recording...")

        recording = True
        frame_rec_count = 0

        filename = os.path.join(
            RECORDINGS_DIR,
            f"rec_{int(cv2.getTickCount())}.avi"
        )

        out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
        print(f"Saving to: {filename}")

    if recording:
        out.write(frame)
        frame_rec_count += 1

        if frame_rec_count >= 240:
            print("Recording finished.")
            recording = False
            out.release()
            out = None

    cv2.imshow("frame", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
if out:
    out.release()
cv2.destroyAllWindows()


