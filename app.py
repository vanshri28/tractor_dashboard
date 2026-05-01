from flask import Flask, render_template, request, redirect, jsonify
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)

# ✅ DB Connection (Render PostgreSQL)
DATABASE_URL = os.environ.get("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# ✅ CREATE TABLE (auto create)
cur.execute("""
CREATE TABLE IF NOT EXISTS farmers (
    id SERIAL PRIMARY KEY,
    farmer TEXT,
    phone TEXT,
    address TEXT,
    tractor TEXT,
    entry INTEGER,
    token INTEGER,
    time TEXT
)
""")
conn.commit()


# ✅ HOME
@app.route('/')
def home():
    return redirect('/office_dashboard')


# ✅ REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        farmer = request.form.get('farmer')
        phone = request.form.get('phone')
        address = request.form.get('address')
        tractor = request.form.get('tractor')

        if not tractor:
            return "Tractor number missing ❌"

        # 🔥 CLEAN NUMBER PLATE
        tractor = tractor.replace(" ", "").replace(".", "").upper()

        cur.execute("""
        INSERT INTO farmers (farmer, phone, address, tractor, entry, token, time)
        VALUES (%s, %s, %s, %s, NULL, NULL, NULL)
        """, (farmer, phone, address, tractor))

        conn.commit()

        return redirect('/office_dashboard')

    return render_template('register.html')


# ✅ DASHBOARD
@app.route('/office_dashboard')
def dashboard():
    cur.execute("SELECT * FROM farmers ORDER BY id DESC")
    data = cur.fetchall()
    return render_template('office_dashboard.html', data=data)


# ✅ API MATCH (OCR call)
@app.route('/check_plate', methods=['POST'])
def check_plate():
    data = request.get_json()

    plate = data.get("plate")

    if not plate:
        return jsonify({"status": "ERROR"})

    # 🔥 CLEAN AGAIN
    plate = plate.replace(" ", "").replace(".", "").upper()

    cur.execute("SELECT * FROM farmers WHERE tractor=%s", (plate,))
    row = cur.fetchone()

    if row:
        entry = row[0]
        token = row[0]

        time_now = datetime.now().strftime("%H:%M:%S")

        cur.execute("""
        UPDATE farmers
        SET entry=%s, token=%s, time=%s
        WHERE tractor=%s
        """, (entry, token, time_now, plate))

        conn.commit()

        return jsonify({"status": "MATCH"})

    else:
        return jsonify({"status": "NOT MATCH"})


if __name__ == "__main__":
    app.run(debug=True)
