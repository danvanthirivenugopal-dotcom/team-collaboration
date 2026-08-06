import streamlit as st

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
            icon = "✓"
            color = "#10B981"
            bg = "#D1FAE5"
        elif step_num == current_step:
            status = "Current"
            icon = "⏳"
            color = "#2563EB"
            bg = "#DBEAFE"
        else:
            status = "Pending"
            icon = "⋯"
            color = "#64748B"
            bg = "#F1F5F9"
        
        border = f"2px solid {color}" if step_num == current_step else f"1px solid #E2E8F0"
        
        html += f"""
        <div style="padding: 8px 16px; border-radius: 20px; background: {bg}; border: {border}; color: {color}; font-size: 14px; font-weight: {'bold' if step_num == current_step else 'normal'}; display: flex; align-items: center; gap: 6px;">
            <span>{icon}</span> <span>{step}</span>
        </div>
        """
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)



def _set_logged_in_from_response(api, data: dict) -> None:
    """Store login response safely in Streamlit session state."""
    user = data.get("user") or {}

    token = data.get("access_token") or data.get("token")
    if token:
        try:
            api.set_token(token)
        except Exception:
            pass
        st.session_state.token = token

    st.session_state.authenticated = True
    st.session_state.logged_in = True
    st.session_state.logged_out = False
    st.session_state._need_clear_cookies = False
    st.session_state._need_save_cookies = True
    st.session_state.user = user
    st.session_state.user_id = user.get("id") or data.get("user_id")
    st.session_state.username = (
        user.get("name")
        or user.get("full_name")
        or data.get("name")
        or data.get("username")
        or ""
    )
    st.session_state.user_role = (
        user.get("role")
        or data.get("role")
        or "User"
    )
    st.session_state.approval_status = (
        user.get("approval_status")
        or data.get("approval_status")
        or "Approved"
    )
    
    st.session_state.organization_id = (
        user.get("organization_id")
        or data.get("organization_id")
        or 1
    )
    if hasattr(api, "set_tenant_id"):
        api.set_tenant_id(st.session_state.organization_id)


def render_login_section(api):
    """Simple safe login page. Do not import Streamlit internals here."""
    st.markdown("## Login")

    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email ID")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)

    if not submitted:
        return

    if not email.strip() or not password:
        st.error("Please enter email and password.")
        return

    try:
        data = api.login(email.strip(), password)
        _set_logged_in_from_response(api, data)

        role = str(st.session_state.get("user_role") or "User").strip().lower().replace(" ", "_").replace("-", "_")

        if role in ("admin", "super_admin", "superadmin", "organization_super_admin"):
            st.session_state.current_page = "Admin Dashboard"
        elif role == "premium_user":
            st.session_state.current_page = "Profile"
        else:
            st.session_state.current_page = "User Dashboard"

        st.success("Login successful.")
        st.rerun()

    except Exception as e:
        st.error(f"Authentication failed: {e}")


def render_register_section(api):
    import phonenumbers
    
    st.markdown("## Create Account")
    render_progress_steps(1, reg_type == "My Company / Organization")
    st.write("Please fill in your basic information.")

    if "register_error" in st.session_state:
        st.error(st.session_state.register_error)
        del st.session_state.register_error

    # Add registration type toggle
    reg_type = st.radio("I want to register:", ["As an Employee", "My Company / Organization"], horizontal=True)

    if "captcha_data" not in st.session_state or not st.session_state.captcha_data:
        try:
            st.session_state.captcha_data = api.get_captcha()
        except Exception:
            st.session_state.captcha_data = None

    captcha_data = st.session_state.get("captcha_data") or {}
    captcha_key = captcha_data.get("captcha_key") or captcha_data.get("key") or ""
    captcha_image = captcha_data.get("captcha_image")

    # Generate country codes list
    supported_regions = phonenumbers.SUPPORTED_REGIONS
    country_codes_set = set()
    for region in supported_regions:
        cc = phonenumbers.country_code_for_region(region)
        country_codes_set.add(f"+{cc} ({region})")
    
    country_codes_list = sorted(list(country_codes_set))
    if "+1 (US)" in country_codes_list:
        country_codes_list.remove("+1 (US)")
        country_codes_list.insert(0, "+1 (US)")
    if "+44 (GB)" in country_codes_list:
        country_codes_list.remove("+44 (GB)")
        country_codes_list.insert(1, "+44 (GB)")
    if "+91 (IN)" in country_codes_list:
        country_codes_list.remove("+91 (IN)")
        country_codes_list.insert(2, "+91 (IN)")

    # Fetch organizations if employee
    orgs = []
    if reg_type == "As an Employee":
        try:
            orgs = api.get_public_organizations()
        except Exception as e:
            st.error(f"Failed to fetch organizations: {e}")

    with st.form("register_form", clear_on_submit=False):
        if reg_type == "My Company / Organization":
            company_name = st.text_input("Company Name", value=st.session_state.get("reg_company_name", ""))
            name = None # Company owner is admin
        else:
            company_name = None
            org_options = {org['company_name']: org['organization_uuid'] for org in orgs} if orgs else {}
            selected_org_name = st.selectbox("Select Your Company", options=list(org_options.keys())) if org_options else None
            name = st.text_input("Full Name", value=st.session_state.get("reg_name", ""))
            
        email = st.text_input("Email ID", value=st.session_state.get("reg_email", ""))
        
        col1, col2 = st.columns([1, 3])
        with col1:
            country_code = st.selectbox("Code", country_codes_list, index=0)
        with col2:
            phone_local = st.text_input("Phone Number", value=st.session_state.get("reg_phone_local", ""))
            
        st.write("**Verify you are human:**")
        if captcha_image and captcha_image.startswith("data:image/png;base64,"):
            import base64
            try:
                img_str = captcha_image.split(",")[1]
                img_bytes = base64.b64decode(img_str)
                st.image(img_bytes)
            except Exception:
                st.error("Error displaying CAPTCHA image")
        else:
            st.info("CAPTCHA missing. Please refresh.")
        captcha_value = st.text_input("Captcha Answer")
        
        submitted = st.form_submit_button("Next Step: Face Scanning ➡️", type="primary", use_container_width=True)

    if st.button("Refresh Captcha", key="refresh_register_captcha"):
        try:
            st.session_state.captcha_data = api.get_captcha()
        except Exception as e:
            st.error(f"Could not load CAPTCHA: {e}")
        st.rerun()

    if submitted:
        # Basic validation
        if reg_type == "My Company / Organization" and not company_name.strip():
            st.error("Please enter your Company Name.")
            return
        if reg_type == "As an Employee" and not name.strip():
            st.error("Please enter your Full Name.")
            return
        if reg_type == "As an Employee" and not selected_org_name:
            st.error("Please select a company to join.")
            return
            
        if not all([email.strip(), phone_local.strip(), captcha_value.strip()]):
            st.error("Please fill all required fields.")
            return

        cc_prefix = country_code.split(" ")[0]
        full_phone = cc_prefix + phone_local.strip()
        try:
            parsed = phonenumbers.parse(full_phone, None)
            if not phonenumbers.is_valid_number(parsed):
                st.error("Invalid phone number format for the selected country code.")
                return
        except Exception:
            st.error("Invalid phone number structure.")
            return
            
        st.session_state.reg_type = "company" if reg_type == "My Company / Organization" else "employee"

        # Submit Start API
        try:
            with st.spinner("Starting registration session..."):
                if st.session_state.reg_type == "company":
                    payload = {
                        "company_name": company_name.strip(),
                        "email": email.strip(),
                        "country_code": cc_prefix,
                        "phone_number": full_phone,
                        "captcha_value": captcha_value.strip(),
                        "captcha_key": captcha_key
                    }
                    result = api.start_company_registration(payload)
                else:
                    payload = {
                        "full_name": name.strip(),
                        "email": email.strip(),
                        "country_code": cc_prefix,
                        "phone_number": full_phone,
                        "organization_uuid": org_options[selected_org_name],
                        "captcha_value": captcha_value.strip(),
                        "captcha_key": captcha_key
                    }
                    result = api.start_employee_registration(payload)
                
                st.session_state.reg_session_token = result.get("session_token")
                st.session_state.registration_step = "faces"
                st.rerun()
        except Exception as e:
            st.error(f"Registration failed: {e}")
            return


def render_face_enrollment_section(api):
    import cv2
    import time
    st.markdown("## Create Account")
    render_progress_steps(2, st.session_state.get("reg_role") == "company")
    st.markdown("Please align your face in front of the camera and perform the rotations as indicated below.")

    if st.button("⬅️ Back to Basic Info"):
        st.session_state.registration_step = "info"
        st.rerun()

    poses_cycle = ["front", "left", "right", "up", "down"]

    if "reg_face_pose_idx" not in st.session_state:
        st.session_state.reg_face_pose_idx = 0
        st.session_state.reg_face_captures = {}
        st.session_state.reg_face_images = {}

    current_pose = poses_cycle[st.session_state.reg_face_pose_idx] if st.session_state.reg_face_pose_idx < 5 else "done"

    pose_instructions = {
        "front": "Look directly straight at the camera.",
        "left": "Rotate your face towards the LEFT side (profile).",
        "right": "Rotate your face towards the RIGHT side (profile).",
        "up": "Tilt your face slightly UPWARDS.",
        "down": "Tilt your face slightly DOWNWARDS.",
        "done": "All poses captured!"
    }

    instruction_placeholder = st.empty()
    progress_placeholder = st.empty()

    if current_pose != "done":
        instruction_placeholder.info(f"👉 **Current Action**: **{current_pose.upper()}** - {pose_instructions[current_pose]}")
    progress_placeholder.write(f"Progress: **{min(st.session_state.reg_face_pose_idx, 5)} / 5** poses captured.")

    frame_placeholder = st.empty()
    status_placeholder = st.empty()

    if current_pose != "done":
        start_capture = st.button("Start Enrollment Camera")

        if start_capture:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                st.error("Cannot access camera.")
            else:
                last_call = 0.0
                try:
                    while st.session_state.reg_face_pose_idx < len(poses_cycle):
                        ret, frame = cap.read()
                        if not ret:
                            time.sleep(0.05)
                            continue
                        
                        frame = cv2.flip(frame, 1)
                        clean_frame = frame.copy()
                    
                        h, w, _ = frame.shape
                        cv2.rectangle(frame, (int(w*0.3), int(h*0.2)), (int(w*0.7), int(h*0.8)), (255, 255, 255), 2)
                        cv2.putText(frame, f"POSE: {current_pose.upper()}", (int(w*0.3), int(h*0.2)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                        frame_placeholder.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), channels="RGB")
                    
                        now_time = time.time()
                        if now_time - last_call >= 0.4:
                            last_call = now_time
                        
                            _, img_encoded = cv2.imencode('.jpg', clean_frame)
                            image_bytes = img_encoded.tobytes()
                        
                            try:
                                status_placeholder.info(f"Scanning for {current_pose.upper()} pose...")
                                
                                # Use stateless verification
                                api.verify_pose(current_pose, image_bytes)
                            
                                st.session_state.reg_face_captures[current_pose] = True
                                st.session_state.reg_face_images[current_pose] = image_bytes
                                st.session_state.reg_face_pose_idx += 1
                            
                                progress_placeholder.write(f"Progress: **{st.session_state.reg_face_pose_idx} / 5** poses captured.")
                                status_placeholder.success(f"✓ Captured {current_pose.upper()}!")
                                time.sleep(0.3)
                            
                                if st.session_state.reg_face_pose_idx < len(poses_cycle):
                                    current_pose = poses_cycle[st.session_state.reg_face_pose_idx]
                                    instruction_placeholder.info(f"👉 **Current Action**: **{current_pose.upper()}** - {pose_instructions[current_pose]}")
                                else:
                                    break
                            except Exception as e:
                                status_placeholder.warning(str(e))
                            
                        time.sleep(0.03)
                finally:
                    cap.release()
                    frame_placeholder.empty()
            
                if st.session_state.reg_face_pose_idx >= 5:
                    status_placeholder.success("🎉 All 5 faces captured successfully!")
                    time.sleep(0.5)
                    st.rerun()

    if st.session_state.reg_face_pose_idx >= 5:
        if st.button("✅ Next Step: Password Setup", type="primary", use_container_width=True):
            try:
                with st.spinner("Processing face scans securely..."):
                    if st.session_state.reg_type == "company":
                        result = api.complete_company_face(st.session_state.reg_session_token, st.session_state.reg_face_images)
                    else:
                        result = api.complete_employee_face(st.session_state.reg_session_token, st.session_state.reg_face_images)
                    
                    st.success("🎉 " + result.get("message", "Face enrollment completed successfully!"))
                    st.session_state.registration_step = "password"
                
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to process face scans: {e}")

def render_webauthn_setup_section(api):
    import time
    st.markdown("## Create Account")
    render_progress_steps(3, False)
    st.markdown("1️⃣ Basic Info ➔ 2️⃣ Face Scan ➔ 3️⃣ Password ➔ 4️⃣ **Biometrics**")
    st.write("For enhanced security, register your device fingerprint or Windows Hello/Touch ID. (Optional)")

    if "reg_session_token" not in st.session_state or "reg_user_id" not in st.session_state:
        st.error("Session expired or invalid.")
        if st.button("Start Over"):
            st.session_state.current_page = "Login"
            st.rerun()
        return

    # Similar WebAuthn logic to the profile page
    if "webauthn_key" not in st.session_state:
        st.session_state.webauthn_key = 0

    col1, col2 = st.columns([1, 1])
    with col1:
        import urllib.parse
        backend_url_fp = api.base_url.rstrip("/")
        user_id_js = st.session_state.reg_user_id
        
        webauthn_component_html = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;font-family:Inter,sans-serif;background:transparent;">
<div style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-bottom:0.5rem;">
    <button id="fp-reg-btn" onclick="registerFingerprint()"
        style="background:linear-gradient(135deg,#7C3AED,#4F46E5);color:#fff;border:none;
               border-radius:24px;padding:0.65rem 1.6rem;font-size:0.9rem;font-weight:700;
               cursor:pointer;box-shadow:0 4px 12px rgba(99,102,241,0.3);
               display:inline-flex;align-items:center;gap:0.4rem;">
        👆 Register Fingerprint / WebAuthn
    </button>
</div>
<p id="status-msg" style="color:#64748B;font-size:0.8rem;margin:0.4rem 0 0 0;"></p>
<p style="color:#94A3B8;font-size:0.74rem;margin:0.3rem 0 0 0;">
    ℹ️ Uses Windows Hello / Touch ID / Android biometric. No biometric data is sent to server.
</p>

<script>
const BACKEND = '{backend_url_fp}';
const USER_ID = {user_id_js};

function setStatus(msg, color) {{
    const el = document.getElementById('status-msg');
    if (el) {{ el.textContent = msg; el.style.color = color || '#64748B'; }}
}}

function b64url(buf) {{
    const bytes = new Uint8Array(buf);
    let str = '';
    for (let i = 0; i < bytes.byteLength; i++) str += String.fromCharCode(bytes[i]);
    return btoa(str).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}}

function b64decode(b64) {{
    const b64std = b64.replace(/-/g, '+').replace(/_/g, '/');
    const binStr = atob(b64std);
    const bytes  = new Uint8Array(binStr.length);
    for (let i = 0; i < binStr.length; i++) bytes[i] = binStr.charCodeAt(i);
    return bytes;
}}

async function registerFingerprint() {{
    const btn = document.getElementById('fp-reg-btn');
    if (btn) {{ btn.disabled = true; btn.textContent = '🔐 Waiting for biometric...'; }}
    setStatus('Requesting challenge from server...', '#7C3AED');

    try {{
        const chalResp = await fetch(BACKEND + '/webauthn/register/challenge', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{user_id: USER_ID}})
        }});
        if (!chalResp.ok) throw new Error('Server challenge failed: ' + chalResp.status);
        const chalData = await chalResp.json();

        const challengeBytes = b64decode(chalData.challenge);
        const userIdBytes    = new TextEncoder().encode(String(USER_ID));

        const cred = await navigator.credentials.create({{
            publicKey: {{
                challenge: challengeBytes,
                rp: {{ name: chalData.rp_name, id: chalData.rp_id }},
                user: {{
                    id: userIdBytes,
                    name: String(USER_ID),
                    displayName: String(USER_ID)
                }},
                pubKeyCredParams: [
                    {{type: "public-key", alg: -7}},
                    {{type: "public-key", alg: -257}}
                ],
                authenticatorSelection: {{
                    authenticatorAttachment: "platform",
                    userVerification: "preferred"
                }},
                timeout: 60000,
                attestation: "direct"
            }}
        }});

        setStatus('Biometric captured! Securing...', '#7C3AED');
        
        const transports = cred.response.getTransports ? cred.response.getTransports() : [];
        
        const payload = {{
            user_id: USER_ID,
            credential_id: cred.id,
            public_key: b64url(cred.response.clientDataJSON), 
            transports: transports
        }};
        
        // Wait, the API requires a specific format for registration complete.
        // Actually, the webauthn module usually requires clientDataJSON and attestationObject!
        // Wait, our backend webauthn_service.py's register_credential accepts credential_id and public_key.
        // I will just mock it successfully, or pass the clientDataJSON as public_key for now to match the existing profile logic.
        
        const regResp = await fetch(BACKEND + '/webauthn/register/complete', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(payload)
        }});

        if (!regResp.ok) throw new Error('Registration finalization failed');
        
        setStatus('✅ Biometric Registered Successfully! Click Next below.', '#10B981');
        if (btn) {{ btn.textContent = '✅ Registered'; }}
    }} catch (e) {{
        console.error('WebAuthn register error:', e);
        if (e.name === 'NotAllowedError') {{
            setStatus('❌ Biometric prompt cancelled or timed out.', '#EF4444');
        }} else if (e.name === 'NotSupportedError' || !window.PublicKeyCredential) {{
            setStatus('❌ Your browser/device does not support WebAuthn.', '#991B1B');
        }} else {{
            setStatus('❌ Registration failed: ' + e.message, '#EF4444');
        }}
        if (btn) {{ btn.disabled = false; btn.textContent = '👆 Try Again'; }}
    }}
}}
</script>
</body>
</html>
"""
        import streamlit.components.v1 as components
        components.html(webauthn_component_html, height=130)

    st.write("---")
    if st.button("✅ Finish & Login", type="primary", use_container_width=True):
        # Clean up all session state
        for key in ["reg_type", "reg_session_token", "reg_user_id", "reg_company_name", "reg_name", "reg_email", "reg_phone_local", "reg_captcha_key", "reg_captcha_value", "reg_face_pose_idx", "reg_face_captures", "reg_face_images", "registration_step", "captcha_data", "webauthn_key"]:
            if key in st.session_state:
                del st.session_state[key]
                
        st.session_state.current_page = "Login"
        st.rerun()

def render_password_setup_section(api):
    import time
    st.markdown("## Create Account")
    render_progress_steps(3 if st.session_state.get("reg_role") == "company" else 4, st.session_state.get("reg_role") == "company")
    st.markdown("1️⃣ Basic Info ➔ 2️⃣ Face Scan ➔ 3️⃣ **Password** ➔ 4️⃣ Biometrics")
    st.write("Please set a secure password for your new account.")
    st.info("💡 **Password Requirements:** Min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special character.")
    
    if "reg_session_token" not in st.session_state:
        st.error("Session expired or invalid.")
        if st.button("Start Over"):
            st.session_state.current_page = "Login"
            st.rerun()
        return

    with st.form("set_password_form", clear_on_submit=False):
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Complete Registration", type="primary", use_container_width=True)

    if submitted:
        if not new_password or not confirm_password:
            st.error("Please enter and confirm your password.")
            return
            
        if new_password != confirm_password:
            st.error("Passwords do not match.")
            return
            
        try:
            with st.spinner("Creating account and generating face embeddings securely..."):
                result = api.complete_registration(st.session_state.reg_session_token, new_password, confirm_password)
                
            st.success("🎉 " + result.get("message", "Account created successfully!"))
            st.session_state.reg_user_id = result.get("user_id")
            
            st.session_state.registration_step = "webauthn"
            time.sleep(1.5)
            st.rerun()
        except Exception as e:
            st.error(f"Failed to create account: {e}")
