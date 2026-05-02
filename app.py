from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# DB INIT
def init_db():
    conn = get_db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        address TEXT,
        tractor TEXT,
        trip TEXT,
        driver TEXT,
        driver_phone TEXT,
        entry TEXT,
        token TEXT,
        time TEXT
    )
    """)
    conn.commit()

init_db()

# ---------------- ROUTES ----------------

@app.route('/')
def index():
    return render_template("index.html")

# REGISTER
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']

        conn = get_db()
        conn.execute("""
        INSERT INTO records (name, phone, address, tractor, trip, driver, driver_phone, entry, token, time)
        VALUES (?, ?, ?, '', '', ?, ?, 'None', 'None', ?)
        """, (name, phone, address, name, phone,
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        conn.commit()
        return redirect('/')

    return render_template("register.html")

# ADMIN
@app.route('/admin_dashboard', methods=['GET','POST'])
def admin():
    conn = get_db()

    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']
        tractor = request.form['tractor']
        trip = request.form['trip']

        conn.execute("""
        UPDATE records SET 
        address=?, tractor=?, trip=?, driver=?, driver_phone=?
        WHERE phone=?
        """, (address, tractor, trip, name, phone, phone))

        conn.commit()

    data = conn.execute("SELECT * FROM records").fetchall()
    return render_template("admin_dashboard.html", data=data)

# OFFICE
@app.route('/office_dashboard')
def office():
    conn = get_db()
    data = conn.execute("SELECT * FROM records ORDER BY id DESC").fetchall()
    return render_template("office_dashboard.html", data=data)

# SEARCH
@app.route('/search', methods=['POST'])
def search():
    phone = request.form['phone']
    conn = get_db()

    data = conn.execute("""
    SELECT * FROM records WHERE driver_phone LIKE ?
    """, ('%' + phone + '%',)).fetchall()

    return render_template("office_dashboard.html", data=data)

# FARMER
@app.route('/farmer_dashboard')
def farmer():
    conn = get_db()
    data = conn.execute("SELECT * FROM records").fetchall()
    return render_template("farmer_dashboard.html", data=data)

# RUN
if __name__ == "__main__":
    app.run(debug=True)
