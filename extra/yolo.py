from ultralytics import YOLO

# Load YOLOv8 nano model
model = YOLO("yolov8n.pt")  # yolov8n = nano model, small and fast

# Run detection on an image
results = model("https://ultralytics.com/images/bus.jpg", show=True)