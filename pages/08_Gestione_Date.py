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
st.markdown("Modifica date, orari e tipologie. Verranno salvate solo le celle modificate.")

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

    # Merge e Mappatura
    df_display = df_stages.merge(df_races, on="id_race")
    type_map = dict(zip(df_types['id_stage_type'], df_types['description']))
    df_display['Tipo Tappa'] = df_display['id_stage_type'].map(type_map)

    # Conversione formati per Streamlit
    df_display['stage_date'] = pd.to_datetime(df_display['stage_date']).dt.date
    df_display['stage_time'] = pd.to_datetime(df_display['stage_time'], format='%H:%M:%S').dt.time

    # --- 5. FILTRI ---
    races_list = sorted(df_races['name'].unique())
    sel_race = st.selectbox("Filtra per Gara", ["Tutte"] + races_list)
    
    if sel_race != "Tutte":
        df_display = df_display[df_display['name'] == sel_race]

    # Prepariamo il DF per la griglia
    df_grid = df_display[[
        'id_stage', 'name', 'id_stage_number', 'stage_date', 'stage_time', 'Tipo Tappa'
    ]].copy().reset_index(drop=True)

    # --- 6. GRIGLIA EDITABILE ---
    st.write("### Griglia Modificabile")
    
    # Usiamo un key specifica per accedere ai cambiamenti tramite session_state
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
        key="stage_editor"
    )

    # --- 7. LOGICA DI SALVATAGGIO OTTIMIZZATA ---
    st.divider()
    
    if st.button("💾 Salva solo modifiche", type="primary"):
        # Recuperiamo solo i dizionari delle righe toccate
        # Formato: { "indice_riga": { "colonna_modificata": "nuovo_valore" } }
        changes = st.session_state["stage_editor"].get("edited_rows", {})

        if not changes:
            st.info("Nessuna modifica rilevata.")
        else:
            inv_type_map = {v: k for k, v in type_map.items()}
            success_count = 0
            
            with st.spinner(f"Salvataggio di {len(changes)} tappe..."):
                for row_idx_str, updated_values in changes.items():
                    row_idx = int(row_idx_str)
                    # Recuperiamo l'ID del record usando l'indice della riga originale
                    id_stage = df_grid.iloc[row_idx]['id_stage']
                    
                    # Costruiamo il payload solo con quello che è cambiato
                    update_payload = {}
                    if 'stage_date' in updated_values:
                        update_payload["stage_date"] = updated_values['stage_date']
                    if 'stage_time' in updated_values:
                        # Assicuriamoci che sia stringa HH:MM:SS
                        val_time = updated_values['stage_time']
                        update_payload["stage_time"] = val_time.strftime('%H:%M:%S') if hasattr(val_time, 'strftime') else val_time
                    if 'Tipo Tappa' in updated_values:
                        update_payload["id_stage_type"] = inv_type_map[updated_values['Tipo Tappa']]

                    # Eseguiamo l'update solo se ci sono dati nel payload
                    if update_payload:
                        try:
                            supabase.table("dim_race_stage")\
                                .update(update_payload)\
                                .eq("id_stage", id_stage)\
                                .execute()
                            success_count += 1
                        except Exception as e:
                            st.error(f"Errore durante l'aggiornamento della riga {row_idx}: {e}")

            if success_count > 0:
                st.success(f"✅ Aggiornate con successo {success_count} tappe!")
                st.cache_data.clear()
                st.rerun()

except Exception as e:
    st.error(f"Errore tecnico: {e}")
