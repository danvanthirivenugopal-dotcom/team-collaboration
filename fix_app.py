import re

file_path = r'D:\FaceAI_Project(!@#)\frontend\app.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Comment out missing page imports
missing_imports = [
    'from pages.organization import render_organization_dashboard',
    'from pages.shifts import show_shifts_dashboard',
    'from pages.leaves import show_leave_dashboard',
    'from pages.visitors import render_visitor_management',
    'from pages.analytics import render_analytics_dashboard'
]

for imp in missing_imports:
    content = content.replace(imp, f'# {imp}')

# Fix page rendering blocks in app.py to prevent undefined function errors
content = content.replace('render_organization_dashboard()', 'st.warning("Organization Dashboard is under construction")')
content = content.replace('show_shifts_dashboard()', 'st.warning("Shifts Dashboard is under construction")')
content = content.replace('show_leave_dashboard()', 'st.warning("Leave Dashboard is under construction")')
content = content.replace('render_visitor_management()', 'st.warning("Visitor Management is under construction")')
content = content.replace('render_analytics_dashboard()', 'st.warning("Analytics Dashboard is under construction")')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("app.py fixed")
