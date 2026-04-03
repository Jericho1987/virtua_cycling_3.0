import streamlit as st

def check_auth():
    """Controlla l'auth e applica il restyling globale dell'app."""
    if 'id_user_loggato' not in st.session_state or st.session_state.id_user_loggato is None:
        st.markdown("<style>[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl'] {display: none !important;}</style>", unsafe_allow_html=True)
        st.warning("⚠️ Accesso negato. Effettua il login nella Home.")
        if st.button("Vai al Login"):
            st.switch_page("Home.py")
        st.stop()
    
    # --- RESTYLING GRAFICO GLOBALE ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
        
        * { font-family: 'Inter', sans-serif; }

        /* --- PULIZIA INTERFACCIA STREAMLIT --- */
        header[data-testid="stHeader"] {
            visibility: hidden;
            height: 0%;
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        div[data-testid="stStatusWidget"] { visibility: hidden; }
        .viewerBadge_container__1QSob { display: none !important; }
        [data-testid="stDecoration"] { display: none; }

        /* Sidebar Glassmorphism */
        [data-testid="stSidebar"] {
            background-color: rgba(20, 20, 20, 0.8) !important;
            backdrop-filter: blur(15px);
            border-right: 1px solid rgba(255, 255, 255, 0.05);
        }

        /* Container delle Card */
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

        /* Bottoni Custom */
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

        /* User Box Sidebar */
        .sidebar-user-box { 
            display: flex; 
            align-items: center; 
            gap: 15px; 
            padding: 15px; 
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            margin-bottom: 20px;
        }
        .sidebar-user-box img {
            border-radius: 50% !important; 
            border: 2px solid #ff4b4b !important;
            width: 50px !important; 
            height: 50px !important; 
            object-fit: cover;
            box-shadow: 0 0 10px rgba(255, 75, 75, 0.3);
        }
        
        .side-header { 
            font-size: 0.75rem; 
            color: #666; 
            text-transform: uppercase; 
            letter-spacing: 1px;
            margin: 20px 0 10px 5px; 
        }
        </style>
    """, unsafe_allow_html=True)

def render_sidebar():
    """Disegna la sidebar con lo stile aggiornato."""
    with st.sidebar:
        # Pagine Standard
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
                st.session_state.clear()
                st.rerun()

        # Pagine Admin
        if st.session_state.get('is_admin', False):
            st.markdown('<p class="side-header" style="color: #ff4b4b;">Admin Panel</p>', unsafe_allow_html=True)
            st.page_link("pages/03_Gestione_Risultati.py", label="Risultati", icon="📊")
            st.page_link("pages/04_Upload_Startlist.py", label="Startlist", icon="📑")
            st.page_link("pages/05_Upload_Mass_Results.py", label="Mass Results", icon="🗂️")
            st.page_link("pages/06_insert_pick_massive.py", label="Massive Pick", icon="⚡")
            st.page_link("pages/08_Gestione_Date.py", label="Gestione Corse", icon="📅")
            st.page_link("pages/09_gestione_team.py", label="Gestione Team", icon="🚴‍♂️")
