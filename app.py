from flask import Flask, request
import mysql.connector
from flask import render_template

app = Flask(__name__)

db = mysql.connector.connect(
    host="localhost",
    user="montha_user",
    password="montha123",
    database="montha_db"
)


cursor = db.cursor()

@app.route("/")
def home():
    return "Montha Help Desk Backend Running 🚨"

@app.route("/report", methods=["POST"])
def report():
    try:
        name = request.form["name"]
        issue = request.form["issue"]
        location = request.form["location"]

        cursor.execute(
            "INSERT INTO reports (name, issue, location) VALUES (%s, %s, %s)",
            (name, issue, location)
        )
        db.commit()

        return {"status": "success"}

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500


@app.route("/reports", methods=["GET"])
def get_reports():
    cursor.execute("SELECT id, name, issue, location, created_at FROM reports")
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


@app.route("/report-form")
def report_form():
    return render_template("report.html")



if __name__ == "__main__":
    app.run(debug=True)
