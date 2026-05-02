import cv2
import easyocr
import numpy as np
import re

# OCR Reader (CPU mode)
reader = easyocr.Reader(['en'], gpu=False)


def clean_text(text):
    # Remove unwanted characters
    text = re.sub(r'[^A-Z0-9]', '', text)
    return text


def detect_number_plate(image_path="test1.jpg"):

    # ---------- LOAD IMAGE ----------
    img = cv2.imread(image_path)

    if img is None:
        print("❌ Image not found:", image_path)
        return None

    # ---------- PREPROCESS ----------
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.bilateralFilter(gray, 11, 17, 17)
    edged = cv2.Canny(blur, 30, 200)

    # ---------- FIND CONTOURS ----------
    contours, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    plate_img = None

    for cnt in contours:
        approx = cv2.approxPolyDP(cnt, 0.018 * cv2.arcLength(cnt, True), True)

        if len(approx) == 4:  # rectangle
            x, y, w, h = cv2.boundingRect(cnt)

            # filter small regions
            if w > 100 and h > 30:
                plate_img = gray[y:y+h, x:x+w]
                break

    # ---------- FALLBACK ----------
    if plate_img is None:
        print("⚠️ Plate not detected, using full image")
        plate_img = gray

    # ---------- OCR ----------
    results = reader.readtext(plate_img)

    detected_text = ""

    for (bbox, text, prob) in results:
        detected_text += text + " "

    detected_text = detected_text.strip().upper()
    detected_text = clean_text(detected_text)

    # ---------- OUTPUT ----------
    print("✅ Detected Number Plate:", detected_text)

    return detected_text


# ---------- DIRECT RUN ----------
if __name__ == "__main__":
    number = detect_number_plate("test1.jpg")

    if number:
        print("🚜 FINAL OUTPUT:", number)
    else:
        print("❌ No number detected")
