import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar
from datetime import datetime, date, time, timedelta

# 1. Configurazione pagina
st.set_page_config(page_title="Virtua Cycling - Home", layout="wide", page_icon="🚴‍♂️")

# --- CSS PER MOBILE E HEADER ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
        header[data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; color: white !important; }
        [data-testid="stDecoration"] { display: none; }
        hr { margin: 10px 0 !important; opacity: 0.15; }
    </style>
""", unsafe_allow_html=True)

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- LOGICA DI SESSIONE E LOGIN ---
if 'id_user_loggato' not in st.session_state:
    st.session_state.id_user_loggato = None

if st.session_state.id_user_loggato is None:
    try:
        res_session = supabase.auth.get_session()
        if res_session and res_session.user:
            u_id = res_session.user.id
            u_info = supabase.table("dim_user").select("nickname, is_admin").eq("id_user", u_id).single().execute()
            st.session_state.id_user_loggato = u_id
            st.session_state.nome_user_loggato = u_info.data['nickname']
            st.session_state.is_admin = u_info.data.get('is_admin', False)
    except:
        pass

if st.session_state.id_user_loggato is None:
    st.markdown("<style>[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl'] { display: none !important; } .stTabs [data-baseweb='tab-list'] { justify-content: center; }</style>", unsafe_allow_html=True)
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
                            u_id = res.user.id
                            u_info = supabase.table("dim_user").select("nickname, is_admin").eq("id_user", u_id).single().execute()
                            st.session_state.id_user_loggato = u_id
                            st.session_state.nome_user_loggato = u_info.data['nickname']
                            st.session_state.is_admin = u_info.data.get('is_admin', False)
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
                        st.success("Ok! Ora accedi.")
                    except Exception as e: st.error(f"Errore: {e}")
    st.stop()

# --- DASHBOARD UTENTE ---
check_auth()
render_sidebar()

logo = "https://github.com/Jericho1987/virtua_cycling_3.0/blob/main/logo_pwa.png?raw=true"
st.markdown(f"""
    <div style="background-color: #1e1e1e; padding: 10px 18px; border-radius: 12px; border-left: 5px solid #ff4b4b; margin-bottom: 15px; display: flex; align-items: center;">
        <img src="{logo}" style="width: 50px; margin-right: 18px;">
        <div style="flex-grow: 1;">
            <h3 style="margin: 0; font-size: 1.5rem; color: white; line-height: 1.1;">👋 Ciao, {st.session_state.nome_user_loggato}!</h3>
            <p style="margin: 2px 0 0 0; color: #b0b0b0; font-size: 0.85rem;">Bentornato in gruppo.</p>
        </div>
    </div>
""", unsafe_allow_html=True)

try:
    p_d = supabase.table("view_stage_to_pick").select("*").execute().data
    c_d = supabase.table("view_stage_current").select("*").execute().data
    l_d = supabase.table("view_stage_last_results").select("*").execute().data
    u_d = supabase.table("view_races_upcoming").select("*").execute().data

    c_tl, c_tr = st.columns(2, gap="medium")
    
    with c_tl:
        st.subheader("✍️ Pick da fare")
        with st.container(border=True):
            if p_d:
                for p in p_d:
                    # Gestione Nome (Nascondi tappa se id_type_race è 3)
                    nome_mostrato = p['race_name'] if p.get('id_type_race') == 3 else f"{p['race_name']} (T{p['stage']})"
                    
                    # Logica Countdown Fighetto con i campi della tua vista
                    countdown_html = ""
                    try:
                        # Uniamo stage_date e stage_time
                        d_val = datetime.fromisoformat(p['stage_date']) if isinstance(p['stage_date'], str) else p['stage_date']
                        t_val = datetime.strptime(p['stage_time'], "%H:%M:%S").time() if isinstance(p['stage_time'], str) else p['stage_time']
                        deadline = datetime.combine(d_val, t_val)
                        
                        diff = deadline - datetime.now()
                        if diff.total_seconds() > 0:
                            ore_tot = int(diff.total_seconds() // 3600)
                            minuti = int((diff.total_seconds() // 60) % 60)
                            
                            if ore_tot > 24:
                                testo = f"{ore_tot//24}d {ore_tot%24}h"
                                colore = "#FFA500"
                            else:
                                testo = f"{ore_tot}h {minuti}m"
                                colore = "#FF4B4B"
                            
                            countdown_html = f'<span style="background-color: {colore}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; margin-left: 8px;">⏳ {testo}</span>'
                    except: pass

                    col_txt, col_btn = st.columns([0.75, 0.25])
                    col_txt.markdown(f"<div style='display: flex; align-items: center;'><b>{nome_mostrato}</b>{countdown_html}</div>", unsafe_allow_html=True)
                    
                    if col_btn.button("Vai", key=f"p_{p['id_stage']}", use_container_width=True):
                        st.session_state.gara_selezionata_id = p['id_race']
                        st.session_state.tappa_selezionata_id = p['id_stage']
                        st.switch_page("pages/01_Inserimento.py")
                    st.markdown("<hr>", unsafe_allow_html=True)
            else:
                st.success("Tutti i pick sono completi ✅")

    with c_tr:
        st.subheader("🏆 Ultimi risultati")
        with st.container(border=True):
            if l_d:
                for l in l_d: st.write(f"✅ {l['race_name']}")
                st.button("CLASSIFICHE 🏆", use_container_width=True, type="primary", on_click=lambda: st.switch_page("pages/02_Classifiche.py"))
            else: st.info("In attesa di risultati.")

    st.markdown("<br>", unsafe_allow_html=True)
    c_bl, c_br = st.columns(2, gap="medium")
    
    with c_bl:
        st.subheader("🏁 In corso")
        with st.container(border=True):
            if c_d:
                for c in c_d: st.write(f"🚴‍♂️ {c['race_name']} (T{c['stage']})")
            else: st.info("Nessuna gara live.")
            
    with c_br:
        st.subheader("📅 Prossime gare")
        with st.container(border=True):
            if u_d:
                for u in u_d: st.write(f"📅 {u['race_name']}")
            else: st.write("Calendario vuoto.")

except Exception as e:
    st.error(f"Errore nel caricamento dati: {e}")
