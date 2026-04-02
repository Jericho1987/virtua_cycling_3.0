import streamlit as st

def check_auth():
    # 1. Controllo se l'utente è loggato
    if 'id_user_loggato' not in st.session_state or st.session_state.id_user_loggato is None:
        # Nasconde la sidebar se qualcuno prova ad accedere direttamente via URL
        st.markdown("<style>[data-testid='stSidebar'] {display: none !important;}</style>", unsafe_allow_html=True)
        st.warning("⚠️ Accesso negato. Effettua il login nella Home.")
        if st.button("Vai al Login"):
            st.switch_page("Home.py")
        st.stop()
    
    # 2. Se è loggato, forza la visualizzazione della sidebar (necessario per GitHub)
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { display: flex !important; }
        .sidebar-user-box { display: flex; align-items: center; gap: 12px; padding: 5px 0; }
        .sidebar-user-box img {
            border-radius: 50% !important; border: 2px solid #ff69b4 !important;
            width: 45px !important; height: 45px !important; object-fit: cover;
        }
        .side-header { font-size: 0.7rem; color: #888; text-transform: uppercase; margin-top: 15px; }
        </style>
    """, unsafe_allow_html=True)

def render_sidebar():
    with st.sidebar:
        # Navigazione
        st.page_link("Home.py", label="Home", icon="🏠")
        st.page_link("pages/01_Inserimento.py", label="Pick", icon="✍️")
        st.page_link("pages/02_Classifiche.py", label="Classifiche", icon="🏆")
        
        st.markdown("---")
        st.markdown('<p class="side-header">Area Personale</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="sidebar-user-box"><img src="https://github.com/Jericho1987/virtua_cycling_3.0/blob/main/rider_logo.jpg?raw=true"> <b>{st.session_state.nome_user_loggato}</b></div>', unsafe_allow_html=True)
        
        if st.button("Esci 🚪", use_container_width=True):
            st.session_state.id_user_loggato = None
            st.switch_page("Home.py")

        st.markdown("---")
        st.markdown('<p class="side-header" style="color: #ff4b4b;">🛠️ Amministrazione</p>', unsafe_allow_html=True)
        st.page_link("pages/03_Gestione_Risultati.py", label="Risultati", icon="📊")
        st.page_link("pages/04_Upload_Startlist.py", label="Startlist", icon="📑")
        st.page_link("pages/05_Upload_Mass_Results.py", label="Mass Results", icon="🗂️")
        st.page_link("pages/06_insert_pick_massive.py", label="Massive Pick", icon="⚡")def check_auth():
    if 'id_user_loggato' not in st.session_state or st.session_state.id_user_loggato is None:
        # Nasconde sidebar nel login
        st.markdown("<style>[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)
        st.warning("⚠️ Effettua il login!")
        st.stop()
    else:
        # FORZA la sidebar a vedersi nelle pagine interne
        st.markdown("<style>[data-testid='stSidebar'] {display: flex !important;}</style>", unsafe_allow_html=True)
