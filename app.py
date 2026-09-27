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
        .upper()
        .replace(" ", "")
        .replace("-", "")
        .replace(".", "")
        .replace("_", "")
        .replace("/", "")
        .strip()
    )


def is_empty_value(value):
    if value is None:
        return True

    value = str(value).strip().lower()

    return value == "" or value == "none"


def current_time():
    return datetime.now().strftime(
        "%d-%m-%Y %I:%M:%S %p"
    )


def generate_entry(cur):
    for _ in range(200):
        value = "E" + str(random.randint(1000, 9999))

        cur.execute(
            """
            SELECT 1
            FROM entries
            WHERE entry_no=%s
            LIMIT 1
            """,
            (value,)
        )

        if cur.fetchone() is None:
            return value

    return "E" + str(random.randint(10000, 99999))


def generate_token(cur):
    for _ in range(200):
        value = "T" + str(random.randint(100, 999))

        cur.execute(
            """
            SELECT 1
            FROM entries
            WHERE token=%s
            LIMIT 1
            """,
            (value,)
        )

        if cur.fetchone() is None:
            return value

    return "T" + str(random.randint(1000, 9999))


def find_registered_tractor(cur, plate):
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
        ORDER BY id ASC
        """
    )

    rows = cur.fetchall()

    for row in rows:
        registered_tractor = clean_plate(row[4])

        print(
            "CHECK:",
            "DB =", registered_tractor,
            "OCR =", plate
        )

        if (
            registered_tractor
            and registered_tractor == plate
        ):
            return row

    return None


def process_plate(plate, image_url):
    plate = clean_plate(plate)

    image_url = str(
        image_url or ""
    ).strip()

    if image_url.lower() == "none":
        image_url = ""

    if not plate:
        return {
            "status": "error",
            "message": "OCR plate number is empty"
        }, 400

    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        print()
        print("=" * 70)
        print("NEW RASPBERRY PI DETECTION RECEIVED")
        print("OCR NUMBER :", plate)
        print("IMAGE URL  :", image_url)
        print("=" * 70)

        matched_row = find_registered_tractor(
            cur,
            plate
        )

        if matched_row is None:
            conn.rollback()

            print("NO REGISTERED TRACTOR MATCH")
            print("OCR NUMBER:", plate)
            print("=" * 70)

            return {
                "status": "not matched",
                "plate": plate,
                "image_url": image_url,
                "message": "No pending registered tractor matched this OCR number"
            }, 200

        entry_id = matched_row[0]
        tractor = clean_plate(matched_row[4])
        existing_entry = matched_row[9]
        existing_token = matched_row[10]

        if not is_empty_value(existing_entry):
            conn.rollback()

            return {
                "status": "already processed",
                "plate": plate,
                "entry": str(existing_entry),
                "token": str(existing_token)
            }, 200

        if not is_empty_value(existing_token):
            conn.rollback()

            return {
                "status": "already processed",
                "plate": plate,
                "entry": str(existing_entry),
                "token": str(existing_token)
            }, 200

        entry_no = generate_entry(cur)
        token = generate_token(cur)
        entry_time = current_time()

        saved_image_url = (
            image_url
            if image_url
            else "None"
        )

        cur.execute(
            """
            UPDATE entries
            SET
                detected_number=%s,
                entry_no=%s,
                token=%s,
                time=%s,
                result_image_url=%s
            WHERE
                id=%s
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
            """,
            (
                plate,
                entry_no,
                token,
                entry_time,
                saved_image_url,
                entry_id
            )
        )

        if cur.rowcount != 1:
            conn.rollback()

            return {
                "status": "already processed",
                "plate": plate,
                "message": "Registration was processed by another request"
            }, 200

        conn.commit()

        print("=" * 70)
        print("MATCH SUCCESS")
        print("DATABASE ID :", entry_id)
        print("TRACTOR     :", tractor)
        print("OCR NUMBER  :", plate)
        print("ENTRY       :", entry_no)
        print("TOKEN       :", token)
        print("TIME        :", entry_time)
        print("IMAGE URL   :", saved_image_url)
        print("DATABASE UPDATED SUCCESSFULLY")
        print("=" * 70)

        return {
            "status": "matched",
            "entry_id": entry_id,
            "plate": plate,
            "tractor": tractor,
            "entry": entry_no,
            "token": token,
            "time": entry_time,
            "image_url": image_url,
            "message": "OCR matched registered tractor and entry generated"
        }, 200

    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass

        print("=" * 70)
        print("PROCESS PLATE ERROR:")
        print(e)
        print("=" * 70)

        return {
            "status": "error",
            "message": str(e)
        }, 500

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


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/admin_login", methods=["POST"])
def admin_login():
    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    if (
        username == "admin"
        and password == "admin123"
    ):
        session["admin"] = True
        return redirect("/admin_dashboard")

    return "Invalid Admin Login"


@app.route("/office_login", methods=["POST"])
def office_login():
    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    if (
        username == "office"
        and password == "office123"
    ):
        session["office"] = True
        return redirect("/office_dashboard")

    return "Invalid Office Login"


@app.route("/farmer_login", methods=["POST"])
def farmer_login():
    phone = request.form.get(
        "phone",
        ""
    ).strip()

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
        name = request.form.get(
            "name",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                """
                INSERT INTO farmers
                (name, phone, address)
                VALUES (%s, %s, %s)
                """,
                (
                    name,
                    phone,
                    address
                )
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

    return render_template(
        "register.html"
    )


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


@app.route(
    "/admin_dashboard",
    methods=["GET", "POST"]
)
def admin_dashboard():
    if "admin" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":

        tractor = clean_plate(
            request.form.get(
                "tractor",
                ""
            )
        )

        if not tractor:
            cur.close()
            conn.close()

            return "Tractor number is required"

        farmer_phone = request.form.get(
            "phone",
            ""
        ).strip()

        farmer_name = request.form.get(
            "name",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        trip = request.form.get(
            "trip",
            ""
        ).strip()

        driver_name = request.form.get(
            "driver_name",
            ""
        ).strip()

        driver_phone = request.form.get(
            "driver_phone",
            ""
        ).strip()

        cur.execute(
            """
            SELECT id
            FROM entries
            WHERE
                tractor=%s
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
                f"and waiting for Raspberry Pi detection."
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
            (
                %s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s
            )
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


@app.route(
    "/delete_registration/<int:entry_id>",
    methods=["POST"]
)
def delete_registration(entry_id):
    if "admin" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            DELETE FROM entries
            WHERE
                id=%s
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


@app.route(
    "/update_plate",
    methods=["POST"]
)
def update_plate():
    try:
        data = request.get_json(
            silent=True
        )

        if not data:
            data = request.form.to_dict()

        plate = clean_plate(
            data.get(
                "plate",
                ""
            )
        )

        image_url = str(
            data.get(
                "image_url",
                ""
            )
        ).strip()

        if image_url.lower() == "none":
            image_url = ""

        print()
        print("=" * 70)
        print("POST /update_plate RECEIVED")
        print("OCR NUMBER :", plate)
        print("IMAGE URL  :", image_url)
        print("=" * 70)

        result, status_code = process_plate(
            plate,
            image_url
        )

        return jsonify(result), status_code

    except Exception as e:
        print(
            "UPDATE PLATE REQUEST ERROR:",
            e
        )

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/detect")
def detect():
    if detect_number_plate is None:
        return jsonify({
            "status": "error",
            "message": "OCR function not available"
        }), 500

    try:
        detected_number = detect_number_plate()

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    result, status_code = process_plate(
        detected_number,
        ""
    )

    return jsonify(result), status_code


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
