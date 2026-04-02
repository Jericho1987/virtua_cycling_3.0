import streamlit as st
from supabase import create_client

# --- 1. CONFIGURAZIONE BRANDING ---
NOME_APP = "Virtua Cycling"
# Nuovo link senza spazi per massima compatibilità
URL_LOGO = "https://github.com/Jericho1987/virtua_cycling_3.0/blob/main/logo_pwa.png?raw=true"

st.set_page_config(
    page_title=NOME_APP, 
    layout="wide", 
    page_icon=URL_LOGO
)

# --- 2. CONNESSIONE A SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 3. LOGICA PWA & CSS CUSTOM ---
# Ho aggiunto 'application-name' e 'mobile-web-app-capable' per Android/Chrome
st.markdown(f"""
    <head>
        <link rel="manifest" href="/manifest.json">
        
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="application-name" content="{NOME_APP}">
        <link rel="icon" sizes="192x192" href="{URL_LOGO}">
        <link rel="icon" sizes="512x512" href="{URL_LOGO}">
        
        <meta name="apple-mobile-web-app-title" content="{NOME_APP}">
        <link rel="apple-touch-icon" href="{URL_LOGO}">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        
        <meta name="theme-color" content="#121212">

        <script>
          if ('serviceWorker' in navigator) {{
            navigator.serviceWorker.register('/sw.js');
          }}
        </script>
    </head>
    
    <style>
    .stApp {{ background-color: #121212; }}
    
    /* Nasconde header e footer per simulare App Nativa */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    /* Ottimizzazione layout mobile */
    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 3rem !important;
    }}

    /* Box sezioni stile Dashboard */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {{
        background-color: #1e1e1e !important;
        border: 1px solid #333 !important;
        border-radius: 15px !important;
        padding: 20px !important;
    }}

    /* Input Login */
    .stTextInput input {{
        background-color: #262626 !important;
        color: white !important;
        border: 1px solid #555 !important;
    }}

    /* Header sezioni */
    .section-header {{
        font-size: 1.4rem;
        font-weight: bold;
        margin-bottom: 12px;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 4. GESTIONE ACCESSO (LOGIN) ---
if 'id_user_loggato' not in st.session_state:
    st.session_state.id_user_loggato = None

if not st.session_state.id_user_loggato:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        st.image(URL_LOGO, width=150)
        st.title(f"{NOME_APP}")
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

# --- 5. MESSAGGIO INSTALLAZIONE PWA (Solo post-login) ---
if 'avviso_pwa_mostrato' not in st.session_state:
    st.toast(f"📱 Installa {NOME_APP} sul tuo smartphone!", icon="💡")
    with st.expander("📲 Come usare Virtua Cycling come un'App"):
        st.info(f"""
        **iPhone (Safari):** Clicca 'Condividi' (quadrato con freccia) e seleziona **'Aggiungi alla schermata Home'**.
        \n**Android (Chrome):** Clicca i tre puntini in alto e seleziona **'Installa applicazione'**.
        """)
    st.session_state.avviso_pwa_mostrato = True

# --- 6. DASHBOARD PRINCIPALE ---
st.title(f"Ciao {st.session_state.nome_user_loggato}! 👋")

# Recupero dati dalle View
pick_data = supabase.table("view_stage_to_pick").select("*").execute().data
current_data = supabase.table("view_stage_current").select("*").execute().data
last_data = supabase.table("view_stage_last_results").select("*").execute().data
upcoming_data = supabase.table("view_races_upcoming").select("*").execute().data

col_left, col_right = st.columns(2, gap="medium")

with col_left:
    st.markdown('<div class="section-header">✍️ Pick da fare</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if pick_data:
            for p in pick_data:
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.write(f"**{p['race_name']}**")
                    st.caption(f"Tappa {p['stage']} • Scadenza: {p['stage_time']}")
                with c2:
                    if st.button("Vai ✍️", key=f"btn_{p['id_stage']}", use_container_width=True):
                        st.session_state.gara_selezionata_id = p['id_race']
                        st.session_state.tappa_selezionata_id = p['id_stage']
                        st.switch_page("pages/01_Inserimento.py")
                st.divider()
        else:
            st.write("Tutti i pick sono completati! ✅")

    st.write("") 

    st.markdown('<div class="section-header">🏁 In corso</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if current_data:
            for c in current_data:
                st.write(f"🚴‍♂️ **{c['race_name']}**")
                st.caption(f"Tappa {c['stage']} • Live")
                st.divider()
        else:
            st.write("Nessuna corsa attiva al momento.")

with col_right:
    st.markdown('<div class="section-header">🏆 Ultimi Risultati</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if last_data:
            st.write(f"Risultati del: {last_data[0]['stage_date']}")
            for l in last_data:
                st.write(f"✅ **{l['race_name']}**")
            if st.button("VEDI CLASSIFICHE 🏆", use_container_width=True):
                st.switch_page("pages/02_Classifiche.py")
        else:
            st.write("In attesa di risultati ufficiali.")

    st.write("") 

    st.markdown('<div class="section-header">📅 Prossime Gare</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if upcoming_data:
            for u in upcoming_data:
                st.write(f"📅 **{u['race_name']}**")
                st.caption(f"Data: {u['stage_date']}")
                st.divider()
        else:
            st.write("Calendario in fase di definizione.")

# Sidebar
with st.sidebar:
    st.image(URL_LOGO, width=100)
    st.write(f"Utente: **{st.session_state.nome_user_loggato}**")
    st.divider()
    if st.button("Esci 🚪", use_container_width=True):
        st.session_state.id_user_loggato = None
        st.rerun()
