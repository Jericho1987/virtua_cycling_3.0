import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar
import pandas as pd

# 1. Configurazione pagina
st.set_page_config(page_title="Inserimento Formazione", layout="wide", page_icon="📝")

# 2. Protezione e Sidebar
check_auth()
render_sidebar()

# --- STILE E FONT ---
st.markdown("""
    <style>
        div[data-baseweb="select"] > div { font-size: 0.9rem !important; min-height: 42px !important; }
        div[data-baseweb="popover"] li { font-size: 0.85rem !important; }
        div[data-testid="stSelectbox"] { margin-bottom: 10px !important; }
    </style>
""", unsafe_allow_html=True)

# 3. Connessione dati
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# 4. Contenuto della pagina
st.title("📝 Inserimento Formazione")

user_id = st.session_state.id_user_loggato
t_race = st.session_state.get('gara_selezionata_id')
t_stage = st.session_state.get('tappa_selezionata_id')

# --- 1. CARICAMENTO DATI PALINSESTO (UNIONE VIEW) ---
res_to_pick = supabase.table("view_stage_to_pick").select("*").execute()
data_to_pick = res_to_pick.data if res_to_pick.data else []

res_current = supabase.table("view_stage_current").select("*").execute()
data_current = res_current.data if res_current.data else []

all_data = data_to_pick + data_current
current_ids = [d['id_stage'] for d in data_current]

if not all_data:
    st.warning("Non ci sono gare disponibili al momento.")
    st.stop()

# --- 2. LOGICA DI SELEZIONE GARA ---
gare_opzioni = []
seen_races = set()
for d in all_data:
    if d['id_race'] not in seen_races:
        suffix = " 🟢 (In corso)" if d['id_stage'] in current_ids else ""
        gare_opzioni.append({
            'id': d['id_race'],
            'name': f"{d['race_name']}{suffix}",
            'type': d.get('id_type_race')
        })
        seen_races.add(d['id_race'])

idx_g = next((i for i, g in enumerate(gare_opzioni) if g['id'] == t_race), 0)
sel_gara = st.selectbox("Seleziona Gara", gare_opzioni, format_func=lambda x: x['name'], index=idx_g, key="sb_gara_main")

# --- 3. LOGICA DI SELEZIONE TAPPA ---
tappe_gara = [t for t in all_data if t['id_race'] == sel_gara['id']]

if sel_gara['type'] == 3:
    sel_tappa = tappe_gara[0]
else:
    idx_t = next((i for i, t in enumerate(tappe_gara) if t['id_stage'] == t_stage), 0)
    sel_tappa = st.selectbox(
        "Seleziona Tappa",
        tappe_gara,
        format_func=lambda x: f"Tappa {x['stage']}" + (" (LIVE)" if x['id_stage'] in current_ids else ""),
        index=idx_t if idx_t < len(tappe_gara) else 0,
        key=f"sb_tappa_{sel_gara['id']}"
    )

# --- 4. CONTROLLO SE LA TAPPA È IN CORSO (MODALITÀ VISUALIZZAZIONE) ---
if sel_tappa['id_stage'] in current_ids:
    st.info(f"🚀 Formazioni schierate per: **{sel_tappa['race_name']}**")
    
    # Query alla vista: view_user_pick_race con ORDINAMENTO
    res_global = supabase.table("view_user_pick_race")\
        .select("display_name, rider_name_short, id_slot")\
        .eq("id_stage", sel_tappa['id_stage'])\
        .order("display_name")\
        .execute()
    
    if res_global.data:
        df_raw = pd.DataFrame(res_global.data)
        
        # Pivot: Utenti su righe, Slot su colonne
        df_pivot = df_raw.pivot(index='display_name', columns='id_slot', values='rider_name_short')
        
        # Rinominiamo le colonne degli slot (1, 2, 3...)
        df_pivot.columns = [f"Slot {int(col)}" for col in df_pivot.columns]
        
        # Pulizia finale e reset index per mostrare il nome partecipante
        df_final = df_pivot.fillna("-").reset_index()
        df_final.rename(columns={'display_name': 'Partecipante'}, inplace=True)
        
        st.dataframe(df_final, use_container_width=True, hide_index=True)
    else:
        st.write("Nessuna formazione inviata per questa tappa.")
    
    st.stop() # Blocca l'esecuzione qui per le gare in corso

# --- 5. LOGICA INSERIMENTO (Gara aperta) ---
res_existing = supabase.table("fact_user_pick")\
    .select("id_slot, id_rider")\
    .eq("id_user", user_id)\
    .eq("id_stage", sel_tappa['id_stage']).execute()

existing_picks = {p['id_slot']: p['id_rider'] for p in res_existing.data}

res_riders = supabase.table("view_start_list_display")\
    .select("id_rider, rider_name, id_team")\
    .eq("id_race", sel_gara['id'])\
    .order("rider_name").execute()

riders_list = [{"id": None, "nome": "-", "id_team": None}] + \
              [{"id": r['id_rider'], "nome": r['rider_name'], "id_team": r['id_team']} for r in res_riders.data]

limit = int(sel_tappa['pick_limit'])
st.divider()
st.info(f"Regolamento per questa tappa: **{limit} pick richiesti**")

picks = []
for i in range(limit):
    slot_number = i + 1
    saved_rider_id = existing_picks.get(slot_number)
    default_idx = 0
    if saved_rider_id:
        for idx, rider in enumerate(riders_list):
            if rider['id'] == saved_rider_id:
                default_idx = idx
                break
    
    p = st.selectbox(
        f"Slot {slot_number}",
        options=riders_list,
        format_func=lambda x: x['nome'],
        index=default_idx,
        key=f"pick_{sel_tappa['id_stage']}_{i}"
    )
    picks.append(p)

# --- 7. BOTTONE SALVATAGGIO ---
st.markdown("<br>", unsafe_allow_html=True)
if st.button("🚀 CONFERMA FORMAZIONE", use_container_width=True, type="primary"):
    selected_ids = [p['id'] for p in picks if p['id'] is not None]
    if len(selected_ids) < limit:
        st.error(f"Devi completare tutti i {limit} slot.")
    elif len(set(selected_ids)) < len(selected_ids):
        st.error("Hai inserito dei corridori duplicati!")
    else:
        try:
            supabase.table("fact_user_pick").delete().eq("id_user", user_id).eq("id_stage", sel_tappa['id_stage']).execute()
            to_insert = [{
                "id_user": user_id,
                "id_race": sel_gara['id'],
                "id_stage": sel_tappa['id_stage'],
                "id_rider": p['id'],
                "id_team": p['id_team'],
                "id_slot": i + 1
            } for i, p in enumerate(picks)]
            supabase.table("fact_user_pick").insert(to_insert).execute()
            st.success("Salvataggio completato!")
            st.balloons()
        except Exception as e:
            st.error(f"Errore: {e}")
