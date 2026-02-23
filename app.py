import jwt
import datetime
from flask import Flask, request, redirect
import mysql.connector
from flask import render_template
from dotenv import load_dotenv
import os
from flask_bcrypt import Bcrypt
from functools import wraps
import pickle

model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))



app = Flask(__name__)

load_dotenv()

DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
SECRET_KEY = os.getenv('SECRET_KEY')

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=3306,
        use_pure=True
    )


app.config['SECRET_KEY'] = SECRET_KEY

bcrypt = Bcrypt(app)


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get("token")

        if not token:
            return redirect("/login-form")

        try:
            decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.user_id = decoded["user_id"]
            request.role = decoded["role"]
        except:
            return redirect("/login-form")

        return f(*args, **kwargs)
    return decorated



@app.route("/")
def home():
    token = request.cookies.get("token")
    logged_in = False

    if token:
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            logged_in = True
        except:
            logged_in = False

    return render_template("home.html", logged_in=logged_in)




@app.route("/register", methods=["POST"])
def register():
    try:
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form.get("role" , "user")
        mobile = request.form["mobile"]

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role, mobile) VALUES (%s, %s, %s, %s,%s)",
            (name, email, hashed_pw, role, mobile)
        )
        db.commit()
        cursor.close()
        db.close()

        return {"status": "success", "message": "User registered successfully"}

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route("/register-form")
def register_form():
    return render_template("register.html")


from flask import make_response, redirect

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        return "Email and password required", 400
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        "SELECT id, password_hash, role FROM users WHERE email=%s",
        (email,)
    )
    result = cursor.fetchone()

    if result is None:
        return "User not found", 404

    user_id, stored_hash, role = result

    if not bcrypt.check_password_hash(stored_hash, password):
        return "Invalid password", 401
    
    cursor.close()
    db.close()
    token = jwt.encode(
        {
            "user_id": user_id,
            "role": role,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        },
        SECRET_KEY,
        algorithm="HS256"
    )

    # 🔴 IMPORTANT: PyJWT may return bytes
    if isinstance(token, bytes):
        token = token.decode("utf-8")

    resp = make_response(redirect("/reports"))
    resp.set_cookie(
        "token",
        token,
        httponly=True,
        samesite="Lax",
        path="/"
    )
    return resp

@app.route("/login-form")
def login_form():
    return render_template("login.html")



@app.route("/report", methods=["POST"])
@token_required
def report():
    try:
        name = request.form["name"]
        issue = request.form["issue"]
        location = request.form["location"]
        mobile = request.form["mobile"]

        # 🔥 ML Prediction
        text_vector = vectorizer.transform([issue])
        prediction = model.predict(text_vector)
        priority = prediction[0]

        prob = model.predict_proba(text_vector)
        confidence = float(max(prob[0]))

        # ✅ Use helper function
        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO reports 
            (name, issue, location, status, users_id, mobile, priority, confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (name, issue, location, "pending", request.user_id, mobile, priority, confidence)
        )

        db.commit()

        cursor.close()
        db.close()

        return {
            "status": "success",
            "priority": priority,
            "confidence": round(confidence, 2)
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500



@app.route("/reports")
@token_required
def get_reports():
    try:
        user_id = request.user_id
        role = request.role

        # ✅ Open fresh connection
        db = get_db_connection()
        cursor = db.cursor()

        if role == "admin":
            cursor.execute("""
                SELECT id, name, issue, location, created_at, mobile, priority, confidence
                FROM reports
            """)
        else:
            cursor.execute("""
                SELECT id, name, issue, location, created_at, mobile, priority, confidence
                FROM reports
                WHERE users_id=%s
            """, (user_id,))

        rows = cursor.fetchall()

        cursor.close()
        db.close()

        reports = []
        for row in rows:
            reports.append({
                "id": row[0],
                "name": row[1],
                "issue": row[2],
                "location": row[3],
                "created_at": str(row[4]),
                "mobile": row[5],
                "priority": row[6],
                "confidence": round(row[7], 2) if row[7] else None
            })

        return render_template("reports.html", reports=reports)

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500


@app.route("/report/<int:report_id>")
@token_required
def report_detail(report_id):
    try:
        # Admin can view any report
        if request.role == "admin":
            cursor.execute(
                "SELECT id, name, issue, location, status, created_at, mobile, assigned_to FROM reports WHERE id=%s",
                (report_id,)
            )
        else:
            # User can view only their report
            cursor.execute(
                "SELECT id, name, issue, location, status, created_at, mobile, assigned_to FROM reports WHERE id=%s AND users_id=%s",
                (report_id, request.user_id)
            )

        r = cursor.fetchone()

        if not r:
            return "Report not found", 404

        report = {
            "id": r[0],
            "name": r[1],
            "issue": r[2],
            "location": r[3],
            "status": r[4],
            "created_at": str(r[5]),
            "mobile": r[6],
            "assigned_to": r[7]

        }

        return render_template("report_detail.html", report=report)

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500
    
    
@app.route("/report/<int:report_id>/assign", methods=["POST"])
@token_required
def assign_report(report_id):
    if request.role != "admin":
        return {"status": "error", "message": "Admin only"}, 403

    officer = request.form["assigned_to"]

    cursor.execute(
        "UPDATE reports SET assigned_to=%s WHERE id=%s",
        (officer, report_id)
    )
    db.commit()

    return redirect(f"/report/{report_id}")




@app.route("/admin/reports/pending", methods=["GET"])
@token_required
def admin_pending_reports():
    try:
        if request.role != "admin":
            return {"status": "error", "message": "Admin access only"}, 403

        cursor.execute(
            "SELECT id, name, issue, location, status, created_at FROM reports WHERE status='pending'"
        )
        rows = cursor.fetchall()

        reports = []
        for r in rows:
            reports.append({
                "id": r[0],
                "name": r[1],
                "issue": r[2],
                "location": r[3],
                "status": r[4],
                "created_at": str(r[5])
            })

        return reports

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

    

@app.route("/report/<int:report_id>/status", methods=["POST"])
@token_required
def update_status(report_id):
    try:
        if request.role != "admin":
            return {"status": "error", "message": "Admin only"}, 403

        new_status = request.form["status"]

        cursor.execute(
            "UPDATE reports SET status=%s WHERE id=%s",
            (new_status, report_id)
        )
        db.commit()

        return redirect(f"/report/{report_id}")

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500





@app.route("/report-form")
def report_form():
    return render_template("report.html")

@app.route("/logout")
def logout():
    resp = make_response(redirect("/login-form"))
    resp.delete_cookie("token", path="/")
    return resp


if __name__ == "__main__":
    app.run(debug=True)
