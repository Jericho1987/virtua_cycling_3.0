import streamlit as st
import pandas as pd
from supabase import create_client
from auth_utils import check_auth, render_sidebar

st.set_page_config(page_title="Simulazione Punti", layout="wide", page_icon="🏆")

# --- PROTEZIONE E SIDEBAR ---
check_auth()
render_sidebar()

if not st.session_state.get('id_user_loggato'):
    st.switch_page("Home.py")

# --- CONNESSIONE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("📊 Simulazione Classifica Live")

# --- LOGICA RECUPERO PARAMETRI DA HOME ---
# Usiamo .get per evitare errori se la chiave non esiste
default_race_id = st.session_state.get('gara_selezionata_id')
default_stage_id = st.session_state.get('tappa_selezionata_id')

# --- FILTRI ---
col_f1, col_f2 = st.columns(2)

with col_f1:
    gare = supabase.table("dim_race").select("id_race, name").execute().data
    
    # TROVA INDICE GARA (Conversione str() per sicurezza)
    idx_g = 0
    if default_race_id is not None:
        for i, g in enumerate(gare):
            if str(g['id_race']) == str(default_race_id):
                idx_g = i
                break
    
    sel_gara = st.selectbox("Seleziona Gara", gare, index=idx_g, format_func=lambda x: x['name'])

with col_f2:
    tappe = supabase.table("dim_race_stage").select("id_stage, id_stage_number").eq("id_race", sel_gara['id_race']).order("id_stage_number").execute().data
    
    # TROVA INDICE TAPPA (Conversione str() per sicurezza)
    idx_t = 0
    if default_stage_id is not None:
        for i, t in enumerate(tappe):
            if str(t['id_stage']) == str(default_stage_id):
                idx_t = i
                break
                
    sel_tappa = st.selectbox("Seleziona Tappa", tappe, index=idx_t, format_func=lambda x: f"Tappa {x['id_stage_number']}")

# --- PULIZIA SESSION STATE ---
# Importante: cancelliamo solo DOPO che i selectbox sono stati renderizzati
if 'gara_selezionata_id' in st.session_state:
    del st.session_state.gara_selezionata_id
if 'tappa_selezionata_id' in st.session_state:
    del st.session_state.tappa_selezionata_id

st.markdown("---")

# --- RECUPERO DATI ---
res = supabase.table("view_simulazione_punti")\
    .select("posizione_classifica, display_name, punti_totali")\
    .eq("id_stage", sel_tappa['id_stage'])\
    .order("posizione_classifica")\
    .execute()

if res.data:
    df = pd.DataFrame(res.data)
    
    # --- 1. IL PODIO ---
    st.subheader("🏆 Il Podio")
    podio_cols = st.columns(3)
    
    for i in range(3):
        with podio_cols[i]:
            if len(df) > i:
                user = df.iloc[i]
                medaglie = ["🥇 1° Posto", "🥈 2° Posto", "🥉 3° Posto"]
                st.metric(label=medaglie[i], value=f"{user['punti_totali']} pt", delta=user['display_name'], delta_color="off")
            else:
                st.empty()

    st.write("") 

    # --- 2. IL TABELLONE COMPLETO ---
    st.subheader(f"Classifica Completa: {sel_gara['name']} - T{sel_tappa['id_stage_number']}")
    
    def make_pretty_pos(pos):
        if pos == 1: return "🥇"
        if pos == 2: return "🥈"
        if pos == 3: return "🥉"
        return str(pos)

    df['Rank'] = df['posizione_classifica'].apply(make_pretty_pos)
    
    df_view = df[['Rank', 'display_name', 'punti_totali']].copy()
    df_view.columns = ["Pos.", "Giocatore", "Punteggio"]

    st.dataframe(
        df_view, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Pos.": st.column_config.TextColumn("Pos.", width="small"),
            "Giocatore": st.column_config.TextColumn("Utente"),
            "Punteggio": st.column_config.NumberColumn("Totale Punti", format="%d ⚡")
        }
    )
else:
    st.info("Nessun dato disponibile per questa selezione.")
