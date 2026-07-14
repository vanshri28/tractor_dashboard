import re
import cv2
import easyocr
import requests

print("Loading OCR...")
reader = easyocr.Reader(['en'])

cap = cv2.VideoCapture(0)

print("Press S to Scan")
print("Press Q to Quit")

while True:

    ret, frame = cap.read()

    if not ret:
        print("Camera not detected")
        break

    cv2.imshow("Registration Plate Scanner", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('s'):

        print("\nScanning...")

        scan_frame = frame.copy()

        results = reader.readtext(scan_frame)

        plate_found = False
        plate_number = ""

        for result in results:

            box = result[0]
            text = result[1]

            # Clean OCR text
            clean_text = text.upper()
            clean_text = clean_text.replace(".", "")
            clean_text = clean_text.replace("-", "")
            clean_text = clean_text.replace(" ", "")
            print("OCR Read:", clean_text)

            # Indian Vehicle Registration Pattern
            pattern = r'^[A-Z]{2}[0-9]{2}[A-Z]{1,3}[0-9]{4}$'

            if re.match(pattern, clean_text):

                plate_found = True
                plate_number = clean_text

                top_left = tuple(map(int, box[0]))
                bottom_right = tuple(map(int, box[2]))

                cv2.rectangle(
                    scan_frame,
                    top_left,
                    bottom_right,
                    (0, 255, 0),
                    3
                )

                cv2.putText(
                    scan_frame,
                    plate_number,
                    (top_left[0], top_left[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )

        if plate_found:

            print("\nDetected Registration Number:")
            print(plate_number)

            requests.post(
                "https://tractor-dashboard-z05m.onrender.com/update_plate",
                json={"plate": plate_number}
            )

        else:

            print("\nNo registration plate found")

        cv2.imshow("Detected Registration Plate", scan_frame)

        cv2.waitKey(0)

    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
