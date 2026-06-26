import email
import profile
import html
from PIL.TiffImagePlugin import name
import streamlit as st
import datetime

def render_profile_page(api=None):
    if api is None:
        api = st.session_state.get("api")

    if api is None:
        st.error("❌ API client not initialized. Please login again.")
        return
    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <h2 style='color: #1F2937; font-family: "Inter", sans-serif; font-weight: 800; font-size: 2rem; margin: 0;'>👤 My Profile</h2>
        <p style='color: #64748B; font-size: 1rem; margin: 0;'>View and manage your account details.</p>
    </div>
    """, unsafe_allow_html=True)
    
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("❌ User session lost. Please log in again.")
        return
        
    try:
        with st.spinner("Loading profile..."):
            profile = api.get_user_profile(user_id)

            if not profile:
                st.error("❌ Profile data not found.")
                return
            
        # Update session state with fresh data per rule 8
        st.session_state.username = profile.get("name", "")
        st.session_state.email = profile.get("email", "")
        st.session_state.phone = profile.get("phone_number", "")
        st.session_state.department = profile.get("department", "")
        st.session_state.user_role = profile.get("role", "User")
        st.session_state.approval_status = profile.get("approval_status", "Pending")
        
        with st.container():
            st.markdown('<div class="saas-card-inside" style="padding: 1.5rem;">', unsafe_allow_html=True)
            
            # Profile Header
            col_img, col_info = st.columns([1, 4])
            with col_img:
                if profile.get("profile_image"):
                    # Assuming the backend provides a valid data URI or path. For now, use a generic avatar if we don't have a direct renderable image.
                    st.markdown("<div style='font-size: 4rem; text-align: center; border-radius: 50%; background: #F1F5F9; width: 100px; height: 100px; line-height: 100px;'>🧑‍💼</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div style='font-size: 4rem; text-align: center; border-radius: 50%; background: #F1F5F9; width: 100px; height: 100px; line-height: 100px;'>🧑‍💼</div>", unsafe_allow_html=True)
                    
            with col_info:
                name = html.escape(str(profile.get("name", "N/A")))
                email = html.escape(str(profile.get("email", "N/A")))

                st.markdown(f"<h3 style='margin: 0; color: #1F2937; font-size: 1.5rem;'>{name}</h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='margin: 0; color: #64748B; font-size: 1rem;'>{email}</p>", unsafe_allow_html=True)
                
                role_badge = f"<span style='background-color: #DBEAFE; color: #1D4ED8; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.875rem; font-weight: 600; display: inline-block; margin-top: 0.5rem;'>{profile.get('role', 'N/A')}</span>"
                status_badge = f"<span style='background-color: #D1FAE5; color: #065F46; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.875rem; font-weight: 600; display: inline-block; margin-top: 0.5rem; margin-left: 0.5rem;'>{profile.get('approval_status', 'N/A')}</span>"
                if profile.get('approval_status') != 'Approved':
                    status_badge = f"<span style='background-color: #FEF3C7; color: #92400E; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.875rem; font-weight: 600; display: inline-block; margin-top: 0.5rem; margin-left: 0.5rem;'>{profile.get('approval_status', 'N/A')}</span>"
                
                st.markdown(f"{role_badge} {status_badge}", unsafe_allow_html=True)
                
            st.markdown("<hr style='margin: 1.5rem 0; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
            
            # Details Grid
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Phone Number:**")
                st.write(profile.get("phone_number", "N/A"))
                
                st.markdown("**Department:**")
                st.write(profile.get("department", "N/A") or "None")
                
                st.markdown("**Account Created:**")
                st.write(profile.get("created_at", "N/A"))
                
            with col2:
                st.markdown("**Face Enrollment Status:**")
                if profile.get("has_face_enrolled"):
                    st.success("✅ Enrolled")
                    st.caption(f"Last updated: {profile.get('last_face_update')}")
                else:
                    st.error("❌ Not Enrolled")
                    
                st.markdown("**Fingerprint Status:**")
                if profile.get("has_fingerprint"):
                    st.success("✅ Enrolled (WebAuthn)")
                else:
                    st.warning("⚠️ Not Enrolled")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
        # Action Buttons
        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            if st.button("Update Face Profile", type="primary", use_container_width=True, key="btn_profile_update_face"):
                st.session_state.update_face_pose_idx = 0
                st.session_state.update_face_captures = {}
                st.session_state.current_page = "Update Face Profile"
                st.rerun()

    except Exception as e:
        import requests
        if isinstance(e, requests.exceptions.ConnectionError) or "Failed to establish" in str(e):
            st.error("❌ Connection to the backend server failed.")
        else:
            st.error(f"Failed to load profile details: {e}")
