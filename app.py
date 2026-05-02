from flask import Flask, render_template, request, redirect
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)

# DATABASE CONNECTION
conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
cur = conn.cursor()


# =========================
# HOME
# =========================
@app.route('/')
def home():
    return render_template("index.html")


# =========================
# FARMER REGISTER
# =========================
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']

        cur.execute("INSERT INTO farmers (name, phone, address) VALUES (%s,%s,%s)",
                    (name, phone, address))
        conn.commit()

        return redirect('/')
    return render_template("register.html")


# =========================
# FARMER LOGIN
# =========================
@app.route('/farmer_login', methods=['POST'])
def farmer_login():
    phone = request.form['phone']

    cur.execute("SELECT * FROM farmers WHERE phone=%s", (phone,))
    data = cur.fetchone()

    if data:
        return render_template("farmer_dashboard.html", data=data)
    else:
        return "Farmer Not Found"


# =========================
# ADMIN LOGIN
# =========================
@app.route('/admin_login', methods=['POST'])
def admin_login():
    username = request.form['username']
    password = request.form['password']

    if username == "admin" and password == "admin123":
        return render_template("admin_dashboard.html")
    else:
        return "Invalid Admin Login"


# =========================
# ADMIN FETCH FARMER
# =========================
@app.route('/fetch', methods=['POST'])
def fetch():
    phone = request.form['phone']

    cur.execute("SELECT * FROM farmers WHERE phone=%s", (phone,))
    data = cur.fetchone()

    return render_template("admin_dashboard.html", data=data)


# =========================
# ADMIN ADD ENTRY
# =========================
@app.route('/add_entry', methods=['POST'])
def add_entry():
    phone = request.form['phone']
    tractor = request.form['tractor']
    trip = request.form['trip']
    driver = request.form['driver']
    driver_phone = request.form['driver_phone']

    cur.execute("""
        UPDATE farmers
        SET tractor=%s, trip=%s, driver=%s, driver_phone=%s
        WHERE phone=%s
    """, (tractor, trip, driver, driver_phone, phone))

    conn.commit()

    return redirect('/admin_dashboard')


@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template("admin_dashboard.html")


# =========================
# OFFICE DASHBOARD
# =========================
@app.route('/office_dashboard')
def office_dashboard():
    cur.execute("SELECT * FROM farmers ORDER BY id ASC")
    data = cur.fetchall()
    return render_template("office_dashboard.html", data=data)


# =========================
# OFFICE LOGIN
# =========================
@app.route('/office_login', methods=['POST'])
def office_login():
    username = request.form['username']
    password = request.form['password']

    if username == "office" and password == "office123":
        return redirect('/office_dashboard')
    else:
        return "Invalid Office Login"


# =========================
# OCR MATCH UPDATE
# =========================
@app.route('/update_entry/<plate>')
def update_entry(plate):

    cur.execute("SELECT * FROM farmers WHERE tractor=%s", (plate,))
    data = cur.fetchone()

    if data:
        entry = data[0]
        token = "T" + str(data[0])
        time = datetime.now().strftime("%H:%M:%S")

        cur.execute("""
            UPDATE farmers
            SET entry=%s, token=%s, time=%s
            WHERE tractor=%s
        """, (entry, token, time, plate))

        conn.commit()

        return "MATCH"
    else:
        return "NOT MATCH"


# =========================
# RUN
# =========================
if __name__ == '__main__':
    app.run(debug=True)
