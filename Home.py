import streamlit as st
from supabase import create_client
from auth_utils import render_sidebar

# --- 1. CONFIGURAZIONE BRANDING ---
NOME_APP = "Virtua Cycling"
URL_LOGO = "https://github.com/Jericho1987/virtua_cycling_3.0/blob/main/logo_pwa.png?raw=true"

st.set_page_config(page_title=NOME_APP, layout="wide", page_icon=URL_LOGO)

# --- 2. CONNESSIONE A SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 3. GESTIONE STATO ACCESSO ---
if 'id_user_loggato' not in st.session_state:
    st.session_state.id_user_loggato = None

# --- 4. LOGICA LOGIN O DASHBOARD ---
if st.session_state.id_user_loggato is None:
    # CSS per nascondere sidebar e centrare il form
    st.markdown("""
        <style>
            [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none !important; }
            .block-container { padding-top: 5rem !important; }
            .stTabs [data-baseweb="tab-list"] { justify-content: center; }
        </style>
    """, unsafe_allow_html=True)

    _, col_login, _ = st.columns([1, 1.2, 1])
    
    with col_login:
        st.image(URL_LOGO, width=100)
        st.title(NOME_APP)
        
        tab_login, tab_reg = st.tabs(["🔐 Accedi", "✨ Registrati"])

        # --- SEZIONE LOGIN ---
        with tab_login:
            with st.form("login_form"):
                email_input = st.text_input("Email")
                password_input = st.text_input("Password", type="password")
                submit_login = st.form_submit_button("ACCEDI ALLA GARA 🚀", use_container_width=True)
                
                if submit_login:
                    try:
                        # Autenticazione sicura tramite Supabase Auth
                        auth_res = supabase.auth.sign_in_with_password({
                            "email": email_input, 
                            "password": password_input
                        })
                        
                        # Recupero dati dal profilo pubblico (popolato dal trigger SQL)
                        user_id = auth_res.user.id
                        user_info = supabase.table("dim_user").select("display_name").eq("id_user", user_id).single().execute()
                        
                        st.session_state.id_user_loggato = user_id
                        st.session_state.nome_user_loggato = user_info.data['display_name']
                        st.rerun()
                    except Exception:
                        st.error("Credenziali errate o account non confermato.")

        # --- SEZIONE REGISTRAZIONE ---
        with tab_reg:
            with st.form("register_form"):
                reg_email = st.text_input("Email")
                reg_pass = st.text_input("Password (min. 6 caratteri)", type="password")
                reg_name = st.text_input("Nome e Cognome")
                reg_nick = st.text_input("Nickname")
                submit_reg = st.form_submit_button("CREA ACCOUNT ✨", use_container_width=True)
                
                if submit_reg:
                    if len(reg_pass) < 6:
                        st.warning("La password deve avere almeno 6 caratteri.")
                    else:
                        try:
                            # Registrazione su Supabase Auth + Metadati per il trigger SQL
                            supabase.auth.sign_up({
                                "email": reg_email,
                                "password": reg_pass,
                                "options": {
                                    "data": {
                                        "display_name": reg_name,
                                        "nickname": reg_nick
                                    }
                                }
                            })
                            st.success("Registrazione effettuata! Ora puoi accedere dal tab 'Accedi'.")
                        except Exception as e:
                            st.error(f"Errore durante la registrazione: {e}")
    st.stop()

else:
    # --- 5. SCHERMATA DASHBOARD (UTENTE LOGGATO) ---
    st.markdown("""
        <style>
        footer {visibility: hidden;}
        [data-testid="stSidebar"] { display: flex !important; }
        .race-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #333; font-size: 0.85rem; }
        </style>
    """, unsafe_allow_html=True)

    # Sidebar centralizzata
    render_sidebar()

    # Intestazione
    t1, t2 = st.columns([0.1, 0.9])
    with t1: st.image(URL_LOGO, width=60)
    with t2: st.markdown(f"### Ciao {st.session_state.nome_user_loggato}! 👋")

    # Recupero dati (Views)
    try:
        pick_data = supabase.table("view_stage_to_pick").select("*").execute().data
        current_data = supabase.table("view_stage_current").select("*").execute().data
        last_data = supabase.table("view_stage_last_results").select("*").execute().data
        upcoming_data = supabase.table("view_races_upcoming").select("*").execute().data

        col_left, col_right = st.columns(2, gap="medium")

        with col_left:
            st.caption("✍️ PICK DA FARE")
            with st.container(border=True):
                if pick_data:
                    for p in pick_data:
                        c1, c2 = st.columns([0.75, 0.25])
                        c1.write(f"**{p['race_name']}**\nT{p['stage']}")
                        if c2.button("Vai", key=f"p_{p['id_stage']}", use_container_width=True):
                            st.session_state.gara_selezionata_id = p['id_race']
                            st.session_state.tappa_selezionata_id = p['id_stage']
                            st.switch_page("pages/01_Inserimento.py")
                else: 
                    st.success("Pick completati! ✅")

            st.caption("🏁 IN CORSO")
            with st.container(border=True):
                if current_data:
                    for c in current_data:
                        st.write(f"🚴‍♂️ {c['race_name']} (T{c['stage']})")
                else: 
                    st.info("Nessuna corsa attiva.")

        with col_right:
            st.caption("🏆 ULTIMI RISULTATI")
            with st.container(border=True):
                if last_data:
                    for l in last_data:
                        st.write(f"✅ {l['race_name']}")
                    if st.button("CLASSIFICHE 🏆", use_container_width=True, type="primary"):
                        st.switch_page("pages/02_Classifiche.py")

            st.caption("📅 PROSSIME GARE")
            with st.container(border=True):
                if upcoming_data:
                    for u in upcoming_data:
                        st.markdown(f'<div class="race-row"><span>📅 {u["race_name"]}</span></div>', unsafe_allow_html=True)
                else:
                    st.write("Nessuna gara in programma.")
                    
    except Exception as e:
        st.error(f"Errore nel caricamento dati: {e}")
