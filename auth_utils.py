def check_auth():
    if 'id_user_loggato' not in st.session_state or st.session_state.id_user_loggato is None:
        # Nasconde sidebar nel login
        st.markdown("<style>[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)
        st.warning("⚠️ Effettua il login!")
        st.stop()
    else:
        # FORZA la sidebar a vedersi nelle pagine interne
        st.markdown("<style>[data-testid='stSidebar'] {display: flex !important;}</style>", unsafe_allow_html=True)
