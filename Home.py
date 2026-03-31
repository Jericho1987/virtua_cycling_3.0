import streamlit as st
from supabase import create_client

# 1. Configurazione Pagina
st.set_page_config(page_title="FantaCiclismo Dashboard", layout="wide", page_icon="🚴‍♂️")

# 2. Connessione a Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 3. CSS PER IL LAYOUT A BLOCCHI E VISIBILITÀ ---
st.markdown("""
    <style>
    .stApp { background-color: #121212; }
    
    /* Stile per i contenitori bianchi/grigi definiti */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: #1e1e1e !important;
        border: 1px solid #333 !important;
        border-radius: 10px !important;
        padding: 20px !important;
    }

    /* Input visibili nel login */
    .stTextInput input {
        background-color: #262626 !important;
        color: white !important;
        border: 1px solid #555 !important;
    }

    /* Titoli sezioni */
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 4. Gestione Accesso
if 'id_user_loggato' not in st.session_state:
    st.session_state.id_user_loggato = None

if not st.session_state.id_user_loggato:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        st.title("🚴‍♂️ FantaCiclismo PRO")
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

# --- 5. DASHBOARD PRINCIPALE (LAYOUT ORIGINALE) ---
st.title(f"Benvenuto, {st.session_state.nome_user_loggato}! 👋")

# Recupero dati dalle View
pick_data = supabase.table("view_stage_to_pick").select("*").execute().data
current_data = supabase.table("view_stage_current").select("*").execute().data
last_data = supabase.table("view_stage_last_results").select("*").execute().data
upcoming_data = supabase.table("view_races_upcoming").select("*").execute().data

# Layout a due grandi colonne
col_left, col_right = st.columns(2, gap="large")

with col_left:
    # --- BLOCCO 1: PICK DA FARE ---
    st.markdown('<div class="section-header">✍️ Pick da fare</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if pick_data:
            for p in pick_data:
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.write(f"**{p['race_name']}** - Tappa {p['stage']}")
                    st.caption(f"👥 {p['pick_limit']} slot • ⏰ Parte alle: {p['stage_time']}")
                with c2:
                    if st.button("Vai ✍️", key=f"btn_{p['id_stage']}", use_container_width=True):
                        st.session_state.gara_selezionata_id = p['id_race']
                        st.session_state.tappa_selezionata_id = p['id_stage']
                        st.switch_page("pages/01_Inserimento.py")
                st.divider()
        else:
            st.write("Nessun pick da fare.")

    st.write("") # Spaziatore

    # --- BLOCCO 2: GARA IN CORSO ---
    st.markdown('<div class="section-header">🏁 Gara in corso</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if current_data:
            for c in current_data:
                st.write(f"🚴‍♂️ **{c['race_name']}**")
                st.caption(f"Tappa {c['stage']} • In svolgimento")
                st.divider()
        else:
            st.write("Nessuna gara attiva.")

with col_right:
    # --- BLOCCO 3: ULTIMI RISULTATI ---
    st.markdown('<div class="section-header">⏪ Ultimi Risultati</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if last_data:
            st.write(f"Gare del: {last_data[0]['stage_date']}")
            for l in last_data:
                st.write(f"✅ **{l['race_name']}** (Tappa {l['stage']})")
            if st.button("VEDI TUTTI 🏆", use_container_width=True):
                st.switch_page("pages/02_Classifiche.py")
        else:
            st.write("Nessun risultato recente.")

    st.write("") # Spaziatore

    # --- BLOCCO 4: PROSSIMI APPUNTAMENTI ---
    st.markdown('<div class="section-header">📅 Prossimi appuntamenti</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if upcoming_data:
            for u in upcoming_data:
                st.write(f"📅 **{u['race_name']}**")
                st.caption(f"Data: {u['stage_date']}")
                st.divider()
        else:
            st.write("Calendario in aggiornamento.")

# Sidebar minimalista (Log out a sinistra)
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3774/3774270.png", width=60)
    st.write(f"👤 Utente: **{st.session_state.nome_user_loggato}**")
    st.divider()
    if st.button("Logout 🚪", use_container_width=True):
        st.session_state.id_user_loggato = None
        st.rerun()