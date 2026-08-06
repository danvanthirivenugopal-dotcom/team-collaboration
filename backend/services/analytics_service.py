from backend.database.db import get_db
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("faceai.analytics")

class AnalyticsService:
    @staticmethod
    def get_dashboard_metrics(organization_id: int, days: int = 30):
        """Aggregate stats for the analytics dashboard."""
        metrics = {
            "total_employees": 0,
            "today_attendance_rate": 0,
            "active_visitors": 0,
            "pending_leaves": 0,
            "attendance_trends": [],
            "department_stats": [],
            "visitor_traffic": [],
            "ai_insights": []
        }

        with get_db() as conn:
            with conn.cursor() as cursor:
                # 1. Total Employees
                cursor.execute(
                    "SELECT COUNT(id) as c FROM users WHERE organization_id = %s",
                    (organization_id,)
                )
                res = cursor.fetchone()
                metrics["total_employees"] = res["c"] if res else 0

                # 2. Today's Attendance Rate
                today = datetime.now().date()
                cursor.execute(
                    "SELECT COUNT(attendance_id) as present FROM attendance WHERE organization_id = %s AND attendance_date = %s AND status IN ('Present', 'Late', 'Half Day')",
                    (organization_id, today)
                )
                pres = cursor.fetchone()
                present_count = pres["present"] if pres else 0
                
                if metrics["total_employees"] > 0:
                    metrics["today_attendance_rate"] = round((present_count / metrics["total_employees"]) * 100, 1)
                
                # 3. Active Visitors (Check if visitor_visits exists, if not safely skip)
                try:
                    cursor.execute(
                        "SELECT COUNT(id) as c FROM visitor_visits WHERE organization_id = %s AND check_in_time IS NOT NULL AND check_out_time IS NULL",
                        (organization_id,)
                    )
                    vis = cursor.fetchone()
                    metrics["active_visitors"] = vis["c"] if vis else 0
                except Exception as e:
                    logger.warning(f"Visitor visits table missing or error: {e}")
                
                # 4. Pending Leaves
                try:
                    cursor.execute(
                        "SELECT COUNT(id) as c FROM leaves WHERE organization_id = %s AND status = 'Pending'",
                        (organization_id,)
                    )
                    lv = cursor.fetchone()
                    metrics["pending_leaves"] = lv["c"] if lv else 0
                except Exception as e:
                    logger.warning(f"Leaves table missing or error: {e}")

                # 5. Attendance Trends (Last X Days)
                start_date = today - timedelta(days=days)
                cursor.execute("""
                    SELECT attendance_date as date, status, COUNT(attendance_id) as count 
                    FROM attendance 
                    WHERE organization_id = %s AND attendance_date >= %s 
                    GROUP BY attendance_date, status 
                    ORDER BY attendance_date ASC
                """, (organization_id, start_date))
                
                trends = cursor.fetchall()
                # Format for frontend charting:
                metrics["attendance_trends"] = [
                    {"date": t["date"].strftime("%Y-%m-%d"), "status": t["status"], "count": t["count"]}
                    for t in trends
                ]

                # 6. Department Stats (All time or this month)
                cursor.execute("""
                    SELECT u.department, a.status, COUNT(a.attendance_id) as count 
                    FROM attendance a 
                    JOIN users u ON a.user_id = u.id 
                    WHERE a.organization_id = %s AND u.department IS NOT NULL
                    GROUP BY u.department, a.status
                """, (organization_id,))
                dep_stats = cursor.fetchall()
                metrics["department_stats"] = [
                    {"department": d["department"], "status": d["status"], "count": d["count"]}
                    for d in dep_stats
                ]
                
                # 7. AI Statistical Insights
                # Example 1: Average check in time
                cursor.execute("""
                    SELECT AVG(TIME_TO_SEC(TIME(check_in_time))) as avg_sec
                    FROM attendance
                    WHERE organization_id = %s AND check_in_time IS NOT NULL
                """, (organization_id,))
                avg_res = cursor.fetchone()
                if avg_res and avg_res["avg_sec"]:
                    avg_time = (datetime.min + timedelta(seconds=int(avg_res["avg_sec"]))).time()
                    metrics["ai_insights"].append({
                        "type": "positive", 
                        "message": f"Average check-in time across the organization is {avg_time.strftime('%I:%M %p')}."
                    })
                
                # Example 2: Department with highest late rate
                late_dict = {}
                total_dict = {}
                for d in dep_stats:
                    dep = d["department"]
                    st = d["status"]
                    c = d["count"]
                    total_dict[dep] = total_dict.get(dep, 0) + c
                    if st == 'Late':
                        late_dict[dep] = late_dict.get(dep, 0) + c
                
                max_late_rate = 0
                max_late_dep = None
                for dep, total in total_dict.items():
                    late_c = late_dict.get(dep, 0)
                    if total > 5: # min threshold
                        rate = late_c / total
                        if rate > max_late_rate:
                            max_late_rate = rate
                            max_late_dep = dep
                
                if max_late_dep and max_late_rate > 0.1:
                    metrics["ai_insights"].append({
                        "type": "warning", 
                        "message": f"Anomaly Detected: The {max_late_dep} department has a high late-arrival rate of {round(max_late_rate*100)}%."
                    })

                if not metrics["ai_insights"]:
                    metrics["ai_insights"].append({
                        "type": "info",
                        "message": "Insufficient data to generate advanced statistical anomalies. Keep recording attendance!"
                    })

        return metrics
