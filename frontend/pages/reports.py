from requests import api
import streamlit as st
import pandas as pd
from datetime import datetime, date
import logging

logger = logging.getLogger("faceai.reports")

def render_reports_page():
    st.markdown("<h2 style='color: #1F2937;'>📊 Admin Attendance Report Center</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748B;'>Query, filter, and download detailed employee attendance history reports.</p>", unsafe_allow_html=True)
    if not st.session_state.get("authenticated") or not st.session_state.get("user_id"):
        st.session_state.post_login_redirect = "Reports"
        st.session_state.current_page = "Login"
        st.rerun()
        
    api = st.session_state.get("api")

    if api is None:
        st.error("❌ API client not initialized. Please login again.")
        return
    
    # 1. Fetch users for filter dropdown
    try:
        raw_users = api.get_admin_users_list()
        user_options = {
            u.get("name", f"User {u.get('id')}"): u.get("id")
            for u in raw_users
            if isinstance(u, dict) and u.get("id")
        }
        user_list = ["All Users"] + list(user_options.keys())
    except Exception as e:
        logger.error(f"Failed to fetch users: {e}")
        user_list = ["All Users"]
        user_options = {}

    # Filters layout
    st.markdown("### Report Filters")
    col_date, col_month, col_year, col_user, col_status = st.columns(5)
    
    with col_date:
        filter_type = st.radio("Date Filter Style", ["None", "Single Date"], horizontal=True, key="rep_filter_style")
        if filter_type == "Single Date":
            sel_date = st.date_input("Date", value=datetime.today().date(), key="rep_date_input")
            date_str = sel_date.strftime("%Y-%m-%d")
        else:
            date_str = None
            
    with col_month:
        month_names = ["None", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        sel_month = st.selectbox("Month", month_names, key="rep_month_input")
        month_val = month_names.index(sel_month) if sel_month != "None" else None
        
    with col_year:
        years = ["None"] + [str(y) for y in range(2020, 2031)]
        sel_year = st.selectbox("Year", years, index=0, key="rep_year_input")
        year_val = int(sel_year) if sel_year != "None" else None
        
    with col_user:
        sel_user_name = st.selectbox("User", user_list, key="rep_user_input")
        user_id = user_options[sel_user_name] if sel_user_name != "All Users" else None
        
    with col_status:
        status_list = ["All Statuses", "Present", "Late", "Half Day", "Absent"]
        sel_status = st.selectbox("Status", status_list, key="rep_status_input")
        status_val = sel_status if sel_status != "All Statuses" else None
        
    # Execute query
    try:
        report_data = api.get_reports(
            date_str=date_str, 
            month_val=month_val, 
            year_val=year_val, 
            user_id=user_id, 
            status_val=status_val
        )
    except Exception as e:
        logger.error(f"Failed to fetch report data: {e}")
        st.warning(f"⚠️ Could not compile report: {e}")
        report_data = []
        
    # PDF download buttons or display grid
    if not report_data:
        st.info("No matching records found for the selected filters.")
    else:
        # Build Pandas DataFrame for clean presentation
        df_data = []
        for r in report_data:
            if not isinstance(r, dict):
                continue

            df_data.append({
                "User ID": r.get("user_id", "-"),
                "Employee ID": r.get("employee_id", "-"),
                "Name": r.get("name", "-"),
                "Email": r.get("email", "-"),
                "Role": r.get("role", "-"),
                "Department": r.get("department", "-"),
                "Status": r.get("attendance_status", "-"),
                "Check-In": r.get("check_in_time", "-"),
                "Check-Out": r.get("check_out_time", "-"),
                "Hours": r.get("working_hours", 0),
                "GPS Verified": "Yes" if r.get("location_verified") else "No",
                "Geo Fence": r.get("geo_fence_name", "-")
            })
            
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
        
        # Professional PDF Download Button
        try:
            pdf_bytes = api.get_reports_pdf(
                date_str=date_str, 
                month_val=month_val, 
                year_val=year_val, 
                user_id=user_id, 
                status_val=status_val
            )
            
            st.download_button(
                label="⬇️ Download PDF Report",
                data=pdf_bytes if pdf_bytes else b"",
                file_name=f"attendance_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Failed to compile PDF: {e}")
