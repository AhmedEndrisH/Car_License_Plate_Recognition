# main.py
# FastAPI app for car license plate detection and recognition using YOLO and EasyOCR

from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import cv2
import numpy as np
from PIL import Image
import io
import uuid
import base64
import re
import easyocr

# --- FastAPI app setup ---
app = FastAPI()

# Allow CORS for local testing (optional)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (for result images)
app.mount("/output_images", StaticFiles(directory="output images"), name="output_images")
os.makedirs("output images", exist_ok=True)

# Set up Jinja2 templates directory
TEMPLATES_DIR = "Index"
os.makedirs(TEMPLATES_DIR, exist_ok=True)
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# --- Model and OCR setup ---
# Detection model (YOLO)
MODEL_PATH = "Y11l_best.pt"  # Make sure this file is in your project root
MIN_PLATE_LENGTH = 5
MAX_PLATE_LENGTH = 12

# Load YOLO model
from ultralytics import YOLO

def load_model(model_path):
    try:
        model = YOLO(model_path)
        return model
    except Exception:
        return None

def get_model():
    return load_model(MODEL_PATH)

model = get_model()

# Initialize EasyOCR reader (for plate text extraction)
reader = easyocr.Reader(['en'], gpu=False)

# --- Helper function for post-processing OCR text ---
def postprocess_plate_text(text):
    # Only allow uppercase letters and digits
    text = ''.join(c for c in text if c.isalnum()).upper()
    # Regex for common plate patterns: 3-4 letters + 3-4 digits
    match = re.search(r'([A-Z]{2,4}\s?\d{3,4})', text)
    if match:
        return match.group(1).replace(' ', '')
    # Remove repeated leading characters (e.g., ACCC444 -> CCC444)
    if len(text) > 2 and text[0] == text[1] and text[1] == text[2]:
        text = text[1:]
    return text

# --- Main plate detection and recognition function ---
def predict_plate(image: Image.Image, conf_threshold: float = 0.3) -> dict:
    """
    Detect license plates in the image using YOLO, then extract plate text using EasyOCR.
    Returns bounding boxes, recognized text, and URLs for input/result images.
    """
    if model is None:
        return {"error": "Model not loaded"}
    # Convert PIL image to OpenCV format
    img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    annotated_img = img.copy()
    results = model(img, conf=conf_threshold)
    plates = []
    plate_preview_url = None
    # Save input image for display
    input_img_url = None
    input_filename = f"input_{uuid.uuid4().hex}.jpg"
    input_path = os.path.join("output images", input_filename)
    cv2.imwrite(input_path, cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    input_img_url = f"/output_images/{input_filename}"
    # Process each detected plate
    for result in results:
        if result.boxes is not None:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                plate_img = img[y1:y2, x1:x2]
                try:
                    # Use EasyOCR for plate text extraction
                    ocr_results = reader.readtext(plate_img, detail=0, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                    text = ocr_results[0] if ocr_results else "UNREADABLE"
                except Exception:
                    text = "UNREADABLE"
                if not text:
                    text = "UNREADABLE"
                # Draw bounding box and recognized text on the annotated image
                cv2.rectangle(annotated_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(annotated_img, text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                plates.append({
                    'text': text,
                    'bbox': [x1, y1, x2, y2]
                })
                # Save the first plate preview for debugging (optional)
                if plate_preview_url is None and plate_img.size > 0:
                    preview_filename = f"plate_preview_{uuid.uuid4().hex}.jpg"
                    preview_path = os.path.join("output images", preview_filename)
                    cv2.imwrite(preview_path, cv2.cvtColor(plate_img, cv2.COLOR_BGR2RGB))
                    plate_preview_url = f"/output_images/{preview_filename}"
    # Save annotated result image
    result_img_url = None
    if len(plates) > 0:
        result_filename = f"result_{uuid.uuid4().hex}.jpg"
        result_path = os.path.join("output images", result_filename)
        cv2.imwrite(result_path, cv2.cvtColor(annotated_img, cv2.COLOR_BGR2RGB))
        result_img_url = f"/output_images/{result_filename}"
    return {
        "plates": plates,  # List of detected plates with text and bounding boxes
        "result_img_url": result_img_url,  # Annotated image URL
        "plate_preview_url": plate_preview_url,  # Cropped plate preview (optional)
        "input_img_url": input_img_url  # Original input image URL
    }

# --- Web endpoints ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Serve the main web interface."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "result": None,
        "filtered_result": None,
        "plate_numbers": [],
        "result_img_url": None,
        "input_img_url": None,
        "plate_preview_url": None,
        "conf_threshold": 0.3,
        "error": None
    })

@app.post("/predict", response_class=HTMLResponse)
async def predict_web(request: Request, file: UploadFile = File(...), conf_threshold: float = Form(0.3)):
    """
    Handle image upload, run detection and OCR, and render results in the web UI.
    """
    contents = await file.read()
    if not contents:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "result": None,
            "filtered_result": None,
            "plate_numbers": [],
            "result_img_url": None,
            "input_img_url": None,
            "plate_preview_url": None,
            "conf_threshold": conf_threshold,
            "error": "Please upload an image before detecting plates."
        })
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    result = predict_plate(image, conf_threshold)
    plate_numbers = [p['text'] for p in result.get('plates', [])]
    # Remove image URLs from JSON data for display
    filtered_result = dict(result)
    filtered_result.pop('result_img_url', None)
    filtered_result.pop('plate_preview_url', None)
    filtered_result.pop('input_img_url', None)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "result": result,
        "filtered_result": filtered_result,
        "plate_numbers": plate_numbers,
        "result_img_url": result.get("result_img_url"),
        "input_img_url": result.get("input_img_url"),
        "plate_preview_url": result.get("plate_preview_url"),
        "conf_threshold": conf_threshold,
        "error": None
    })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)