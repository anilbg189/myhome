from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
from ultralytics import YOLO
from imagekitio import ImageKit
from datetime import datetime, timedelta
import time
import firebase_admin
from firebase_admin import credentials, messaging
import json
import os

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# Load models once when the server starts
print("Loading YOLO models...")

# model = YOLO("yolo8n.pt")
model = None

def get_model():
    global model
    if model is None:
        model = YOLO("yolo11n.pt")
    return model


# model = YOLO("yyolov8n.pt")
print("Models loaded successfully.")

# ImageKit Configuration (Replace with your actual keys)
# If you face SSL certificate issues, you can use verify=False in httpx Client (not recommended for production)
import httpx
# SSL Verification is disabled (verify=False) as a workaround for local certificate issues.
# In a production environment, you should fix the local CA certificates instead.
http_client = httpx.Client(verify=False) 

imagekit = ImageKit(
    private_key='private_0zYmQbpW4ROzIe7uV+cKIhluOl4=',
    http_client=http_client
)

# Cooldown logic
last_upload_time = None
UPLOAD_COOLDOWN = timedelta(minutes=2)
frame_count = 0
detection_enabled = True
TOKENS_FILE = "tokens.json"

def load_tokens():
    if os.path.exists(TOKENS_FILE):
        try:
            with open(TOKENS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading tokens: {e}")
    return []

def save_tokens(tokens):
    try:
        with open(TOKENS_FILE, "w") as f:
            json.dump(tokens, f)
    except Exception as e:
        print(f"Error saving tokens: {e}")

registration_tokens = load_tokens() # Store device tokens for FCM
print(f"Loaded {len(registration_tokens)} tokens from storage.")

# Initialize Firebase Admin SDK
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK initialized.")
except Exception as e:
    print(f"Failed to initialize Firebase Admin SDK: {e}")
    print("Push notifications will be disabled until serviceAccountKey.json is provided.")

@app.route('/detect', methods=['POST'])
def detect_person():
    global frame_count, last_upload_time, detection_enabled
    
    if not detection_enabled:
        return jsonify({"person_count": 0, "status": "detection_disabled"})

    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    
    file = request.files['image']
    # Read image from received bytes
    npimg = np.frombuffer(file.read(), np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    if frame is None:
        return jsonify({"error": "Failed to decode image"}), 400

    model = get_model()

    frame_count += 1

    # Run inference on EVERY frame to avoid missing detections, 
    # since the client already throttles hits to every 3 seconds.
    results = model.predict(frame, imgsz=320, device="cpu", conf=0.3, verbose=False, half=False, augment=False)
    
    count: int = 0
    for r in results:
        for box in r.boxes:
            c = int(box.cls[0])
            if model.names[c] == "person":
                count += 1
                
    if count > 0:
        print(f"{count} person detected")
        
        # Send mobile notification
        send_push_notification("Person Detected!", f"{count} person(s) spotted in the camera.")
        
        current_time = datetime.now()
        
        if last_upload_time is None or (current_time - last_upload_time) >= UPLOAD_COOLDOWN:
            print("Uploading image to ImageKit...")
            try:
                # Re-encode frame to bytes for upload
                _, buffer = cv2.imencode('.jpg', frame)
                img_bytes = buffer.tobytes()
                
                upload_results = imagekit.files.upload(
                    file=img_bytes,
                    file_name=f"person_detected_{current_time.strftime('%Y%m%d_%H%M%S')}.jpg",
                    folder="/person_detections/",
                    tags=["person", "detection"],
                    public_key='public_yeGoRA3Ufc+D8mVw7v/3QlOsEns='
                )
                print(f"Upload successful: {upload_results.url}")
                last_upload_time = current_time
            except Exception as e:
                import traceback
                print(f"Failed to upload image to ImageKit: {e}")
                traceback.print_exc()
        else:
            wait_time = (UPLOAD_COOLDOWN - (current_time - last_upload_time)).total_seconds()
            print(f"Upload cooldown active. Next upload available in {int(wait_time)} seconds.")

    return jsonify({"person_count": count})

@app.route('/images', methods=['GET'])
def get_images():
    try:
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        skip = int(request.args.get('skip', 0))
        limit = int(request.args.get('limit', 20))
        
        # Build Lucene-like search query for ImageKit
        # Docs: https://docs.imagekit.io/api-reference/media-library-management-apis/list-and-search-assets
        query_parts = ['path = "/person_detections/"']
        
        if from_date:
            # from_date is expected in YYYY-MM-DD format from frontend
            query_parts.append(f'createdAt >= "{from_date}"')
        if to_date:
            # to_date is expected in YYYY-MM-DD format
            # We append 23:59:59 to include the entire day
            query_parts.append(f'createdAt <= "{to_date}T23:59:59Z"')
            
        search_query = " AND ".join(query_parts)
        
        # List files using the search query
        results = imagekit.assets.list(
            search_query=search_query,
            sort="DESC_CREATED",
            limit=limit,
            skip=skip
        )
        
        images = []
        for asset in results:
            images.append({
                "file_id": asset.file_id,
                "name": asset.name,
                "url": asset.url,
                "thumbnail_url": asset.thumbnail,
                "created_at": asset.created_at
            })
            
        return jsonify(images)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/status', methods=['GET'])
def get_status():
    global detection_enabled
    return jsonify({"detection_enabled": detection_enabled})

@app.route('/toggle-detection', methods=['POST'])
def toggle_detection():
    global detection_enabled
    detection_enabled = not detection_enabled
    return jsonify({"detection_enabled": detection_enabled})

@app.route('/register-token', methods=['POST'])
def register_token():
    global registration_tokens
    data = request.json
    token = data.get('token')
    if token and token not in registration_tokens:
        registration_tokens.append(token)
        save_tokens(registration_tokens)
        print(f"Token registered and saved: {token}")
    return jsonify({"status": "success"})

def send_push_notification(title, body):
    global registration_tokens
    if not registration_tokens:
        print("not registered tokens")
        return
    
    print("registration_tokens : ",registration_tokens)
    
    for token in registration_tokens:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=token,
        )
        try:
            response = messaging.send(message)
            print(f"Successfully sent message to {token}: {response}")
        except Exception as e:
            print(f"Failed to send notification to {token}: {e}")

if __name__ == '__main__':
    # Run the server on port 5000
    app.run(host='0.0.0.0', port=5000)
