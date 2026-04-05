import cv2
import threading
import requests

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

# API endpoint for person detection
API_URL = "http://127.0.0.1:5000/detect"

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
        # Encode frame as JPEG
        success, buffer = cv2.imencode('.jpg', frame)
        if success:
            try:
                # Send the frame to the detection API
                response = requests.post(API_URL, files={"image": buffer.tobytes()})
                if response.status_code == 200:
                    data = response.json()
                    count = data.get("person_count", 0)
                    if count > 0:
                        print(f"API returned: {count} person(s) detected")
            except Exception as e:
                print(f"API Error: {e}")

        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

if hasattr(cap, 'stop'):
    cap.stop()
else:
    cap.release()
cv2.destroyAllWindows()