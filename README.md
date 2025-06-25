# Car License Plate Recognition 🚗

A simple, modern web app for car license plate detection and recognition using YOLO and EasyOCR, powered by FastAPI.

## Features
- Upload car images and detect license plates in your browser
- Accurate plate text extraction using EasyOCR
- Adjustable detection confidence threshold
- Beautiful, responsive web interface

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the app:**
   ```bash
   python main.py
   ```
   The app will be available at [http://localhost:8000](http://localhost:8000)

3. **Usage:**
   - Open the web interface in your browser
   - Upload a car image and click "Detect Plates"
   - View detected plate(s) and results side by side
   - Adjust the confidence threshold in Advanced Settings if needed
   - Click "Clear" to reset the interface

## Notes
- Only `main.py` is needed. Old files like `app.py` and `app_new.py` are not used.
- The app uses YOLO for plate detection and EasyOCR for text extraction.
- For best performance, a GPU is recommended but not required.

## License
MIT
