from flask import Flask, render_template, request, redirect, session, jsonify
import psycopg
import random
import os
from datetime import datetime


# =========================================================
# OCR IMPORT
# =========================================================
try:
    from detect_ocr import detect_number_plate
except Exception:
    detect_number_plate = None


# =========================================================
# FLASK APP
# =========================================================
app = Flask(__name__)
app.secret_key = "secret123"


# =========================================================
# DATABASE
# =========================================================
DATABASE_URL = os.environ.get("DATABASE_URL")


def get_connection():
    return psycopg.connect(DATABASE_URL)


# =========================================================
# DATABASE INITIALIZATION
# =========================================================
def init_db():

    conn = get_connection()
    cur = conn.cursor()

    # ---------------- FARMERS TABLE ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS farmers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            phone VARCHAR(20) UNIQUE,
            address VARCHAR(200)
        )
    """)

    # ---------------- ENTRIES TABLE ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id SERIAL PRIMARY KEY,
            farmer_phone VARCHAR(20),
            farmer_name VARCHAR(100),
            address VARCHAR(200),
            tractor VARCHAR(50),
            trip VARCHAR(50),
            driver_name VARCHAR(100),
            driver_phone VARCHAR(20),
            detected_number VARCHAR(50) DEFAULT 'None',
            entry_no VARCHAR(50) DEFAULT 'None',
            token VARCHAR(50) DEFAULT 'None',
            time VARCHAR(50) DEFAULT 'None',
            result_image_url VARCHAR(500)
            DEFAULT 'None'
        )
    """)

    # -------------------------------------------------
    # OLD DATABASE SUPPORT
    # -------------------------------------------------

    cur.execute("""
        ALTER TABLE entries
        ADD COLUMN IF NOT EXISTS detected_number VARCHAR(50)
        DEFAULT 'None'
    """)

    cur.execute("""
        ALTER TABLE entries
        ADD COLUMN IF NOT EXISTS entry_no VARCHAR(50)
        DEFAULT 'None'
    """)

    cur.execute("""
        ALTER TABLE entries
        ADD COLUMN IF NOT EXISTS token VARCHAR(50)
        DEFAULT 'None'
    """)

    cur.execute("""
        ALTER TABLE entries
        ADD COLUMN IF NOT EXISTS time VARCHAR(50)
        DEFAULT 'None'
    """)

    cur.execute("""
        ALTER TABLE entries
        ADD COLUMN IF NOT EXISTS result_image_url TEXT
    """)
    cur.execute("""
        ALTER TABLE entries
        ADD COLUMN IF NOT EXISTS result_image_url VARCHAR(500) DEFAULT 'None'
    """)

    conn.commit()

    cur.close()
    conn.close()


# Initialize database
init_db()


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def clean_plate(number):

    if number is None:
        return ""

    return (
        str(number)
        .replace(" ", "")
        .replace("-", "")
        .replace(".", "")
        .upper()
        .strip()
    )


def generate_entry():
    return "E" + str(random.randint(1000, 9999))


def generate_token():
    return "T" + str(random.randint(100, 999))


def current_time():
    return datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route("/admin_login", methods=["POST"])
def admin_login():

    username = request.form.get("username", "")
    password = request.form.get("password", "")

    if username == "admin" and password == "admin123":

        session["admin"] = True

        return redirect("/admin_dashboard")

    return "Invalid Admin Login"


# =========================================================
# OFFICE LOGIN
# =========================================================

@app.route("/office_login", methods=["POST"])
def office_login():

    username = request.form.get("username", "")
    password = request.form.get("password", "")

    if username == "office" and password == "office123":

        session["office"] = True

        return redirect("/office_dashboard")

    return "Invalid Office Login"


# =========================================================
# FARMER LOGIN
# =========================================================

@app.route("/farmer_login", methods=["POST"])
def farmer_login():

    phone = request.form.get("phone", "")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM farmers WHERE phone=%s",
        (phone,)
    )

    farmer = cur.fetchone()

    cur.close()
    conn.close()

    if farmer:

        session["farmer"] = phone

        return redirect("/farmer_dashboard")

    return "Not Registered"


# =========================================================
# FARMER REGISTRATION
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "")
        phone = request.form.get("phone", "")
        address = request.form.get("address", "")

        conn = get_connection()
        cur = conn.cursor()

        try:

            cur.execute("""
                INSERT INTO farmers
                (name, phone, address)
                VALUES (%s, %s, %s)
            """, (
                name,
                phone,
                address
            ))

            conn.commit()

        except Exception as e:

            conn.rollback()

            cur.close()
            conn.close()

            return f"Registration Error: {e}"

        cur.close()
        conn.close()

        return redirect("/")

    return render_template("register.html")


# =========================================================
# FETCH FARMER
# =========================================================

@app.route("/get_farmer/<phone>")
def get_farmer(phone):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT name, address
        FROM farmers
        WHERE phone=%s
    """, (phone,))

    data = cur.fetchone()

    cur.close()
    conn.close()

    if data:

        return jsonify({
            "name": data[0],
            "address": data[1]
        })

    return jsonify({
        "error": "not found"
    })


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin_dashboard", methods=["GET", "POST"])
def admin_dashboard():

    if "admin" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()

    # -----------------------------------------------------
    # ADD NEW TRACTOR ENTRY
    # -----------------------------------------------------

    if request.method == "POST":

        entry_time = datetime.now().strftime(
            "%d-%m-%Y %I:%M:%S %p"
        )

        cur.execute("""
            INSERT INTO entries
            (
                farmer_phone,
                farmer_name,
                address,
                tractor,
                trip,
                driver_name,
                driver_phone,
                detected_number,
                entry_no,
                token,
                time,
                result_image_url
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (

            request.form.get("phone", ""),
            request.form.get("name", ""),
            request.form.get("address", ""),
            request.form.get("tractor", ""),
            request.form.get("trip", ""),
            request.form.get("driver_name", ""),
            request.form.get("driver_phone", ""),

            "None",
            "None",
            "None",
            entry_time,
            None
        ))

        conn.commit()

    # -----------------------------------------------------
    # SHOW ALL ENTRIES
    # -----------------------------------------------------

    cur.execute("""
        SELECT *
        FROM entries
        ORDER BY id DESC
    """)

    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "admin_dashboard.html",
        data=data
    )


# =========================================================
# OCR DETECTION API
# =========================================================

@app.route("/detect")
def detect():

    if detect_number_plate is None:

        return jsonify({
            "status": "error",
            "message": "OCR function not available"
        })

    detected_number = detect_number_plate()

    detected_number = clean_plate(detected_number)

    if not detected_number:

        return jsonify({
            "status": "no plate",
            "message": "Number plate not detected"
        })

    conn = get_connection()
    cur = conn.cursor()

    # -----------------------------------------------------
    # ONLY PENDING ENTRY
    # -----------------------------------------------------

    cur.execute("""
        SELECT id, tractor, entry_no, token
        FROM entries
        WHERE
            (entry_no IS NULL OR entry_no = 'None')
            AND
            (token IS NULL OR token = 'None')
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cur.fetchone()

    if not row:

        cur.close()
        conn.close()

        return jsonify({
            "status": "no active entry",
            "message": "Please create a new tractor entry first."
        })

    entry_id = row[0]
    tractor_number = clean_plate(row[1])

    # Save detected number
    cur.execute("""
        UPDATE entries
        SET detected_number=%s
        WHERE id=%s
    """, (
        detected_number,
        entry_id
    ))

    # -----------------------------------------------------
    # MATCH
    # -----------------------------------------------------

    if tractor_number == detected_number:

        entry_no = generate_entry()
        token = generate_token()
        entry_time = current_time()

        cur.execute("""
            UPDATE entries
            SET
                detected_number=%s,
                entry_no=%s,
                token=%s,
                time=%s
            WHERE id=%s
        """, (
            detected_number,
            entry_no,
            token,
            entry_time,
            entry_id
        ))

        conn.commit()

        cur.close()
        conn.close()

        return jsonify({
            "status": "matched",
            "tractor": tractor_number,
            "plate": detected_number,
            "entry": entry_no,
            "token": token
        })

    # -----------------------------------------------------
    # NOT MATCHED
    # -----------------------------------------------------

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "status": "not matched",
        "tractor": tractor_number,
        "plate": detected_number
    })


# =========================================================
# OFFICE DASHBOARD
# =========================================================

@app.route("/office_dashboard")
def office_dashboard():

    if "office" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM entries
        ORDER BY id DESC
    """)

    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "office_dashboard.html",
        data=data
    )


# =========================================================
# FARMER DASHBOARD
# =========================================================

@app.route("/farmer_dashboard")
def farmer_dashboard():

    if "farmer" not in session:
        return redirect("/")

    phone = session["farmer"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM entries
        WHERE farmer_phone=%s
        ORDER BY id DESC
    """, (phone,))

    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "farmer_dashboard.html",
        data=data
    )


# =========================================================
# DATABASE TEST
# =========================================================

@app.route("/db_test")
def db_test():

    try:

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT 1")
        cur.fetchone()

        cur.close()
        conn.close()

        return "Database Connected Successfully ✅"

    except Exception as e:

        return str(e)


# =========================================================
# UPDATE DETECTED NUMBER + CLOUDINARY IMAGE
# =========================================================

@app.route("/update_plate", methods=["POST"])
def update_plate():

    try:

        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "status": "error",
                "message": "No JSON data received"
            }), 400

        plate = clean_plate(data.get("plate", ""))
        image_url = data.get("image_url", "")

        if not plate:
            return jsonify({
                "status": "error",
                "message": "Empty plate number"
            }), 400

        conn = get_connection()
        cur = conn.cursor()

        # ---------------------------------------------
        # TAKE LATEST MANUAL ENTRY
        # ---------------------------------------------

        cur.execute("""
            SELECT
                id,
                tractor,
                entry_no,
                token
            FROM entries
            ORDER BY id DESC
            LIMIT 1
        """)

        row = cur.fetchone()

        if not row:

            cur.close()
            conn.close()

            return jsonify({
                "status": "no entry",
                "plate": plate,
                "image_url": image_url
            })

        entry_id = row[0]

        tractor_number = clean_plate(row[1])

        existing_entry = row[2]
        existing_token = row[3]

        print("========================================")
        print("LATEST ENTRY ID :", entry_id)
        print("MANUAL TRACTOR  :", tractor_number)
        print("OCR PLATE       :", plate)
        print("IMAGE URL       :", image_url)
        print("========================================")

        # ---------------------------------------------
        # SAVE OCR + IMAGE
        # ---------------------------------------------

        cur.execute("""
            UPDATE entries
            SET
                detected_number=%s,
                result_image_url=%s
            WHERE id=%s
        """, (
            plate,
            image_url if image_url else "None",
            entry_id
        ))

        # ---------------------------------------------
        # CHECK MATCH
        # ---------------------------------------------

        if tractor_number == plate:

            if (
                existing_entry is None
                or existing_entry == ""
                or existing_entry == "None"
            ):
                entry_no = generate_entry()
            else:
                entry_no = existing_entry

            if (
                existing_token is None
                or existing_token == ""
                or existing_token == "None"
            ):
                token = generate_token()
            else:
                token = existing_token

            entry_time = current_time()

            cur.execute("""
                UPDATE entries
                SET
                    detected_number=%s,
                    entry_no=%s,
                    token=%s,
                    time=%s,
                    result_image_url=%s
                WHERE id=%s
            """, (
                plate,
                entry_no,
                token,
                entry_time,
                image_url if image_url else "None",
                entry_id
            ))

            conn.commit()

            cur.close()
            conn.close()

            print("========================================")
            print("MATCHED SUCCESSFULLY")
            print("TRACTOR :", tractor_number)
            print("PLATE   :", plate)
            print("ENTRY   :", entry_no)
            print("TOKEN   :", token)
            print("IMAGE   :", image_url)
            print("========================================")

            return jsonify({
                "status": "matched",
                "plate": plate,
                "tractor": tractor_number,
                "entry": entry_no,
                "token": token,
                "image_url": image_url
            })

        # ---------------------------------------------
        # NOT MATCHED
        # ---------------------------------------------

        conn.commit()

        cur.close()
        conn.close()

        print("========================================")
        print("NOT MATCHED")
        print("TRACTOR :", tractor_number)
        print("PLATE   :", plate)
        print("IMAGE   :", image_url)
        print("========================================")

        return jsonify({
            "status": "not matched",
            "plate": plate,
            "tractor": tractor_number,
            "entry": "None",
            "token": "None",
            "image_url": image_url
        })

    except Exception as e:

        print("UPDATE PLATE ERROR:", e)

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
