import streamlit as st

# Theme Tokens based on Modern UI Design System
THEMES = {
    "light": {
        "--app-bg": "#F8FAFC",
        "--surface": "#FFFFFF",
        "--surface-secondary": "#F1F5F9",
        "--surface-hover": "#E2E8F0",
        "--card-bg": "#FFFFFF",
        "--sidebar-bg": "#F8FAFC",
        "--text-primary": "#0F172A",
        "--text-secondary": "#475569",
        "--text-muted": "#64748B",
        "--border": "#CBD5E1",
        "--input-bg": "#FFFFFF",
        "--input-text": "#0F172A",
        "--placeholder": "#94A3B8",
        "--primary": "#2563EB",
        "--primary-hover": "#1D4ED8",
        "--secondary": "#475569",
        "--success": "#10B981",
        "--warning": "#F59E0B",
        "--error": "#EF4444",
        "--info": "#3B82F6",
        "--shadow": "0 12px 35px rgba(15, 23, 42, 0.08)",
        "--disabled-bg": "#F1F5F9",
        "--disabled-text": "#94A3B8",
        "--table-header": "#F8FAFC",
        "--table-row": "#FFFFFF",
        "--table-row-hover": "#F1F5F9",
        "--overlay": "rgba(255, 255, 255, 0.75)"
    },
    "dark": {
        "--app-bg": "#0F172A",
        "--surface": "#111827",
        "--surface-secondary": "#1E293B",
        "--surface-hover": "#334155",
        "--card-bg": "#111827",
        "--sidebar-bg": "#0F172A",
        "--text-primary": "#F8FAFC",
        "--text-secondary": "#CBD5E1",
        "--text-muted": "#94A3B8",
        "--border": "#334155",
        "--input-bg": "#1E293B",
        "--input-text": "#F8FAFC",
        "--placeholder": "#64748B",
        "--primary": "#3B82F6",
        "--primary-hover": "#60A5FA",
        "--secondary": "#94A3B8",
        "--success": "#34D399",
        "--warning": "#FBBF24",
        "--error": "#F87171",
        "--info": "#60A5FA",
        "--shadow": "0 12px 35px rgba(0, 0, 0, 0.4)",
        "--disabled-bg": "#1E293B",
        "--disabled-text": "#475569",
        "--table-header": "#0F172A",
        "--table-row": "#111827",
        "--table-row-hover": "#1E293B",
        "--overlay": "rgba(15, 23, 42, 0.85)"
    }
}

def initialize_theme():
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "light"

def toggle_theme():
    if st.session_state.theme_mode == "light":
        st.session_state.theme_mode = "dark"
    else:
        st.session_state.theme_mode = "light"

def get_current_theme():
    return st.session_state.get("theme_mode", "light")

def get_theme_tokens():
    return THEMES[get_current_theme()]

def render_theme_toggle():
    initialize_theme()
    mode = get_current_theme()
    icon = "🌙" if mode == "light" else "☀️"
    label = "Dark Mode" if mode == "light" else "Light Mode"
    
    if st.sidebar.button(f"{icon} {label}", key="theme_toggle_btn", use_container_width=True):
        toggle_theme()
        st.rerun()

def get_plotly_theme():
    mode = get_current_theme()
    if mode == "dark":
        return {
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font": {"color": "#F8FAFC"},
            "xaxis": {"gridcolor": "#334155"},
            "yaxis": {"gridcolor": "#334155"}
        }
    else:
        return {
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font": {"color": "#0F172A"},
            "xaxis": {"gridcolor": "#E2E8F0"},
            "yaxis": {"gridcolor": "#E2E8F0"}
        }

def apply_global_theme():
    initialize_theme()
    mode = get_current_theme()
    tokens = THEMES[mode]
    
    # Generate CSS variables for the root
    css_vars = "\n".join([f"        {k}: {v};" for k, v in tokens.items()])
    
    css = f"""
    <style>
    :root {{
{css_vars}
    }}
    
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* Core Typography and Backgrounds */
    html, body, [class*="css"], .stApp, .stAppViewContainer, .main, [data-testid="stHeader"] {{
        font-family: 'Inter', sans-serif !important;
        background-color: var(--app-bg) !important;
        background-image: none !important;
        color: var(--text-primary) !important;
    }}
    
    /* Streamlit overrides */
    header[data-testid="stHeader"] {{
        background-color: transparent !important;
    }}
    div[data-testid="stDecoration"] {{
        display: none !important;
    }}
    
    /* Typography Overrides */
    h1, h2, h3, h4, h5, h6, p, span, div, label {{
        color: var(--text-primary) !important;
    }}
    .stMarkdown p {{
        color: var(--text-secondary) !important;
    }}
    
    /* Global Card Component */
    .saas-card {{
        background-color: var(--card-bg) !important;
        border: 1px solid var(--border) !important;
        border-radius: 24px !important;
        padding: 2.5rem !important;
        box-shadow: var(--shadow) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        height: 100%;
        box-sizing: border-box;
    }}
    .saas-card:hover {{
        transform: translateY(-5px);
        border-color: var(--primary) !important;
    }}
    
    /* Inputs */
    .stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox select, .stMultiSelect [data-baseweb="select"] {{
        background-color: var(--input-bg) !important;
        color: var(--input-text) !important;
        border-color: var(--border) !important;
    }}
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {{
        color: var(--placeholder) !important;
    }}
    
    /* Primary Buttons */
    button[kind="primary"] {{
        background-color: var(--primary) !important;
        color: #ffffff !important;
        border-color: var(--primary) !important;
    }}
    button[kind="primary"]:hover {{
        background-color: var(--primary-hover) !important;
        border-color: var(--primary-hover) !important;
    }}
    
    /* Secondary Buttons */
    button[kind="secondary"] {{
        background-color: var(--surface) !important;
        color: var(--text-primary) !important;
        border-color: var(--border) !important;
    }}
    button[kind="secondary"]:hover {{
        border-color: var(--primary) !important;
        color: var(--primary) !important;
    }}
    
    /* Success, Error, Warning Alerts */
    [data-testid="stAlert"] {{
        background-color: var(--surface-secondary) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
    }}
    
    /* Navbar Custom Styles */
    .custom-navbar {{
        border-radius: 50px !important;
        padding: 0.6rem 2rem !important;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        width: 100%;
        margin-top: 1rem;
        margin-bottom: 2.5rem;
        position: sticky;
        top: 10px;
        z-index: 1000;
        height: 80px;
        box-sizing: border-box;
        transition: all 0.3s ease;
        background: var(--overlay) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid var(--border) !important;
        box-shadow: var(--shadow) !important;
    }}
    .custom-navbar .logo-title {{ color: var(--text-primary) !important; }}
    .custom-navbar .logo-subtitle {{ color: var(--text-muted) !important; }}
    .custom-navbar .logo-svg path {{ stroke: var(--primary) !important; }}
    .custom-navbar .logo-svg path[fill] {{ fill: var(--primary) !important; }}
    .custom-navbar .nav-login-btn {{ color: var(--text-secondary) !important; }}
    .custom-navbar .nav-login-btn:hover {{ color: var(--primary) !important; }}
    
    .custom-navbar button {{
        color: var(--text-secondary) !important;
        background-color: transparent;
        border: none;
    }}
    .custom-navbar button:hover {{
        color: var(--primary) !important;
        background-color: var(--surface-secondary) !important;
    }}
    .custom-navbar button.active {{
        background-color: var(--primary) !important;
        color: #ffffff !important;
    }}
    
    /* Modals / Overlays */
    [data-testid="stModal"] > div {{
        background-color: var(--surface) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
    }}
    
    /* Tables */
    [data-testid="stTable"] th {{
        background-color: var(--table-header) !important;
        color: var(--text-primary) !important;
        border-color: var(--border) !important;
    }}
    [data-testid="stTable"] td {{
        background-color: var(--table-row) !important;
        color: var(--text-secondary) !important;
        border-color: var(--border) !important;
    }}
    
    /* Dataframes */
    [data-testid="stDataFrame"] {{
        background-color: var(--surface) !important;
    }}
    
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
