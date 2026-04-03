import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar
import pandas as pd

# 1. Configurazione della pagina
st.set_page_config(page_title="Admin Quick Panel", layout="wide", page_icon="🚲")

check_auth()      
render_sidebar()  

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- CSS ---
st.markdown("""
    <style>
    [data-testid="stMainView"] [data-testid="stVerticalBlock"] { gap: 0.2rem !important; }
    .user-label { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; font-size: 14px; font-weight: bold; padding-top: 5px; }
    .stSelectbox div[data-baseweb="select"] { min-height: 32px !important; font-size: 13px !important; }
    [data-testid="column"] { padding: 0px 3px !important; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=60)
def get_base_info():
    stages = supabase.table("dim_race_stage").select("id_race, stage_date").execute().data
    df_s = pd.DataFrame(stages)
    min_dates = df_s.groupby('id_race')['stage_date'].min().to_dict()
    gare_raw = supabase.table("dim_race").select("id_race, name").execute().data
    for g in gare_raw:
        g['d'] = min_dates.get(g['id_race'], '9999-12-31')
    gare_sorted = sorted(gare_raw, key=lambda x: x['d'])
    tappe = supabase.table("dim_race_stage").select("*").order("id_stage_number").execute().data
    utenti = supabase.table("dim_user").select("id_user, display_name").order("display_name").execute().data
    return gare_sorted, tappe, utenti

try:
    all_gare, all_tappe, all_users = get_base_info()
    st.title("⚡ Pannello Admin Ultra-Responsive")

    c1, c2 = st.columns(2)
    with c1:
        g_opts = {f"{g['name']} ({g['d']})": g['id_race'] for g in all_gare}
        sel_race_id = g_opts[st.selectbox("Scegli Gara", list(g_opts.keys()))]
    with c2:
        t_f = [t for t in all_tappe if t['id_race'] == sel_race_id]
        sel_tappa = st.selectbox("Scegli Tappa", t_f, format_func=lambda x: f"Tappa {x['id_stage_number']}")
        id_stage = sel_tappa['id_stage']

    # --- MAPPING INTELLIGENTE ---
    res_r = supabase.table("view_start_list_display").select("id_rider, rider_name, id_team").eq("id_race", sel_race_id).order("rider_name").execute()
    r_map = {r['id_rider']: {"n": r['rider_name'], "t": r['id_team']} for r in res_r.data}
    
    # Mapping flessibile: cerchiamo se il pezzetto di nome nel CSV è contenuto nel nome DB
    r_list_db = [{"id": r['id_rider'], "name": r['rider_name'].lower().strip()} for r in res_r.data]
    u_name_to_id = {u['display_name'].lower().strip(): u['id_user'] for u in all_users}

    with st.expander("📂 Caricamento Massivo tramite CSV"):
        uploaded_file = st.file_uploader("Scegli file CSV", type="csv")
        if uploaded_file:
            df_csv = pd.read_csv(uploaded_file)
            if st.button("PROCESSA E SALVA CSV 🚀"):
                csv_payload = []
                errors = []
                
                for _, row in df_csv.iterrows():
                    u_input = str(row['display_name']).lower().strip()
                    uid = u_name_to_id.get(u_input)
                    if not uid:
                        errors.append(f"Utente non trovato: {row['display_name']}")
                        continue
                    
                    for slot in range(1, 6):
                        col = f'rider_{slot}'
                        if col in df_csv.columns:
                            val_csv = str(row[col]).lower().strip()
                            if val_csv in ["nan", "-", "", "none"]: continue
                            
                            # Cerca il corridore (Fuzzy match: se il testo CSV è parte del nome DB)
                            match = next((r for r in r_list_db if val_csv in r['name'] or r['name'] in val_csv), None)
                            
                            if match:
                                rid = match['id']
                                csv_payload.append({
                                    "id_user": uid, "id_race": sel_race_id, "id_stage": id_stage,
                                    "id_rider": rid, "id_team": r_map[rid]['t'], "id_slot": slot
                                })
                            else:
                                errors.append(f"Non trovato: {row[col]} (Utente: {row['display_name']})")

                if csv_payload:
                    supabase.table("fact_user_pick").delete().eq("id_stage", id_stage).execute()
                    supabase.table("fact_user_pick").insert(csv_payload).execute()
                    st.success(f"✅ {len(csv_payload)} pick salvati correttamente!")
                
                if errors:
                    st.subheader("⚠️ Warning (Righe saltate):")
                    for e in errors: st.warning(e)
                
                st.info("Clicca 'Aggiorna Griglia' per vedere i dati sotto.")

        if st.button("🔄 Aggiorna Griglia"): st.rerun()

    # --- GRIGLIA MANUALE ---
    r_list_sel = [{"id": None, "n": "-"}] + [{"id": rid, "n": d['n']} for rid, d in r_map.items()]
    res_p = supabase.table("fact_user_pick").select("id_user, id_rider, id_slot").eq("id_stage", id_stage).execute()
    existing = {p['id_user']: {} for p in res_p.data}
    for p in res_p.data: existing[p['id_user']][p['id_slot']] = p['id_rider']

    st.divider()
    with st.form("admin_input_form"):
        c_btn = st.columns(2)
        if c_btn[0].form_submit_button("🔄 REFRESH", use_container_width=True): st.rerun()
        submit_btn = c_btn[1].form_submit_button("💾 SALVA MODIFICHE", type="primary", use_container_width=True)

        new_payload = []
        for user in all_users:
            u_id, u_name = user['id_user'], user['display_name']
            row = st.columns([1.5, 2, 2, 2, 2, 2])
            row[0].markdown(f"<span class='user-label'>{u_name[:14]}</span>", unsafe_allow_html=True)
            for slot in range(1, 6):
                pre_id = existing.get(u_id, {}).get(slot)
                d_idx = next((i for i, r in enumerate(r_list_sel) if r['id'] == pre_id), 0)
                with row[slot]:
                    sel = st.selectbox(f"u{u_id}s{slot}", options=r_list_sel, format_func=lambda x: x['n'], index=d_idx, key=f"k_{id_stage}_{u_id}_{slot}", label_visibility="collapsed")
                    if sel['id']:
                        new_payload.append({"id_user": u_id, "id_race": sel_race_id, "id_stage": id_stage, "id_rider": sel['id'], "id_team": r_map[sel['id']]['t'], "id_slot": slot})

    if submit_btn:
        supabase.table("fact_user_pick").delete().eq("id_stage", id_stage).execute()
        if new_payload: supabase.table("fact_user_pick").insert(new_payload).execute()
        st.rerun()

except Exception as e:
    st.error(f"Errore: {e}")
