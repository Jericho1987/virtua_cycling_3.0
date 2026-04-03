import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar

# 1. Configurazione pagina
st.set_page_config(page_title="Inserimento Formazione", layout="wide", page_icon="📝")

# 2. Protezione e Sidebar
check_auth()
render_sidebar()

# CSS CUSTOM PER MIGLIORARE LA LEGGIBILITÀ DEI SELECTBOX
st.markdown("""
    <style>
        /* Riduce il font dei testi dentro le selectbox */
        div[data-baseweb="select"] > div {
            font-size: 0.82rem !important;
            min-height: 38px !important;
        }
        
        /* Riduce il font delle etichette (Slot 1, Slot 2...) */
        div[data-testid="stSelectbox"] label p {
            font-size: 0.8rem !important;
            color: #ff4b4b !important;
            font-weight: 600;
        }

        /* Migliora il menu a tendina che si apre (dropdown) */
        div[data-baseweb="popover"] li {
            font-size: 0.8rem !important;
            padding: 4px 8px !important;
            line-height: 1.1 !important;
        }

        /* Rende l'informativa sui pick più compatta */
        .stAlert {
            padding: 0.5rem 1rem !important;
            border-radius: 10px !important;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Connessione dati
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# 4. Recupero variabili di sessione
user_id = st.session_state.id_user_loggato
t_race = st.session_state.get('gara_selezionata_id')
t_stage = st.session_state.get('tappa_selezionata_id')

# --- 1. CARICAMENTO DATI DALLA VIEW ---
query = supabase.table("view_stage_to_pick").select("*").execute()
all_data = query.data

if not all_data:
    st.warning("Non ci sono gare aperte al momento.")
    st.stop()

# --- 2. LOGICA DI SELEZIONE GARA ---
gare_opzioni = []
seen_races = set()
for d in all_data:
    if d['id_race'] not in seen_races:
        gare_opzioni.append({'id': d['id_race'], 'name': d['race_name']})
        seen_races.add(d['id_race'])

idx_g = next((i for i, g in enumerate(gare_opzioni) if g['id'] == t_race), 0)
sel_gara = st.selectbox("Seleziona Gara", gare_opzioni, format_func=lambda x: x['name'], index=idx_g, key="sb_gara_main")

# --- 3. LOGICA DI SELEZIONE TAPPA ---
tappe_gara = [t for t in all_data if t['id_race'] == sel_gara['id']]
idx_t = next((i for i, t in enumerate(tappe_gara) if t['id_stage'] == t_stage), 0)

sel_tappa = st.selectbox(
    "Seleziona Tappa", 
    tappe_gara, 
    format_func=lambda x: f"Tappa {x['stage']}", 
    index=idx_t if idx_t < len(tappe_gara) else 0,
    key=f"sb_tappa_{sel_gara['id']}" 
)

# --- 4. RECUPERO IL LIMITE ---
limit = int(sel_tappa['pick_limit']) 

st.divider()
st.info(f"📍 Regolamento: **{limit} pick richiesti** per questa tappa.")

# --- 5. CARICAMENTO CORRIDORI CON FORMATTAZIONE OTTIMIZZATA ---
# Includiamo 'team_code' per brevità (es: [ADC] invece di Alpecin-Deceuninck)
res_riders = supabase.table("view_start_list_display")\
    .select("id_rider, rider_name, id_team, team_code")\
    .eq("id_race", sel_gara['id'])\
    .order("rider_name").execute()

# Formattiamo la lista per la visualizzazione
riders_list = [{"id": None, "display": "-"}]
for r in res_riders.data:
    t_code = r.get('team_code') if r.get('team_code') else "???"
    riders_list.append({
        "id": r['id_rider'], 
        "id_team": r['id_team'],
        "display": f"[{t_code}] {r['rider_name']}"
    })

# --- 6. GENERAZIONE SLOT DINAMICI (Layout a 3 colonne) ---
picks = []
# Usiamo 3 colonne per dare più larghezza ai nomi ed evitare i puntini di sospensione
n_cols = 3 if limit >= 3 else limit
cols = st.columns(n_cols)

for i in range(limit):
    with cols[i % n_cols]:
        p = st.selectbox(
            f"Slot {i+1}", 
            options=riders_list, 
            format_func=lambda x: x['display'], 
            key=f"pick_{sel_tappa['id_stage']}_{i}"
        )
        picks.append(p)

# --- 7. BOTTONE SALVATAGGIO ---
st.write("") # Spazio
if st.button("🚀 CONFERMA FORMAZIONE", use_container_width=True, type="primary"):
    selected_ids = [p['id'] for p in picks if p['id'] is not None]
    
    if len(selected_ids) < limit:
        st.error(f"Devi completare tutti i {limit} slot disponibili.")
    elif len(set(selected_ids)) < len(selected_ids):
        st.error("Attenzione: hai selezionato lo stesso corridore più di una volta!")
    else:
        try:
            with st.spinner("Salvataggio in corso..."):
                # 1. Eliminiamo i pick precedenti per questa tappa
                supabase.table("fact_user_pick")\
                    .delete()\
                    .eq("id_user", user_id)\
                    .eq("id_stage", sel_tappa['id_stage'])\
                    .execute()
                
                # 2. Prepariamo i nuovi dati
                to_insert = []
                for i, p in enumerate(picks):
                    to_insert.append({
                        "id_user": user_id,
                        "id_race": sel_gara['id'],
                        "id_stage": sel_tappa['id_stage'],
                        "id_rider": p['id'],
                        "id_team": p['id_team'],
                        "id_slot": i + 1
                    })
                
                # 3. Inserimento massivo
                supabase.table("fact_user_pick").insert(to_insert).execute()
                
            st.success("Formazione salvata con successo! Buona gara 🚴‍♂️")
            st.balloons()
            
        except Exception as e:
            st.error(f"Errore durante il salvataggio: {e}")
