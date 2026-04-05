from ultralytics import YOLO
import cv2
import threading


class RTSPStreamReader:
    def __init__(self, rtsp_url):
        self.cap = cv2.VideoCapture(rtsp_url)
        self.ret = False
        self.frame = None
        self.stopped = False
        # Start the background thread
        threading.Thread(target=self.update, daemon=True).start()

    def update(self):
        while not self.stopped:
            if self.cap.isOpened():
                (self.ret, self.frame) = self.cap.read()
            if not self.ret:
                self.stopped = True

    def get_frame(self):
        return self.frame

    def stop(self):
        self.stopped = True
        self.cap.release()

# Load a YOLO26n PyTorch model
model = YOLO("yolo26n.pt")

# Export the model to NCNN format
model.export(format="ncnn")  # creates 'yolo26n_ncnn_model'

# Load the exported NCNN model
ncnn_model = YOLO("yolo26n_ncnn_model")

# Open the webcam (0 = default camera)
# cap = cv2.VideoCapture('rtsp://admin:24%40Sherlock36@192.168.31.101:554/cam/realmonitor?channel=2&subtype=1')
cap = cv2.VideoCapture(0)

# RTSP_URL = "rtsp://admin:24%40Sherlock36@192.168.31.101:554/cam/realmonitor?channel=2&subtype=1"
# cap = RTSPStreamReader(RTSP_URL)


while True:
    if hasattr(cap, 'get_frame'):
        frame = cap.get_frame()
    else:
        ret, frame = cap.read()
        if not ret:
            break

    if frame is not None:
        # Run YOLOv8 inference on the frame
        results = ncnn_model.predict(frame, imgsz=640, conf=0.3, verbose=False)

        # Visualize results
        for r in results:
            annotated_frame = r.plot()
            # cv2.imshow("YOLOv8 Nano - Webcam", annotated_frame)
            count = 0
            for box in r.boxes:
                c = int(box.cls[0])
                # print(f"Detected: {model.names[c]} @ {float(box.conf[0]):.2f}")
                # print(f"Detected: {model.names[c]} @ {float(box.conf[0]):.2f}")
                if model.names[c] =="person":
                    count=count+1

            if count:
                print(f"{count} person detected")


        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

if hasattr(cap, 'stop'):
    cap.stop()
else:
    cap.release()
cv2.destroyAllWindows()