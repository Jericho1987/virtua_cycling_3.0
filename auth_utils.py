def render_sidebar():
    """Disegna la sidebar manuale."""
    with st.sidebar:
        # Navigazione Principale
        st.page_link("Home.py", label="Home", icon="🏠")
        st.page_link("pages/01_Inserimento.py", label="Pick", icon="✍️")
        st.page_link("pages/02_Classifiche.py", label="Classifiche", icon="🏆")
        
        st.markdown("---")
        
        # Area Personale
        st.markdown('<p class="side-header">Area Personale</p>', unsafe_allow_html=True)
        st.markdown(f"""
            <div class="sidebar-user-box">
                <img src="https://github.com/Jericho1987/virtua_cycling_3.0/blob/main/rider_logo.jpg?raw=true">
                <b>{st.session_state.get('nome_user_loggato', 'Utente')}</b>
            </div>
        """, unsafe_allow_html=True)
        
        # --- MODIFICA QUI: DUE COLONNE PER I TASTI ---
        c1, c2 = st.columns(2)
        
        with c1:
            if st.button("⚙️", use_container_width=True, help="Modifica Profilo"):
                # Punat alla nuova pagina che creerai
                st.switch_page("pages/07_modifica_profilo.py")
        
        with c2:
            if st.button("Esci 🚪", use_container_width=True):
                st.session_state.id_user_loggato = None
                st.session_state.nome_user_loggato = None
                st.switch_page("Home.py")
        # --------------------------------------------

        st.markdown("---")
        
        # Sezione Amministrazione
        st.markdown('<p class="side-header" style="color: #ff4b4b;">🛠️ Amministrazione</p>', unsafe_allow_html=True)
        st.page_link("pages/03_Gestione_Risultati.py", label="Risultati", icon="📊")
        st.page_link("pages/04_Upload_Startlist.py", label="Startlist", icon="📑")
        st.page_link("pages/05_Upload_Mass_Results.py", label="Mass Results", icon="🗂️")
        st.page_link("pages/06_insert_pick_massive.py", label="Massive Pick", icon="⚡")
