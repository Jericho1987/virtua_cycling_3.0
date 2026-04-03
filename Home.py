import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar
from datetime import datetime, timedelta
import extra_streamlit_components as stx
import time

# 1. Configurazione pagina
st.set_page_config(page_title="Virtua Cycling - Home", layout="wide", page_icon="🚴‍♂️")

# --- INIZIALIZZAZIONE COOKIE MANAGER (Unica istanza per la Home) ---
cookie_manager = stx.CookieManager(key="home_cookie_manager")

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

# Configurazione Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- LOGICA DI SESSIONE E RECUPERO AUTOMATICO ---
if 'id_user_loggato' not in st.session_state:
    st.session_state.id_user_loggato = None

if st.session_state.id_user_loggato is None:
    time.sleep(0.2) # Delay ridotto per velocità
    saved_token = cookie_manager.get(cookie="supabase_refresh_token")
    
    if saved_token:
        try:
            res_session = supabase.auth.refresh_session(saved_token)
            if res_session and res_session.user:
                u_id = res_session.user.id
                u_info = supabase.table("dim_user").select("nickname, is_admin").eq("id_user", u_id).single().execute()
                
                st.session_state.id_user_loggato = u_id
                st.session_state.nome_user_loggato = u_info.data['nickname']
                st.session_state.is_admin = u_info.data.get('is_admin', False)
                
                cookie_manager.set("supabase_refresh_token", res_session.session.refresh_token, 
                                 expires_at=datetime.now() + timedelta(days=30))
                st.rerun()
        except:
            pass

# --- FORM DI LOGIN / REGISTRAZIONE ---
if st.session_state.id_user_loggato is None:
    st.markdown("""<style>[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl'] { display: none !important; }</style>""", unsafe_allow_html=True)
    
    _, col_login, _ = st.columns([1, 1.2, 1])
    with col_login:
        st.title("Virtua Cycling")
        t1, t2 = st.tabs(["🔐 Accedi", "✨ Registrati"])
        
        with t1:
            with st.form("login_form"):
                e_in = st.text_input("Email").strip()
                p_in = st.text_input("Password", type="password")
                submit = st.form_submit_button("ACCEDI 🚀", use_container_width=True)
                
                if submit:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": e_in, "password": p_in})
                        if res.user:
                            cookie_manager.set("supabase_refresh_token", res.session.refresh_token, 
                                             expires_at=datetime.now() + timedelta(days=30))
                            
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
                        st.success("Registrazione effettuata!")
                    except Exception as e: 
                        st.error(f"Errore: {e}")
    st.stop()

# --- DASHBOARD UTENTE ---
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

    # --- 1. SEZIONE PICK DA FARE ---
    st.markdown('<div class="section-title">✍️ Pick da fare</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if p_d:
            for p in p_d:
                nome_mostrato = p['race_name'] if p.get('id_type_race') == 3 else f"{p['race_name']} (T{p['stage']})"
                countdown_html = ""
                
                # --- FIX ERRORE FLOAT / ISOFORMAT ---
                try:
                    raw_date = p.get('stage_date')
                    raw_time = p.get('stage_time')
                    
                    if raw_date and raw_time:
                        d_val = datetime.fromisoformat(raw_date) if isinstance(raw_date, str) else raw_date
                        t_val = datetime.strptime(raw_time, "%H:%M:%S").time() if isinstance(raw_time, str) else raw_time
                        
                        deadline = datetime.combine(d_val, t_val)
                        diff = deadline - datetime.now()
                        
                        if diff.total_seconds() > 0:
                            g, o, m = diff.days, diff.seconds // 3600, (diff.seconds // 60) % 60
                            color_num = "#ff4b4b" if g == 0 and o < 12 else "#b0b0b0"
                            countdown_html = f'''
                                <div style="display: flex; align-items: center; gap: 4px; font-family: monospace; font-weight: bold; margin-left: 12px; transform: scale(0.9);">
                                    <span style="color: {color_num}; border: 1px solid #333; padding: 2px 5px; border-radius: 4px;">
                                        {f"{g}d " if g > 0 else ""}{o:02d}h {m:02d}m
                                    </span>
                                </div>
                            '''
                except: 
                    countdown_html = "" 

                col_txt, col_btn = st.columns([0.8, 0.2])
                col_txt.markdown(f"<div style='display: flex; align-items: center; min-height: 45px;'><b>{nome_mostrato}</b>{countdown_html}</div>", unsafe_allow_html=True)
                if col_btn.button("Vai", key=f"p_{p['id_stage']}", use_container_width=True):
                    st.session_state.gara_selezionata_id = p['id_race']
                    st.session_state.tappa_selezionata_id = p['id_stage']
                    st.switch_page("pages/01_Inserimento.py")
                st.markdown("<hr>", unsafe_allow_html=True)
        else:
            st.success("Tutti i pick sono completi ✅")

    # --- 2. SEZIONE IN CORSO ---
    st.markdown('<div class="section-title">🏁 In corso</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if c_d:
            for c in c_d:
                nome_live = c['race_name'] if c.get('id_type_race') == 3 else f"{c['race_name']} (Tappa {c['stage']})"
                col_txt_c, col_btn_c = st.columns([0.8, 0.2])
                col_txt_c.markdown(f"<div style='display: flex; align-items: center; min-height: 45px;'>🚴‍♂️ <b>{nome_live}</b></div>", unsafe_allow_html=True)
                if col_btn_c.button("Vai", key=f"c_{c['id_stage']}", use_container_width=True):
                    st.session_state.gara_selezionata_id = c['id_race']
                    st.session_state.tappa_selezionata_id = c['id_stage']
                    st.switch_page("pages/02_Classifiche.py")
                st.markdown("<hr>", unsafe_allow_html=True)
        else:
            st.info("Nessuna gara live.")

    # --- 3. ULTIMI RISULTATI ---
    st.markdown('<div class="section-title">🏆 Ultimi risultati</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if l_d:
            for l in l_d:
                col_l_txt, col_l_btn = st.columns([0.8, 0.2])
                col_l_txt.markdown(f"<div style='display: flex; align-items: center; min-height: 45px;'>✅ <b>{l['race_name']}</b></div>", unsafe_allow_html=True)
                if col_l_btn.button("Vai", key=f"l_{l['id_stage']}", use_container_width=True):
                    st.session_state.gara_selezionata_id = l['id_race']
                    st.session_state.tappa_selezionata_id = l['id_stage']
                    st.switch_page("pages/02_Classifiche.py")
                st.markdown("<hr>", unsafe_allow_html=True)

    # --- 4. PROSSIME GARE ---
    st.markdown('<div class="section-title">📅 Prossime gare</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if u_d:
            for u in u_d:
                data_str = ""
                if u.get('stage_date'):
                    try:
                        dt = datetime.fromisoformat(str(u['stage_date']))
                        data_str = dt.strftime("%d/%m")
                    except: data_str = str(u['stage_date'])
                st.markdown(f"<div style='margin-bottom: 8px;'><span style='color: #ff4b4b; font-weight: bold;'>{data_str}</span> {u['race_name']}</div>", unsafe_allow_html=True)
except Exception as e:
    st.error(f"Errore dati: {e}")
