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
                        user_id = auth_res.user.id
                        
                        # Recupero nickname dalla tabella utenti
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
    st.stop()

# --- 5. DASHBOARD (UTENTE LOGGATO) ---
check_auth()      # Protezione e CSS personalizzato
render_sidebar()  # Navigazione laterale

# Intestazione utente
st.title(f"👋 Ciao {st.session_state.nome_user_loggato}!")

# Griglia Dashboard
try:
    # Caricamento dati dalle View di Supabase
    pick_data = supabase.table("view_stage_to_pick").select("*").execute().data
    current_data = supabase.table("view_stage_current").select("*").execute().data
    last_data = supabase.table("view_stage_last_results").select("*").execute().data
    upcoming_data = supabase.table("view_races_upcoming").select("*").execute().data

    col_left, col_right = st.columns(2, gap="medium")

    # --- COLONNA SINISTRA: OPERATIVITÀ ---
    with col_left:
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

        st.caption("🏁 IN CORSO")
        with st.container(border=True):
            if current_data:
                for c in current_data:
                    st.write(f"🚴‍♂️ {c['race_name']} (T{c['stage']})")
            else:
                st.info("Nessuna corsa attiva.")

    # --- COLONNA DESTRA: STATISTICHE E PROGRAMMA ---
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
                    st.markdown(
                        f'<div class="race-row"><span>📅 {u["race_name"]}</span></div>', 
                        unsafe_allow_html=True
                    )
            else:
                st.write("Nessuna gara in programma.")

except Exception as e:
    st.error(f"Errore nel caricamento dati: {e}")
