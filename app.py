from flask import Flask, render_template, request, redirect, session, jsonify
import psycopg
import os
import random
from datetime import datetime

# ==========================
# OCR IMPORT
# ==========================
try:
    from detect_ocr import detect_number_plate
except ImportError:
    detect_number_plate = None

# ==========================
# FLASK APP
# ==========================
app = Flask(__name__)
app.secret_key = "tractor_secret_key"

# ==========================
# DATABASE
# ==========================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL not found.")

def get_connection():
    return psycopg.connect(
        DATABASE_URL,
        sslmode="require"
    )

# ==========================
# CREATE TABLES
# ==========================

def init_db():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS farmers(
        id SERIAL PRIMARY KEY,
        name VARCHAR(100),
        phone VARCHAR(20) UNIQUE,
        address VARCHAR(200)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS entries(
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
    );
    """)

    conn.commit()
    cur.close()
    conn.close()


try:
    init_db()
    print("Database Connected")
except Exception as e:
    print("Database Error:", e)

# ==========================
# FUNCTIONS
# ==========================

def generate_entry():
    return "E" + str(random.randint(1000,9999))

def generate_token():
    return "T" + str(random.randint(100,999))

def current_time():
    return datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")

# ==========================
# HOME
# ==========================

@app.route("/")
def home():
    return render_template("index.html")

# ==========================
# ADMIN LOGIN
# ==========================

@app.route("/admin_login", methods=["POST"])
def admin_login():

    username = request.form.get("username")
    password = request.form.get("password")

    if username=="admin" and password=="admin123":
        session["admin"]=True
        return redirect("/admin_dashboard")

    return "Invalid Admin Login"

# ==========================
# OFFICE LOGIN
# ==========================

@app.route("/office_login", methods=["POST"])
def office_login():

    username=request.form.get("username")
    password=request.form.get("password")

    if username=="office" and password=="office123":
        session["office"]=True
        return redirect("/office_dashboard")

    return "Invalid Office Login"

# ==========================
# FARMER LOGIN
# ==========================

@app.route("/farmer_login", methods=["POST"])
def farmer_login():

    phone=request.form.get("phone")

    conn=get_connection()
    cur=conn.cursor()

    cur.execute(
        "SELECT * FROM farmers WHERE phone=%s",
        (phone,)
    )

    farmer=cur.fetchone()

    cur.close()
    conn.close()

    if farmer:
        session["farmer"]=phone
        return redirect("/farmer_dashboard")

    return "Farmer Not Registered"

# ==========================
# REGISTER
# ==========================

@app.route("/register",methods=["GET","POST"])
def register():

    if request.method=="POST":

        name=request.form.get("name")
        phone=request.form.get("phone")
        address=request.form.get("address")

        try:

            conn=get_connection()
            cur=conn.cursor()

            cur.execute(
                """
                INSERT INTO farmers(name,phone,address)
                VALUES(%s,%s,%s)
                """,
                (name,phone,address)
            )

            conn.commit()

            cur.close()
            conn.close()

            return redirect("/")

        except Exception as e:
            return str(e)

    return render_template("register.html")

# ==========================
# GET FARMER DETAILS
# ==========================

@app.route("/get_farmer/<phone>")
def get_farmer(phone):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute(
        """
        SELECT name,address
        FROM farmers
        WHERE phone=%s
        """,
        (phone,)
    )

    farmer=cur.fetchone()

    cur.close()
    conn.close()

    if farmer:

        return jsonify({

            "name":farmer[0],
            "address":farmer[1]

        })

    return jsonify({
        "error":"Farmer Not Found"
    })
    # ==========================
# ADMIN DASHBOARD
# ==========================

@app.route("/admin_dashboard", methods=["GET", "POST"])
def admin_dashboard():

    if "admin" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":

        farmer_phone = request.form.get("phone")
        farmer_name = request.form.get("name")
        address = request.form.get("address")
        tractor = request.form.get("tractor")
        trip = request.form.get("trip")
        driver_name = request.form.get("driver_name")
        driver_phone = request.form.get("driver_phone")

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
            farmer_phone,
            farmer_name,
            address,
            tractor,
            trip,
            driver_name,
            driver_phone,
            current_time()
        ))

        conn.commit()

    cur.execute("SELECT * FROM entries ORDER BY id DESC")
    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "admin_dashboard.html",
        data=data
    )


# ==========================
# OCR DETECTION
# ==========================

@app.route("/detect")
def detect():

    if detect_number_plate is None:
        return "detect_ocr.py not found", 500

    detected_number = detect_number_plate()

    if detected_number is None:
        return "No Plate Detected"

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM entries WHERE tractor=%s ORDER BY id DESC LIMIT 1",
        (detected_number,)
    )

    row = cur.fetchone()

    if row:

        entry = generate_entry()
        token = generate_token()

        cur.execute("""
        UPDATE entries
        SET
            detected_number=%s,
            entry_no=%s,
            token=%s,
            time=%s
        WHERE id=%s
        """,
        (
            detected_number,
            entry,
            token,
            current_time(),
            row[0]
        ))

        conn.commit()

    cur.close()
    conn.close()

    return "Detection Completed"


# ==========================
# OFFICE DASHBOARD
# ==========================

@app.route("/office_dashboard")
def office_dashboard():

    if "office" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM entries ORDER BY id DESC")

    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "office_dashboard.html",
        data=data
    )


# ==========================
# FARMER DASHBOARD
# ==========================

@app.route("/farmer_dashboard")
def farmer_dashboard():

    if "farmer" not in session:
        return redirect("/")

    phone = session["farmer"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM entries WHERE farmer_phone=%s ORDER BY id DESC",
        (phone,)
    )

    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "farmer_dashboard.html",
        data=data
    )


# ==========================
# UPDATE DETECTED PLATE
# ==========================

@app.route("/update_plate", methods=["POST"])
def update_plate():

    data = request.get_json()

    if not data:
        return jsonify({"status": "error"})

    plate = data.get("plate")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    UPDATE entries
    SET detected_number=%s
    WHERE id=
    (
        SELECT id
        FROM entries
        ORDER BY id DESC
        LIMIT 1
    )
    """, (plate,))

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "status": "success",
        "plate": plate
    })


# ==========================
# DATABASE TEST
# ==========================

@app.route("/db_test")
def db_test():

    try:

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT NOW()")

        time = cur.fetchone()

        cur.close()
        conn.close()

        return f"Database Connected Successfully<br>{time}"

    except Exception as e:

        return str(e)


# ==========================
# LOGOUT
# ==========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ==========================
# MAIN
# ==========================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )
