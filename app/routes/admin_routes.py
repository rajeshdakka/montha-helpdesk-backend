from flask import Blueprint, request, redirect
from app.services.db_service import get_db_connection
from app.utils.auth_decorator import token_required

admin_bp = Blueprint("admin", __name__)


# ---------------------------------
# Assign Report to Officer
# ---------------------------------
@admin_bp.route("/report/<int:report_id>/assign", methods=["POST"])
@token_required
def assign_report(report_id):

    if request.role != "admin":
        return {"status": "error", "message": "Admin only"}, 403

    try:
        officer = request.form["assigned_to"]

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            "UPDATE reports SET assigned_to=? WHERE id=?",
            (officer, report_id)
        )

        db.commit()
        cursor.close()
        db.close()

        return redirect(f"/report/{report_id}")

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500


# ---------------------------------
# Update Report Status
# ---------------------------------
@admin_bp.route("/report/<int:report_id>/status", methods=["POST"])
@token_required
def update_status(report_id):

    if request.role != "admin":
        return {"status": "error", "message": "Admin only"}, 403

    try:
        new_status = request.form["status"]

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            "UPDATE reports SET status=? WHERE id=?",
            (new_status, report_id)
        )

        db.commit()
        cursor.close()
        db.close()

        return redirect(f"/report/{report_id}")

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500


# ---------------------------------
# View Pending Reports (Admin)
# ---------------------------------
@admin_bp.route("/admin/reports/pending", methods=["GET"])
@token_required
def admin_pending_reports():

    if request.role != "admin":
        return {"status": "error", "message": "Admin access only"}, 403

    try:
        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT id, name, issue, location, status, created_at 
            FROM reports 
            WHERE status='pending'
            """
        )

        rows = cursor.fetchall()

        cursor.close()
        db.close()

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