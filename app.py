import jwt
import datetime
from flask import Flask, request
import mysql.connector
from flask import render_template
from dotenv import load_dotenv
import os
from flask_bcrypt import Bcrypt
from functools import wraps



app = Flask(__name__)

load_dotenv()

DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
SECRET_KEY = os.getenv('SECRET_KEY')

app.config['SECRET_KEY'] = SECRET_KEY

bcrypt = Bcrypt(app)


db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    port=3306,
    use_pure=True
)



cursor = db.cursor()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            return {"status": "error", "message": "Token missing"}, 401

        try:
            decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.user_id = decoded["user_id"]
        except:
            return {"status": "error", "message": "Invalid or expired token"}, 401

        return f(*args, **kwargs)
    return decorated


@app.route("/")
def home():
    return "Montha Help Desk Backend Running 🚨"


@app.route("/register", methods=["POST"])
def register():
    try:
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form.get("role" , "user")

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            (name, email, hashed_pw, role)
        )
        db.commit()

        return {"status": "success", "message": "User registered successfully"}

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route("/register-form")
def register_form():
    return render_template("register.html")


@app.route("/login", methods=["POST"])
def login():
    try:
        email = request.form["email"]
        password = request.form["password"]

        
        cursor.execute("SELECT id, password_hash, role FROM users WHERE email=%s", (email,))
        result = cursor.fetchone()

        if result is None:
            return {"status": "error", "message": "User not found"}, 404

        user_id = result[0]
        stored_hash = result[1]
        role = result[2]

        
        if not bcrypt.check_password_hash(stored_hash, password):
            return {"status": "error", "message": "Invalid password"}, 401

        
        token = jwt.encode(
            {"user_id": user_id, "role":role, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)},
            SECRET_KEY,
            algorithm="HS256"
        )

        return {"status": "success", "token": token}

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500
    
@app.route("/login-form")
def login_form():
    return render_template("login.html")



@app.route("/report", methods=["POST"])
def report():
    try:
        name = request.form["name"]
        issue = request.form["issue"]
        location = request.form["location"]

        cursor.execute(
            "INSERT INTO reports (name, issue, location, user_id) VALUES (%s, %s, %s, %s)",
            (name, issue, location, request.user_id)
        )
        db.commit()

        return {"status": "success"}

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500


@app.route("/reports", methods=["GET"])
@token_required
def get_reports():
    try:
        user_id = request.user_id  # from decoded token

        role = None
        token = request.headers.get('Authorization')
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        role = decoded["role"]

        if role == "admin":
            cursor.execute("SELECT id, name, issue, location, created_at FROM reports")
        else:
            cursor.execute("SELECT id, name, issue, location, created_at FROM reports WHERE users_id=%s", (user_id,))

        rows = cursor.fetchall()
        reports = []
        for row in rows:
            reports.append({
                "id": row[0],
                "name": row[1],
                "issue": row[2],
                "location": row[3],
                "created_at": str(row[4])
            })

        return reports

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500



@app.route("/report-form")
def report_form():
    return render_template("report.html")



if __name__ == "__main__":
    app.run(debug=True)
