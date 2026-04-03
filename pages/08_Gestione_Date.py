import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar
import pandas as pd
from datetime import datetime

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
@st.cache_data(ttl=10) # Cache breve per permettere aggiornamenti veloci
def get_admin_data():
    # Recuperiamo le tappe
    res_stages = supabase.table("dim_race_stage").select("*").order("id_race, id_stage_number").execute()
    # Recuperiamo i tipi tappa per la selectbox
    res_types = supabase.table("dim_stage_type").select("id_stage_type, description").execute()
    # Recuperiamo i nomi delle gare per il display
    res_races = supabase.table("dim_race").select("id_race, name").execute()
    
    return pd.DataFrame(res_stages.data), pd.DataFrame(res_types.data), pd.DataFrame(res_races.data)

try:
    df_stages, df_types, df_races = get_admin_data()

    if df_stages.empty:
        st.info("Nessuna tappa trovata.")
        st.stop()

    # Prepariamo il dataframe per la visualizzazione "Excel"
    # Uniamo i nomi delle gare
    df_display = df_stages.merge(df_races, on="id_race")
    
    # Creiamo una colonna leggibile per il tipo tappa attuale
    type_map = dict(zip(df_types['id_stage_type'], df_types['description']))
    df_display['Tipo Tappa'] = df_display['id_stage_type'].map(type_map)

    # --- 5. FILTRI ---
    races_list = sorted(df_races['name'].unique())
    sel_race = st.selectbox("Filtra per Gara", ["Tutte"] + races_list)
    
    if sel_race != "Tutte":
        df_display = df_display[df_display['name'] == sel_race]

    # Selezione delle colonne da mostrare nella griglia
    # Riordiniamo e rinominiamo per l'utente
    df_grid = df_display[[
        'id_stage', 'name', 'id_stage_number', 'stage_date', 'stage_time', 'Tipo Tappa'
    ]].copy()

    # --- 6. GRIGLIA EDITABILE (EXCEL STYLE) ---
    st.write("### Griglia Modificabile")
    st.caption("Modifica le celle e clicca su 'Salva Modifiche' in basso.")

    edited_df = st.data_editor(
        df_grid,
        column_config={
            "id_stage": None, # Nascondiamo l'ID tecnico
            "name": st.column_config.TextColumn("Gara", disabled=True),
            "id_stage_number": st.column_config.NumberColumn("Tappa #", disabled=True, format="%d"),
            "stage_date": st.column_config.DateColumn("Data", format="DD/MM/YYYY", required=True),
            "stage_time": st.column_config.TimeColumn("Orario Limite", format="HH:mm", required=True),
            "Tipo Tappa": st.column_config.SelectboxColumn(
                "Tipologia",
                options=list(type_map.values()),
                required=True
            )
        },
        hide_index=True,
        use_container_width=True,
        key="stage_editor"
    )

    # --- 7. LOGICA DI SALVATAGGIO ---
    st.divider()
    col_btn, _ = st.columns([1, 4])
    
    if col_btn.button("💾 Salva Tutte le Modifiche", type="primary", use_container_width=True):
        # Invertiamo la mappa dei tipi per ottenere l'ID dalla descrizione
        inv_type_map = {v: k for k, v in type_map.items()}
        
        success_count = 0
        with st.spinner("Aggiornamento database in corso..."):
            for index, row in edited_df.iterrows():
                # Prepariamo l'update
                update_payload = {
                    "stage_date": str(row['stage_date']),
                    "stage_time": str(row['stage_time']),
                    "id_stage_type": inv_type_map[row['Tipo Tappa']]
                }
                
                try:
                    supabase.table("dim_race_stage")\
                        .update(update_payload)\
                        .eq("id_stage", row['id_stage'])\
                        .execute()
                    success_count += 1
                except Exception as e:
                    st.error(f"Errore riga {row['id_stage']}: {e}")

        if success_count > 0:
            st.success(f"✅ Aggiornate correttamente {success_count} tappe!")
            st.cache_data.clear()
            st.rerun()

except Exception as e:
    st.error(f"Errore tecnico: {e}")
