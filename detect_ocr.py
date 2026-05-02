import cv2
import easyocr
import numpy as np

# OCR reader
reader = easyocr.Reader(['en'], gpu=False)

def detect_number_plate():

    # 👉 IMAGE LOAD
    img = cv2.imread("test1.jpg")

    if img is None:
        print("Image not found")
        return None

    # 👉 PREPROCESSING
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.bilateralFilter(gray, 11, 17, 17)
    edged = cv2.Canny(blur, 30, 200)

    # 👉 FIND CONTOURS
    contours, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    plate_img = None

    for cnt in contours:
        approx = cv2.approxPolyDP(cnt, 0.018 * cv2.arcLength(cnt, True), True)

        if len(approx) == 4:  # rectangle (plate shape)
            x, y, w, h = cv2.boundingRect(cnt)
            plate_img = gray[y:y+h, x:x+w]
            break

    # 👉 अगर contour detect नाही झाला तर full image OCR
    if plate_img is None:
        plate_img = gray

    # 👉 OCR
    result = reader.readtext(plate_img)

    text = ""

    for detection in result:
        text += detection[1] + " "

    text = text.strip().replace(" ", "").upper()

    print("Detected Number Plate:", text)

    return text


# 👉 TEST RUN (direct run साठी)
if __name__ == "__main__":
    detect_number_plate()
