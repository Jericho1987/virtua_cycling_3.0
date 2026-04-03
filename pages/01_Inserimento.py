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
        div[data-baseweb="select"] > div {
            font-size: 0.9rem !important;
            min-height: 42px !important;
        }
        div[data-baseweb="popover"] li {
            font-size: 0.85rem !important;
        }
        div[data-testid="stSelectbox"] {
            margin-bottom: 10px !important;
        }
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

# --- 1. CARICAMENTO DATI PALINSESTO ---
query = supabase.table("view_stage_to_pick").select("*").execute()
all_data = query.data

# Carichiamo anche le tappe "correnti" (chiuse ai pick)
query_current = supabase.table("view_stage_current").select("id_stage").execute()
current_stages_ids = [item['id_stage'] for item in query_current.data]

if not all_data and not query_current.data:
    st.warning("Non ci sono gare aperte o in corso al momento.")
    st.stop()

# Uniamo i dati se necessario per permettere la selezione di tappe in corso
# Se view_stage_to_pick non include le correnti, dobbiamo recuperarle per mostrarle nel menu
all_combined = all_data + [d for d in query_current.data if d['id_stage'] not in [x['id_stage'] for x in all_data]]

# --- 2. LOGICA DI SELEZIONE GARA ---
gare_opzioni = []
seen_races = set()
for d in all_data:
    if d['id_race'] not in seen_races:
        gare_opzioni.append({
            'id': d['id_race'],
            'name': d['race_name'],
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
        format_func=lambda x: f"Tappa {x['stage']}",
        index=idx_t if idx_t < len(tappe_gara) else 0,
        key=f"sb_tappa_{sel_gara['id']}"
    )

# --- CONTROLLO STATO TAPPA (MODIFICA RICHIESTA) ---
is_locked = sel_tappa['id_stage'] in current_stages_ids

if is_locked:
    st.subheader(f"📊 Scelte della Community - Tappa {sel_tappa['stage']}")
    st.info("La gara è in corso: non è più possibile modificare la formazione.")
    
    # Recupero di TUTTE le pick per questa tappa (Ipotizzando una view o join per i nomi)
    # Se non hai una view pronta, questa query recupera i dati grezzi da fact_user_pick
    res_global = supabase.rpc("get_global_picks", {"p_stage_id": sel_tappa['id_stage']}).execute() 
    # NOTA: Se non hai una rpc, usa una select semplice sulla tabella fact:
    # res_global = supabase.table("fact_user_pick").select("id_user, id_rider, id_slot").eq("id_stage", sel_tappa['id_stage']).execute()
    
    if res_global.data:
        df = pd.DataFrame(res_global.data)
        st.dataframe(df, use_container_width=True)
    else:
        st.write("Nessuna formazione inserita per questa tappa.")
else:
    # --- 4. RECUPERO PICK ESISTENTI ---
    res_existing = supabase.table("fact_user_pick")\
        .select("id_slot, id_rider")\
        .eq("id_user", user_id)\
        .eq("id_stage", sel_tappa['id_stage']).execute()

    existing_picks = {p['id_slot']: p['id_rider'] for p in res_existing.data}

    # --- 5. CARICAMENTO CORRIDORI ---
    res_riders = supabase.table("view_start_list_display")\
        .select("id_rider, rider_name, id_team")\
        .eq("id_race", sel_gara['id'])\
        .order("rider_name").execute()

    riders_list = [{"id": None, "nome": "-", "id_team": None}] + \
                  [{"id": r['id_rider'], "nome": r['rider_name'], "id_team": r['id_team']} for r in res_riders.data]

    # --- 6. GENERAZIONE SLOT DINAMICI ---
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
