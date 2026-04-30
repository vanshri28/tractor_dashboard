from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import random
import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect("database.db")
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

# ---------- ROUTES ----------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/admin_login", methods=["POST"])
def admin_login():
    if request.form["username"] == "admin" and request.form["password"] == "admin123":
        session["admin"] = True
        return redirect("/admin_dashboard")
    return "Invalid Admin Login"

@app.route("/office_login", methods=["POST"])
def office_login():
    if request.form["username"] == "office" and request.form["password"] == "office123":
        session["office"] = True
        return redirect("/office_dashboard")
    return "Invalid Office Login"

@app.route("/farmer_login", methods=["POST"])
def farmer_login():
    phone = request.form["phone"]

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM farmers WHERE phone=?", (phone,))
    farmer = cur.fetchone()
    conn.close()

    if farmer:
        session["farmer"] = phone
        return redirect("/farmer_dashboard")

    return "Not Registered"

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        address = request.form["address"]

        if len(phone) != 10 or not phone.isdigit():
            return "Invalid Phone Number"

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        try:
            cur.execute("INSERT INTO farmers (name, phone, address) VALUES (?,?,?)",
                        (name, phone, address))
            conn.commit()
        except:
            return "Phone already exists"

        conn.close()
        return redirect("/")

    return render_template("register.html")

@app.route("/get_farmer/<phone>")
def get_farmer(phone):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT name,address FROM farmers WHERE phone=?", (phone,))
    data = cur.fetchone()
    conn.close()

    if data:
        return jsonify({"name": data[0], "address": data[1]})
    return jsonify({"error":"not found"})

@app.route("/admin_dashboard", methods=["GET","POST"])
def admin_dashboard():
    if "admin" not in session:
        return redirect("/")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    if request.method == "POST":
        entry_no = generate_entry()
        token = generate_token()
        time = current_time()

        cur.execute("""
        INSERT INTO entries (farmer_phone, farmer_name, address, tractor, trip, entry_no, token, time)
        VALUES (?,?,?,?,?,?,?,?)
        """, (
            request.form["phone"],
            request.form["name"],
            request.form["address"],
            request.form["tractor"],
            request.form["trip"],
            entry_no,
            token,
            time
        ))
        conn.commit()

    cur.execute("SELECT * FROM entries")
    data = cur.fetchall()
    conn.close()

    return render_template("admin_dashboard.html", data=data)

@app.route("/farmer_dashboard")
def farmer_dashboard():
    if "farmer" not in session:
        return redirect("/")

    phone = session["farmer"]

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM entries WHERE farmer_phone=?", (phone,))
    data = cur.fetchall()
    conn.close()

    return render_template("farmer_dashboard.html", data=data)

@app.route("/office_dashboard")
def office_dashboard():
    if "office" not in session:
        return redirect("/")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM entries")
    data = cur.fetchall()
    conn.close()

    return render_template("office_dashboard.html", data=data)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
