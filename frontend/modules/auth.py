import streamlit as st


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

        if role in ("admin", "super_admin", "superadmin"):
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
    """
    Safe registration page.
    Backend expects: name, email, phone_number, department, password, captcha_key, captcha_value.
    """
    st.markdown("## Create Account")

    if "register_error" in st.session_state:
        st.error(st.session_state.register_error)
        del st.session_state.register_error

    if "captcha_data" not in st.session_state or not st.session_state.captcha_data:
        try:
            st.session_state.captcha_data = api.get_captcha()
        except Exception:
            st.session_state.captcha_data = None

    captcha_data = st.session_state.get("captcha_data") or {}
    captcha_key = captcha_data.get("captcha_key") or captcha_data.get("key") or ""
    captcha_image = captcha_data.get("captcha_image")

    with st.form("register_form", clear_on_submit=False):
        name = st.text_input("Full Name")
        email = st.text_input("Email ID")
        phone_number = st.text_input("Phone Number with Country Code")
        department = st.text_input("Department")
        password = st.text_input("Set Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
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
        submitted = st.form_submit_button("Register", type="primary", use_container_width=True)

    if st.button("Refresh Captcha", key="refresh_register_captcha"):
        try:
            st.session_state.captcha_data = api.get_captcha()
        except Exception as e:
            st.error(f"Could not load CAPTCHA: {e}")
        st.rerun()

    if not submitted:
        return

    if not all([name.strip(), email.strip(), phone_number.strip(), password, confirm_password, captcha_value.strip()]):
        st.error("Please fill all required fields.")
        return

    if password != confirm_password:
        st.error("Password and confirm password do not match.")
        return

    try:
        payload = {
            "name": name.strip(),
            "email": email.strip(),
            "phone_number": phone_number.strip(),
            "department": department.strip(),
            "password": password,
            "captcha_key": captcha_key,
            "captcha_value": captcha_value.strip(),
        }
        result = api.register(payload)

        user_id = result.get("user_id")
        st.session_state.registration_user_id = user_id
        st.session_state.user_id = user_id
        st.session_state.registration_step = "face_enrollment"

        st.success(result.get("message", "Registration submitted. Continue face enrollment."))
        st.rerun()

    except Exception as e:
        st.session_state.register_error = f"Registration failed: {e}"
        try:
            st.session_state.captcha_data = api.get_captcha()
        except Exception:
            st.session_state.captcha_data = None
        st.rerun()

def render_face_enrollment_section(api):
    import cv2
    import time
    st.markdown("## 👤 New User Face Enrollment")
    st.markdown("Please align your face in front of the camera and perform the rotations as indicated below.")

    poses_cycle = ["front", "left", "right", "up", "down"]

    if "reg_face_pose_idx" not in st.session_state:
        st.session_state.reg_face_pose_idx = 0
        st.session_state.reg_face_captures = {}

    current_pose = poses_cycle[st.session_state.reg_face_pose_idx]

    pose_instructions = {
        "front": "Look directly straight at the camera.",
        "left": "Rotate your face towards the LEFT side (profile).",
        "right": "Rotate your face towards the RIGHT side (profile).",
        "up": "Tilt your face slightly UPWARDS.",
        "down": "Tilt your face slightly DOWNWARDS."
    }

    instruction_placeholder = st.empty()
    progress_placeholder = st.empty()

    instruction_placeholder.info(f"👉 **Current Action**: **{current_pose.upper()}** - {pose_instructions[current_pose]}")
    progress_placeholder.write(f"Progress: **{st.session_state.reg_face_pose_idx} / 5** poses captured.")

    frame_placeholder = st.empty()
    status_placeholder = st.empty()

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
                    if now_time - last_call >= 0.8:
                        last_call = now_time
                    
                        _, img_encoded = cv2.imencode('.jpg', clean_frame)
                        image_bytes = img_encoded.tobytes()
                    
                        try:
                            status_placeholder.info(f"Scanning for {current_pose.upper()} pose...")
                            api.upload_enrollment_pose(st.session_state.user_id, current_pose, image_bytes)
                        
                            st.session_state.reg_face_captures[current_pose] = True
                            st.session_state.reg_face_pose_idx += 1
                        
                            progress_placeholder.write(f"Progress: **{st.session_state.reg_face_pose_idx} / 5** poses captured.")
                            status_placeholder.success(f"✓ Captured {current_pose.upper()}!")
                            time.sleep(1.0)
                        
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
                status_placeholder.info("Finalizing face profiles...")
                try:
                    api.complete_enrollment(st.session_state.user_id)
                    st.success("🎉 Registration complete! Please wait for an Admin to approve your account before logging in.")
                    
                    if "reg_face_pose_idx" in st.session_state:
                        del st.session_state.reg_face_pose_idx
                    if "reg_face_captures" in st.session_state:
                        del st.session_state.reg_face_captures
                    
                    st.session_state.registration_step = "form"
                    st.session_state.current_page = "Login"
                    time.sleep(3)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to finalize registration: {e}")
