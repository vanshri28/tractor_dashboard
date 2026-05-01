from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import random
import datetime
import os

app = Flask(__name__)
app.secret_key = "secret123"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

# ---------- INIT DB ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS farmers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT UNIQUE,
        address TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_phone TEXT,
        farmer_name TEXT,
        address TEXT,
        tractor TEXT,
        trip TEXT,
        driver_name TEXT,
        driver_phone TEXT,
        entry_no TEXT,
        token TEXT,
        time TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------- FUNCTIONS ----------
def generate_entry():
    return "E" + str(random.randint(1000,9999))

def generate_token():
    return "T" + str(random.randint(100,999))

def current_time():
    return datetime.datetime.now().strftime("%H:%M:%S")

# ---------- HOME ----------
@app.route("/")
def home():
    return render_template("index.html")

# ---------- REGISTER ----------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO farmers (name, phone, address) VALUES (?,?,?)",
                    (request.form["name"], request.form["phone"], request.form["address"]))
        conn.commit()
        conn.close()
        return redirect("/")
    return render_template("register.html")

# ---------- FETCH FARMER ----------
@app.route("/get_farmer/<phone>")
def get_farmer(phone):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name,address FROM farmers WHERE phone=?", (phone,))
    data = cur.fetchone()
    conn.close()

    if data:
        return jsonify({"name": data[0], "address": data[1]})
    return jsonify({})

# ---------- ADMIN ----------
@app.route("/admin_dashboard", methods=["GET","POST"])
def admin_dashboard():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if request.method == "POST":
        # ❗ ENTRY & TOKEN NOT GENERATED HERE
        cur.execute("""
        INSERT INTO entries 
        (farmer_phone, farmer_name, address, tractor, trip, driver_name, driver_phone)
        VALUES (?,?,?,?,?,?,?)
        """, (
            request.form["phone"],
            request.form["name"],
            request.form["address"],
            request.form["tractor"],
            request.form["trip"],
            request.form["driver_name"],
            request.form["driver_phone"]
        ))
        conn.commit()

    cur.execute("SELECT * FROM entries ORDER BY id DESC")
    data = cur.fetchall()
    conn.close()

    return render_template("admin_dashboard.html", data=data)

# ---------- OFFICE ----------
@app.route("/office_dashboard")
def office_dashboard():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM entries ORDER BY id DESC")
    data = cur.fetchall()
    conn.close()

    return render_template("office_dashboard.html", data=data)

# ---------- 🔥 AI MATCH ROUTE ----------
@app.route("/check_plate", methods=["POST"])
def check_plate():
    detected_plate = request.json["plate"].strip().upper()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # match tractor number
    cur.execute("SELECT * FROM entries WHERE UPPER(tractor)=?", (detected_plate,))
    data = cur.fetchone()

    if data:
        # already generated?
        if data[8] is not None:
            return jsonify({
                "status": "ALREADY",
                "entry": data[8],
                "token": data[9]
            })

        entry_no = generate_entry()
        token = generate_token()
        time = current_time()

        cur.execute("""
        UPDATE entries 
        SET entry_no=?, token=?, time=? 
        WHERE id=?
        """, (entry_no, token, time, data[0]))

        conn.commit()
        conn.close()

        return jsonify({
            "status": "MATCH",
            "entry": entry_no,
            "token": token
        })

    else:
        conn.close()
        return jsonify({"status": "NOT MATCH"})

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
