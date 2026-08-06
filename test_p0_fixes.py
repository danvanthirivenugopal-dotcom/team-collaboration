import os
import sys
from datetime import datetime

# Setup paths so we can import backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from backend.database.db import get_db
from backend.services.attendance_service import mark_check_in, get_today_attendance

def setup_test_data():
    with get_db() as conn:
        with conn.cursor() as cursor:
            # Create a test organization
            cursor.execute('''INSERT IGNORE INTO organizations (id, organization_uuid, company_name, slug) 
                              VALUES (999, 'test-uuid-999', 'Test Org', 'test-org-slug')''')
            cursor.execute('''INSERT IGNORE INTO organizations (id, organization_uuid, company_name, slug) 
                              VALUES (998, 'test-uuid-998', 'Other Org', 'other-org-slug')''')
            
            # Create a test user for each org
            cursor.execute('''INSERT IGNORE INTO users (id, name, email, password, role, organization_id, phone_number) 
                              VALUES (9999, 'Test User', 'test9999@test.com', 'hash', 'employee', 999, '123')''')
            cursor.execute('''INSERT IGNORE INTO users (id, name, email, password, role, organization_id, phone_number) 
                              VALUES (9998, 'Other User', 'test9998@test.com', 'hash', 'employee', 998, '123')''')
            
            # Clean up today's attendance for the test users
            current_date = datetime.now().date()
            cursor.execute("DELETE FROM attendance WHERE user_id IN (9999, 9998) AND attendance_date = %s", (current_date,))
            cursor.execute("DELETE FROM attendance_logs WHERE user_id IN (9999, 9998)")
            
            conn.commit()

def test_idempotency():
    print("Testing Idempotency (Duplicate Attendance Check-in)...")
    try:
        # First check-in
        res1 = mark_check_in(user_id=9999, organization_id=999)
        print("First Check-in Response:", res1['status'])
        
        # Second check-in (simulate double click / race condition)
        res2 = mark_check_in(user_id=9999, organization_id=999)
        print("Second Check-in Response:", res2['status'])
        
        print("Idempotency Test Passed! No crashes occurred on duplicate submission.")
    except Exception as e:
        print("Idempotency Test Failed:", e)

def test_tenant_isolation():
    print("\nTesting Tenant Isolation (Multi-Organization data boundary)...")
    try:
        # Get attendance for user 9999 in org 999 (should exist)
        record1 = get_today_attendance(user_id=9999, organization_id=999)
        print(f"User 9999 in Org 999: {'Found' if record1 else 'Not Found'}")
        
        # Try to get attendance for user 9999 in org 998 (should NOT exist)
        record2 = get_today_attendance(user_id=9999, organization_id=998)
        print(f"User 9999 in Org 998: {'Found' if record2 else 'Not Found'}")
        
        if record1 and not record2:
            print("Tenant Isolation Test Passed!")
        else:
            print("Tenant Isolation Test Failed!")
    except Exception as e:
        print("Tenant Isolation Test Failed:", e)

def cleanup_test_data():
    with get_db() as conn:
        with conn.cursor() as cursor:
            current_date = datetime.now().date()
            cursor.execute("DELETE FROM attendance WHERE user_id IN (9999, 9998) AND attendance_date = %s", (current_date,))
            cursor.execute("DELETE FROM attendance_logs WHERE user_id IN (9999, 9998)")
            cursor.execute("DELETE FROM users WHERE id IN (9999, 9998)")
            cursor.execute("DELETE FROM organizations WHERE id IN (999, 998)")
            conn.commit()

if __name__ == '__main__':
    setup_test_data()
    test_idempotency()
    test_tenant_isolation()
    cleanup_test_data()
