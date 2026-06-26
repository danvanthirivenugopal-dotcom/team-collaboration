import os

frontend_files = [
    r'D:\New folder\frontend\app.py',
    r'D:\New folder\frontend\modules\auth.py',
    r'D:\New folder\frontend\modules\scanner.py',
    r'D:\New folder\frontend\utils\api_client.py',
]

def replace_roles(content):
    # First, replace the direct casing (without lower())
    content = content.replace('st.session_state.user_role in ["admin", "super admin", "developer"]', 'st.session_state.user_role in ["Admin", "Super_Admin", "Developer"]')
    content = content.replace('st.session_state.user_role in ["admin", "super admin"]', 'st.session_state.user_role in ["Admin", "Super_Admin"]')
    content = content.replace('st.session_state.user_role in ["user", "premium user", "developer"]', 'st.session_state.user_role in ["User", "Premium_User", "Developer"]')

    # Now the .lower() comparisons
    content = content.replace('["admin", "super admin", "developer"]', '["admin", "super_admin", "developer"]')
    content = content.replace('["admin", "super admin"]', '["admin", "super_admin"]')
    content = content.replace('["user", "premium user"]', '["user", "premium_user"]')
    content = content.replace('["user", "premium user", "developer"]', '["user", "premium_user", "developer"]')

    content = content.replace('== "super admin"', '== "super_admin"')
    content = content.replace('!= "super admin"', '!= "super_admin"')
    content = content.replace('== "premium user"', '== "premium_user"')

    # Role options array in app.py
    content = content.replace('role_options = ["super admin", "admin", "developer", "premium user", "user", "guest"]', 'role_options = ["Super_Admin", "Admin", "Developer", "Premium_User", "User", "Guest"]')
    content = content.replace('role_options = ["admin", "developer", "premium user", "user", "guest"]', 'role_options = ["Admin", "Developer", "Premium_User", "User", "Guest"]')

    # Mapping dictionary
    content = content.replace('"super admin": "make_super_admin",', '"Super_Admin": "make_super_admin",')
    content = content.replace('"admin": "make_admin",', '"Admin": "make_admin",')
    content = content.replace('"developer": "make_developer",', '"Developer": "make_developer",')
    content = content.replace('"premium user": "make_premium_user",', '"Premium_User": "make_premium_user",')
    content = content.replace('"user": "make_user",', '"User": "make_user",')
    content = content.replace('"guest": "make_guest"', '"Guest": "make_guest"')

    return content

for fp in frontend_files:
    if os.path.exists(fp):
        with open(fp, 'r', encoding='utf-8') as f:
            c = f.read()
        new_c = replace_roles(c)
        if c != new_c:
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(new_c)

print("Frontend roles replaced.")
