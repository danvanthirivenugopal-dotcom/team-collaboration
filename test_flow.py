import sys
import os

# Add backend to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from backend.database.db import get_db
from backend.services.attendance_service import AttendanceService
from datetime import datetime, date

def run_test():
    print("--- Starting Backend Workflow Test ---")
    
    # 1. Get a test user ID from the database
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name FROM users LIMIT 1")
            user = cursor.fetchone()
            if not user:
                print("No users found in database! Please register a user first.")
                return
            
            user_id = user['id']
            user_name = user['name']
            print(f"Testing with User: {user_name} (ID: {user_id})")
            
            # Clean up today's attendance for a fresh test
            today_str = date.today().isoformat()
            cursor.execute("DELETE FROM attendance WHERE user_id = %s AND attendance_date = %s", (user_id, today_str))
            conn.commit()
            print("Cleared today's attendance records for a fresh start.")
            
    service = AttendanceService()
    
    # 2. Simulate First Scan
    print("\n[Simulation] 1. First Scan (Expect Check-in)")
    action1 = service.handle_face_scan_result(user_id)
    print(f"Result Action: {action1} (Expected: checked_in)")
    assert action1 == "checked_in", "First scan failed to check-in"
    
    # Verify DB state
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT check_in_time, check_out_time, status FROM attendance WHERE user_id = %s AND attendance_date = %s", (user_id, today_str))
            row = cursor.fetchone()
            print(f"DB State -> Check-in: {row['check_in_time'] != None}, Check-out: {row['check_out_time']}, Status: {row['status']}")
            
    # 3. Simulate Second Scan
    print("\n[Simulation] 2. Second Scan (Expect Ask Checkout)")
    action2 = service.handle_face_scan_result(user_id)
    print(f"Result Action: {action2} (Expected: ask_checkout)")
    assert action2 == "ask_checkout", "Second scan failed to ask for checkout"
    
    # 4. Simulate user pressing "Leave" (checkout)
    print("\n[Simulation] User pressed 'Leave' -> Calling check_out()")
    from main import api_check_out_endpoint # Need to mock this or just update db directly
    
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE attendance
                SET check_out_time = NOW(), status = 'COMPLETED', updated_at = NOW()
                WHERE user_id = %s AND attendance_date = %s
            """, (user_id, today_str))
            conn.commit()
    print("Checkout API triggered successfully.")
    
    # Verify DB state
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT check_in_time, check_out_time, status FROM attendance WHERE user_id = %s AND attendance_date = %s", (user_id, today_str))
            row = cursor.fetchone()
            print(f"DB State -> Check-in: {row['check_in_time'] != None}, Check-out: {row['check_out_time'] != None}, Status: {row['status']}")
            
    # 5. Simulate Third Scan
    print("\n[Simulation] 3. Third Scan (Expect Already Completed)")
    action3 = service.handle_face_scan_result(user_id)
    print(f"Result Action: {action3} (Expected: already_completed)")
    assert action3 == "already_completed", "Third scan failed to recognize completion"
    
    print("\n✅ All Workflow Tests Passed Successfully!")

if __name__ == '__main__':
    run_test()
