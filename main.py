from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
from ultralytics import YOLO
from imagekitio import ImageKit
from datetime import datetime, timedelta
import time

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# Load models once when the server starts
print("Loading YOLO models...")
model = YOLO("yyolov8n.pt")
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

@app.route('/detect', methods=['POST'])
def detect_person():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    
    file = request.files['image']
    # Read image from received bytes
    npimg = np.frombuffer(file.read(), np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    if frame is None:
        return jsonify({"error": "Failed to decode image"}), 400

    # Run inference
    results = model.predict(frame, imgsz=640, conf=0.3, verbose=False)
    
    count: int = 0
    for r in results:
        for box in r.boxes:
            c = int(box.cls[0])
            if model.names[c] == "person":
                count += 1
                
    if count > 0:
        print(f"{count} person detected")
        
        global last_upload_time
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
            limit=100
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

if __name__ == '__main__':
    # Run the server on port 5000
    app.run(host='0.0.0.0', port=5000)
