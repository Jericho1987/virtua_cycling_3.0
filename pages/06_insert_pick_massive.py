import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar
import pandas as pd

# 1. Configurazione della pagina (Uniforme a Pagina 5)
st.set_page_config(page_title="Admin Quick Panel", layout="wide", page_icon="🚲")

# --- PROTEZIONE E SIDEBAR (Standardizzato) ---
check_auth()      
render_sidebar()  

# 2. Inizializzazione Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- CSS SPECIFICO PER LA GRIGLIA (Senza rompere la Sidebar) ---
st.markdown("""
    <style>
    /* Applica il gap ridotto SOLO al corpo principale della pagina */
    [data-testid="stMainView"] [data-testid="stVerticalBlock"] { 
        gap: 0.2rem !important; 
    }
    
    .user-label { 
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis; 
        display: block; 
        font-size: 14px;
        font-weight: bold;
        padding-top: 5px;
    }

    /* Compattezza delle selectbox nella griglia */
    .stSelectbox div[data-baseweb="select"] { 
        min-height: 32px !important; 
        font-size: 13px !important; 
    }
    
    [data-testid="column"] { padding: 0px 3px !important; }

    /* Gestione Tooltip */
    .tooltip-container { position: relative; width: 100%; }
    .tooltip-overlay {
        position: absolute;
        top: 0; left: 0; width: 100%; height: 100%;
        z-index: 10;
        cursor: help;
    }
    .tooltip-overlay:active { pointer-events: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CARICAMENTO DATI ---
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

    # --- 4. SELEZIONE GARA/TAPPA ---
    c1, c2 = st.columns(2)
    with c1:
        g_opts = {f"{g['name']} ({g['d']})": g['id_race'] for g in all_gare}
        sel_race_id = g_opts[st.selectbox("Scegli Gara", list(g_opts.keys()))]
    with c2:
        t_f = [t for t in all_tappe if t['id_race'] == sel_race_id]
        sel_tappa = st.selectbox("Scegli Tappa", t_f, format_func=lambda x: f"Tappa {x['id_stage_number']}")
        id_stage = sel_tappa['id_stage']

    # --- 5. DATI GRIGLIA ---
    res_r = supabase.table("view_start_list_display").select("id_rider, rider_name, id_team").eq("id_race", sel_race_id).order("rider_name").execute()
    r_map = {r['id_rider']: {"n": r['rider_name'], "t": r['id_team']} for r in res_r.data}
    r_list = [{"id": None, "n": "-"}] + [{"id": rid, "n": d['n']} for rid, d in r_map.items()]

    res_p = supabase.table("fact_user_pick").select("id_user, id_rider, id_slot").eq("id_stage", id_stage).execute()
    existing = {}
    for p in res_p.data:
        existing.setdefault(p['id_user'], {})[p['id_slot']] = p['id_rider']

    st.divider()

    # --- 6. GRIGLIA DI INPUT ---
    with st.form("admin_input_form"):
        btn_col_sx, btn_col_dx = st.columns(2)
        refresh_btn = btn_col_sx.form_submit_button("🔄 1. REFRESH DATI", use_container_width=True)
        submit_btn = btn_col_dx.form_submit_button("💾 2. SALVA TUTTE LE MODIFICHE", type="primary", use_container_width=True)

        st.write("")
        new_payload = []
        
        # Header Colonne
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
                
                # Trova indice per la selectbox
                d_idx = 0
                if pre_id:
                    for idx, r in enumerate(r_list):
                        if r['id'] == pre_id:
                            d_idx = idx
                            break
                
                with row[slot]:
                    full_name_rider = r_map.get(pre_id, {}).get('n', '-') if pre_id else "-"
                    
                    st.markdown(f'<div class="tooltip-container"><div class="tooltip-overlay" title="{full_name_rider}"></div>', unsafe_allow_html=True)
                    
                    sel = st.selectbox(
                        f"u{u_id}s{slot}", 
                        options=r_list, 
                        format_func=lambda x: x['n'],
                        index=d_idx, 
                        key=f"k_{id_stage}_{u_id}_{slot}", 
                        label_visibility="collapsed"
                    )
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    if sel['id']:
                        new_payload.append({
                            "id_user": u_id, 
                            "id_race": sel_race_id, 
                            "id_stage": id_stage,
                            "id_rider": sel['id'], 
                            "id_team": r_map[sel['id']]['t'], 
                            "id_slot": slot
                        })

    # --- 7. LOGICA SALVATAGGIO ---
    if refresh_btn:
        st.cache_data.clear()
        st.rerun()

    if submit_btn:
        try:
            # Elimina i vecchi pick per questa tappa e inserisce i nuovi
            supabase.table("fact_user_pick").delete().eq("id_stage", id_stage).execute()
            if new_payload:
                supabase.table("fact_user_pick").insert(new_payload).execute()
            st.success(f"✅ Modifiche salvate con successo per {len(new_payload)} pick!")
            st.balloons()
        except Exception as e:
            st.error(f"Errore durante il salvataggio: {e}")

except Exception as e:
    st.error(f"Errore generale: {e}")
