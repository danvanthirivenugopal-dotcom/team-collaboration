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


def get_today_attendance(user_id: int):
    current_date = datetime.now().date()

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM attendance
                WHERE user_id = %s AND attendance_date = %s
                LIMIT 1
                """,
                (user_id, current_date)
            )
            return cursor.fetchone()


def get_attendance_settings() -> dict:
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
    latitude: float = None,
    longitude: float = None,
    fence_id: int = None,
    fence_name: str = None,
    similarity: float = 1.0
) -> dict:
    current_date = datetime.now().date()
    now_dt = datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    settings = get_attendance_settings()
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
                    checkin_latitude,
                    checkin_longitude,
                    location_verified,
                    geo_fence_id,
                    attendance_status
                )
                VALUES (%s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    current_date,
                    now_str,
                    attendance_status,
                    float(similarity),
                    is_half_day,
                    latitude,
                    longitude,
                    True,
                    fence_id,
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
                    f"Check-In ({attendance_status}) from {fence_name or 'Allowed Location'}"
                )
            )

    return {
        "status": "ok",
        "message": "Check-in marked successfully.",
        "attendance_status": attendance_status
    }


def mark_check_out(
    user_id: int,
    latitude: float = None,
    longitude: float = None
) -> dict:
    from backend.services import geofence_service, audit_service

    current_date = datetime.now().date()
    now_dt = datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    loc_ok, fence_id, fence_name = geofence_service.verify_location(latitude, longitude)

    if not loc_ok:
        audit_service.log_audit_action(
            None,
            f"Geo-fence warning: Checkout recorded outside allowed geofence for user ID {user_id}.",
            user_id
        )
        fence_name = "Outside Allowed Location"

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, check_in_time, status
                FROM attendance
                WHERE user_id = %s
                  AND attendance_date = %s
                  AND check_out_time IS NULL
                LIMIT 1
                """,
                (user_id, current_date)
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
                    checkout_latitude = %s,
                    checkout_longitude = %s,
                    working_hours = %s,
                    status = %s,
                    attendance_status = %s
                WHERE id = %s
                """,
                (
                    now_str,
                    latitude,
                    longitude,
                    hours,
                    final_status,
                    final_status,
                    record["id"]
                )
            )

            cursor.execute(
                """
                INSERT INTO attendance_logs (user_id, action)
                VALUES (%s, %s)
                """,
                (
                    user_id,
                    f"Check-Out (Hours worked: {hours:.2f}, Status: {final_status}) from {fence_name or 'Allowed Location'}"
                )
            )

    return {
        "status": "checked_out",
        "message": "Checkout marked successfully.",
        "working_hours": hours,
        "final_status": final_status
    }


def handle_face_scan_result(user_id: int) -> str:
    record = get_today_attendance(user_id)

    if not record:
        return "CHECK_IN_MARKED"

    if record["check_out_time"] is None:
        return "ASK_LEAVE_CONFIRMATION"

    return "ALREADY_CHECKED_OUT"


def handle_biometric_attendance(
    user_id: int,
    method: str,
    latitude: float = None,
    longitude: float = None
) -> dict:
    from backend.services import geofence_service

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT name FROM users WHERE id = %s",
                (user_id,)
            )
            user_row = cursor.fetchone()

    user_name = user_row["name"] if user_row else "User"

    loc_ok, fence_id, fence_name = geofence_service.verify_location(latitude, longitude)

    if not loc_ok:
        if geofence_service.is_location_required() and (latitude is None or longitude is None):
            message = "Location access is required. Please enable GPS/location in your browser and reload the page."
        else:
            loc_details = geofence_service.get_location_details(latitude, longitude)
            dist_m = loc_details.get("distance_m")
            nearest_fence = loc_details.get("fence_name", "office")

            if dist_m is not None:
                message = (
                    f"You are {dist_m:.0f}m away from '{nearest_fence}'. "
                    "Please move closer to the office and try again."
                )
            else:
                message = "You are not in the allowed location. Please move closer to the office and try again."

        return {
            "status": "location_error",
            "message": message,
            "user_id": user_id,
            "method": method,
            "user_name": user_name
        }

    record = get_today_attendance(user_id)

    if not record:
        settings = get_attendance_settings()
        now_dt = datetime.now()
        now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        current_date = now_dt.date()

        attendance_status = determine_checkin_status(now_dt, settings)
        is_half_day = attendance_status == "Half Day"

        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id
                    FROM attendance
                    WHERE user_id = %s AND attendance_date = %s
                    LIMIT 1
                    """,
                    (user_id, current_date)
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
                            checkin_latitude,
                            checkin_longitude,
                            location_verified,
                            geo_fence_id,
                            attendance_status,
                            attendance_method
                        )
                        VALUES (%s, %s, %s, %s, NULL, 1.0, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            user_id,
                            current_date,
                            now_str,
                            attendance_status,
                            is_half_day,
                            latitude,
                            longitude,
                            True,
                            fence_id,
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
                            f"Check-In via {method} ({attendance_status}) from {fence_name or 'Allowed Location'}"
                        )
                    )

                except Exception as insert_err:
                    if getattr(insert_err, "args", (None,))[0] != 1062:
                        raise

                    record = get_today_attendance(user_id)

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
                        "message": "Today's attendance is already completed.",
                        "user_id": user_id,
                        "method": method,
                        "user_name": user_name
                    }

        return {
            "status": "checked_in",
            "message": "Attendance marked successfully.",
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
            "message": f"{user_name}, Are you leave now?",
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