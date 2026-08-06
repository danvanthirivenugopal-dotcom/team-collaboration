import logging
from datetime import datetime, date
from backend.database.db import get_db

logger = logging.getLogger("faceai.report_service")

def get_report_data(
    organization_id: int,
    selected_date: str = None,
    selected_month: int = None,
    selected_year: int = None,
    user_id: int = None,
    status: str = None
) -> list[dict]:
    """
    Retrieve master attendance report data filtering by date, month, year, user, and status.
    Returns a list of matching records.
    """
    try:
        query = """
            SELECT 
                u.id AS user_id,
                u.id AS employee_id,
                u.name,
                u.email,
                u.role,
                u.department,
                a.attendance_date,
                a.check_in_time,
                a.check_out_time,
                a.working_hours,
                a.status AS attendance_status
            FROM users u
            LEFT JOIN attendance a ON u.id = a.user_id
            WHERE u.approval_status = 'Approved' AND u.organization_id = %s
        """
        params = [organization_id]
        
        # Apply filters
        if selected_date:
            query += " AND a.attendance_date = %s"
            params.append(selected_date)
            
        if selected_month:
            query += " AND MONTH(a.attendance_date) = %s"
            params.append(selected_month)
            
        if selected_year:
            query += " AND YEAR(a.attendance_date) = %s"
            params.append(selected_year)
            
        if user_id:
            query += " AND u.id = %s"
            params.append(user_id)
            
        if status:
            if status == "Absent":
                # Special check for Absent status: either status is explicitly Absent or no attendance record exists
                query += " AND (a.status = 'Absent' OR a.id IS NULL)"
            else:
                query += " AND a.status = %s"
                params.append(status)
                
        query += " ORDER BY a.attendance_date DESC, u.name ASC"
        
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                
        # Post-process dates and times for response output
        result = []
        for row in rows:
            # If the filter was for "Absent" and we did LEFT JOIN where attendance_id IS NULL:
            # The attendance_date would be None. We can default it if needed, or represent it.
            att_date = row["attendance_date"]
            att_date_str = att_date.strftime("%Y-%m-%d") if isinstance(att_date, (date, datetime)) else "-"
            
            check_in = row["check_in_time"]
            check_in_str = check_in.strftime("%Y-%m-%d %H:%M:%S") if isinstance(check_in, datetime) else "-"
            
            check_out = row["check_out_time"]
            check_out_str = check_out.strftime("%Y-%m-%d %H:%M:%S") if isinstance(check_out, datetime) else "-"
            
            w_hours = row["working_hours"]
            w_hours_val = float(w_hours) if w_hours is not None else 0.0
            
            # If no attendance record exists, the status is Absent
            status_val = row["attendance_status"] if row["attendance_status"] else "Absent"
            
            result.append({
                "user_id": row["user_id"],
                "employee_id": row["employee_id"],
                "name": row["name"],
                "email": row["email"],
                "role": row["role"],
                "department": row["department"] or "N/A",
                "attendance_date": att_date_str,
                "check_in_time": check_in_str,
                "check_out_time": check_out_str,
                "working_hours": w_hours_val,
                "attendance_status": status_val
            })
            
        return result
    except Exception as e:
        logger.error(f"Failed to generate report data: {e}")
        return []
