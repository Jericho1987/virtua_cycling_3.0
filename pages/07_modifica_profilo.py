import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar 

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Modifica Profilo", layout="wide", page_icon="⚙️")

# --- 2. PROTEZIONE E SIDEBAR ---
check_auth()      
render_sidebar()  

if not st.session_state.get('id_user_loggato'):
    st.switch_page("Home.py")

# --- 3. CONNESSIONE CON GESTIONE SESSIONE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# Colleghiamo la sessione al client per permettere le modifiche protette (Auth)
if "supabase_session" in st.session_state and st.session_state.supabase_session:
    supabase.auth.set_session(
        st.session_state.supabase_session.access_token, 
        st.session_state.supabase_session.refresh_token
    )

st.title("⚙️ Gestione Profilo")
st.write(f"Stai modificando l'account di: **{st.session_state.nome_user_loggato}**")

# Organizzazione in Tabs
tab_nick, tab_mail, tab_pass = st.tabs(["👤 Nickname & Display", "📧 Email", "🔑 Password"])

# --- TAB 1: MODIFICA NICKNAME E DISPLAY NAME ---
with tab_nick:
    st.subheader("Personalizza la tua identità")
    with st.form("form_nickname"):
        nuovo_nick = st.text_input("Nuovo Nickname / Display Name", value=st.session_state.nome_user_loggato)
        
        if st.form_submit_button("Aggiorna Profilo", use_container_width=True):
            if nuovo_nick:
                try:
                    # Aggiorna entrambi i campi nella tabella dim_user
                    supabase.table("dim_user").update({
                        "nickname": nuovo_nick,
                        "display_name": nuovo_nick
                    }).eq("id_user", st.session_state.id_user_loggato).execute()
                    
                    # Aggiorna la sessione locale per la sidebar
                    st.session_state.nome_user_loggato = nuovo_nick
                    
                    st.success("Profilo aggiornato con successo! ✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante l'aggiornamento: {e}")
            else:
                st.warning("Il campo non può essere vuoto.")

# --- TAB 2: MODIFICA EMAIL ---
with tab_mail:
    st.subheader("Cambia Indirizzo Email")
    st.info("L'email verrà aggiornata istantaneamente sia nel sistema di login che nel tuo profilo.")
    with st.form("form_email"):
        nuova_email = st.text_input("Nuova Email")
        if st.form_submit_button("Aggiorna Email", use_container_width=True):
            if "@" in nuova_email and "." in nuova_email:
                try:
                    # 1. Aggiorna l'autenticazione di sistema (Richiede sessione valida)
                    supabase.auth.update_user({"email": nuova_email})
                    
                    # 2. Aggiorna il riferimento email nella tabella dim_user
                    supabase.table("dim_user").update({"email": nuova_email})\
                        .eq("id_user", st.session_state.id_user_loggato).execute()
                    
                    st.success(f"Email aggiornata correttamente a: {nuova_email}")
                except Exception as e:
                    st.error(f"Errore: {e}")
            else:
                st.error("Inserisci un indirizzo email valido.")

# --- TAB 3: MODIFICA PASSWORD ---
with tab_pass:
    st.subheader("Sicurezza Account")
    with st.form("form_password"):
        n_pass = st.text_input("Nuova Password", type="password", help="Minimo 6 caratteri")
        c_pass = st.text_input("Conferma Nuova Password", type="password")
        
        if st.form_submit_button("Cambia Password", use_container_width=True):
            if len(n_pass) >= 6 and n_pass == c_pass:
                try:
                    # Richiede sessione valida
                    supabase.auth.update_user({"password": n_pass})
                    st.success("Password modificata con successo! 🔐")
                except Exception as e:
                    st.error(f"Errore: {e}")
            else:
                st.error("Le password non coincidono o sono troppo brevi.")

st.divider()
st.caption("Virtua Cycling 3.0 | Impostazioni Account")
