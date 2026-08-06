import re

with open(r"D:\FaceAI_Project(!@#)\frontend\app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Update User page options
content = content.replace(
    """    else:
        page_options = ["Dashboard", "Home / Scanner", "Reports", "Profile"]
        allowed_pages = page_options + ["User Dashboard", "Logout", "Feature", "Techstack", "Comment", "Team", "Welcome", "Update Face Profile"]""",
    """    else:
        page_options = ["Dashboard", "Home / Scanner", "Reports", "Profile", "Leaves"]
        allowed_pages = page_options + ["User Dashboard", "Logout", "Feature", "Techstack", "Comment", "Team", "Welcome", "Update Face Profile"]"""
)

# Update protected pages
content = content.replace(
    """"Update Face Profile", "Guest Dashboard", "Organization Dashboard"
]""",
    """"Update Face Profile", "Guest Dashboard", "Organization Dashboard", "Leaves", "Shifts"
]"""
)

# Add imports for the new pages at the top
if "from pages.shifts import show_shifts_dashboard" not in content:
    content = content.replace(
        "from pages.organization import render_organization_dashboard",
        "from pages.organization import render_organization_dashboard\nfrom pages.shifts import show_shifts_dashboard\nfrom pages.leaves import show_leave_dashboard"
    )

# Add route rendering
route_code = """
elif st.session_state.current_page == "Shifts":
    show_shifts_dashboard(api, st.session_state)
elif st.session_state.current_page == "Leaves":
    show_leave_dashboard(api, st.session_state)
elif st.session_state.current_page == "User Dashboard":"""
content = content.replace(
    'elif st.session_state.current_page == "User Dashboard":',
    route_code
)

with open(r"D:\FaceAI_Project(!@#)\frontend\app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated app.py routing")
