import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar
import pandas as pd
from datetime import datetime, time

# 1. Configurazione pagina
st.set_page_config(page_title="Admin - Gestione Palinsesto", layout="wide", page_icon="📅")

# 2. Protezione e Sidebar
check_auth()
render_sidebar()

if not st.session_state.get('is_admin', False):
    st.error("Accesso riservato agli amministratori.")
    st.stop()

# 3. Connessione Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("📅 Gestione Palinsesto Gare")
st.markdown("Modifica date, orari e tipologie in formato griglia compatta.")

# --- 4. CARICAMENTO DATI ---
@st.cache_data(ttl=5) 
def get_admin_data():
    res_stages = supabase.table("dim_race_stage").select("*").order("id_race, id_stage_number").execute()
    res_types = supabase.table("dim_stage_type").select("id_stage_type, description").execute()
    res_races = supabase.table("dim_race").select("id_race, name").execute()
    
    return pd.DataFrame(res_stages.data), pd.DataFrame(res_types.data), pd.DataFrame(res_races.data)

try:
    df_stages, df_types, df_races = get_admin_data()

    if df_stages.empty:
        st.info("Nessuna tappa trovata.")
        st.stop()

    # Merge per avere i nomi delle gare
    df_display = df_stages.merge(df_races, on="id_race")
    
    # Mappa dei tipi tappa
    type_map = dict(zip(df_types['id_stage_type'], df_types['description']))
    df_display['Tipo Tappa'] = df_display['id_stage_type'].map(type_map)

    # --- TRASFORMAZIONE DATI PER COMPATIBILITÀ EDITING ---
    # Convertiamo la stringa "YYYY-MM-DD" in oggetto Date di Python
    df_display['stage_date'] = pd.to_datetime(df_display['stage_date']).dt.date
    
    # Convertiamo la stringa "HH:MM:SS" in oggetto Time di Python
    df_display['stage_time'] = pd.to_datetime(df_display['stage_time'], format='%H:%M:%S').dt.time

    # --- 5. FILTRI ---
    races_list = sorted(df_races['name'].unique())
    sel_race = st.selectbox("Filtra per Gara", ["Tutte"] + races_list)
    
    if sel_race != "Tutte":
        df_display = df_display[df_display['name'] == sel_race]

    df_grid = df_display[[
        'id_stage', 'name', 'id_stage_number', 'stage_date', 'stage_time', 'Tipo Tappa'
    ]].copy()

    # --- 6. GRIGLIA EDITABILE ---
    st.write("### Griglia Modificabile")
    
    edited_df = st.data_editor(
        df_grid,
        column_config={
            "id_stage": None, 
            "name": st.column_config.TextColumn("Gara", disabled=True),
            "id_stage_number": st.column_config.NumberColumn("Tappa #", disabled=True),
            "stage_date": st.column_config.DateColumn("Data", format="DD/MM/YYYY", required=True),
            "stage_time": st.column_config.TimeColumn("Orario", format="HH:mm", required=True),
            "Tipo Tappa": st.column_config.SelectboxColumn(
                "Tipologia",
                options=list(type_map.values()),
                required=True
            )
        },
        hide_index=True,
        use_container_width=True,
        key="stage_editor_v2"
    )

    # --- 7. LOGICA DI SALVATAGGIO ---
    st.divider()
    if st.button("💾 Salva Tutte le Modifiche", type="primary"):
        inv_type_map = {v: k for k, v in type_map.items()}
        
        success_count = 0
        with st.spinner("Salvataggio..."):
            for index, row in edited_df.iterrows():
                update_payload = {
                    "stage_date": row['stage_date'].isoformat(), # Torna stringa per il DB
                    "stage_time": row['stage_time'].strftime('%H:%M:%S'), # Torna stringa per il DB
                    "id_stage_type": inv_type_map[row['Tipo Tappa']]
                }
                
                supabase.table("dim_race_stage")\
                    .update(update_payload)\
                    .eq("id_stage", row['id_stage'])\
                    .execute()
                success_count += 1

        if success_count > 0:
            st.success(f"✅ Aggiornate {success_count} tappe!")
            st.cache_data.clear()
            st.rerun()

except Exception as e:
    st.error(f"Errore tecnico: {e}")
