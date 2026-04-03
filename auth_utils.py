import streamlit as st
import extra_streamlit_components as stx
from supabase import create_client
from datetime import datetime, timedelta
import time

def get_supabase():
    """Inizializza il client Supabase usando i secrets."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def init_session():
    """
    Gestisce il recupero della sessione tramite cookie in modo centralizzato.
    Aggiunge un delay per permettere al componente JS di caricarsi.
    """
    if 'id_user_loggato' not in st.session_state:
        st.session_state.id_user_loggato = None

    # Se non loggato in sessione, proviamo il recupero dal cookie
    if st.session_state.id_user_loggato is None:
        # Usiamo una chiave statica per il CookieManager per coerenza tra le pagine
        cookie_manager = stx.CookieManager(key="virtua_cycling_global_auth")
        
        # Pausa tecnica per l'asincronia di Streamlit/JS
        time.sleep(0.5)
        
        saved_token = cookie_manager.get(cookie="supabase_refresh_token")
        
        if saved_token:
            try:
                supabase = get_supabase()
                res_session = supabase.auth.refresh_session(saved_token)
                if res_session and res_session.user:
                    u_id = res_session.user.id
                    u_info = supabase.table("dim_user").select("nickname, is_admin").eq("id_user", u_id).single().execute()
                    
                    st.session_state.id_user_loggato = u_id
                    st.session_state.nome_user_loggato = u_info.data['nickname']
                    st.session_state.is_admin = u_info.data.get('is_admin', False)
                    
                    # Aggiorniamo la scadenza del cookie
                    cookie_manager.set("supabase_refresh_token", res_session.session.refresh_token, 
                                     expires_at=datetime.now() + timedelta(days=30))
                    st.rerun()
            except:
                # Token non valido o errore: l'utente dovrà loggarsi manualmente
                pass

def check_auth():
    """Controlla l'auth, gestisce il recupero cookie e applica il restyling globale."""
    
    # 1. Tenta il recupero automatico se necessario
    init_session()
    
    if 'id_user_loggato' not in st.session_state or st.session_state.id_user_loggato is None:
        # Nascondi sidebar se non loggato
        st.markdown("<style>[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl'] {display: none !important;}</style>", unsafe_allow_html=True)
        st.warning("⚠️ Accesso negato. Effettua il login nella Home.")
        if st.button("Vai al Login"):
            st.switch_page("Home.py")
        st.stop()
    else:
        # Forza la visualizzazione della sidebar se loggato
        st.markdown("<style>[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl'] {display: flex !important;}</style>", unsafe_allow_html=True)
    
    # --- RESTYLING GRAFICO GLOBALE ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
        
        * { font-family: 'Inter', sans-serif; }

        footer, [data-testid="stDecoration"] { display: none !important; }

        .stAppDeployButton, [data-testid="stStatusWidget"], div[class*="viewerBadge"] { display: none !important; }

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
            background: rgba(255, 255, 255, 0.03); border-radius: 12px; margin-bottom: 20px;
        }
        .sidebar-user-box img {
            border-radius: 50% !important; border: 2px solid #ff4b4b !important;
            width: 50px !important; height: 50px !important; object-fit: cover;
        }
        
        .side-header { 
            font-size: 0.75rem; color: #666; text-transform: uppercase; 
            letter-spacing: 1px; margin: 20px 0 10px 5px; 
        }
        </style>
    """, unsafe_allow_html=True)

def render_sidebar():
    """Disegna la sidebar con lo stile aggiornato e gestione logout."""
    cookie_manager = stx.CookieManager(key="virtua_cycling_global_auth")

    with st.sidebar:
        st.page_link("Home.py", label="Home", icon="🏠")
        st.page_link("pages/01_Inserimento.py", label="Pick", icon="✍️")
        st.page_link("pages/02_Classifiche.py", label="Leaderboard", icon="🏆")
        
        st.markdown('<p class="side-header">Account</p>', unsafe_allow_html=True)
        st.markdown(f"""
            <div class="sidebar-user-box">
                <img src="https://github.com/Jericho1987/virtua_cycling_3.0/blob/main/rider_logo.jpg?raw=true">
                <div>
                    <div style="font-weight: 600; color: white;">{st.session_state.get('nome_user_loggato', 'Rider')}</div>
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
                cookie_manager.delete("supabase_refresh_token")
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
