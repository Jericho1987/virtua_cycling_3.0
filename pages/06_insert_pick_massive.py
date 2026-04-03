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

# --- CSS (Invariato) ---
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

    # --- DATI PER MAPPING (Necessari anche per CSV) ---
    res_r = supabase.table("view_start_list_display").select("id_rider, rider_name, id_team").eq("id_race", sel_race_id).order("rider_name").execute()
    r_map = {r['id_rider']: {"n": r['rider_name'], "t": r['id_team']} for r in res_r.data}
    # Mapping inverso per il CSV (Nome Corridore -> ID)
    r_name_to_id = {r['rider_name'].lower().strip(): r['id_rider'] for r in res_r.data}
    u_name_to_id = {u['display_name'].lower().strip(): u['id_user'] for u in all_users}

    # --- NUOVA SEZIONE: CARICAMENTO CSV ---
    with st.expander("📂 Caricamento Massivo tramite CSV"):
        st.info("Il CSV deve avere le colonne: display_name, rider_1, rider_2, rider_3, rider_4, rider_5")
        uploaded_file = st.file_uploader("Scegli file CSV", type="csv")
        
        if uploaded_file:
            df_csv = pd.read_csv(uploaded_file)
            if st.button("PROCESSA E SALVA CSV 🚀"):
                csv_payload = []
                errors = []
                
                for _, row in df_csv.iterrows():
                    u_name = str(row['display_name']).lower().strip()
                    if u_name not in u_name_to_id:
                        errors.append(f"Utente non trovato: {row['display_name']}")
                        continue
                    
                    uid = u_name_to_id[u_name]
                    for slot in range(1, 6):
                        rider_col = f'rider_{slot}'
                        r_name = str(row[rider_col]).lower().strip()
                        
                        if r_name and r_name != "nan" and r_name != "-":
                            if r_name in r_name_to_id:
                                rid = r_name_to_id[r_name]
                                csv_payload.append({
                                    "id_user": uid, "id_race": sel_race_id, "id_stage": id_stage,
                                    "id_rider": rid, "id_team": r_map[rid]['t'], "id_slot": slot
                                })
                            else:
                                errors.append(f"Corridore non in Startlist: {row[rider_col]} (Utente: {row['display_name']})")

                if errors:
                    for err in errors[:10]: st.warning(err)
                    if len(errors) > 10: st.write("...")

                if csv_payload:
                    try:
                        supabase.table("fact_user_pick").delete().eq("id_stage", id_stage).execute()
                        supabase.table("fact_user_pick").insert(csv_payload).execute()
                        st.success(f"Caricati con successo {len(csv_payload)} pick!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore database: {e}")

    # --- 5. DATI GRIGLIA (Invariato) ---
    r_list = [{"id": None, "n": "-"}] + [{"id": rid, "n": d['n']} for rid, d in r_map.items()]
    res_p = supabase.table("fact_user_pick").select("id_user, id_rider, id_slot").eq("id_stage", id_stage).execute()
    existing = {}
    for p in res_p.data:
        existing.setdefault(p['id_user'], {})[p['id_slot']] = p['id_rider']

    st.divider()

    # --- 6. GRIGLIA DI INPUT (Invariato) ---
    with st.form("admin_input_form"):
        btn_col_sx, btn_col_dx = st.columns(2)
        refresh_btn = btn_col_sx.form_submit_button("🔄 1. REFRESH DATI", use_container_width=True)
        submit_btn = btn_col_dx.form_submit_button("💾 2. SALVA TUTTE LE MODIFICHE", type="primary", use_container_width=True)

        new_payload = []
        h = st.columns([1.5, 2, 2, 2, 2, 2])
        h[0].write("**Utente**")
        for i in range(1, 6): h[i].caption(f"Slot {i}")

        for user in all_users:
            u_id, u_name = user['id_user'], user['display_name']
            short_name = (u_name[:14] + '..') if len(u_name) > 16 else u_name
            row = st.columns([1.5, 2, 2, 2, 2, 2])
            row[0].markdown(f"<span class='user-label' title='{u_name}'>{short_name}</span>", unsafe_allow_html=True)
            
            for slot in range(1, 6):
                pre_id = existing.get(u_id, {}).get(slot)
                d_idx = 0
                if pre_id:
                    for idx, r in enumerate(r_list):
                        if r['id'] == pre_id:
                            d_idx = idx
                            break
                with row[slot]:
                    sel = st.selectbox(f"u{u_id}s{slot}", options=r_list, format_func=lambda x: x['n'],
                                     index=d_idx, key=f"k_{id_stage}_{u_id}_{slot}", label_visibility="collapsed")
                    if sel['id']:
                        new_payload.append({
                            "id_user": u_id, "id_race": sel_race_id, "id_stage": id_stage,
                            "id_rider": sel['id'], "id_team": r_map[sel['id']]['t'], "id_slot": slot
                        })

    if refresh_btn:
        st.cache_data.clear()
        st.rerun()

    if submit_btn:
        try:
            supabase.table("fact_user_pick").delete().eq("id_stage", id_stage).execute()
            if new_payload:
                supabase.table("fact_user_pick").insert(new_payload).execute()
            st.success(f"✅ Modifiche salvate con successo!")
            st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")

except Exception as e:
    st.error(f"Errore generale: {e}")
