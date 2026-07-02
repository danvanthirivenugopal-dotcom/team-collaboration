import streamlit as st
import cv2
import time
import base64
from io import BytesIO
from pathlib import Path
import streamlit.components.v1 as components

def draw_face_overlay(frame, x1, y1, x2, y2, name, user_id, status_det):
    # Select color based on status (BGR format)
    if status_det == "recognized" or status_det == "checked_in":
        box_color = (255, 255, 0)    # Cyan to match requested design
        status_text = "MARKED"
    elif status_det in ["already_marked", "ask_leave", "ask_checkout", "already_completed"]:
        box_color = (255, 255, 0)    # Cyan for already marked/leaving
        status_text = "ALREADY MARKED"
    elif status_det == "not_approved":
        box_color = (0, 165, 255)    # Orange for pending approval
        status_text = "PENDING"
    elif status_det == "location_error":
        box_color = (0, 165, 255)    # Orange/Yellow for location error
        status_text = "LOCATION ERROR"
    elif status_det == "method_mismatch":
        box_color = (0, 0, 255)      # Red for method mismatch
        status_text = "METHOD ERROR"
    elif status_det == "error":
        box_color = (0, 0, 255)      # Red for general error
        status_text = "ERROR"
    else:
        box_color = (0, 0, 255)      # Red for guest/guest
        status_text = "NEW USER"

    # Draw bounding box around face
    cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
    
    # Format labels - Name + Status on line 1, ID on line 2
    # For guest/guest/unknown faces, override name display
    display_name = name if (name and status_det not in ("guest", "unknown", None)) else "UNREGISTERED"
    label_line1 = f"{display_name.upper()} ({status_text})"
    # Handle None user_id
    student_id = user_id if user_id is not None else None
    label_line2 = f"ID: STU{100 + student_id}" if student_id is not None else "Unregistered Face"
        
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale_line1 = 0.55
    scale_line2 = 0.45
    thick_line1 = 2
    thick_line2 = 1
    
    (w_line1, h_line1), _ = cv2.getTextSize(label_line1, font, scale_line1, thick_line1)
    (w_line2, h_line2), _ = cv2.getTextSize(label_line2, font, scale_line2, thick_line2)
    label_w = max(w_line1, w_line2) + 16
    label_h = h_line1 + h_line2 + 20
        
    # Place label ABOVE the bounding box
    lx1 = x1 + (x2 - x1 - label_w) // 2
    ly1 = y1 - label_h - 6
    
    # Fallback to drawing BELOW if it goes above the frame boundary
    if ly1 < 5:
        ly1 = y2 + 6
        
    lx2 = lx1 + label_w
    ly2 = ly1 + label_h
    
    # Clip coordinates to frame size
    fh, fw, _ = frame.shape
    lx1 = max(0, min(lx1, fw - 1))
    lx2 = max(0, min(lx2, fw - 1))
    ly1 = max(0, min(ly1, fh - 1))
    ly2 = max(0, min(ly2, fh - 1))
    
    # Solid background drawing
    if lx2 > lx1 and ly2 > ly1:
        # Draw solid background matching the box color
        cv2.rectangle(frame, (lx1, ly1), (lx2, ly2), box_color, -1)
        
        # Draw text on frame (white text)
        ty1 = ly1 + h_line1 + 8
        cv2.putText(frame, label_line1, (lx1 + 8, ty1), font, scale_line1, (255, 255, 255), thick_line1, cv2.LINE_AA)
        
        # Draw text on frame - Line 2 (ID)
        ty2 = ty1 + h_line2 + 8
        cv2.putText(frame, label_line2, (lx1 + 8, ty2), font, scale_line2, (255, 255, 255), thick_line2, cv2.LINE_AA)

# Process HTML navigation query parameters
# Navigation query parameters are handled only in frontend/app.py.


def detect_local_faces(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80)
    )

    results = []
    for (x, y, w, h) in faces:
        results.append([int(x), int(y), int(x + w), int(y + h)])

    return results


def render_scanner_section(api):
    if "cooldowns" not in st.session_state:
        st.session_state.cooldowns = {}
        
    # Initialize the requested fingerprint session state variables
    if "fingerprint_scanning" not in st.session_state:
        st.session_state.fingerprint_scanning = False
    if "fingerprint_verified" not in st.session_state:
        st.session_state.fingerprint_verified = False
    if "attendance_marked" not in st.session_state:
        st.session_state.attendance_marked = False
    if "checkout_marked" not in st.session_state:
        st.session_state.checkout_marked = False
    if "status_message" not in st.session_state:
        st.session_state.status_message = None
    if "webauthn_key" not in st.session_state:
        st.session_state.webauthn_key = 0


    # Handle a pending WebAuthn result from JS first thing
    fp_user_id_q = st.query_params.get("fp_user_id")
    fp_name_q = st.query_params.get("fp_name")
    fp_status_q = st.query_params.get("fp_status")

    if fp_status_q:
        st.session_state.fingerprint_scanning = False
        st.session_state.fingerprint_verified = False
        st.session_state.attendance_marked = False
        st.session_state.checkout_marked = False
        st.session_state.status_message = None
        st.session_state.webauthn_key += 1

        if fp_status_q == "ask_checkout" and fp_user_id_q and fp_name_q:
            st.session_state.fingerprint_verified = True
            if not st.session_state.get("show_leave_confirmation"):
                st.session_state.pending_checkout_user_id = int(fp_user_id_q)
                st.session_state.pending_checkout_user_name = fp_name_q
                fp_role_q = st.query_params.get("fp_role", "user")
                st.session_state.pending_checkout_user_role = fp_role_q
                st.session_state.pending_attendance_method = "fingerprint"
                st.session_state.show_leave_confirmation = True
                fp_img_q = st.query_params.get("fp_img")
                st.session_state.scanned_user = {
                    "profile_image": fp_img_q if fp_img_q else None
                }
                fp_warn_q = st.query_params.get("fp_warning")
                st.session_state.pending_checkout_warning = fp_warn_q if fp_warn_q else None
                st.query_params.clear()
                st.rerun()
        elif fp_status_q == "checked_in" and fp_name_q:
            st.session_state.fingerprint_verified = True
            st.session_state.attendance_marked = True
            st.session_state.status_message = ("success", f"✅ {fp_name_q}'s attendance marked successfully using fingerprint.")
            st.query_params.clear()
            st.rerun()
        elif fp_status_q == "checked_out" and fp_name_q:
            st.session_state.fingerprint_verified = True
            st.session_state.checkout_marked = True
            st.session_state.status_message = ("success", f"👋 {fp_name_q}'s check-out marked successfully using fingerprint.")
            st.query_params.clear()
            st.rerun()
        elif fp_status_q == "already_completed" and fp_name_q:
            st.session_state.fingerprint_verified = True
            st.session_state.status_message = ("info", "ℹ️ Today's attendance is already completed.")
            st.query_params.clear()
            st.rerun()
        elif fp_status_q == "method_mismatch" and fp_name_q:
            fp_warn_q = st.query_params.get("fp_warning", f"❌ {fp_name_q}'s attendance is already marked with our face")
            st.session_state.status_message = ("warning", fp_warn_q)
            st.query_params.clear()
            st.rerun()
        elif fp_status_q == "error":
            st.session_state.status_message = ("error", "❌ Fingerprint not recognized.")
            st.query_params.clear()
            st.rerun()

    col_scanner, col_rules = st.columns([1.2, 1])
    
    with col_rules:
        status_placeholder = st.empty()

        # Display any pending fingerprint/scanner status message on the right side
        if "status_message" in st.session_state and st.session_state.status_message:
            msg_type, msg_text = st.session_state.status_message
            if msg_type == "success":
                st.success(msg_text)
            elif msg_type == "info":
                st.info(msg_text)
            elif msg_type == "warning":
                st.warning(msg_text)
            elif msg_type == "error":
                st.error(msg_text)
            
            # Clear the state so it doesn't persist on next interaction
            st.session_state.status_message = None
            st.session_state.fingerprint_scanning = False
            st.session_state.fingerprint_verified = False
            st.session_state.attendance_marked = False
            st.session_state.checkout_marked = False
        st.markdown("""
        <div class="saas-card">
            <div class="rules-header">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                    <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
                <h3>Attendance Rules</h3>
            </div>
            <div class="rules-list">
                <div class="rule-item">
                    <div class="rule-badge badge-green">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                    </div>
                    <div class="rule-text">
                        <h4>Daily Record</h4>
                        <p>Only one attendance record allowed per day.</p>
                    </div>
                </div>
                <div class="rule-item">
                    <div class="rule-badge badge-blue">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    </div>
                    <div class="rule-text">
                        <h4>Check-In</h4>
                        <p>Attendance automatically marked on first recognition.</p>
                    </div>
                </div>
                <div class="rule-item">
                    <div class="rule-badge badge-orange">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                    </div>
                    <div class="rule-text">
                        <h4>Check-Out</h4>
                        <p>Attendance marked after check-out confirmation.</p>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Checkout Confirmation Prompt in empty space of col_rules
        if st.session_state.get("show_leave_confirmation"):
            warning_msg = st.session_state.get("pending_checkout_warning")
            if warning_msg:
                st.warning(f"⚠️ {warning_msg}")
            user_id = st.session_state.pending_checkout_user_id
            user_name = st.session_state.pending_checkout_user_name
            user_role = st.session_state.get("pending_checkout_user_role", "user").lower()
            scanned = st.session_state.get("scanned_user") or {}
            
            # Render user avatar
            avatar_html = ""
            profile_image = scanned.get("profile_image")
            if profile_image and Path(profile_image).exists():
                import base64
                with open(profile_image, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                avatar_html = f'<img src="data:image/jpeg;base64,{img_b64}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 4px solid #DBEAFE; margin-bottom: 0.5rem;" />'
            else:
                avatar_html = '<svg viewBox="0 0 24 24" width="80" height="80" style="fill: #3b82f6; border-radius: 50%; background-color: #DBEAFE; padding: 10px; margin-bottom: 0.5rem;"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>'

            att_method = st.session_state.get("pending_attendance_method", "face")
            method_icon = "📷" if att_method == "face" else "👆"
            method_label = "Face Scan" if att_method == "face" else "Fingerprint"
            method_color = "#2563EB" if att_method == "face" else "#7C3AED"

            # Format role display
            role_display = user_role.replace("_", " ").title() if "_" in user_role else user_role.title()

            st.markdown(f"""
            <div class="saas-card" style="text-align: center; padding: 1.5rem; margin-top: 1rem; border: 1px solid rgba(0,0,0,0.05); box-shadow: 0 4px 15px rgba(0,0,0,0.03); border-radius: 20px;">
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 0.5rem;">
                    {avatar_html}
                    <h3 style="margin: 0.8rem 0 0.8rem 0; color: #1F2937; font-family: 'Inter', sans-serif; font-weight: 800; font-size: 1.8rem;">{user_name.title()}</h3>
                    <span style="background:#F8FAFC; color:{method_color}; border:1px solid #DBEAFE; border-radius:20px; padding:6px 16px; font-size:0.9rem; font-weight:700; margin-bottom:1.5rem; display:inline-flex; align-items:center; gap:0.4rem;">{method_icon} {method_label}</span>
                    <p style="margin: 0; color: #2563EB; font-family: 'Inter', sans-serif; font-weight: 700; font-size: 1.4rem;">Are you leaving now?</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            c_stay, c_leave = st.columns(2)
            with c_stay:
                st.markdown("<style>div[class*='st-key-btn_cancel_checkout'] button { background-color: #10B981 !important; color: white !important; border-color: #10B981 !important; font-weight: bold !important; }</style>", unsafe_allow_html=True)
                if st.button("Stay", key="btn_cancel_checkout", use_container_width=True):
                    st.session_state.status_message = ("info", "ℹ️ Okay, attendance unchanged.")
                    st.session_state.show_leave_confirmation = False
                    st.session_state.pending_checkout_user_id = None
                    st.session_state.pending_checkout_user_name = ""
                    st.session_state.pending_checkout_user_role = "user"
                    st.session_state.pending_attendance_method = "face"
                    st.session_state.scanned_user = None
                    st.session_state.pending_checkout_warning = None
                    if "cooldowns" not in st.session_state:
                        st.session_state.cooldowns = {}
                    st.session_state.cooldowns[user_id] = time.time()
                    st.session_state.cooldowns[f"ask_{user_id}"] = time.time()
                    st.session_state.scanning = True
                    st.rerun()
            with c_leave:
                st.markdown("<style>div[class*='st-key-btn_confirm_checkout'] button { background-color: #EF4444 !important; color: white !important; border-color: #EF4444 !important; font-weight: bold !important; }</style>", unsafe_allow_html=True)
                if st.button("Leave", type="primary", key="btn_confirm_checkout", use_container_width=True):
                    try:
                        res = api.check_out(user_id=user_id)
                        if res and res.get("status") == "ok":
                            st.session_state.status_message = ("success", f"✅ Check-Out successful! Have a great day.")
                        else:
                            st.session_state.status_message = ("error", f"❌ Failed to mark check-out for {user_name}")
                        # Stop scanning during checkout API call
                        st.session_state.scanning = False
                        if "camera" in st.session_state and st.session_state.camera is not None:
                            st.session_state.camera.release()
                            st.session_state.camera = None
                        
                        st.session_state.show_leave_confirmation = False
                        st.session_state.pending_checkout_user_id = None
                        st.session_state.pending_checkout_user_name = ""
                        st.session_state.pending_checkout_user_role = "user"
                        st.session_state.pending_attendance_method = "face"
                        st.session_state.scanned_user = None
                        st.session_state.pending_checkout_warning = None
                        if "cooldowns" not in st.session_state:
                            st.session_state.cooldowns = {}
                        st.session_state.cooldowns[user_id] = time.time()
                        st.session_state.cooldowns[f"ask_{user_id}"] = time.time()
                        st.session_state.scanning = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Checkout failed: {e}")

    with col_scanner:
        st.markdown('<div class="saas-card" style="text-align: center;">', unsafe_allow_html=True)
        st.markdown('<div class="scanner-card-marker"></div>', unsafe_allow_html=True)


        
        is_scanning = st.session_state.get("scanning", False)
        show_checkout = st.session_state.get("show_leave_confirmation", False)
        
        # Don't show scanner if checkout confirmation is active
        if show_checkout:
            is_scanning = False

        
        if not is_scanning:
            try:
                import base64
                with open("face_scanner_icon.png", "rb") as f:
                    icon_b64 = base64.b64encode(f.read()).decode()
            except Exception:
                icon_b64 = ""

            st.markdown(f"""
            <div style="text-align: center;">
                <h2 style='font-family: "Inter", sans-serif; font-weight: 800; color: #1F2937; margin-bottom: 0.5rem;'>Live Attendance Scanner</h2>
                <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 2rem;">Start camera scanning to mark attendance instantly.</p>
            </div>
            <div class="scan-circle-wrapper">
                <div class="scan-circle-ring-1"></div>
                <div class="scan-circle-ring-2"></div>
                <div class="scan-circle-center" style="background: none; border: none; box-shadow: none;">
                    <img src="data:image/png;base64,{icon_b64}" width="150" height="150" style="border-radius: 50%; border: 4px solid #DBEAFE; object-fit: cover;">
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<div class='custom-action-btn'>", unsafe_allow_html=True)
            if st.button(
                "Start Camera Scanner",
                type="primary",
                key="btn_start_scanner_custom",
            ):
                st.session_state.scanning = True
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

            # ── Fingerprint Attendance Button ──────────────────────────────────
            st.markdown("<hr style='margin: 1rem 0; border-color: #E5E7EB;'/>", unsafe_allow_html=True)
            st.markdown("""
            <div style='text-align:center; margin-bottom: 0.5rem;'>
                <span style='color:#64748B; font-size:0.85rem; font-weight:600;'>— OR —</span>
            </div>
            """, unsafe_allow_html=True)

            # WebAuthn result states
            if "webauthn_result" not in st.session_state:
                st.session_state.webauthn_result = None
            if "webauthn_processing" not in st.session_state:
                st.session_state.webauthn_processing = False

            # Inject WebAuthn JS that calls the backend and redirects with result
            # IMPORTANT: st.components.v1.html() must be used (not st.markdown) so <script> executes
            backend_url = getattr(api, "base_url", "http://127.0.0.1:8000")
            scanner_webauthn_html = f"""<!DOCTYPE html>
<!-- key: {st.session_state.webauthn_key} -->
<html>
<body style="margin:0;padding:0;background:transparent;text-align:center;">

<button id="fp-btn" onclick="startFingerprintAttendance()"
    style="background:linear-gradient(135deg,#7C3AED,#4F46E5);
           color:#fff;border:none;border-radius:30px;
           padding:0.75rem 2rem;font-size:0.95rem;font-weight:700;
           cursor:pointer;box-shadow:0 4px 15px rgba(99,102,241,0.35);
           display:inline-flex;align-items:center;gap:0.5rem;">
    👆 Fingerprint Attendance
</button>
<p id="fp-status" style="color:#94A3B8;font-size:0.78rem;margin:0.4rem 0 0 0;">
    ℹ️ Uses Windows Hello / Touch ID / Android biometric. No biometric data is sent to server.
</p>

<script>
const BACKEND = '{backend_url}';

function setStatus(msg, color) {{
    const el = document.getElementById('fp-status');
    if (el) {{ el.textContent = msg; el.style.color = color || '#94A3B8'; }}
}}

function b64url(buf) {{
    const bytes = new Uint8Array(buf);
    let s = '';
    for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
    return btoa(s).replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,'');
}}

function b64decode(b64) {{
    const std = b64.replace(/-/g,'+').replace(/_/g,'/');
    const bin = atob(std);
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
}}

async function startFingerprintAttendance() {{
    const btn = document.getElementById('fp-btn');
    if (btn) {{ btn.disabled = true; btn.textContent = '🔄 Scanning...'; }}
    setStatus('🔄 Scanning fingerprint...', '#7C3AED');

    try {{
        // Step 1: Get challenge (user_id=0 — server resolves user from credential_id)
        const chalResp = await fetch(BACKEND + '/webauthn/authenticate/challenge', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}}
            }});
        if (!chalResp.ok) throw new Error('Challenge request failed');
        const chalData = await chalResp.json();
        const challenge = b64decode(chalData.challenge);

        // Step 2: Browser biometric assertion
        const assertion = await navigator.credentials.get({{
            publicKey: {{
                challenge: challenge,
                timeout: 120000,
                userVerification: 'preferred',
                rpId: chalData.rp_id
            }}
        }});

        // Step 3: Encode assertion response
        const credId         = b64url(assertion.rawId);
        const clientDataJSON = b64url(assertion.response.clientDataJSON);
        const authData       = b64url(assertion.response.authenticatorData);
        const sig            = b64url(assertion.response.signature);
        const userHandle     = assertion.response.userHandle ? b64url(assertion.response.userHandle) : null;

        // Step 4: Send to backend
        const authResp = await fetch(BACKEND + '/webauthn/authenticate', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                credential_id: credId,
                client_data_json: clientDataJSON,
                authenticator_data: authData,
                signature: sig,
                user_handle: userHandle
            }})
        }});

        if (!authResp.ok) throw new Error('Authentication request failed: ' + authResp.status);
        const result = await authResp.json();

        // Step 5: Navigate parent with result
        const name    = encodeURIComponent(result.user_name || '');
        const uid     = result.user_id || '';
        const status  = result.status || 'error';
        const img     = encodeURIComponent(result.profile_image || '');
        const warning = encodeURIComponent(result.warning || '');
        const locMsg  = encodeURIComponent(result.message || '');
        setStatus('✅ Fingerprint verified.', '#166534');
        if (btn) {{ btn.disabled = false; btn.textContent = '👆 Fingerprint Attendance'; }}
        try {{
            const url = new URL(window.parent.location.href);
            url.searchParams.set('fp_status', status);
            url.searchParams.set('fp_user_id', uid);
            url.searchParams.set('fp_name', name);
            url.searchParams.set('fp_img', img);
            url.searchParams.set('fp_warning', warning);
            window.parent.location.href = url.href;
        }} catch(e) {{
            const parentUrl = document.referrer || window.location.href;
            let targetUrl = parentUrl.split('?')[0] + '?fp_status=' + status + '&fp_user_id=' + uid + '&fp_name=' + name + '&fp_img=' + img + '&fp_warning=' + warning;
            const a = document.createElement('a');
            a.href = targetUrl;
            a.target = '_parent';
            document.body.appendChild(a);
            a.click();
        }}

    }} catch(e) {{
        console.error('Fingerprint attendance error:', e);
        if (e.name === 'NotAllowedError') {{
            setStatus('❌ Cancelled by user.', '#EF4444');
        }} else if (e.name === 'NotSupportedError') {{
            setStatus('❌ Device does not support WebAuthn.', '#EF4444');
        }} else {{
            setStatus('❌ ' + e.message, '#EF4444');
        }}
        if (btn) {{ btn.disabled = false; btn.textContent = '👆 Fingerprint Attendance'; }}
        setTimeout(() => {{
            setStatus('ℹ️ Uses Windows Hello / Touch ID / Android biometric. No biometric data is sent to server.', '#94A3B8');
        }}, 3000);
    }}
}}
</script>
</body>
</html>"""
            components.html(scanner_webauthn_html, height=100) 
            cap = None


        else:
            st.markdown("""
            <div style="text-align: center;">
                <h2 style='font-family: "Inter", sans-serif; font-weight: 800; color: #1F2937; margin-bottom: 0.5rem;'>Live Attendance Scanner</h2>
                <p style="color: #2563EB; font-size: 0.95rem; margin-bottom: 1.5rem; font-weight: 600;">Webcam Active - Face recognition in progress</p>
            </div>
            """, unsafe_allow_html=True)
            
            frame_placeholder = st.empty()
            
            st.markdown("<div class='custom-action-btn'>", unsafe_allow_html=True)
            if st.button("Stop Camera Scanner", key="btn_stop_scanner_custom"):
                st.session_state.scanning = False
                if "camera" in st.session_state and st.session_state.camera is not None:
                    st.session_state.camera.release()
                    st.session_state.camera = None
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

            if "scan_stats" not in st.session_state:
                st.session_state.scan_stats = {"total_scans": 0, "recognized": 0}
            
            acc = 0.0
            if st.session_state.scan_stats["total_scans"] > 0:
                acc = (st.session_state.scan_stats["recognized"] / st.session_state.scan_stats["total_scans"]) * 100
                
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; margin-top: 2rem;">
                <div style="background: white; border-radius: 12px; padding: 1.5rem; text-align: center; width: 23%; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                    <h3 style="color: #60A5FA; font-size: 2rem; margin: 0; font-family: 'Inter', sans-serif; font-weight: 800;">{st.session_state.scan_stats['total_scans']}</h3>
                    <p style="color: #64748B; font-size: 0.8rem; margin: 0.5rem 0 0 0; font-weight: 600;">Total Scans</p>
                </div>
                <div style="background: white; border-radius: 12px; padding: 1.5rem; text-align: center; width: 23%; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                    <h3 style="color: #818CF8; font-size: 2rem; margin: 0; font-family: 'Inter', sans-serif; font-weight: 800;">{st.session_state.scan_stats['recognized']}</h3>
                    <p style="color: #64748B; font-size: 0.8rem; margin: 0.5rem 0 0 0; font-weight: 600;">Recognized</p>
                </div>
                <div style="background: white; border-radius: 12px; padding: 1.5rem; text-align: center; width: 23%; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                    <h3 style="color: #A78BFA; font-size: 2rem; margin: 0; font-family: 'Inter', sans-serif; font-weight: 800;">{acc:.1f}%</h3>
                    <p style="color: #64748B; font-size: 0.8rem; margin: 0.5rem 0 0 0; font-weight: 600;">Accuracy</p>
                </div>
                <div style="background: white; border-radius: 12px; padding: 1.5rem; text-align: center; width: 23%; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                    <h3 style="color: #93C5FD; font-size: 2rem; margin: 0; font-family: 'Inter', sans-serif; font-weight: 800;">54.5%</h3>
                    <p style="color: #64748B; font-size: 0.8rem; margin: 0.5rem 0 0 0; font-weight: 600;">Attendance Rate</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if "camera" not in st.session_state or st.session_state.camera is None or not st.session_state.camera.isOpened():
                # Don't start camera if checkout modal is active
                if not st.session_state.get("show_leave_confirmation"):
                    st.session_state.camera = cv2.VideoCapture(0)
                else:
                    st.session_state.camera = None
                
            cap = st.session_state.camera

        if cap is not None:
            if not cap.isOpened():
                status_placeholder.error("Cannot open system web-camera. Make sure it is connected.")
            else:
                last_call_time = 0.0
                scan_line_y = 0
                scan_dir = 1
            
                if "active_scanner_detections" not in st.session_state:
                    st.session_state.active_scanner_detections = []
                
                # Continuous scanner loop
                try:
                    while st.session_state.get("scanning", False):
                        # Break immediately if checkout modal is needed
                        if st.session_state.get("show_leave_confirmation"):
                            break
                            
                        ret, frame = cap.read()
                        if not ret:
                            time.sleep(0.05)
                            continue
                        
                        frame = cv2.flip(frame, 1)
                        clean_frame = frame.copy()
                        h, w, _ = frame.shape
                    
                        # Draw real-time bounding boxes
                        if st.session_state.get("active_scanner_detections"):
                            for det in st.session_state.active_scanner_detections:
                                bbox = det.get("bbox")
                                if bbox and len(bbox) == 4:
                                    x1, y1, x2, y2 = bbox
                                    name = det.get("name", "guest")
                                    status_det = det.get("status", "guest")
                                    user_id = det.get("user_id")
                                    draw_face_overlay(frame, x1, y1, x2, y2, name, user_id, status_det)
                        else:
                            # Local real-time face detection while backend recognition is processing
                            local_faces = detect_local_faces(clean_frame)

                            if local_faces:
                                # Show largest detected face like image 2
                                local_faces = sorted(
                                    local_faces,
                                    key=lambda b: (b[2] - b[0]) * (b[3] - b[1]),
                                    reverse=True
                                )

                                x1, y1, x2, y2 = local_faces[0]
                                draw_face_overlay(
                                    frame,
                                    x1, y1, x2, y2,
                                    "Detecting",
                                    None,
                                    "recognized"
                                )
                            else:
                                # Draw default guides only when no face detected
                                box_w, box_h = int(w * 0.45), int(h * 0.55)
                                bx1, by1 = int((w - box_w) / 2), int((h - box_h) / 2)
                                bx2, by2 = bx1 + box_w, by1 + box_h

                                cv2.rectangle(frame, (bx1, by1), (bx2, by2), (255, 255, 255), 2)
                                cv2.putText(
                                    frame,
                                    "ALIGN FACE HERE",
                                    (bx1 + 10, by1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.6,
                                    (255, 255, 255),
                                    2
                                )
                        
                        # Scanning line animation
                        scan_line_y += 8 * scan_dir
                        box_h_guide = int(h * 0.55)
                        if scan_line_y >= box_h_guide or scan_line_y <= 0:
                            scan_dir *= -1
                        by1_guide = int((h - box_h_guide)/2)
                        bx1_guide = int((w - int(w * 0.45))/2)
                        bx2_guide = bx1_guide + int(w * 0.45)
                        line_pos = by1_guide + scan_line_y
                        cv2.line(frame, (bx1_guide + 5, line_pos), (bx2_guide - 5, line_pos), (255, 255, 255), 2)
                    
                        frame_placeholder.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), channels="RGB")
                    
                        # Trigger API scan validation every 800ms
                        current_time = time.time()
                        if current_time - last_call_time >= 0.8:
                            last_call_time = current_time
                        
                            _, img_encoded = cv2.imencode('.jpg', clean_frame)
                            image_bytes = img_encoded.tobytes()
                        
                            try:
                                res = api.scan_attendance_face(image_bytes)
                                status = res.get("status")
                            
                                if status in ["checked_in", "already_completed", "ask_checkout", "not_approved"]:
                                    res["results"] = [{"status": status, "name": res.get("name"), "user_id": res.get("user_id"), "bbox": res.get("bbox", [])}]
                                    status = "recognized_multiple"
                                
                                if res and status == "recognized_multiple":
                                    items = res.get("results", [])
                                    st.session_state.active_scanner_detections = items
                                    
                                    # Update stats
                                    st.session_state.scan_stats["total_scans"] += len(items)
                                    st.session_state.scan_stats["recognized"] += sum(1 for it in items if it.get("status") not in ["guest", "unknown", "error"])
                                
                                    need_rerun = False
                                    messages = []
                                    has_guest = False
                                    
                                    for item in items:
                                        item_status = item.get("status")
                                        user_id = item.get("user_id")
                                        
                                        if item_status in ["guest", "unknown"]:
                                            has_guest = True
                                            continue
                                            
                                        if not user_id:
                                            continue
                                        
                                        # --- ask_checkout: MUST bypass 30s cooldown, but use its own 15s cooldown ---
                                        if item_status == "ask_checkout":
                                            last_ask_time = st.session_state.cooldowns.get(f"ask_{user_id}", 0)
                                            if current_time - last_ask_time >= 15.0:
                                                if not st.session_state.get("show_leave_confirmation"):
                                                    st.session_state.pending_checkout_user_id = user_id
                                                    st.session_state.pending_checkout_user_name = item["name"]
                                                    st.session_state.pending_checkout_user_role = item.get("role", "user")
                                                    st.session_state.pending_attendance_method = "face"
                                                    st.session_state.scanned_user = item
                                                    st.session_state.pending_checkout_warning = item.get("warning")
                                                    st.session_state.show_leave_confirmation = True
                                                st.session_state.scanning = False
                                                # Remove any stale cooldown so Leave card shows immediately
                                                st.session_state.cooldowns.pop(f"ask_{user_id}", None)
                                                if "camera" in st.session_state and st.session_state.camera is not None:
                                                    st.session_state.camera.release()
                                                    st.session_state.camera = None
                                                print("ASK_CHECKOUT triggered for:", user_id, item["name"])
                                                need_rerun = True
                                            continue  # skip cooldown logic below for ask_checkout
                                        
                                        # Check cooldown (30 seconds) — only for non-ask_checkout statuses
                                        last_action_time = st.session_state.cooldowns.get(user_id, 0)
                                        if current_time - last_action_time < 30.0:
                                            continue
                                        
                                        if item_status == "checked_in":
                                            st.session_state.cooldowns[user_id] = current_time
                                            messages.append(("success", f"✅ Attendance Marked! Welcome, {item['name']}."))
                                        
                                        elif item_status == "already_completed":
                                            st.session_state.cooldowns[user_id] = current_time
                                            messages.append(("info", f"ℹ️ Attendance already completed today."))


                                        elif item_status == "not_approved":
                                            st.session_state.cooldowns[user_id] = current_time
                                            messages.append(("warning", f"⏳ {item['name']}, your account is pending admin approval."))

                                        elif item_status == "error":
                                            st.session_state.cooldowns[user_id] = current_time
                                            err_msg = item.get("message") or "Failed to log attendance."
                                            messages.append(("warning", f"❌ {item.get('name', 'User')}: {err_msg}"))

                                        elif item_status == "method_mismatch":
                                            st.session_state.cooldowns[user_id] = current_time
                                            messages.append(("warning", f"❌ {item['name']}'s attendance is marked with your fingerprint"))
                                    
                                    if has_guest:
                                        last_guest_time = st.session_state.cooldowns.get("guest_face", 0)
                                        if current_time - last_guest_time >= 3.0:
                                            st.session_state.cooldowns["guest_face"] = current_time
                                            messages.append(("info", "👤 Guest detected. Face not registered — attendance cannot be marked."))
                                            
                                    if messages:
                                        with status_placeholder.container():
                                            for msg_type, msg_text in messages:
                                                if msg_type == "success":
                                                    st.success(msg_text)
                                                elif msg_type == "info":
                                                    st.info(msg_text)
                                                elif msg_type == "warning":
                                                    st.warning(msg_text)
                                                elif msg_type == "error":
                                                    st.error(msg_text)
                                                    
                                    if need_rerun:
                                        st.rerun()
                                    
                                elif status == "guest":
                                    st.session_state.active_scanner_detections = res.get("results", [])
                                    status_placeholder.info("👤 Guest Face Detected — Not Registered")
                                    
                                elif status in ["not_aligned", "no_face", "unknown"]:
                                    st.session_state.active_scanner_detections = []
                                
                            except Exception as e:
                                last_error_time = st.session_state.get("cooldowns", {}).get("scan_api_error", 0)
                                if current_time - last_error_time >= 5.0:
                                    st.session_state.cooldowns["scan_api_error"] = current_time
                                    status_placeholder.error(f"Scan failed: {e}")
                            
                        time.sleep(0.03)
                finally:
                    if not st.session_state.get("scanning", False):
                        if "camera" in st.session_state and st.session_state.camera is not None:
                            st.session_state.camera.release()
                            st.session_state.camera = None
        st.markdown('</div>', unsafe_allow_html=True)

