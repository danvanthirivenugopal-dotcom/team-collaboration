import streamlit as st
import cv2
import time
import base64
from io import BytesIO
from pathlib import Path
import streamlit.components.v1 as components


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

    if "user_lat" not in st.session_state or "user_lon" not in st.session_state:
        user_lat_q = st.query_params.get("user_lat")
        user_lon_q = st.query_params.get("user_lon")
        
        geo_error_q = st.query_params.get("geo_error")
        if user_lat_q and user_lon_q:
            st.session_state.user_lat = float(user_lat_q)
            st.session_state.user_lon = float(user_lon_q)
            st.query_params.pop("user_lat", None)
            st.query_params.pop("user_lon", None)
            st.query_params.pop("geo_error", None)
        elif geo_error_q:
            st.session_state.user_lat = None
            st.session_state.user_lon = None
            st.error(f"Browser Location Error: {geo_error_q}. Please ensure you are on localhost or HTTPS, and have granted location permissions.")
            st.query_params.pop("geo_error", None)
        else:
            st.session_state.user_lat = None
            st.session_state.user_lon = None
            st.components.v1.html("""
            <script>
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        const urlParams = new URLSearchParams(window.parent.location.search);
                        if (!urlParams.has('user_lat')) {
                            urlParams.set('user_lat', position.coords.latitude);
                            urlParams.set('user_lon', position.coords.longitude);
                            window.parent.location.search = urlParams.toString();
                        }
                    },
                    (error) => {
                        let errMsg = error.message;
                        if (error.code === error.PERMISSION_DENIED) errMsg = "Permission Denied";
                        else if (error.code === error.POSITION_UNAVAILABLE) errMsg = "Position Unavailable";
                        else if (error.code === error.TIMEOUT) errMsg = "Timeout";
                        
                        const urlParams = new URLSearchParams(window.parent.location.search);
                        if (!urlParams.has('geo_error')) {
                            urlParams.set('geo_error', errMsg);
                            window.parent.location.search = urlParams.toString();
                        }
                    }
                );
            } else {
                const urlParams = new URLSearchParams(window.parent.location.search);
                urlParams.set('geo_error', 'Geolocation API not supported by browser (or blocked due to HTTP/iframe rules)');
                window.parent.location.search = urlParams.toString();
            }
            </script>
            """, height=0, width=0)


    # Handle a pending WebAuthn result from JS first thing
    fp_user_id_q = st.query_params.get("fp_user_id")
    fp_name_q = st.query_params.get("fp_name")
    fp_status_q = st.query_params.get("fp_status")
    
    fc_status_q = st.query_params.get("fc_status")
    fc_user_id_q = st.query_params.get("fc_user_id")
    fc_name_q = st.query_params.get("fc_name")
    fc_role_q = st.query_params.get("fc_role")

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

    if fc_status_q:
        if fc_status_q == "ask_checkout" and fc_user_id_q and fc_name_q:
            if not st.session_state.get("show_leave_confirmation"):
                st.session_state.pending_checkout_user_id = int(fc_user_id_q)
                st.session_state.pending_checkout_user_name = fc_name_q
                st.session_state.pending_checkout_user_role = fc_role_q if fc_role_q else "user"
                st.session_state.pending_attendance_method = "face"
                st.session_state.show_leave_confirmation = True
                
                # Fetch warning if needed (or pass via URL, omitted for brevity)
                st.session_state.pending_checkout_warning = None
                
                # Clean URL and rerun
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
                    <span style="background:var(--secondary-background-color); color:{method_color}; border:1px solid #DBEAFE; border-radius:20px; padding:6px 16px; font-size:0.9rem; font-weight:700; margin-bottom:1.5rem; display:inline-flex; align-items:center; gap:0.4rem;">{method_icon} {method_label}</span>
                    <p style="margin: 0; color: #2563EB; font-family: 'Inter', sans-serif; font-weight: 700; font-size: 1.4rem;">Are you leaving now?</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            c_stay, c_leave = st.columns(2)
            with c_stay:
                
                if st.button("Stay", key="btn_cancel_checkout", use_container_width=True):
                    st.session_state.status_message = ("info", "Attendance remains active. Checkout was not marked.")
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
                
                if st.button("Leave", type="primary", key="btn_confirm_checkout", use_container_width=True):
                    try:
                        res = api.check_out(user_id=user_id)
                        if res and res.get("status") == "ok":
                            st.session_state.status_message = ("success", f"{user_name}, checkout time successfully marked.")
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
        
        is_scanning = st.session_state.get("scanning", False)
        show_checkout = st.session_state.get("show_leave_confirmation", False)
        
        # Don't show scanner if checkout confirmation is active
        if show_checkout:
            pass # Do not hide camera during prompt

        # ALWAYS SHOW TITLE
        st.markdown("""
        <div style="text-align: center;">
            <h2 style='font-family: "Inter", sans-serif; font-weight: 800; color: #1F2937; margin-bottom: 0.5rem;'>Live Attendance Scanner</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 2rem;">Start camera scanning to mark attendance instantly.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if not is_scanning:
            try:
                import base64
                with open("face_scanner_icon.png", "rb") as f:
                    icon_b64 = base64.b64encode(f.read()).decode()
            except Exception:
                icon_b64 = ""

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
            


            # --- NATIVE JAVASCRIPT WEBRTC SCANNER ---
            backend_url = getattr(api, "base_url", "http://127.0.0.1:8000")
            org_id = st.session_state.get("organization_id", 1)
            token = st.session_state.get("token", "")
            
            webrtc_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; display: flex; justify-content: center; align-items: center; position: relative; font-family: 'Inter', sans-serif; }}
                    #container {{ position: relative; width: 100%; max-width: 640px; aspect-ratio: 4/3; background: transparent; overflow: hidden; border-radius: 12px; }}
                    video {{ width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }}
                    canvas {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }}
                    #toast-container {{ position: absolute; top: 10px; left: 10px; right: 10px; z-index: 10; display: flex; flex-direction: column; gap: 8px; pointer-events: none; }}
                    .toast {{ background: rgba(0,0,0,0.7); color: white; padding: 10px 15px; border-radius: 8px; font-size: 14px; backdrop-filter: blur(4px); box-shadow: 0 4px 6px rgba(0,0,0,0.3); animation: slideIn 0.3s ease-out; transform-origin: top; }}
                    .toast.success {{ border-left: 4px solid #10B981; }}
                    .toast.warning {{ border-left: 4px solid #F59E0B; }}
                    .toast.error {{ border-left: 4px solid #EF4444; }}
                    .toast.info {{ border-left: 4px solid #3B82F6; }}
                    #controls {{ position: absolute; bottom: 15px; right: 15px; z-index: 20; display: flex; gap: 10px; }}
                    .btn {{ background: rgba(0, 0, 0, 0.7); border: 1px solid rgba(255,255,255,0.4); color: white; padding: 8px 12px; border-radius: 6px; cursor: pointer; backdrop-filter: blur(4px); font-size: 13px; font-weight: bold; transition: all 0.2s; box-shadow: 0 4px 6px rgba(0,0,0,0.5); }}
                    .btn:hover {{ background: rgba(0, 0, 0, 0.9); border-color: rgba(255,255,255,0.8); }}
                    #guide {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 45%; height: 55%; border: 2px dashed rgba(255,255,255,0.5); pointer-events: none; }}
                    #guide::after {{ content: 'ALIGN FACE HERE'; position: absolute; top: -25px; left: 50%; transform: translateX(-50%); color: rgba(255,255,255,0.7); font-size: 14px; font-weight: bold; white-space: nowrap; }}
                    @keyframes slideIn {{ from {{ transform: translateY(-20px); opacity: 0; }} to {{ transform: translateY(0); opacity: 1; }} }}
                </style>
            </head>
            <body>
                <div id="container">
                    <video id="video" autoplay playsinline muted></video>
                    <canvas id="canvas"></canvas>
                    <div id="guide"></div>
                    <div id="toast-container"></div>
                    <div id="controls">
                        <button class="btn" id="btn-switch-cam" onclick="switchCamera()">🔄 Switch Camera</button>
                    </div>
                </div>

                <script>
                    const video = document.getElementById('video');
                    const canvas = document.getElementById('canvas');
                    const ctx = canvas.getContext('2d');
                    const toastContainer = document.getElementById('toast-container');
                    const BACKEND_URL = "{backend_url}";
                    const ORG_ID = {org_id};
                    const IS_PROMPT_ACTIVE = {str(show_checkout).lower()};
                    
                    let stream = null;
                    let facingMode = "user";
                    let isScanning = false;
                    let scanInterval = null;
                    
                    let currentLat = null;
                    let currentLon = null;
                    
                    const cooldowns = new Map();

                    function showToast(msg, type='info', duration=4000) {{
                        const el = document.createElement('div');
                        el.className = `toast ${{type}}`;
                        el.innerHTML = msg;
                        toastContainer.appendChild(el);
                        setTimeout(() => {{
                            el.style.opacity = '0';
                            el.style.transition = 'opacity 0.3s';
                            setTimeout(() => el.remove(), 300);
                        }}, duration);
                    }}

                    // 1. Initialize Geolocation
                    function initGeolocation() {{
                        if (navigator.geolocation) {{
                            navigator.geolocation.getCurrentPosition(
                                (pos) => {{
                                    currentLat = pos.coords.latitude;
                                    currentLon = pos.coords.longitude;
                                    showToast("📍 Location acquired.", "success", 2000);
                                }},
                                (err) => {{
                                    showToast("⚠️ Location access denied. Attendance may fail.", "error");
                                }},
                                {{ enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }}
                            );
                        }}
                    }}

                    // 2. Initialize Camera
                    async function startCamera() {{
                        if (stream) {{
                            stream.getTracks().forEach(t => t.stop());
                        }}
                        try {{
                            stream = await navigator.mediaDevices.getUserMedia({{
                                video: {{ facingMode: facingMode, width: {{ ideal: 640 }}, height: {{ ideal: 480 }} }},
                                audio: false
                            }});
                            video.srcObject = stream;
                            
                            video.onloadedmetadata = () => {{
                                canvas.width = video.videoWidth;
                                canvas.height = video.videoHeight;
                                if(!isScanning) {{
                                    isScanning = true;
                                    scanInterval = setInterval(processFrame, 800);
                                }}
                            }};
                        }} catch (err) {{
                            showToast("❌ Camera Error: " + err.message, "error", 10000);
                        }}
                    }}

                    function switchCamera() {{
                        facingMode = facingMode === "user" ? "environment" : "user";
                        startCamera();
                    }}

                    // 3. Process Frame
                    async function processFrame() {{
                        if (IS_PROMPT_ACTIVE) return;
                        if (!video.videoWidth) return;
                        
                        // Create a temporary canvas to get the blob
                        const tempCanvas = document.createElement('canvas');
                        tempCanvas.width = video.videoWidth;
                        tempCanvas.height = video.videoHeight;
                        const tctx = tempCanvas.getContext('2d');
                        
                        // We no longer mirror the canvas before sending to the backend!
                        // Sending the raw original feed ensures the backend bounding box coordinates
                        // map perfectly to the un-mirrored feed, which is then visually flipped by CSS.
                        tctx.drawImage(video, 0, 0);
                        
                        tempCanvas.toBlob(async (blob) => {{
                            if (!blob) return;
                            
                            const formData = new FormData();
                            formData.append("image", blob, "frame.jpg");
                            if (currentLat) formData.append("latitude", currentLat);
                            if (currentLon) formData.append("longitude", currentLon);
                            
                            try {{
                                const headers = {{
                                    "Authorization": "Bearer {token}"
                                }};
                                const res = await fetch(BACKEND_URL + "/attendance/scan?organization_id=" + ORG_ID, {{
                                    method: "POST",
                                    body: formData,
                                    headers: headers
                                }});
                                
                                if (res.ok) {{
                                    const data = await res.json();
                                    handleScanResponse(data);
                                }}
                            }} catch (e) {{
                                console.error("Scan API error:", e);
                            }}
                        }}, 'image/jpeg', 0.8);
                    }}

                    function drawBoundingBox(bbox, label1, label2, color) {{
                        const [x1, y1, x2, y2] = bbox;
                        
                        // If camera is mirrored on screen (user facing), we must mirror coordinates on canvas
                        let drawX1 = x1;
                        let drawX2 = x2;
                        
                        ctx.strokeStyle = color;
                        ctx.lineWidth = 3;
                        ctx.strokeRect(drawX1, y1, drawX2 - drawX1, y2 - y1);
                        
                        // Background for text
                        ctx.fillStyle = color;
                        ctx.font = "bold 14px Arial";
                        const w1 = ctx.measureText(label1).width;
                        const w2 = ctx.measureText(label2).width;
                        const maxW = Math.max(w1, w2) + 16;
                        
                        ctx.fillRect(drawX1, y1 - 45, maxW, 40);
                        
                        // Text
                        ctx.fillStyle = "#ffffff";
                        ctx.fillText(label1, drawX1 + 8, y1 - 25);
                        ctx.font = "12px Arial";
                        ctx.fillText(label2, drawX1 + 8, y1 - 9);
                    }}

                    function handleScanResponse(data) {{
                        // Clear previous drawings
                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                        
                        // Check for warnings like animals/weapons
                        if (data.detection_warnings && data.detection_warnings.length > 0) {{
                            data.detection_warnings.forEach(w => showToast("⚠️ " + w, "warning"));
                        }}
                        
                        let results = data.results || [];
                        if (data.status && !data.results) {{
                            // Wrap single response in array
                            results = [data];
                        }}
                        
                        const now = Date.now();
                        
                        results.forEach(item => {{
                            if (!item.bbox || item.bbox.length !== 4) return;
                            
                            const status = item.status;
                            const name = item.name || "Unknown";
                            const uid = item.user_id;
                            
                            let boxColor = "#ef4444"; // red
                            let statusText = "UNKNOWN";
                            
                            if (status === "recognized" || status === "checked_in") {{
                                boxColor = "#00ffff"; // cyan
                                statusText = "MARKED";
                            }} else if (["already_marked", "already_completed", "ask_leave"].includes(status)) {{
                                boxColor = "#00ffff";
                                statusText = "ALREADY MARKED";
                            }} else if (status === "disabled") {{
                                boxColor = "#f59e0b";
                                statusText = "INACTIVE";
                            }} else if (status === "not_approved") {{
                                boxColor = "#f59e0b";
                                statusText = "PENDING";
                            }} else if (status === "location_error") {{
                                boxColor = "#f59e0b";
                                statusText = "LOCATION ERROR";
                            }} else if (status === "method_mismatch") {{
                                boxColor = "#f59e0b";
                                statusText = "FINGERPRINT ONLY";
                            }}
                            
                            drawBoundingBox(item.bbox, `${{name.toUpperCase()}} (${{statusText}})`, uid ? `ID: STU${{100+uid}}` : "Unregistered", boxColor);
                            
                            // Process status logic and notifications
                            if (uid) {{
                                if (status === "ask_checkout") {{
                                    const cd = cooldowns.get("ask_" + uid) || 0;
                                    if (now - cd > 15000) {{
                                        cooldowns.set("ask_" + uid, now);
                                        // Redirect parent to show checkout dialog
                                        try {{
                                            const url = new URL(window.parent.location.href);
                                            url.searchParams.set('fc_status', 'ask_checkout');
                                            url.searchParams.set('fc_user_id', uid);
                                            url.searchParams.set('fc_name', name);
                                            url.searchParams.set('fc_role', item.role || 'user');
                                            window.parent.location.href = url.href;
                                        }} catch(e) {{
                                            showToast("⚠️ Could not trigger checkout. Parent frame blocked.", "error");
                                        }}
                                    }}
                                }} else {{
                                    const cd = cooldowns.get("act_" + uid) || 0;
                                    if (now - cd > 30000) {{
                                        if (status === "checked_in") {{
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`${{name}}, attendance successfully marked.`, "success");
                                        }} else if (status === "already_completed") {{
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`${{name}}, today's attendance is already completed.`, "info");
                                        }} else if (status === "disabled") {{
                                            cooldowns.set("act_" + uid, now);
                                            showToast("This account is inactive. Contact your organization administrator.", "error");
                                        }} else if (status === "not_approved") {{
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`${{name}}, your account is awaiting approval. Attendance cannot be marked.`, "warning");
                                        }} else if (status === "location_error") {{
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`${{name}}, you are not in the approved location.`, "error");
                                        }} else if (status === "method_mismatch") {{
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`${{name}}'s attendance is mapped to fingerprint.`, "error");
                                        }}
                                    }}
                                }}
                            }} else {{
                                const cd = cooldowns.get("act_unknown") || 0;
                                if (now - cd > 30000) {{
                                    if (status === "unknown") {{
                                        cooldowns.set("act_unknown", now);
                                        showToast("Unknown user detected. No attendance was marked.", "error");
                                    }} else if (status === "multiple_faces") {{
                                        cooldowns.set("act_unknown", now);
                                        showToast("Multiple faces detected. Only one person can mark attendance at a time.", "error");
                                    }}
                                }}
                            }}
                        }});
                    }}

                    // Start everything
                    initGeolocation();
                    startCamera();
                </script>
            </body>
            </html>
            """
            components.html(webrtc_html, height=480)

            st.markdown("<div class='custom-action-btn' style='margin-top: 1rem;'>", unsafe_allow_html=True)
            if st.button("Stop Camera Scanner", key="btn_stop_scanner_custom", type="primary", use_container_width=True):
                st.session_state.scanning = False
                if "camera" in st.session_state and st.session_state.camera is not None:
                    try:
                        st.session_state.camera.release()
                    except:
                        pass
                    st.session_state.camera = None
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
