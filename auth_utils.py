import streamlit as st
import uuid

def generate_token():
    return str(uuid.uuid4())

def save_session_to_cookie(supabase, user_id, nickname, is_admin):
    try:
        token = generate_token()
        supabase.table("dim_user").update({"session_token": token}).eq("id_user", user_id).execute()
        st.query_params["token"] = token
        st.session_state._session_token = token
        st.session_state.id_user_loggato = user_id
        st.session_state.nome_user_loggato = nickname
        st.session_state.is_admin = is_admin
    except Exception as e:
        st.error(f"Errore salvataggio sessione: {e}")

def restore_session_from_cookie(supabase):
    if st.session_state.get("id_user_loggato"):
        return True
    
    try:
        token = st.query_params.get("token")
        if not token:
            token = st.session_state.get("_session_token")
        if not token:
            return False
        
        res = supabase.table("dim_user").select("id_user, nickname, is_admin").eq("session_token", token).single().execute()
        if res.data:
            st.session_state.id_user_loggato = res.data["id_user"]
            st.session_state.nome_user_loggato = res.data["nickname"]
            st.session_state.is_admin = res.data.get("is_admin", False)
            st.session_state._session_token = token
            return True
    except Exception:
        pass
    
    return False

def clear_session_cookie(supabase=None):
    try:
        user_id = st.session_state.get("id_user_loggato")
        if user_id and supabase:
            supabase.table("dim_user").update({"session_token": None}).eq("id_user", user_id).execute()
        st.query_params.clear()
    except Exception:
        pass

def init_cookies():
    pass

def check_auth():
    if 'id_user_loggato' not in st.session_state or st.session_state.id_user_loggato is None:
        st.markdown(
            "<style>[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl'] {display: none !important;}</style>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<style>[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl'] {display: flex !important;}</style>",
            unsafe_allow_html=True
        )

    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
        * { font-family: 'Inter', sans-serif; }
        footer, [data-testid="stDecoration"] { display: none !important; }
        .stAppDeployButton, [data-testid="stStatusWidget"],
        div[class*="viewerBadge"], button[title="View source on GitHub"] { display: none !important; }
        [data-testid="stSidebar"] {
            background-color: rgba(20, 20, 20, 0.8) !important;
            backdrop-filter: blur(15px);
            border-right: 1px solid rgba(255, 255, 255, 0.05);
        }
        div[data-testid="stVerticalBlock"] > div > div[style*="border"] {
            background: rgba(30, 30, 30, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 15px !important;
            padding: 20px !important;
            transition: all 0.3s ease;
        }
        div[data-testid="stVerticalBlock"] > div > div[style*="border"]:hover {
            transform: translateY(-5px);
            border-color: #ff4b4b !important;
            box-shadow: 0 10px 20px rgba(0,0,0,0.3);
        }
        .stButton > button {
            border-radius: 10px !important;
            border: none !important;
            background: linear-gradient(135deg, #ff4b4b 0%, #ff7575 100%) !important;
            color: white !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }
        .stButton > button:hover {
            transform: scale(1.03);
            box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4);
        }
        .sidebar-user-box {
            display: flex; align-items: center; gap: 15px; padding: 15px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px; margin-bottom: 20px;
        }
        .sidebar-user-box img {
            border-radius: 50% !important; border: 2px solid #ff4b4b !important;
            width: 50px !important; height: 50px !important;
            object-fit: cover; box-shadow: 0 0 10px rgba(255, 75, 75, 0.3);
        }
        .side-header {
            font-size: 0.75rem; color: #666; text-transform: uppercase;
            letter-spacing: 1px; margin: 20px 0 10px 5px;
        }
        .nav-button > button {
            background: transparent !important;
            color: white !important;
            text-align: left !important;
            font-weight: 400 !important;
            box-shadow: none !important;
            border: none !important;
            padding: 4px 8px !important;
        }
        .nav-button > button:hover {
            background: rgba(255,255,255,0.05) !important;
            transform: none !important;
            box-shadow: none !important;
        }
        </style>
    """, unsafe_allow_html=True)


def render_sidebar():
    from supabase import create_client
    try:
        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        supabase = None

    token = st.session_state.get("_session_token", "")

    with st.sidebar:
        # Navigazione principale con token
        st.markdown('<div class="nav-button">', unsafe_allow_html=True)
        if st.button("🏠 Home", use_container_width=True, key="nav_home"):
            st.query_params["token"] = token
            st.switch_page("Home.py")

        if st.button("✍️ Pick", use_container_width=True, key="nav_pick"):
            st.query_params["token"] = token
            st.switch_page("pages/01_Inserimento.py")

        if st.button("🏆 Leaderboard", use_container_width=True, key="nav_leaderboard"):
            st.query_params["token"] = token
            st.switch_page("pages/02_Classifiche.py")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<p class="side-header">Account</p>', unsafe_allow_html=True)

        user_display_name = st.session_state.get('nome_user_loggato', 'Rider')

        st.markdown(f"""
            <div class="sidebar-user-box">
                <img src="https://github.com/Jericho1987/virtua_cycling_3.0/blob/main/rider_logo.jpg?raw=true">
                <div>
                    <div style="font-weight: 600; color: white;">{user_display_name}</div>
                    <div style="font-size: 0.7rem; color: #888;">Pro Member</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Profilo ⚙️", key="btn_settings", use_container_width=True):
                st.query_params["token"] = token
                st.switch_page("pages/07_modifica_profilo.py")
        with col2:
            if st.button("Esci 🚪", key="btn_logout", use_container_width=True):
                clear_session_cookie(supabase)
                st.session_state.clear()
                st.rerun()

        if st.session_state.get('is_admin', False):
            st.markdown('<p class="side-header" style="color: #ff4b4b;">Admin Panel</p>', unsafe_allow_html=True)

            if st.button("📊 Risultati", use_container_width=True, key="nav_risultati"):
                st.query_params["token"] = token
                st.switch_page("pages/03_Gestione_Risultati.py")

            if st.button("📑 Startlist", use_container_width=True, key="nav_startlist"):
                st.query_params["token"] = token
                st.switch_page("pages/04_Upload_Startlist.py")

            if st.button("🗂️ Mass Results", use_container_width=True, key="nav_mass"):
                st.query_params["token"] = token
                st.switch_page("pages/05_Upload_Mass_Results.py")

            if st.button("⚡ Massive Pick", use_container_width=True, key="nav_massive"):
                st.query_params["token"] = token
                st.switch_page("pages/06_insert_pick_massive.py")

            if st.button("📅 Gestione Corse", use_container_width=True, key="nav_corse"):
                st.query_params["token"] = token
                st.switch_page("pages/08_Gestione_Date.py")

            if st.button("🚴‍♂️ Gestione Team", use_container_width=True, key="nav_team"):
                st.query_params["token"] = token
                st.switch_page("pages/09_gestione_team.py")
