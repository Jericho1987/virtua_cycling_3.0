import streamlit as st 
from supabase import create_client 
from auth_utils import check_auth, render_sidebar # Importi le tue funzioni 

# 1. Configurazione pagina 
st.set_page_config(page_title="Inserimento Formazione", layout="wide", page_icon="📝") 

# 2. Protezione e Sidebar 
check_auth()      
render_sidebar()  

# --- STILE E FONT ---
st.markdown("""
    <style>
        /* Font ottimizzato per la lettura su riga intera */
        div[data-baseweb="select"] > div {
            font-size: 0.9rem !important;
            min-height: 42px !important;
        }
        div[data-baseweb="popover"] li {
            font-size: 0.85rem !important;
        }
        /* Spaziatura tra gli slot verticali */
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

# --- 1. CARICAMENTO DATI FRESCHI DALLA VIEW --- 
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
st.info(f"Regolamento per questa tappa: **{limit} pick richiesti**") 

# --- 5. CARICAMENTO CORRIDORI --- 
res_riders = supabase.table("view_start_list_display")\
    .select("id_rider, rider_name, id_team")\
    .eq("id_race", sel_gara['id'])\
    .order("rider_name").execute() 

riders_list = [{"id": None, "nome": "-", "id_team": None}] + \
              [{"id": r['id_rider'], "nome": r['rider_name'], "id_team": r['id_team']} for r in res_riders.data] 

# --- 6. GENERAZIONE SLOT DINAMICI (VERTICALE) --- 
picks = [] 

# Rimosso st.columns: ora ogni selectbox viene creata una sotto l'altra
for i in range(limit): 
    p = st.selectbox( 
        f"Slot {i+1}",  
        options=riders_list,  
        format_func=lambda x: x['nome'],  
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
