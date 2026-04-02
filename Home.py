import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar  # Funzioni certificate

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Virtua Cycling - Home", 
    layout="wide", 
    page_icon="🚴‍♂️"
)

# --- 2. CONNESSIONE A SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 3. GESTIONE ACCESSO ---
if 'id_user_loggato' not in st.session_state:
    st.session_state.id_user_loggato = None

# --- 4. LOGICA LOGIN (Se non loggato) ---
if st.session_state.id_user_loggato is None:
    # CSS per nascondere la sidebar e centrare il login
    st.markdown("""
        <style>
            [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none !important; }
            .stTabs [data-baseweb="tab-list"] { justify-content: center; }
        </style>
    """, unsafe_allow_html=True)

    _, col_login, _ = st.columns([1, 1.2, 1])
    
    with col_login:
        st.title("Virtua Cycling")
        tab_login, tab_reg = st.tabs(["🔐 Accedi", "✨ Registrati"])
        
        with tab_login:
            with st.form("login_form"):
                email_input = st.text_input("Email")
                password_input = st.text_input("Password", type="password")
                
                if st.form_submit_button("ACCEDI 🚀", use_container_width=True):
                    try:
                        auth_res = supabase.auth.sign_in_with_password({
                            "email": email_input, 
                            "password": password_input
                        })
                        
                        st.session_state.supabase_session = auth_res.session
                        user_id = auth_res.user.id
                        
                        user_info = (supabase.table("dim_user")
                                     .select("nickname")
                                     .eq("id_user", user_id)
                                     .single()
                                     .execute())
                        
                        st.session_state.id_user_loggato = user_id
                        st.session_state.nome_user_loggato = user_info.data['nickname']
                        st.rerun()
                    except Exception:
                        st.error("Credenziali errate.")

        with tab_reg:
            with st.form("registration_form"):
                new_email = st.text_input("Email")
                new_password = st.text_input("Password", type="password")
                new_nickname = st.text_input("Nickname")
                
                if st.form_submit_button("REGISTRATI ✨", use_container_width=True):
                    try:
                        supabase.auth.sign_up({
                            "email": new_email,
                            "password": new_password,
                            "options": {
                                "data": { "nickname": new_nickname }
                            }
                        })
                        st.success("Registrazione effettuata! Ora puoi accedere.")
                    except Exception as e:
                        st.error(f"Errore: {e}")

    st.stop()

# --- 5. DASHBOARD (UTENTE LOGGATO) ---
check_auth()      # Protezione e CSS personalizzato
render_sidebar()  # Navigazione laterale

st.title(f"👋 Ciao {st.session_state.nome_user_loggato}!")

# Griglia Dashboard
try:
    # Caricamento dati
    pick_data = supabase.table("view_stage_to_pick").select("*").execute().data
    current_data = supabase.table("view_stage_current").select("*").execute().data
    last_data = supabase.table("view_stage_last_results").select("*").execute().data
    upcoming_data = supabase.table("view_races_upcoming").select("*").execute().data

    # --- RIGA 1: OPERATIVITÀ E RISULTATI ---
    col_top_left, col_top_right = st.columns(2, gap="medium")

    with col_top_left:
        st.subheader("✍️ Pick da fare")
        with st.container(border=True):
            if pick_data:
                for p in pick_data:
                    c1, c2 = st.columns([0.7, 0.3])
                    c1.write(f"**{p['race_name']}** (Tappa {p['stage']})")
                    if c2.button("Vai", key=f"p_{p['id_stage']}", use_container_width=True):
                        st.session_state.gara_selezionata_id = p['id_race']
                        st.session_state.tappa_selezionata_id = p['id_stage']
                        st.switch_page("pages/01_Inserimento.py")
            else:
                st.success("Pick completati! ✅")

    with col_top_right:
        st.subheader("🏆 Ultimi risultati")
        with st.container(border=True):
            if last_data:
                for l in last_data:
                    st.write(f"✅ {l['race_name']}")
                st.button("CLASSIFICHE 🏆", use_container_width=True, type="primary", on_click=lambda: st.switch_page("pages/02_Classifiche.py"))
            else:
                st.info("Nessun risultato recente.")

    st.markdown("<br>", unsafe_allow_html=True) # Spazio per stacco visivo

    # --- RIGA 2: IN CORSO E PROSSIME GARE ---
    # Creiamo nuove colonne per forzare l'allineamento orizzontale dei titoli
    col_bot_left, col_bot_right = st.columns(2, gap="medium")

    with col_bot_left:
        st.subheader("🏁 In corso")
        with st.container(border=True):
            if current_data:
                for c in current_data:
                    st.write(f"🚴‍♂️ {c['race_name']} (T{c['stage']})")
            else:
                st.info("Nessuna corsa attiva.")

    with col_bot_right:
        st.subheader("📅 Prossime gare")
        with st.container(border=True):
            if upcoming_data:
                for u in upcoming_data:
                    st.markdown(
                        f'<div class="race-row"><span>📅 {u["race_name"]}</span></div>', 
                        unsafe_allow_html=True
                    )
            else:
                st.write("Nessuna gara in programma.")

except Exception as e:
    st.error(f"Errore nel caricamento dati: {e}")
