import streamlit as st
from supabase import create_client
from auth_utils import render_sidebar  # Importiamo la sidebar centralizzata

# --- 1. CONFIGURAZIONE BRANDING ---
NOME_APP = "Virtua Cycling"
URL_LOGO = "https://github.com/Jericho1987/virtua_cycling_3.0/blob/main/logo_pwa.png?raw=true"

# Deve essere la prima istruzione Streamlit
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
    # --- SCHERMATA LOGIN ---
    # CSS per nascondere sidebar e centrare il form
    st.markdown("""
        <style>
            [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {
                display: none !important;
            }
            .block-container {
                padding-top: 5rem !important;
            }
        </style>
    """, unsafe_allow_html=True)

    _, col_login, _ = st.columns([1, 1.2, 1])
    with col_login:
        st.image(URL_LOGO, width=100)
        st.title("Virtua Cycling")
        with st.form("login_form"):
            email_input = st.text_input("Email")
            password_input = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI ALLA GARA 🚀", use_container_width=True):
                query = supabase.table("dim_user").select("*").eq("email", email_input).eq("password", password_input).execute()
                if query.data:
                    st.session_state.id_user_loggato = query.data[0]['id_user']
                    st.session_state.nome_user_loggato = query.data[0]['display_name']
                    st.rerun()
                else:
                    st.error("Credenziali errate")
    st.stop()

else:
    # --- SCHERMATA DASHBOARD (UTENTE LOGGATO) ---
    
    # CSS per ripristinare la sidebar e stile generale
    st.markdown("""
        <style>
        footer {visibility: hidden;}
        [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
        [data-testid="stSidebar"] { display: flex !important; }
        
        .sidebar-user-box { display: flex; align-items: center; gap: 12px; padding: 5px 0; }
        .sidebar-user-box img {
            border-radius: 50% !important; border: 2px solid #ff69b4 !important;
            width: 45px !important; height: 45px !important; object-fit: cover;
        }
        .race-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #333; font-size: 0.85rem; }
        .side-header { font-size: 0.7rem; color: #888; text-transform: uppercase; margin-top: 15px; margin-bottom: 5px; }
        </style>
    """, unsafe_allow_html=True)

    # Richiamiamo la sidebar dal file auth_utils
    render_sidebar()

    # Intestazione Dashboard
    t1, t2 = st.columns([0.1, 0.9])
    with t1: st.image(URL_LOGO, width=60)
    with t2: st.markdown(f"### Ciao {st.session_state.nome_user_loggato}! 👋")

    # Recupero dati da Supabase
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
            else: st.success("Pick completati! ✅")

        st.caption("🏁 IN CORSO")
        with st.container(border=True):
            if current_data:
                for c in current_data:
                    st.write(f"🚴‍♂️ {c['race_name']} (T{c['stage']})")
            else: st.info("Nessuna corsa attiva.")

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
                    st.markdown(f'<div class="race-row"><span>📅 {u["race_name"]}</span><span style="color:#666;">{u["stage_date"]}</span></div>', unsafe_allow_html=True)
