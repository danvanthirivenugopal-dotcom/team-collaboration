
import sys
import re

file_path = r"D:\FaceAI_Project(!@#)\frontend\app.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add import
content = content.replace("from pages.leaves import show_leave_dashboard", "from pages.leaves import show_leave_dashboard\nfrom pages.visitors import render_visitor_management")

# 2. Add to Admin page_options
content = content.replace('page_options = ["Dashboard", "Manage Users", "Attendance", "Attendance Log", "Reports", "Organization Dashboard", "Leaves", "Profile"]', 'page_options = ["Dashboard", "Manage Users", "Attendance", "Attendance Log", "Reports", "Organization Dashboard", "Leaves", "Visitors", "Profile"]')

# 3. Add to User page_options
content = content.replace('page_options = ["Dashboard", "Home / Scanner", "Reports", "Profile", "Leaves"]', 'page_options = ["Dashboard", "Home / Scanner", "Reports", "Profile", "Leaves", "Visitors"]')

# 4. Add to Premium User page_options
content = content.replace('page_options = ["Profile", "Leaves"]', 'page_options = ["Profile", "Leaves", "Visitors"]')

# 5. Add to protected_nav_pages
content = content.replace('"Update Face Profile", "Guest Dashboard", "Organization Dashboard", "Leaves", "Shifts"', '"Update Face Profile", "Guest Dashboard", "Organization Dashboard", "Leaves", "Shifts", "Visitors"')

# 6. Add the page rendering block
target_block = """        elif st.session_state.current_page == "Leaves":
            show_leave_dashboard()"""

replacement_block = """        elif st.session_state.current_page == "Leaves":
            show_leave_dashboard()
        elif st.session_state.current_page == "Visitors":
            render_visitor_management()"""

content = content.replace(target_block, replacement_block)

# 7. Add Notification Bell
# We will inject the bell near the top navigation or sidebar profile section
bell_injection = """
if _is_logged_in():
    st.sidebar.write("---")
    st.sidebar.write(f"Logged in as: **{st.session_state.get('username', '')}** ({st.session_state.get('user_role', 'User')})")"""

bell_replacement = """
if _is_logged_in():
    st.sidebar.write("---")
    # Fetch alerts for bell
    try:
        unread_alerts = st.session_state.api.get_alerts(unread_only=True)
        alert_count = len(unread_alerts)
        if alert_count > 0:
            if st.sidebar.button(f"🔔 Notifications ({alert_count})"):
                st.session_state.show_notifications = not st.session_state.get("show_notifications", False)
                st.rerun()
        else:
            st.sidebar.write("🔔 No new notifications")
            
        if st.session_state.get("show_notifications"):
            st.sidebar.markdown("**Unread Notifications:**")
            for alert in unread_alerts:
                st.sidebar.info(f"**{alert['title']}**\\n{alert['message']}")
                if st.sidebar.button("Mark Read", key=f"read_{alert['id']}"):
                    st.session_state.api.mark_alert_read(alert['id'])
                    st.rerun()
    except Exception:
        pass
    st.sidebar.write("---")
    st.sidebar.write(f"Logged in as: **{st.session_state.get('username', '')}** ({st.session_state.get('user_role', 'User')})")"""

content = content.replace(bell_injection, bell_replacement)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated app.py successfully")
