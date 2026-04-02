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

# --- 3. CONNESSIONE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 4. GESTIONE SESSIONE ---
if "supabase_session" in st.session_state and st.session_state.supabase_session:
    supabase.auth.set_session(
        st.session_state.supabase_session.access_token, 
        st.session_state.supabase_session.refresh_token
    )

st.title("⚙️ Gestione Profilo")
st.write(f"Stai modificando l'account di: **{st.session_state.nome_user_loggato}**")

tab_nick, tab_mail, tab_pass = st.tabs(["👤 Nickname & Display", "📧 Email", "🔑 Password"])

# --- TAB 1: NICKNAME ---
with tab_nick:
    st.subheader("Personalizza la tua identità")
    with st.form("form_nickname"):
        nuovo_nick = st.text_input("Nuovo Nickname / Display Name", value=st.session_state.nome_user_loggato)
        if st.form_submit_button("Aggiorna Profilo", use_container_width=True):
            if nuovo_nick:
                try:
                    supabase.table("dim_user").update({"nickname": nuovo_nick, "display_name": nuovo_nick}).eq("id_user", st.session_state.id_user_loggato).execute()
                    st.session_state.nome_user_loggato = nuovo_nick
                    st.success("Profilo aggiornato! ✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

# --- TAB 2: EMAIL (AGGIORNATA) ---
with tab_mail:
    st.subheader("Cambia Indirizzo Email")
    with st.form("form_email"):
        nuova_email = st.text_input("Nuova Email")
        if st.form_submit_button("Aggiorna Email", use_container_width=True):
            if "@" in nuova_email and "." in nuova_email:
                try:
                    # Forza il token attuale prima dell'invio
                    supabase.auth.set_session(st.session_state.supabase_session.access_token, st.session_state.supabase_session.refresh_token)
                    
                    # Aggiorna Auth di sistema
                    supabase.auth.update_user({"email": nuova_email})
                    
                    # Aggiorna Tabella Utenti
                    supabase.table("dim_user").update({"email": nuova_email}).eq("id_user", st.session_state.id_user_loggato).execute()
                    
                    st.success("Email modificata! Effettua il logout e rientra per confermare.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

# --- TAB 3: PASSWORD ---
with tab_pass:
    st.subheader("Sicurezza Account")
    with st.form("form_password"):
        n_pass = st.text_input("Nuova Password", type="password")
        c_pass = st.text_input("Conferma Password", type="password")
        if st.form_submit_button("Cambia Password", use_container_width=True):
            if len(n_pass) >= 6 and n_pass == c_pass:
                try:
                    supabase.auth.update_user({"password": n_pass})
                    st.success("Password aggiornata! 🔐")
                except Exception as e:
                    st.error(f"Errore: {e}")
            else:
                st.error("Errore nelle password.")

st.divider()
st.caption("Virtua Cycling 3.0 | Impostazioni Account")
