import streamlit as st
from supabase import create_client

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

# --- 4. CSS DINAMICO ---
if st.session_state.id_user_loggato is None:
    # NASCONDE SIDEBAR SE NON LOGGATO
    st.markdown("""
        <style>
            [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {
                display: none !important;
            }
        </style>
    """, unsafe_allow_html=True)
else:
    # MOSTRA SIDEBAR SE LOGGATO (Resetta il display)
    st.markdown("""
        <style>
            [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {
                display: flex !important;
            }
        </style>
    """, unsafe_allow_html=True)

# CSS Standard per elementi grafici
st.markdown("""
    <style>
    footer {visibility: hidden;}
    .sidebar-user-box { display: flex; align-items: center; gap: 12px; padding: 5px 0; }
    .sidebar-user-box img {
        border-radius: 50% !important; border: 2px solid #ff69b4 !important;
        width: 45px !important; height: 45px !important; object-fit: cover;
    }
    .race-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #333; font-size: 0.85rem; }
    .side-header { font-size: 0.7rem; color: #888; text-transform: uppercase; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. GESTIONE LOGIN ---
if st.session_state.id_user_loggato is None:
    _, col_login, _ = st.columns([1, 1.2, 1])
    with col_login:
        st.image(URL_LOGO, width=100)
        st.title("Virtua Cycling")
        with st.form("login_form"):
            email_input = st.text_input("Email")
            password_input = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI 🚀", use_container_width=True):
                query = supabase.table("dim_user").select("*").eq("email", email_input).eq("password", password_input).execute()
                if query.data:
                    st.session_state.id_user_loggato = query.data[0]['id_user']
                    st.session_state.nome_user_loggato = query.data[0]['display_name']
                    st.rerun()
                else:
                    st.error("Credenziali errate")
    st.stop()

# --- 6. DASHBOARD (Sotto il login) ---
# ... qui metti tutto il codice della tua dashboard (t1, t2, col_left, col_right) ...

# --- 7. SIDEBAR (CORRETTA PER GITHUB) ---
with st.sidebar:
    # ATTENZIONE: Usa "Home.py" con la H maiuscola se il file su GitHub si chiama così!
    st.page_link("Home.py", label="Home", icon="🏠") 
    st.page_link("pages/01_Inserimento.py", label="Pick", icon="✍️")
    st.page_link("pages/02_Classifiche.py", label="Classifiche", icon="🏆")

    st.markdown("---")
    st.markdown('<p class="side-header">Area Personale</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="sidebar-user-box"><img src="https://github.com/Jericho1987/virtua_cycling_3.0/blob/main/rider_logo.jpg?raw=true"> <b>{st.session_state.nome_user_loggato}</b></div>', unsafe_allow_html=True)
    
    if st.button("Esci 🚪", use_container_width=True):
        st.session_state.id_user_loggato = None
        st.rerun()

    st.markdown("---")
    st.markdown('<p class="side-header" style="color: #ff4b4b;">🛠️ Amministrazione</p>', unsafe_allow_html=True)
    st.page_link("pages/03_Gestione_Risultati.py", label="Risultati", icon="📊")
    st.page_link("pages/04_Upload_Startlist.py", label="Startlist", icon="📑")
