import pathlib

file_path = pathlib.Path(r'D:\FaceAI_Project(!@#)\frontend\modules\scanner.py')
text = file_path.read_text('utf-8')

# Remove the top button and st.rerun()
target_to_remove = """            if st.button("Stop Camera Scanner", key="btn_stop_scanner_custom", type="primary", use_container_width=True):
                st.session_state.scanning = False
                if "camera" in st.session_state and st.session_state.camera is not None:
                    try:
                        st.session_state.camera.release()
                    except:
                        pass
                    st.session_state.camera = None
            st.rerun()"""
text = text.replace(target_to_remove, '')

# Fix subtitle
old_subtitle = '<p style="color: #2563EB; font-size: 0.95rem; margin-bottom: 1.5rem; font-weight: 600;">Webcam Active - Face recognition in progress</p>'
new_subtitle = '<p style="color: #64748B; font-size: 0.95rem; margin-bottom: 2rem;">Start camera scanning to mark attendance instantly.</p>'
text = text.replace(old_subtitle, new_subtitle)

# Add the button at the bottom properly
# Check if it's already there to prevent duplicates
bottom_button = """            st.markdown("<div class='custom-action-btn' style='margin-top: 1rem;'>", unsafe_allow_html=True)
            if st.button("Stop Camera Scanner", key="btn_stop_scanner_custom", type="primary", use_container_width=True):
                st.session_state.scanning = False
                if "camera" in st.session_state and st.session_state.camera is not None:
                    try:
                        st.session_state.camera.release()
                    except:
                        pass
                    st.session_state.camera = None
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)"""

if "btn_stop_scanner_custom" not in text:
    text += "\n" + bottom_button + "\n"

file_path.write_text(text, 'utf-8')
print("Successfully updated scanner.py")
