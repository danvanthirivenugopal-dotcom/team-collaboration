import re

file_path = r'D:\FaceAI_Project(!@#)\frontend\modules\auth.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

progress_steps_code = '''
def render_progress_steps(current_step, is_company):
    if is_company:
        steps = ["Basic Information", "Face Enrollment", "Password Setup"]
    else:
        steps = ["Basic Information", "Face Enrollment", "Biometrics", "Password Setup"]
    
    html = '<div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;">'
    for i, step in enumerate(steps):
        step_num = i + 1
        if step_num < current_step:
            status = "Completed"
            icon = "?"
            color = "var(--success)"
            bg = "var(--surface-secondary)"
        elif step_num == current_step:
            status = "Current"
            icon = "?"
            color = "var(--primary)"
            bg = "var(--surface)"
        else:
            status = "Pending"
            icon = "?"
            color = "var(--text-muted)"
            bg = "var(--surface-secondary)"
        
        border = f"2px solid {color}" if step_num == current_step else f"1px solid var(--border)"
        
        html += f"""
        <div style="padding: 8px 16px; border-radius: 20px; background: {bg}; border: {border}; color: {color}; font-size: 14px; font-weight: {'bold' if step_num == current_step else 'normal'}; display: flex; align-items: center; gap: 6px;">
            <span>{icon}</span> <span>{step}</span>
        </div>
        """
    html += '</div>'
    import streamlit as st
    st.markdown(html, unsafe_allow_html=True)
'''

# Add the progress_steps_code right after imports
if 'def render_progress_steps' not in content:
    content = content.replace('import json\n', 'import json\n' + progress_steps_code)

# Replace the step headers in auth.py
# Step 1
content = re.sub(r'st\.markdown\("## Create Account - Step 1/3 \(Basic Info\)"\)\n\s*st\.markdown\(".*?"\)', 
                 'st.markdown("## Create Account")\n    render_progress_steps(1, reg_type == "My Company / Organization")', content)

# Step 2
content = re.sub(r'st\.markdown\("## Create Account - Step 2/3 \(Face Scan\)"\)\n\s*st\.markdown\(".*?"\)', 
                 'st.markdown("## Create Account")\n    render_progress_steps(2, st.session_state.get("reg_role") == "company")', content)

# Step 3 (Biometrics for employees is step 3 technically in code but user wants "3. Fingerprint/WebAuthn, 4. Password")
# Actually, the user says Employee is Basic -> Face -> WebAuthn -> Password. 
# So Biometrics is step 3 for Employee, Password is step 4.
content = re.sub(r'st\.markdown\("## Create Account - Step 4/4 \(Biometrics\)"\)', 
                 'st.markdown("## Create Account")\n    render_progress_steps(3, False)', content)

# Step Password (Step 3 for company, Step 4 for employee)
content = re.sub(r'st\.markdown\("## Create Account - Step 3/4 \(Password Setup\)"\)', 
                 'st.markdown("## Create Account")\n    render_progress_steps(3 if st.session_state.get("reg_role") == "company" else 4, st.session_state.get("reg_role") == "company")', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated auth.py successfully")
