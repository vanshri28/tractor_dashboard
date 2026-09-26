from flask import Flask, render_template, request, redirect, session, jsonify
import psycopg
import random
import os
from datetime import datetime

try:
    from detect_ocr import detect_number_plate
except Exception:
    detect_number_plate = None

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret123")

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg.connect(DATABASE_URL)


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
            driver_phone VARCHAR(50),
            detected_number VARCHAR(50) DEFAULT 'None',
            entry_no VARCHAR(50) DEFAULT 'None',
            token VARCHAR(50) DEFAULT 'None',
            time VARCHAR(50) DEFAULT 'None',
            result_image_url TEXT DEFAULT 'None'
        )
    """)

    cur.execute("""
        ALTER TABLE entries
        ADD COLUMN IF NOT EXISTS detected_number VARCHAR(50) DEFAULT 'None'
    """)

    cur.execute("""
        ALTER TABLE entries
        ADD COLUMN IF NOT EXISTS entry_no VARCHAR(50) DEFAULT 'None'
    """)

    cur.execute("""
        ALTER TABLE entries
        ADD COLUMN IF NOT EXISTS token VARCHAR(50) DEFAULT 'None'
    """)

    cur.execute("""
        ALTER TABLE entries
        ADD COLUMN IF NOT EXISTS time VARCHAR(50) DEFAULT 'None'
    """)

    cur.execute("""
        ALTER TABLE entries
        ADD COLUMN IF NOT EXISTS result_image_url TEXT DEFAULT 'None'
    """)

    conn.commit()
    cur.close()
    conn.close()


init_db()


def clean_plate(number):
    if number is None:
        return ""

    return (
        str(number)
        .replace(" ", "")
        .replace("-", "")
        .replace(".", "")
        .replace("_", "")
        .upper()
        .strip()
    )


def generate_entry():
    return "E" + str(random.randint(1000, 9999))


def generate_token():
    return "T" + str(random.randint(100, 999))


def current_time():
    return datetime.now().strftime(
        "%d-%m-%Y %I:%M:%S %p"
    )


def is_empty_value(value):
    return (
        value is None
        or str(value).strip() == ""
        or str(value).strip().lower() == "none"
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/admin_login", methods=["POST"])
def admin_login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if username == "admin" and password == "admin123":
        session["admin"] = True
        return redirect("/admin_dashboard")

    return "Invalid Admin Login"


@app.route("/office_login", methods=["POST"])
def office_login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if username == "office" and password == "office123":
        session["office"] = True
        return redirect("/office_dashboard")

    return "Invalid Office Login"


@app.route("/farmer_login", methods=["POST"])
def farmer_login():
    phone = request.form.get("phone", "").strip()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM farmers
        WHERE phone=%s
        """,
        (phone,)
    )

    farmer = cur.fetchone()

    cur.close()
    conn.close()

    if farmer:
        session["farmer"] = phone
        return redirect("/farmer_dashboard")

    return "Not Registered"


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                """
                INSERT INTO farmers
                (name, phone, address)
                VALUES (%s, %s, %s)
                """,
                (name, phone, address)
            )

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


@app.route("/get_farmer/<phone>")
def get_farmer(phone):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT name, address
        FROM farmers
        WHERE phone=%s
        """,
        (phone,)
    )

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


@app.route("/admin_dashboard", methods=["GET", "POST"])
def admin_dashboard():
    if "admin" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        tractor = clean_plate(
            request.form.get("tractor", "")
        )

        if not tractor:
            cur.close()
            conn.close()
            return "Tractor number is required"

        farmer_phone = request.form.get("phone", "").strip()
        farmer_name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()
        trip = request.form.get("trip", "").strip()
        driver_name = request.form.get("driver_name", "").strip()
        driver_phone = request.form.get("driver_phone", "").strip()

        cur.execute(
            """
            SELECT id
            FROM entries
            WHERE tractor=%s
            AND (
                entry_no IS NULL
                OR entry_no=''
                OR entry_no='None'
            )
            AND (
                token IS NULL
                OR token=''
                OR token='None'
            )
            LIMIT 1
            """,
            (tractor,)
        )

        existing = cur.fetchone()

        if existing:
            cur.close()
            conn.close()
            return (
                f"Tractor {tractor} is already registered "
                f"and waiting for detection."
            )

        cur.execute(
            """
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
            """,
            (
                farmer_phone,
                farmer_name,
                address,
                tractor,
                trip,
                driver_name,
                driver_phone,
                "None",
                "None",
                "None",
                "None",
                "None"
            )
        )

        conn.commit()

    cur.execute(
        """
        SELECT *
        FROM entries
        ORDER BY id DESC
        """
    )

    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "admin_dashboard.html",
        data=data
    )


@app.route("/delete_registration/<int:entry_id>", methods=["POST"])
def delete_registration(entry_id):
    if "admin" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            DELETE FROM entries
            WHERE id=%s
            """,
            (entry_id,)
        )

        conn.commit()

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return f"Delete Error: {e}"

    cur.close()
    conn.close()

    return redirect("/admin_dashboard")


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

    cur.execute(
        """
        SELECT
            id,
            tractor,
            entry_no,
            token
        FROM entries
        WHERE
            (
                entry_no IS NULL
                OR entry_no=''
                OR entry_no='None'
            )
            AND
            (
                token IS NULL
                OR token=''
                OR token='None'
            )
        ORDER BY id DESC
        """
    )

    rows = cur.fetchall()

    matched_row = None

    for row in rows:
        tractor_number = clean_plate(row[1])

        if tractor_number and tractor_number == detected_number:
            matched_row = row
            break

    if not matched_row:
        cur.close()
        conn.close()

        return jsonify({
            "status": "not matched",
            "plate": detected_number
        })

    entry_id = matched_row[0]
    entry_no = generate_entry()
    token = generate_token()
    entry_time = current_time()

    cur.execute(
        """
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
            entry_no,
            token,
            entry_time,
            entry_id
        )
    )

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "status": "matched",
        "plate": detected_number,
        "entry": entry_no,
        "token": token,
        "time": entry_time
    })


@app.route("/update_plate", methods=["POST"])
def update_plate():
    conn = None
    cur = None

    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "status": "error",
                "message": "No JSON data received"
            }), 400

        plate = clean_plate(
            data.get("plate", "")
        )

        image_url = str(
            data.get("image_url", "")
        ).strip()

        if image_url.lower() == "none":
            image_url = ""

        if not plate:
            return jsonify({
                "status": "error",
                "message": "Empty plate number"
            }), 400

        conn = get_connection()
        cur = conn.cursor()

        print("=" * 60)
        print("OCR PLATE       :", plate)
        print("CLOUDINARY IMAGE:", image_url)
        print("=" * 60)

        cur.execute(
            """
            SELECT
                id,
                tractor,
                entry_no,
                token
            FROM entries
            WHERE
                (
                    entry_no IS NULL
                    OR entry_no=''
                    OR entry_no='None'
                )
                AND
                (
                    token IS NULL
                    OR token=''
                    OR token='None'
                )
            ORDER BY id DESC
            """
        )

        rows = cur.fetchall()

        matched_row = None

        for row in rows:
            entry_id = row[0]
            tractor_number = clean_plate(row[1])

            print(
                "CHECK:",
                entry_id,
                tractor_number,
                "VS",
                plate
            )

            if (
                tractor_number
                and tractor_number == plate
            ):
                matched_row = row
                break

        if matched_row is None:
            conn.rollback()

            print("NO MATCH FOUND")

            return jsonify({
                "status": "not matched",
                "plate": plate,
                "image_url": image_url,
                "message": "Registered tractor not found"
            })

        entry_id = matched_row[0]
        tractor = clean_plate(matched_row[1])
        existing_entry = matched_row[2]
        existing_token = matched_row[3]

        if is_empty_value(existing_entry):
            entry_no = generate_entry()
        else:
            entry_no = str(existing_entry)

        if is_empty_value(existing_token):
            token = generate_token()
        else:
            token = str(existing_token)

        entry_time = current_time()

        cur.execute(
            """
            UPDATE entries
            SET
                detected_number=%s,
                entry_no=%s,
                token=%s,
                time=%s,
                result_image_url=%s
            WHERE id=%s
            """,
            (
                plate,
                entry_no,
                token,
                entry_time,
                image_url if image_url else "None",
                entry_id
            )
        )

        conn.commit()

        print("=" * 60)
        print("MATCH SUCCESS")
        print("ENTRY ID :", entry_id)
        print("TRACTOR  :", tractor)
        print("PLATE    :", plate)
        print("ENTRY    :", entry_no)
        print("TOKEN    :", token)
        print("TIME     :", entry_time)
        print("IMAGE    :", image_url)
        print("=" * 60)

        return jsonify({
            "status": "matched",
            "plate": plate,
            "tractor": tractor,
            "entry": entry_no,
            "token": token,
            "time": entry_time,
            "image_url": image_url
        })

    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass

        print("UPDATE PLATE ERROR:", e)

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass

        if conn:
            try:
                conn.close()
            except Exception:
                pass


@app.route("/office_dashboard")
def office_dashboard():
    if "office" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
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
        FROM entries
        WHERE
            detected_number IS NOT NULL
            AND detected_number != ''
            AND detected_number != 'None'
            AND entry_no IS NOT NULL
            AND entry_no != ''
            AND entry_no != 'None'
            AND token IS NOT NULL
            AND token != ''
            AND token != 'None'
        ORDER BY id DESC
        """
    )

    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "office_dashboard.html",
        data=data
    )


@app.route("/farmer_dashboard")
def farmer_dashboard():
    if "farmer" not in session:
        return redirect("/")

    phone = session["farmer"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM entries
        WHERE farmer_phone=%s
        ORDER BY id DESC
        """,
        (phone,)
    )

    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "farmer_dashboard.html",
        data=data
    )


@app.route("/db_test")
def db_test():
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT 1")
        cur.fetchone()

        cur.close()
        conn.close()

        return "Database Connected Successfully"

    except Exception as e:
        return str(e)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=False
    )
