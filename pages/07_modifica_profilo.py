import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar 

# --- 1. CONFIGURAZIONE PAGINA (Identica a 02) ---
st.set_page_config(page_title="Modifica Profilo", layout="wide", page_icon="⚙️")

# --- 2. PROTEZIONE E SIDEBAR (Identica a 02) ---
check_auth()      
render_sidebar()  

if not st.session_state.get('id_user_loggato'):
    st.switch_page("Home.py")

# --- 3. CONNESSIONE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("⚙️ Gestione Profilo")
st.write(f"Stai modificando l'account di: **{st.session_state.nome_user_loggato}**")

# Usiamo i Tabs per organizzare le tre diverse modifiche
tab_nick, tab_mail, tab_pass = st.tabs(["👤 Nickname", "📧 Email", "🔑 Password"])

# --- TAB 1: MODIFICA NICKNAME ---
with tab_nick:
    st.subheader("Cambia il tuo Nickname")
    with st.form("form_nickname"):
        nuovo_nick = st.text_input("Nuovo Nickname", value=st.session_state.nome_user_loggato)
        if st.form_submit_button("Aggiorna Nickname", use_container_width=True):
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
    st.warning("Nota: Poiché 'Confirm Email' è OFF, l'email verrà cambiata immediatamente.")
    with st.form("form_email"):
        nuova_email = st.text_input("Nuova Email")
        if st.form_submit_button("Aggiorna Email", use_container_width=True):
            if "@" in nuova_email and "." in nuova_email:
                try:
                    # Aggiorna Auth
                    supabase.auth.update_user({"email": nuova_email})
                    # Aggiorna dim_user (se hai la colonna email lì)
                    supabase.table("dim_user").update({"email": nuova_email})\
                        .eq("id_user", st.session_state.id_user_loggato).execute()
                    
                    st.success(f"Email aggiornata a: {nuova_email}")
                except Exception as e:
                    st.error(f"Errore: {e}")
            else:
                st.error("Inserisci un'email valida.")

# --- TAB 3: MODIFICA PASSWORD ---
with tab_pass:
    st.subheader("Cambia Password")
    with st.form("form_password"):
        n_pass = st.text_input("Nuova Password", type="password")
        c_pass = st.text_input("Conferma Nuova Password", type="password")
        if st.form_submit_button("Aggiorna Password", use_container_width=True):
            if len(n_pass) >= 6 and n_pass == c_pass:
                try:
                    supabase.auth.update_user({"password": n_pass})
                    st.success("Password aggiornata con successo!")
                except Exception as e:
                    st.error(f"Errore: {e}")
            else:
                st.error("Le password non coincidono o sono troppo corte (min 6 car.).")

st.divider()
st.caption("Virtua Cycling 3.0 - Gestione Account Sicura")
