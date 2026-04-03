import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar
from datetime import datetime, date, time, timedelta

# 1. Configurazione pagina
st.set_page_config(page_title="Virtua Cycling - Home", layout="wide", page_icon="🚴‍♂️")

# --- CSS COMPLETO (Incluso lo stile per le nuove Race Card) ---
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

        /* Stile per il box Prossime Gare */
        .race-card {
            display: flex;
            align-items: center;
            background: #1e1e1e;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 10px;
            border-left: 4px solid #ff4b4b;
        }
        .date-badge {
            background-color: #0e1117;
            color: #ff4b4b;
            padding: 6px 0;
            border-radius: 8px;
            font-weight: bold;
            font-size: 0.85rem;
            min-width: 60px;
            text-align: center;
            margin-right: 15px;
            border: 1px solid #333;
            line-height: 1.2;
        }
        .race-info { flex-grow: 1; }
        .stage-text {
            color: #b0b0b0;
            font-size: 0.85rem;
            margin-left: 5px;
        }
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
                submit = st.form_submit_button("ACCEDI 🚀", use_container_width=True)
                if submit:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": e_in, "password": p_in})
                        if res.user:
                            u_id = res.user.id
                            u_info = supabase.table("dim_user").select("nickname, is_admin").eq("id_user", u_id).single().execute()
                            st.session_state.id_user_loggato = u_id
                            st.session_state.nome_user_loggato = u_info.data['nickname']
                            st.session_state.is_admin = u_info.data.get('is_admin', False)
                            st.rerun()
                        else:
                            st.error("Credenziali errate.")
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
                    except Exception as e: 
                        st.error(f"Errore: {e}")
    st.stop()

# --- DASHBOARD ---
check_auth()
render_sidebar()

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

try:
    p_d = supabase.table("view_stage_to_pick").select("*").execute().data
    c_d = supabase.table("view_stage_current").select("*").execute().data
    l_d = supabase.table("view_stage_last_results").select("*").execute().data
    u_d = supabase.table("view_races_upcoming").select("*").execute().data

    # --- 1. PICK DA FARE ---
    st.markdown('<div class="section-title">✍️ Pick da fare</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if p_d:
            for p in p_d:
                nome_mostrato = p['race_name'] if p.get('id_type_race') == 3 else f"{p['race_name']} (T{p['stage']})"
                countdown_html = ""
                try:
                    d_val = datetime.fromisoformat(str(p['stage_date']))
                    t_val = datetime.strptime(str(p['stage_time']), "%H:%M:%S").time()
                    deadline = datetime.combine(d_val, t_val)
                    diff = deadline - datetime.now()
                    if diff.total_seconds() > 0:
                        g, o, m = diff.days, diff.seconds // 3600, (diff.seconds // 60) % 60
                        color = "#ff4b4b" if g == 0 and o < 12 else "#b0b0b0"
                        countdown_html = f'<span style="color: {color}; font-size: 0.8rem; margin-left: 10px;">⏳ {g}d {o}h {m}m</span>'
                except: pass

                col_t, col_b = st.columns([0.8, 0.2])
                col_t.markdown(f"<div style='display: flex; align-items: center; min-height: 45px;'><b>{nome_mostrato}</b>{countdown_html}</div>", unsafe_allow_html=True)
                if col_b.button("Vai", key=f"p_{p['id_stage']}", use_container_width=True):
                    st.session_state.gara_selezionata_id = p['id_race']
                    st.session_state.tappa_selezionata_id = p['id_stage']
                    st.switch_page("pages/01_Inserimento.py")
                st.markdown("<hr>", unsafe_allow_html=True)
        else:
            st.success("Tutti i pick sono completi ✅")

    # --- 2. ULTIMI RISULTATI ---
    st.markdown('<div class="section-title">🏆 Ultimi risultati</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if l_d:
            for l in l_d:
                st.markdown(f"✅ {l['race_name']}")
            st.button("VEDI CLASSIFICHE 🏆", use_container_width=True, type="primary", on_click=lambda: st.switch_page("pages/02_Classifiche.py"))
        else: st.info("In attesa di risultati.")

    # --- 3. IN CORSO ---
    st.markdown('<div class="section-title">🏁 In corso</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if c_d:
            for c in c_d:
                nome_live = c['race_name'] if c.get('id_type_race') == 3 else f"{c['race_name']} (Tappa {c['stage']})"
                col_tc, col_bc = st.columns([0.8, 0.2])
                col_tc.markdown(f"<div style='display: flex; align-items: center; min-height: 45px;'>🚴‍♂️ <b>{nome_live}</b></div>", unsafe_allow_html=True)
                if col_bc.button("Vai", key=f"c_{c['id_stage']}", use_container_width=True):
                    st.session_state.gara_selezionata_id = c['id_race']
                    st.session_state.tappa_selezionata_id = c['id_stage']
                    st.switch_page("pages/01_Inserimento.py")
                st.markdown("<hr>", unsafe_allow_html=True)
        else: st.info("Nessuna gara live.")

    # --- 4. PROSSIME GARE (Stilizzato) ---
    st.markdown('<div class="section-title">📅 Prossime gare</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if u_d:
            for u in u_d:
                # Formattazione Data
                data_f = "--/--"
                if u.get('stage_date'):
                    try: data_f = datetime.fromisoformat(str(u['stage_date'])).strftime("%d/%m")
                    except: data_f = str(u['stage_date'])
                
                # Testo Tappa esteso
                tappa_label = ""
                if u.get('id_type_race') != 3 and u.get('stage'):
                    tappa_label = f"<span class='stage-text'>• Tappa {u['stage']}</span>"
                
                st.markdown(f"""
                    <div class="race-card">
                        <div class="date-badge">{data_f}</div>
                        <div class="race-info">
                            <span style="font-weight: bold; color: white;">{u['race_name']}</span>
                            {tappa_label}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else: st.write("Nessuna gara in programma.")

except Exception as e:
    st.error(f"Errore: {e}")
