from flask import Flask, render_template, request, redirect, session, jsonify
import psycopg
import random
import datetime
import os
from datetime import datetime

# 👇 OCR FILE IMPORT (IMPORTANT)
try:
    from detect_ocr import detect_number_plate
except:
    detect_number_plate = None  # function should return detected number

app = Flask(__name__)
app.secret_key = "secret123"

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    return psycopg.connect(DATABASE_URL)

# ---------- DATABASE ----------
def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS farmers (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100),
        phone VARCHAR(20) UNIQUE,
        address VARCHAR(200)
    )
    """)

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
    time VARCHAR(50) DEFAULT 'None'
)
    """)

    conn.commit()
    cur.close()
    conn.close()

init_db()

# ---------- FUNCTIONS ----------
def generate_entry():
    return "E" + str(random.randint(1000,9999))

def generate_token():
    return "T" + str(random.randint(100,999))

def current_time():
    return datetime.now().strftime("%H:%M:%S")

# ---------- HOME ----------
@app.route("/")
def home():
    return render_template("index.html")

# ---------- ADMIN LOGIN ----------
@app.route("/admin_login", methods=["POST"])
def admin_login():
    if request.form["username"] == "admin" and request.form["password"] == "admin123":
        session["admin"] = True
        return redirect("/admin_dashboard")
    return "Invalid Admin Login"

# ---------- OFFICE LOGIN ----------
@app.route("/office_login", methods=["POST"])
def office_login():
    if request.form["username"] == "office" and request.form["password"] == "office123":
        session["office"] = True
        return redirect("/office_dashboard")
    return "Invalid Office Login"

# ---------- FARMER LOGIN ----------
@app.route("/farmer_login", methods=["POST"])
def farmer_login():
    phone = request.form["phone"]

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM farmers WHERE phone=%s", (phone,))
    farmer = cur.fetchone()
    conn.close()

    if farmer:
        session["farmer"] = phone
        return redirect("/farmer_dashboard")

    return "Not Registered"

# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        address = request.form["address"]

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("INSERT INTO farmers (name, phone, address) VALUES (%s,%s,%s)",
                    (name, phone, address))
        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("register.html")

# ---------- FETCH FARMER ----------
@app.route("/get_farmer/<phone>")
def get_farmer(phone):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name,address FROM farmers WHERE phone=%s", (phone,))
    data = cur.fetchone()
    conn.close()

    if data:
        return jsonify({"name": data[0], "address": data[1]})
    return jsonify({"error": "not found"})

# ---------- ADMIN DASHBOARD ----------
# ---------- ADMIN DASHBOARD ----------
@app.route("/admin_dashboard", methods=["GET", "POST"])
def admin_dashboard():

    if "admin" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":

        current_time = datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")

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
            time
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            request.form["phone"],
            request.form["name"],
            request.form["address"],
            request.form["tractor"],
            request.form["trip"],
            request.form["driver_name"],
            request.form["driver_phone"],
            current_time
        ))

        conn.commit()

    cur.execute("SELECT * FROM entries ORDER BY id DESC")
    data = cur.fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        data=data
    )

# ---------- OCR MATCH API ----------
@app.route("/detect")
def detect():
    detected_number = detect_number_plate()

    print("Detected:", detected_number)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM entries WHERE tractor=%s", (detected_number,))
    row = cur.fetchone()

    if row:
        entry = generate_entry()
        token = generate_token()
        time = current_time()

        cur.execute("""
        UPDATE entries SET entry_no=%s, token=%s, time=%s WHERE id=%s
        """, (entry, token, time, row[0]))

        conn.commit()

        print("MATCH FOUND → Entry Generated")

    conn.close()

    return "Detection Done"

# ---------- OFFICE DASHBOARD ----------
@app.route("/office_dashboard")
def office_dashboard():
    if "office" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM entries ORDER BY id DESC")
    data = cur.fetchall()
    conn.close()

    return render_template("office_dashboard.html", data=data)

# ---------- add_detected_column ----------
@app.route("/add_detected_column")
def add_detected_column():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        ALTER TABLE entries
        ADD COLUMN detected_number VARCHAR(50)
    """)

    conn.commit()
    conn.close()

    return "Column Added Successfully"
# ---------- FARMER DASHBOARD ----------
@app.route("/farmer_dashboard")
def farmer_dashboard():
    if "farmer" not in session:
        return redirect("/")

    phone = session["farmer"]

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM entries WHERE farmer_phone=%s", (phone,))
    data = cur.fetchall()
    conn.close()

    return render_template("farmer_dashboard.html", data=data)

@app.route("/db_test")
def db_test():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        conn.close()
        return "Database Connected Successfully ✅"
    except Exception as e:
        return str(e)

@app.route("/update_plate", methods=["POST"])
def update_plate():

    data = request.get_json()
    plate = data.get("plate")

    # Clean OCR plate
    plate = plate.replace(" ", "").replace("-", "").upper()

    conn = get_connection()
    cur = conn.cursor()

    # Get latest tractor entry
    cur.execute("""
        SELECT id, tractor
        FROM entries
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cur.fetchone()

    if row:

        entry_id = row[0]
        tractor_number = row[1].replace(" ", "").replace("-", "").upper()

        if tractor_number == plate:

            cur.execute("""
                UPDATE entries
                SET detected_number=%s
                WHERE id=%s
            """, (plate, entry_id))

            conn.commit()

            conn.close()

            return jsonify({
                "status": "matched",
                "plate": plate
            })

    conn.close()

    return jsonify({
        "status": "not matched",
        "plate": plate
    })

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
