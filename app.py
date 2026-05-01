from flask import Flask, request, jsonify, render_template, redirect
import psycopg2
import os
import random
from datetime import datetime

app = Flask(__name__)

# ---------------- DB CONNECTION ----------------
def get_connection():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

# ---------------- NORMALIZE FUNCTION ----------------
def normalize_plate(plate):
    return plate.replace(" ", "").replace("-", "").replace(".", "").upper()

# ---------------- HOME ----------------
@app.route('/')
def index():
    return render_template("index.html")

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        farmer = request.form['farmer']
        phone = request.form['phone']
        address = request.form['address']
        tractor = normalize_plate(request.form['tractor'])
        trip = request.form['trip']
        driver = request.form['driver']
        driver_phone = request.form['driver_phone']

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO farmers 
            (farmer, phone, address, tractor, trip, driver, driver_phone)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (farmer, phone, address, tractor, trip, driver, driver_phone))

        conn.commit()
        cur.close()
        conn.close()

        return redirect('/office_dashboard')

    return render_template("register.html")

# ---------------- DASHBOARD ----------------
@app.route('/office_dashboard')
def office_dashboard():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM farmers ORDER BY id DESC")
    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("office_dashboard.html", data=data)

# ---------------- CHECK PLATE API ----------------
@app.route('/check_plate', methods=['POST'])
def check_plate():
    data = request.get_json()
    plate = data.get("plate")

    norm_plate = normalize_plate(plate)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, tractor FROM farmers")
    rows = cur.fetchall()

    for row in rows:
        db_id = row[0]
        db_plate = normalize_plate(row[1])

        if norm_plate == db_plate:
            entry = random.randint(100, 999)
            token = random.randint(1, 50)
            now = datetime.now().strftime("%H:%M:%S")

            cur.execute("""
                UPDATE farmers 
                SET entry=%s, token=%s, time=%s 
                WHERE id=%s
            """, (entry, token, now, db_id))

            conn.commit()
            cur.close()
            conn.close()

            return jsonify({
                "status": "MATCH",
                "entry": entry,
                "token": token,
                "time": now
            })

    cur.close()
    conn.close()

    return jsonify({"status": "NOT MATCH"})


if __name__ == "__main__":
    app.run(debug=True)
