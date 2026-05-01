import cv2
from ultralytics import YOLO
import easyocr
import requests

# -------- LOAD MODEL --------
model = YOLO("best.pt")

# -------- OCR --------
reader = easyocr.Reader(['en'], gpu=False)

# -------- IMAGE PATH --------
image_path = "test1.jpg"   # 👈 तुझी image इथे change करू शकतेस

# -------- LOAD IMAGE --------
img = cv2.imread(image_path)

if img is None:
    print("❌ Image not found. Check path.")
    exit()

# -------- DETECTION --------
results = model(img)

plate_found = False

for r in results:
    for box in r.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])

        # crop number plate
        plate = img[y1:y2, x1:x2]

        # OCR
        ocr_result = reader.readtext(plate)

        for res in ocr_result:
            plate_text = res[1].replace(" ", "").upper()

            print("\n🔍 Detected Plate:", plate_text)

            plate_found = True

            # -------- API CALL --------
            try:
                response = requests.post(
                       "https://tractor-dashboard-z05m.onrender.com/check_plate",
                        json={"plate": plate_text}
                )

                data = response.json()

                if data["status"] == "MATCH":
                    print("✅ MATCH FOUND")
                    print("🎫 Entry:", data["entry"])
                    print("🎟 Token:", data["token"])
                else:
                    print("❌ NOT MATCH")

            except Exception as e:
                print("⚠️ API Error:", e)

# -------- NO PLATE --------
if not plate_found:
    print("❌ No number plate detected")