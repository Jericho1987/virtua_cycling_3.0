import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar
from datetime import datetime

# 1. Configurazione pagina
st.set_page_config(page_title="Virtua Cycling - Home", layout="wide", page_icon="🚴‍♂️")

# --- CSS PER MOBILE E HEADER ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
        header[data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; color: white !important; }
        [data-testid="stDecoration"] { display: none; }
        hr { margin: 15px 0 !important; opacity: 0.15; }
        .section-title { 
            font-size: 1.4rem; 
            font-weight: bold; 
            margin-bottom: 10px; 
            display: flex; 
            align-items: center; 
            gap: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# --- INIZIALIZZAZIONE SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- LOGICA SESSIONE ---
if 'id_user_loggato' not in st.session_state:
    st.session_state.id_user_loggato = None

if "just_logged" not in st.session_state:
    st.session_state.just_logged = False

# --- SCHERMATA LOGIN ---
if st.session_state.id_user_loggato is None:
    st.markdown(
        "<style>[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl'] { display: none !important; } .stTabs [data-baseweb='tab-list'] { justify-content: center; }</style>",
        unsafe_allow_html=True
    )

    _, col_login, _ = st.columns([1, 1.2, 1])

    with col_login:
        st.title("Virtua Cycling")
        t1, t2 = st.tabs(["🔐 Accedi", "✨ Registrati"])

        # --- LOGIN ---
        with t1:
            with st.form("login_form"):
                e_in = st.text_input("Email")
                p_in = st.text_input("Password", type="password")
                submit = st.form_submit_button("ACCEDI 🚀", use_container_width=True)

                if submit:
                    if not e_in or not p_in:
                        st.error("Inserisci email e password")
                    else:
                        try:
                            res = supabase.auth.sign_in_with_password({
                                "email": e_in,
                                "password": p_in
                            })

                            if res and res.user:
                                u_info = supabase.table("dim_user") \
                                    .select("nickname, is_admin") \
                                    .eq("id_user", res.user.id) \
                                    .single().execute()

                                # SESSIONE
                                st.session_state.id_user_loggato = res.user.id
                                st.session_state.nome_user_loggato = u_info.data['nickname']
                                st.session_state.is_admin = u_info.data.get('is_admin', False)
                                st.session_state.supabase_session = res.session
                                st.session_state.just_logged = True

                                st.rerun()
                            else:
                                st.error("Credenziali errate.")
                        except Exception:
                            st.error("Credenziali errate.")

        # --- REGISTRAZIONE ---
        with t2:
            with st.form("reg_form"):
                n_e = st.text_input("Email")
                n_p = st.text_input("Password", type="password")
                n_n = st.text_input("Nickname")

                if st.form_submit_button("REGISTRATI ✨", use_container_width=True):
                    try:
                        supabase.auth.sign_up({
                            "email": n_e,
                            "password": n_p,
                            "options": {"data": {"nickname": n_n}}
                        })
                        st.success("Ok! Ora accedi.")
                    except Exception as e:
                        st.error(f"Errore: {e}")

    st.stop()

# --- RESET FLAG POST LOGIN ---
if st.session_state.just_logged:
    st.session_state.just_logged = False

# --- DASHBOARD UTENTE ---
check_auth()
render_sidebar()

# Forza sidebar mobile
st.markdown("""
    <style>
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { 
            display: flex !important; 
        }
    </style>
""", unsafe_allow_html=True)

logo = "https://github.com/Jericho1987/virtua_cycling_3.0/blob/main/logo_pwa.png?raw=true"

st.markdown(f"""
    <div style="background-color: #1e1e1e; padding: 10px 18px; border-radius: 12px; border-left: 5px solid #ff4b4b; margin-bottom: 25px; display: flex; align-items: center;">
        <img src="{logo}" style="width: 50px; margin-right: 18px;">
        <div style="flex-grow: 1;">
            <h3 style="margin: 0; font-size: 1.5rem; color: white; line-height: 1.1;">👋 Ciao, {st.session_state.nome_user_loggato}!</h3>
            <p style="margin: 2px 0 0 0; color: #b0b0b0; font-size: 0.85rem;">Bentornato in gruppo.</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- DATI DASHBOARD ---
try:
    p_d = supabase.table("view_stage_to_pick").select("*").limit(3).execute().data
    c_d = supabase.table("view_stage_current").select("*").execute().data
    l_d = supabase.table("view_stage_last_results").select("*").execute().data
    u_d = supabase.table("view_races_upcoming").select("*").execute().data

    # --- PICK ---
    st.markdown('<div class="section-title">✍️ Pick da fare</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if p_d:
            for p in p_d:
                nome_mostrato = p['race_name'] if p.get('id_type_race') == 3 else f"{p['race_name']} (T{p['stage']})"

                col_txt, col_btn = st.columns([0.8, 0.2])
                col_txt.markdown(f"<b>{nome_mostrato}</b>", unsafe_allow_html=True)

                if col_btn.button("Vai", key=f"p_{p['id_stage']}", use_container_width=True):
                    st.session_state.gara_selezionata_id = p['id_race']
                    st.session_state.tappa_selezionata_id = p['id_stage']
                    st.switch_page("pages/01_Inserimento.py")

                st.markdown("<hr>", unsafe_allow_html=True)
        else:
            st.success("Tutti i pick sono completi ✅")

    # --- IN CORSO ---
    st.markdown('<div class="section-title">🏁 In corso</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if c_d:
            for c in c_d:
                nome_live = c['race_name'] if c.get('id_type_race') == 3 else f"{c['race_name']} (Tappa {c['stage']})"

                col_txt_c, col_btn_c = st.columns([0.8, 0.2])
                col_txt_c.markdown(f"🚴‍♂️ <b>{nome_live}</b>", unsafe_allow_html=True)

                if col_btn_c.button("Vai", key=f"c_{c['id_stage']}", use_container_width=True):
                    st.session_state.gara_selezionata_id = c['id_race']
                    st.session_state.tappa_selezionata_id = c['id_stage']
                    st.switch_page("pages/01_Inserimento.py")

                st.markdown("<hr>", unsafe_allow_html=True)
        else:
            st.info("Nessuna gara live in questo momento.")

except Exception as e:
    st.error(f"Errore nel caricamento dati: {e}")
