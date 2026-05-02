from flask import Flask, render_template, request, redirect, session, jsonify
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret"

DATABASE_URL = os.environ.get("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# ------------------ TABLE ------------------
cur.execute("""
CREATE TABLE IF NOT EXISTS farmers (
    id SERIAL PRIMARY KEY,
    farmer TEXT,
    phone TEXT,
    address TEXT,
    tractor TEXT,
    trip TEXT,
    driver TEXT,
    driver_phone TEXT,
    entry INTEGER,
    token INTEGER,
    time TEXT
)
""")
conn.commit()

# ------------------ LOGIN PAGE ------------------
@app.route('/')
def index():
    return render_template("index.html")

# ------------------ FARMER REGISTER ------------------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        farmer = request.form['farmer']
        phone = request.form['phone']
        address = request.form['address']

        cur.execute("""
        INSERT INTO farmers (farmer, phone, address)
        VALUES (%s,%s,%s)
        """,(farmer,phone,address))
        conn.commit()

        return redirect('/')
    return render_template("register.html")

# ------------------ ADMIN LOGIN ------------------
@app.route('/admin_login', methods=['POST'])
def admin_login():
    if request.form['username']=="admin" and request.form['password']=="admin123":
        return redirect('/admin_dashboard')
    return "Invalid"

# ------------------ OFFICE LOGIN ------------------
@app.route('/office_login', methods=['POST'])
def office_login():
    if request.form['username']=="office" and request.form['password']=="office123":
        return redirect('/office_dashboard')
    return "Invalid"

# ------------------ ADMIN DASHBOARD ------------------
@app.route('/admin_dashboard', methods=['GET','POST'])
def admin():
    data=None

    if request.method=='POST':
        phone=request.form['phone']

        cur.execute("SELECT * FROM farmers WHERE phone=%s",(phone,))
        data=cur.fetchone()

        if 'submit' in request.form:
            tractor=request.form['tractor'].replace(" ","").upper()
            trip=request.form['trip']
            driver=request.form['driver']
            driver_phone=request.form['driver_phone']

            cur.execute("""
            UPDATE farmers SET tractor=%s,trip=%s,driver=%s,driver_phone=%s
            WHERE phone=%s
            """,(tractor,trip,driver,driver_phone,phone))
            conn.commit()

    return render_template("admin_dashboard.html", data=data)

# ------------------ OFFICE DASHBOARD ------------------
@app.route('/office_dashboard')
def office():
    cur.execute("SELECT * FROM farmers ORDER BY id ASC")
    data=cur.fetchall()
    return render_template("office_dashboard.html", data=data)

# ------------------ MATCH API ------------------
@app.route('/check_plate', methods=['POST'])
def check_plate():
    plate=request.json['plate']
    plate=plate.replace(" ","").upper()

    cur.execute("SELECT * FROM farmers WHERE tractor=%s",(plate,))
    row=cur.fetchone()

    if row:
        entry=row[0]
        token=row[0]
        time=datetime.now().strftime("%H:%M:%S")

        cur.execute("""
        UPDATE farmers SET entry=%s,token=%s,time=%s WHERE tractor=%s
        """,(entry,token,time,plate))
        conn.commit()

        return jsonify({"status":"MATCH"})
    else:
        return jsonify({"status":"NOT MATCH"})

# ------------------ PRINT ------------------
@app.route('/print/<int:id>')
def print_page(id):
    cur.execute("SELECT * FROM farmers WHERE id=%s",(id,))
    data=cur.fetchone()
    return render_template("print.html",data=data)

if __name__ == "__main__":
    app.run(debug=True)
