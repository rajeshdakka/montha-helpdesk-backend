from flask import Blueprint, request, render_template, redirect
from app.services.db_service import get_db_connection
from app.services.ml_service import predict_priority
from app.utils.auth_decorator import token_required

report_bp = Blueprint("report", __name__)


# -----------------------------
# Submit Complaint (ML Enabled)
# -----------------------------
@report_bp.route("/report", methods=["POST"])
@token_required
def submit_report():
    try:
        name = request.form["name"]
        issue = request.form["issue"]
        location = request.form["location"]
        mobile = request.form["mobile"]

        # 🔥 ML Prediction
        priority, confidence = predict_priority(issue)

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO reports 
            (name, issue, location, status, users_id, mobile, priority, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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


# -----------------------------
# View Reports (User / Admin)
# -----------------------------
@report_bp.route("/reports")
@token_required
def get_reports():
    try:
        user_id = request.user_id
        role = request.role

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
                WHERE users_id=?
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


# -----------------------------
# Report Detail
# -----------------------------
@report_bp.route("/report/<int:report_id>")
@token_required
def report_detail(report_id):
    try:
        db = get_db_connection()
        cursor = db.cursor()

        if request.role == "admin":
            cursor.execute(
                """
                SELECT id, name, issue, location, status, created_at, mobile, assigned_to 
                FROM reports WHERE id=?
                """,
                (report_id,)
            )
        else:
            cursor.execute(
                """
                SELECT id, name, issue, location, status, created_at, mobile, assigned_to 
                FROM reports WHERE id=? AND users_id=?
                """,
                (report_id, request.user_id)
            )

        r = cursor.fetchone()
        cursor.close()
        db.close()

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


# -----------------------------
# Report Form
# -----------------------------
@report_bp.route("/report-form")
def report_form():
    return render_template("report.html")