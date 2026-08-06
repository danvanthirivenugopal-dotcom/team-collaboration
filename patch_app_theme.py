import re

file_path = r'D:\FaceAI_Project(!@#)\frontend\app.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Import theme module
if 'from utils.theme import' not in content:
    content = content.replace('from utils.api_client import FaceAiApiClient', 'from utils.api_client import FaceAiApiClient\nfrom utils.theme import apply_global_theme, render_theme_toggle')

# 2. Replace inject_css() function entirely
# We will use regex to find def inject_css(): and replace it with a pass or remove it
pattern = re.compile(r'def inject_css\(\):.*?st\.markdown\("""<style>.*?</style>""", unsafe_allow_html=True\)', re.DOTALL)
content = pattern.sub('def inject_css():\n    apply_global_theme()', content)

# 3. Add theme toggle to sidebar
sidebar_injection = '''
if _is_logged_in():
    st.sidebar.write("---")'''
sidebar_replacement = '''
if _is_logged_in():
    st.sidebar.write("---")
    render_theme_toggle()'''

if 'render_theme_toggle()' not in content:
    content = content.replace(sidebar_injection, sidebar_replacement)

# Remove hardcoded CSS overrides on cards
content = re.sub(r'style=".*?background-color:\s*white.*?"', 'class="saas-card"', content)
content = re.sub(r'style=".*?background-color:\s*#FFFFFF.*?"', 'class="saas-card"', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated app.py successfully")
