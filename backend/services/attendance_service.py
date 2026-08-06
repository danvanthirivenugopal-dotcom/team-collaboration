import logging
from datetime import datetime, timedelta
from backend.database.db import get_db

logger = logging.getLogger("faceai.attendance_service")


def parse_hhmm_to_timedelta(t_str: str) -> timedelta:
    """Parse 'HH:MM' string to a timedelta object."""
    try:
        parts = str(t_str).split(":")
        h, m = int(parts[0]), int(parts[1])
        return timedelta(hours=h, minutes=m)
    except Exception:
        return timedelta(hours=9)


def calculate_working_hours(check_in: datetime, check_out: datetime) -> float:
    """Calculate working hours between check-in and check-out."""
    if not check_in or not check_out:
        return 0.0

    try:
        delta = check_out - check_in
        hours = delta.total_seconds() / 3600.0
        return round(max(0.0, hours), 2)
    except Exception as e:
        logger.error(f"Error calculating working hours: {e}")
        return 0.0


def determine_checkin_status(check_in_dt: datetime, settings: dict) -> str:
    """Determine Present, Late, or Half Day."""
    try:
        now_time_td = timedelta(
            hours=check_in_dt.hour,
            minutes=check_in_dt.minute,
            seconds=check_in_dt.second
        )

        start_str = settings.get("start_time", "09:00")
        end_str = settings.get("end_time", "18:00")
        grace = int(settings.get("grace_period_minutes", 30))

        start_td = parse_hhmm_to_timedelta(start_str)
        end_td = parse_hhmm_to_timedelta(end_str)
        grace_td = timedelta(minutes=grace)

        midpoint_td = start_td + (end_td - start_td) / 2.0

        if now_time_td >= midpoint_td:
            return "Half Day"

        if now_time_td > (start_td + grace_td):
            return "Late"

        return "Present"

    except Exception as e:
        logger.error(f"Error determining check-in status: {e}")
        return "Present"


def evaluate_checkout_status(
    check_in_dt: datetime,
    check_out_dt: datetime,
    current_status: str
) -> tuple[float, str]:
    """Calculate working hours and final status."""
    hours = calculate_working_hours(check_in_dt, check_out_dt)

    final_status = current_status
    if hours < 4.0:
        final_status = "Half Day"

    return hours, final_status


def get_today_attendance(user_id: int, organization_id: int = 1):
    current_date = datetime.now().date()

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM attendance
                WHERE user_id = %s AND attendance_date = %s AND organization_id = %s
                LIMIT 1
                """,
                (user_id, current_date, organization_id)
            )
            return cursor.fetchone()


def get_attendance_settings(organization_id: int = 1) -> dict:
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT start_time, end_time, grace_period_minutes
                    FROM attendance_settings
                    ORDER BY id DESC
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()

        if row:
            def td_to_str(val):
                if val is None:
                    return "09:00"
                if isinstance(val, str):
                    return val
                total_seconds = int(val.total_seconds())
                h = total_seconds // 3600
                m = (total_seconds % 3600) // 60
                return f"{h:02d}:{m:02d}"

            return {
                "start_time": td_to_str(row["start_time"]),
                "end_time": td_to_str(row["end_time"]),
                "grace_period_minutes": row["grace_period_minutes"]
            }

    except Exception as e:
        logger.warning(f"Using default attendance settings: {e}")

    return {
        "start_time": "09:00",
        "end_time": "18:00",
        "grace_period_minutes": 30
    }


def mark_check_in(
    user_id: int,
    similarity: float = 1.0
) -> dict:
    current_date = datetime.now().date()
    now_dt = datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    settings = get_attendance_settings(organization_id)
    attendance_status = determine_checkin_status(now_dt, settings)
    is_half_day = attendance_status == "Half Day"

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO attendance (
                    user_id,
                    attendance_date,
                    check_in_time,
                    status,
                    image_path,
                    confidence,
                    half_day,
                    attendance_status
                )
                VALUES (%s, %s, %s, %s, NULL, %s, %s, %s)
                """,
                (
                    user_id,
                    current_date,
                    now_str,
                    attendance_status,
                    float(similarity),
                    is_half_day,
                    attendance_status
                )
            )

            cursor.execute(
                """
                INSERT INTO attendance_logs (user_id, action, image_path)
                VALUES (%s, %s, NULL)
                """,
                (
                    user_id,
                    f"Check-In ({attendance_status}) from Allowed Location"
                )
            )

    return {
        "status": "ok",
        "message": "Check-in marked successfully.",
        "attendance_status": attendance_status
    }


def mark_check_out(
    user_id: int
) -> dict:
    from backend.services import audit_service

    current_date = datetime.now().date()
    now_dt = datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT attendance_id, check_in_time, status
                FROM attendance
                WHERE user_id = %s
                  AND attendance_date = %s
                  AND organization_id = %s
                  AND check_out_time IS NULL
                LIMIT 1
                """,
                (user_id, current_date, organization_id)
            )
            record = cursor.fetchone()

            if not record:
                raise Exception("No check-in record found to sign out.")

            check_in_dt = record["check_in_time"]
            current_status = record["status"]

            hours, final_status = evaluate_checkout_status(
                check_in_dt,
                now_dt,
                current_status
            )

            cursor.execute(
                """
                UPDATE attendance
                SET check_out_time = %s,
                    working_hours = %s,
                    status = %s,
                    attendance_status = %s
                WHERE attendance_id = %s
                """,
                (
                    now_str,
                    hours,
                    final_status,
                    final_status,
                    record["attendance_id"]
                )
            )

            cursor.execute(
                """
                INSERT INTO attendance_logs (user_id, action)
                VALUES (%s, %s)
                """,
                (
                    user_id,
                    f"Check-Out (Hours worked: {hours:.2f}, Status: {final_status}) from Allowed Location"
                )
            )

    return {
        "status": "checked_out",
        "message": "Checkout marked successfully.",
        "working_hours": hours,
        "final_status": final_status
    }


def handle_face_scan_result(user_id: int, organization_id: int = 1) -> str:
    record = get_today_attendance(user_id, organization_id)

    if not record:
        mark_check_in(user_id=user_id, similarity=1.0)
        return "CHECK_IN_MARKED"

    if record["check_out_time"] is None:
        return "ASK_LEAVE_CONFIRMATION"

    return "ALREADY_CHECKED_OUT"


def handle_biometric_attendance(
    user_id: int,
    method: str
) -> dict:
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT name FROM users WHERE id = %s",
                (user_id,)
            )
            user_row = cursor.fetchone()

    user_name = user_row["name"] if user_row else "User"

    record = get_today_attendance(user_id)

    if not record:
        settings = get_attendance_settings(organization_id)
        now_dt = datetime.now()
        now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        current_date = now_dt.date()

        attendance_status = determine_checkin_status(now_dt, settings)
        is_half_day = attendance_status == "Half Day"

        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT attendance_id
                    FROM attendance
                    WHERE user_id = %s AND attendance_date = %s
                    LIMIT 1
                    """,
                    (user_id, current_date, organization_id)
                )

                if cursor.fetchone():
                    return {
                        "status": "already_completed",
                        "message": "Today's attendance is already completed.",
                        "user_id": user_id,
                        "method": method,
                        "user_name": user_name
                    }

                try:
                    cursor.execute(
                        """
                        INSERT INTO attendance (
                            user_id,
                            attendance_date,
                            check_in_time,
                            status,
                            image_path,
                            confidence,
                            half_day,
                            attendance_status,
                            attendance_method
                        )
                        VALUES (%s, %s, %s, %s, NULL, 1.0, %s, %s, %s)
                        """,
                        (
                            user_id,
                            current_date,
                            now_str,
                            attendance_status,
                            is_half_day,
                            attendance_status,
                            method
                        )
                    )

                    cursor.execute(
                        """
                        INSERT INTO attendance_logs (user_id, action)
                        VALUES (%s, %s)
                        """,
                        (
                            user_id,
                            f"Check-In via {method} ({attendance_status}) from Allowed Location"
                        )
                    )

                except Exception as insert_err:
                    if getattr(insert_err, "args", (None,))[0] != 1062:
                        raise

                    record = get_today_attendance(user_id, organization_id)

                    if record and record["check_out_time"] is None:
                        existing_method = record.get("attendance_method") or "face"
                        warning = None

                        if existing_method != method:
                            if existing_method == "face":
                                warning = f"{user_name}'s attendance is already marked using face scanner."
                            else:
                                warning = f"{user_name}'s attendance is marked with your fingerprint."

                        return {
                            "status": "ask_checkout",
                            "message": f"{user_name}, Are you leave now?",
                            "user_id": user_id,
                            "method": method,
                            "warning": warning,
                            "user_name": user_name
                        }

                    return {
                        "status": "already_completed",
                        "message": f"{user_name}, today's attendance is already completed.",
                        "user_id": user_id,
                        "method": method,
                        "user_name": user_name
                    }

        return {
            "status": "checked_in",
            "message": f"{user_name}, attendance successfully marked.",
            "user_id": user_id,
            "method": method,
            "attendance_status": attendance_status,
            "user_name": user_name
        }

    if record["check_out_time"] is None:
        existing_method = record.get("attendance_method") or "face"
        warning = None

        if existing_method != method:
            if existing_method == "face":
                warning = f"{user_name}'s attendance is already marked using face scanner."
            else:
                warning = f"{user_name}'s attendance is marked with your fingerprint."

        return {
            "status": "ask_checkout",
            "message": f"{user_name}, are you leaving now?",
            "user_id": user_id,
            "method": method,
            "warning": warning,
            "user_name": user_name
        }

    return {
        "status": "already_completed",
        "message": "Today's attendance is already completed.",
        "user_id": user_id,
        "method": method,
        "user_name": user_name
    }