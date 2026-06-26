from requests import api
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import logging
import streamlit.components.v1 as components

logger = logging.getLogger("faceai.geo_settings")

def render_geo_settings():
    st.markdown("<h2 style='color: #1F2937;'>📍 Geo Location Settings</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748B;'>Configure and manage office geofences for secure biometric check-in.</p>", unsafe_allow_html=True)

    api = st.session_state.get("api")

    if api is None:
        st.error("API client not initialized. Please login again.")
        return

    # ── Handle "Use My Current Location" query-param injection ──────────────
    try:
        geo_lat_q = st.query_params.get("geo_lat")
        geo_lon_q = st.query_params.get("geo_lon")
    except Exception:
        params = st.experimental_get_query_params()
        geo_lat_q = params.get("geo_lat", [None])[0]
        geo_lon_q = params.get("geo_lon", [None])[0]
    if geo_lat_q and geo_lon_q:
        try:
            st.session_state.fence_lat = float(geo_lat_q)
            st.session_state.fence_lon = float(geo_lon_q)
        except ValueError:
            pass
        st.query_params.clear()
        st.rerun()

    # ── Initialize form state ────────────────────────────────────────────────
    if "fence_edit_id" not in st.session_state:
        st.session_state.fence_edit_id = None
        st.session_state.fence_name = ""
        # Use admin's already-captured GPS location if available, else sane default
        st.session_state.fence_lat = st.session_state.get("latitude") or 11.6643
        st.session_state.fence_lon = st.session_state.get("longitude") or 78.1460
        st.session_state.fence_radius = 100.0
        st.session_state.fence_active = True

    # ── Fetch all geofences ──────────────────────────────────────────────────
    try:
        fences = api.get_geofences()
    except Exception as e:
        st.error(f"Failed to fetch geofences: {e}")
        fences = []

    # ── Layout ───────────────────────────────────────────────────────────────
    col_list, col_form = st.columns([1.2, 1])

    with col_list:
        st.markdown("### Active Geofences")
        if not fences:
            st.info("No geofences configured. Add one on the right.")
        else:
            for f in fences:
                # is_active may be 1/0 (MySQL TINYINT) or True/False — normalise
                is_active = bool(f.get("is_active", True))
                status_emoji = "🟢" if is_active else "🔴"
                with st.container():
                    st.markdown(
                        f"""
                        <div class="saas-card" style="margin-bottom: 0.75rem; padding: 0.75rem;">
                            <strong>{status_emoji} {f.get("location_name", "Unnamed Location")}</strong><br>
                            <span style="font-size: 0.85rem; color: #6B7280;">
                                Lat: {f.get("latitude", 0.0):.6f}, Lon: {f.get("longitude", 0.0):.6f}<br>
                                Radius: {f.get("radius_meters", 100)} meters
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button("Edit", key=f"edit_{f['id']}", use_container_width=True):
                            st.session_state.fence_edit_id = f["id"]
                            st.session_state.fence_name = f["location_name"]
                            st.session_state.fence_lat = float(f["latitude"])
                            st.session_state.fence_lon = float(f["longitude"])
                            st.session_state.fence_radius = float(f["radius_meters"])
                            st.session_state.fence_active = bool(f["is_active"])
                            st.rerun()
                    with c2:
                        toggle_label = "Deactivate" if is_active else "Activate"
                        if st.button(toggle_label, key=f"toggle_{f['id']}", use_container_width=True):
                            try:
                                api.update_geofence(
                                    f["id"],
                                    f["location_name"],
                                    float(f["latitude"]),
                                    float(f["longitude"]),
                                    float(f["radius_meters"]),
                                    not is_active
                                )
                                st.success("✅ Geofence status updated!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")
                    with c3:
                        if st.button("Delete", key=f"del_{f['id']}", type="secondary", use_container_width=True):
                            try:
                                api.delete_geofence(f["id"])
                                st.success("🗑️ Geofence deleted!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")

    with col_form:
        if st.session_state.fence_edit_id:
            st.markdown(f"### ✏️ Edit Geofence (ID: {st.session_state.fence_edit_id})")
        else:
            st.markdown("### ➕ Create New Geofence")

        # ── "Use My Current Location" button ────────────────────────────────
        admin_lat = st.session_state.get("latitude")
        admin_lon = st.session_state.get("longitude")
        if admin_lat is not None and admin_lon is not None:
            if st.button("📍 Use My Current Location", use_container_width=True, key="btn_use_my_loc"):
                st.session_state.fence_lat = float(admin_lat)
                st.session_state.fence_lon = float(admin_lon)
                st.rerun()
            st.caption(f"Your GPS: {admin_lat:.6f}, {admin_lon:.6f}")
        else:
            # Inject JS to grab location and pass via query params
            components.html( 
                """
                <button onclick="getMyLocation()"
                    style="width:100%;background:linear-gradient(135deg,#2563EB,#1D4ED8);
                           color:#fff;border:none;border-radius:8px;padding:0.6rem 1rem;
                           font-size:0.9rem;font-weight:700;cursor:pointer;">
                    📍 Detect My Current Location
                </button>
                <p id="loc-status" style="color:#94A3B8;font-size:0.78rem;margin:0.3rem 0 0 0;">
                    Click to detect your GPS coordinates
                </p>
                <script>
                function getMyLocation() {
                    const s = document.getElementById('loc-status');
                    if(s) { s.textContent = '🔄 Detecting...'; s.style.color='#7C3AED'; }
                    navigator.geolocation.getCurrentPosition(
                        function(pos) {
                            const lat = pos.coords.latitude;
                            const lon = pos.coords.longitude;
                            if(s) { s.textContent = '✅ Got: ' + lat.toFixed(6) + ', ' + lon.toFixed(6); s.style.color='#166534'; }
                            try {
                                const url = new URL(window.parent.location.href);
                                url.searchParams.set('geo_lat', lat);
                                url.searchParams.set('geo_lon', lon);
                                window.parent.location.href = url.href;
                            } catch(e) {
                                const a = document.createElement('a');
                                a.href = (document.referrer || window.location.href).split('?')[0]
                                       + '?geo_lat=' + lat + '&geo_lon=' + lon;
                                a.target = '_parent';
                                document.body.appendChild(a);
                                a.click();
                            }
                        },
                        function(err) {
                            if(s) { s.textContent = '❌ ' + err.message; s.style.color='#DC2626'; }
                        },
                        { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
                    );
                }
                </script>
                """,
                height=70
            )

        st.markdown("---")
        name = st.text_input("Location Name", value=st.session_state.fence_name, placeholder="e.g. Head Office")
        lat = st.number_input("Latitude", value=float(st.session_state.fence_lat), format="%.6f", step=0.000001)
        lon = st.number_input("Longitude", value=float(st.session_state.fence_lon), format="%.6f", step=0.000001)
        radius = st.number_input("Radius (meters)", value=float(st.session_state.fence_radius), min_value=10.0, max_value=5000.0, step=10.0)
        active = st.checkbox("Is Active", value=bool(st.session_state.fence_active))

        # Live map preview
        try:
            map_df = pd.DataFrame({"lat": [lat], "lon": [lon]})
            st.map(map_df, zoom=16)
        except Exception:
            st.caption(f"Map preview: {lat:.6f}, {lon:.6f}")

        c1, c2 = st.columns(2)
        DEFAULT_LAT = st.session_state.get("latitude") or 11.6643
        DEFAULT_LON = st.session_state.get("longitude") or 78.1460

        with c1:
            if st.session_state.fence_edit_id:
                if st.button("💾 Update Geofence", type="primary", use_container_width=True):
                    if not name.strip():
                        st.error("❌ Location name is required.")
                    else:
                        try:
                            api.update_geofence(st.session_state.fence_edit_id, name.strip(), lat, lon, radius, active)
                            st.success("✅ Geofence updated successfully!")
                            st.session_state.fence_edit_id = None
                            st.session_state.fence_name = ""
                            st.session_state.fence_lat = DEFAULT_LAT
                            st.session_state.fence_lon = DEFAULT_LON
                            st.session_state.fence_radius = 100.0
                            st.session_state.fence_active = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ {e}")
            else:
                if st.button("💾 Save Geofence", type="primary", use_container_width=True):
                    if not name.strip():
                        st.error("❌ Location name is required.")
                    else:
                        try:
                            api.create_geofence(name.strip(), lat, lon, radius, active)
                            st.success("✅ Geofence created successfully!")
                            st.session_state.fence_name = ""
                            st.session_state.fence_lat = DEFAULT_LAT
                            st.session_state.fence_lon = DEFAULT_LON
                            st.session_state.fence_radius = 100.0
                            st.session_state.fence_active = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ {e}")
        with c2:
            if st.button("🔄 Reset Form", use_container_width=True):
                st.session_state.fence_edit_id = None
                st.session_state.fence_name = ""
                st.session_state.fence_lat = DEFAULT_LAT
                st.session_state.fence_lon = DEFAULT_LON
                st.session_state.fence_radius = 100.0
                st.session_state.fence_active = True
                st.rerun()
