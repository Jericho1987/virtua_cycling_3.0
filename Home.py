import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar
from datetime import datetime

# 1. Configurazione pagina
st.set_page_config(page_title="Virtua Cycling - Home", layout="wide", page_icon="🚴‍♂️")

# --- CSS ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
        header[data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; color: white !important; }
        [data-testid="stDecoration"] { display: none; }
        hr { margin: 15px 0 !important; opacity: 0.15; }
        .section-title { font-size: 1.4rem; font-weight: bold; margin-bottom: 10px; display: flex; align-items: center; gap: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- INIZIALIZZAZIONE SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- LOGICA DI SESSIONE SEMPLIFICATA ---
if 'id_user_loggato' not in st.session_state:
    st.session_state.id_user_loggato = None
if 'nome_user_loggato' not in st.session_state:
    st.session_state.nome_user_loggato = None
if 'supabase_session' not in st.session_state:
    st.session_state.supabase_session = None

# Recupero sessione esistente all'avvio
if st.session_state.id_user_loggato is None:
    try:
        session = supabase.auth.get_session()
        if session and session.user:
            res = supabase.table("dim_user").select("nickname, is_admin").eq("id_user", session.user.id).single().execute()
            st.session_state.id_user_loggato = session.user.id
            st.session_state.nome_user_loggato = res.data['nickname']
            st.session_state.is_admin = res.data.get('is_admin', False)
            st.session_state.supabase_session = session
    except:
        pass

# --- LOGICA DI LOGIN ---
if st.session_state.id_user_loggato is None:
    st.markdown("<style>[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl'] { display: none !important; }</style>", unsafe_allow_html=True)
    _, col_login, _ = st.columns([1, 1.2, 1])
    
    with col_login:
        st.title("Virtua Cycling")
        t1, t2 = st.tabs(["🔐 Accedi", "✨ Registrati"])
        
        with t1:
            with st.form("login_form"):
                e_in = st.text_input("Email")
                p_in = st.text_input("Password", type="password")
                if st.form_submit_button("ACCEDI 🚀", use_container_width=True):
                    try:
                        res = supabase.auth.sign_in_with_password({"email": e_in, "password": p_in})
                        if res.user:
                            u_info = supabase.table("dim_user").select("nickname, is_admin").eq("id_user", res.user.id).single().execute()
                            st.session_state.id_user_loggato = res.user.id
                            st.session_state.nome_user_loggato = u_info.data['nickname']
                            st.session_state.is_admin = u_info.data.get('is_admin', False)
                            st.session_state.supabase_session = res.session
                            st.rerun()
                    except:
                        st.error("Credenziali errate.")
        
        with t2:
            with st.form("reg_form"):
                n_e = st.text_input("Email")
                n_p = st.text_input("Password", type="password")
                n_n = st.text_input("Nickname")
                if st.form_submit_button("REGISTRATI ✨", use_container_width=True):
                    try:
                        supabase.auth.sign_up({"email": n_e, "password": n_p, "options": {"data": {"nickname": n_n}}})
                        st.success("Registrazione completata! Ora puoi accedere.")
                    except Exception as e:
                        st.error(f"Errore: {e}")
    st.stop()

# --- DASHBOARD LOGGATA ---
check_auth()
render_sidebar()

st.markdown(f"""
    <div style="background-color: #1e1e1e; padding: 15px; border-radius: 12px; border-left: 5px solid #ff4b4b; margin-bottom: 25px;">
        <h3 style="margin: 0; color: white;">👋 Ciao, {st.session_state.nome_user_loggato}!</h3>
        <p style="margin: 5px 0 0 0; color: #b0b0b0;">Bentornato in gruppo.</p>
    </div>
""", unsafe_allow_html=True)

try:
    # Caricamento dati per la dashboard
    p_d = supabase.table("view_stage_to_pick").select("*").limit(3).execute().data
    c_d = supabase.table("view_stage_current").select("*").execute().data
    l_d = supabase.table("view_stage_last_results").select("*").execute().data
    u_d = supabase.table("view_races_upcoming").select("*").execute().data

    # Sezione Pick
    st.markdown('<div class="section-title">✍️ Pick da fare</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if p_d:
            for p in p_d:
                col_t, col_b = st.columns([0.8, 0.2])
                col_t.write(f"**{p['race_name']}** (T{p.get('stage', 1)})")
                if col_b.button("Vai", key=f"p_{p['id_stage']}", use_container_width=True):
                    st.session_state.gara_selezionata_id = p['id_race']
                    st.session_state.tappa_selezionata_id = p['id_stage']
                    st.switch_page("pages/01_Inserimento.py")
        else:
            st.success("Tutti i pick completati ✅")

except Exception as e:
    st.error(f"Errore caricamento dati: {e}")
