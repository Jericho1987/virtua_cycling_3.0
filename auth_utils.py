import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta

@st.cache_resource
def get_cookie_manager():
    return stx.CookieManager(key="virtua_cookie_manager")

def init_cookies():
    return get_cookie_manager()

def restore_session_from_cookie(supabase):
    if st.session_state.get("id_user_loggato"):
        return True
    
    try:
        cm = get_cookie_manager()
        saved_user_id = cm.get("user_id")
        saved_nickname = cm.get("nickname")
        saved_is_admin = cm.get("is_admin")

        if saved_user_id and saved_nickname:
            st.session_state.id_user_loggato = saved_user_id
            st.session_state.nome_user_loggato = saved_nickname
            st.session_state.is_admin = saved_is_admin == "True"
            return True
    except Exception:
        pass
    
    return False

def save_session_to_cookie(user_id, nickname, is_admin):
    try:
        cm = get_cookie_manager()
        expiry = datetime.now() + timedelta(days=30)
        cm.set("user_id", user_id, expires_at=expiry)
        cm.set("nickname", nickname, expires_at=expiry)
        cm.set("is_admin", str(is_admin), expires_at=expiry)
    except Exception:
        pass

def clear_session_cookie():
    try:
        cm = get_cookie_manager()
        cm.delete("user_id")
        cm.delete("nickname")
        cm.delete("is_admin")
    except Exception:
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
        </style>
    """, unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.page_link("Home.py", label="Home", icon="🏠")
        st.page_link("pages/01_Inserimento.py", label="Pick", icon="✍️")
        st.page_link("pages/02_Classifiche.py", label="Leaderboard", icon="🏆")
        
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
                st.switch_page("pages/07_modifica_profilo.py")
        with col2:
            if st.button("Esci 🚪", key="btn_logout", use_container_width=True):
                clear_session_cookie()
                st.session_state.clear()
                st.rerun()

        if st.session_state.get('is_admin', False):
            st.markdown('<p class="side-header" style="color: #ff4b4b;">Admin Panel</p>', unsafe_allow_html=True)
            st.page_link("pages/03_Gestione_Risultati.py", label="Risultati", icon="📊")
            st.page_link("pages/04_Upload_Startlist.py", label="Startlist", icon="📑")
            st.page_link("pages/05_Upload_Mass_Results.py", label="Mass Results", icon="🗂️")
            st.page_link("pages/06_insert_pick_massive.py", label="Massive Pick", icon="⚡")
            st.page_link("pages/08_Gestione_Date.py", label="Gestione Corse", icon="📅")
            st.page_link("pages/09_gestione_team.py", label="Gestione Team", icon="🚴‍♂️")
