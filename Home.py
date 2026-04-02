import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar

st.set_page_config(page_title="Virtua Cycling - Home", layout="wide", page_icon="🚴‍♂️")

st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
        header { visibility: hidden; height: 0px; }
    </style>
""", unsafe_allow_html=True)

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

if 'id_user_loggato' not in st.session_state:
    st.session_state.id_user_loggato = None

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
                        # Autenticazione Supabase
                        res = supabase.auth.sign_in_with_password({"email": e_in, "password": p_in})
                        
                        if res.user:
                            u_id = res.user.id
                            # Recupero dati profilo
                            u_info = supabase.table("dim_user").select("nickname, is_admin").eq("id_user", u_id).single().execute()
                            
                            # Scrittura immediata in session_state
                            st.session_state.id_user_loggato = u_id
                            st.session_state.nome_user_loggato = u_info.data['nickname']
                            st.session_state.is_admin = u_info.data.get('is_admin', False)
                            
                            # Rerun forzato per saltare subito alla dashboard
                            st.rerun()
                    except Exception:
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

# Se arriviamo qui, l'utente è loggato
check_auth()
render_sidebar()

logo = "https://github.com/Jericho1987/virtua_cycling_3.0/blob/main/logo_pwa.png?raw=true"
st.markdown(f"""
    <div style="background-color: #1e1e1e; padding: 10px 18px; border-radius: 12px; border-left: 5px solid #ff4b4b; margin-bottom: 15px; display: flex; align-items: center;">
        <img src="{logo}" style="width: 50px; margin-right: 18px;">
        <div style="flex-grow: 1;">
            <h3 style="margin: 0; font-size: 1.5rem; color: white; line-height: 1.1;">👋 Ciao, {st.session_state.nome_user_loggato}!</h3>
            <p style="margin: 2px 0 0 0; color: #b0b0b0; font-size: 0.85rem;">Bentornato in gruppo. Ecco i tuoi aggiornamenti.</p>
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
                    c1, c2 = st.columns([0.7, 0.3])
                    c1.write(f"**{p['race_name']}** (T{p['stage']})")
                    if c2.button("Vai", key=f"p_{p['id_stage']}", use_container_width=True):
                        st.session_state.gara_selezionata_id = p['id_race']
                        st.session_state.tappa_selezionata_id = p['id_stage']
                        st.switch_page("pages/01_Inserimento.py")
            else: st.success("Pick completati! ✅")
    with c_tr:
        st.subheader("🏆 Ultimi risultati")
        with st.container(border=True):
            if l_d:
                for l in l_d: st.write(f"✅ {l['race_name']}")
                st.button("CLASSIFICHE 🏆", use_container_width=True, type="primary", on_click=lambda: st.switch_page("pages/02_Classifiche.py"))
            else: st.info("Nessuno.")

    st.markdown("<br>", unsafe_allow_html=True) 
    c_bl, c_br = st.columns(2, gap="medium")
    with c_bl:
        st.subheader("🏁 In corso")
        with st.container(border=True):
            if c_d:
                for c in c_d: st.write(f"🚴‍♂️ {c['race_name']} (T{c['stage']})")
            else: st.info("Nessuna.")
    with c_br:
        st.subheader("📅 Prossime gare")
        with st.container(border=True):
            if u_d:
                for u in u_d: st.markdown(f"<span>📅 {u['race_name']}</span>", unsafe_allow_html=True)
            else: st.write("Nessuna.")
except Exception as e:
    st.error(f"Errore: {e}")
