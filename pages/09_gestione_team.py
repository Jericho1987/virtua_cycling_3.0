import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar
import pandas as pd

# 1. Configurazione pagina
st.set_page_config(page_title="Admin - Gestione Team", layout="wide", page_icon="🚴‍♂️")

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

st.title("🚴‍♂️ Gestione Team (UCI)")
st.markdown("Modifica i dettagli dei team ufficiali. Gli aggiornamenti verranno salvati solo per le righe modificate.")

# --- 4. CARICAMENTO DATI ---
@st.cache_data(ttl=10)
def get_team_data():
    res = supabase.table("dim_team").select("*").order("name").execute()
    return pd.DataFrame(res.data)

try:
    df_teams = get_team_data()

    if df_teams.empty:
        st.info("Nessun team in database.")
        st.stop()

    # Prepariamo il DF per la griglia (riordiniamo le colonne per chiarezza)
    df_grid = df_teams[[
        'id_team', 'uci_code', 'name', 'short_txt', 'updated_at'
    ]].copy()

    # --- 5. INTESTAZIONE E BOTTONE ---
    col_titolo, col_bottone = st.columns([0.7, 0.3], vertical_alignment="bottom")
    
    with col_titolo:
        st.write("### Elenco Team")
    
    with col_bottone:
        save_clicked = st.button("💾 Salva Modifiche Team", type="primary", use_container_width=True)

    # --- 6. GRIGLIA EDITABILE ---
    edited_df = st.data_editor(
        df_grid,
        column_config={
            "id_team": st.column_config.NumberColumn("ID", disabled=True),
            "uci_code": st.column_config.TextColumn("Codice UCI (3 lettere)", max_chars=3, required=True),
            "name": st.column_config.TextColumn("Nome Team Full", required=True),
            "short_txt": st.column_config.TextColumn("Nome Breve / Abbr."),
            "updated_at": st.column_config.DatetimeColumn("Ultimo Update", disabled=True, format="DD/MM/YYYY HH:mm"),
        },
        hide_index=True,
        use_container_width=True,
        key="team_editor"
    )

    # --- 7. LOGICA DI SALVATAGGIO ---
    if save_clicked:
        # Recupera solo i cambiamenti dal session_state del data_editor
        changes = st.session_state["team_editor"].get("edited_rows", {})

        if not changes:
            st.info("Nessuna modifica rilevata.")
        else:
            success_count = 0
            with st.spinner("Salvataggio team in corso..."):
                for row_idx_str, updated_values in changes.items():
                    row_idx = int(row_idx_str)
                    # Recuperiamo l'ID reale usando l'indice della riga
                    real_id = df_grid.iloc[row_idx]['id_team']
                    
                    # Eseguiamo l'update su Supabase
                    if updated_values: # Se il dizionario non è vuoto
                        try:
                            supabase.table("dim_team")\
                                .update(updated_values)\
                                .eq("id_team", real_id)\
                                .execute()
                            success_count += 1
                        except Exception as e:
                            st.error(f"Errore sull'ID {real_id}: {e}")

            if success_count > 0:
                st.success(f"✅ Aggiornati {success_count} team con successo!")
                st.cache_data.clear() # Svuota la cache per ricaricare i dati freschi
                st.rerun()

except Exception as e:
    st.error(f"Errore caricamento dati: {e}")
