import cv2
import threading
import requests
import urllib3
import time

# Suppress insecure request warnings if SSL verification is disabled
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
API_URL = "https://myhome-7rfa.onrender.com/detect"
# API_URL = "http://127.0.0.1:5000/detect" # Local server for testing
VERIFY_SSL = False  # Set to False as a workaround for SSL certificate errors

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
        frame = cv2.resize(frame, (320, 240))
        success, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
        if success:
            try:
                # Send the frame to the detection API
                # print("Sending frame to API...")
                response = requests.post(API_URL, files={"image": buffer.tobytes()}, verify=VERIFY_SSL)
                # print(response.json())
                
                if response.status_code == 200:
                    data = response.json()
                    count = data.get("person_count", 0)
                    if count > 0:
                        print(f"API returned: {count} person(s) detected")
                else:
                    print(f"Server Error ({response.status_code}): {response.reason}")
            except requests.exceptions.SSLError as ssl_err:
                print(f"SSL Certificate Error: {ssl_err}")
                print("Tip: Run 'pip install --upgrade certifi' or set VERIFY_SSL = False in cam5.py")
            except Exception as e:
                print(f"API Error: {e}")

        # Add a small delay to avoid overwhelming the server
        time.sleep(0.5)

        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

if hasattr(cap, 'stop'):
    cap.stop()
else:
    cap.release()
cv2.destroyAllWindows()