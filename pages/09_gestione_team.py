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
st.markdown("Modifica i dettagli dei team. Ordinati per Codice UCI.")

# --- 4. CARICAMENTO DATI ---
@st.cache_data(ttl=10)
def get_team_data():
    # Ordiniamo direttamente dalla query per codice UCI
    res = supabase.table("dim_team").select("*").order("uci_code").execute()
    return pd.DataFrame(res.data)

try:
    df_teams = get_team_data()

    if df_teams.empty:
        st.info("Nessun team in database.")
        st.stop()

    # Prepariamo il DF (teniamo id_team solo per l'aggiornamento, ma lo nascondiamo)
    df_grid = df_teams[[
        'id_team', 'uci_code', 'name', 'short_txt'
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
            # Nascondiamo l'ID impostandolo a None
            "id_team": None, 
            "uci_code": st.column_config.TextColumn("Codice UCI", max_chars=3, required=True),
            "name": st.column_config.TextColumn("Nome Team", required=True),
            "short_txt": st.column_config.TextColumn("Abbreviazione"),
        },
        hide_index=True,
        use_container_width=True,
        key="team_editor"
    )

    # --- 7. LOGICA DI SALVATAGGIO ---
    if save_clicked:
        changes = st.session_state["team_editor"].get("edited_rows", {})

        if not changes:
            st.info("Nessuna modifica rilevata.")
        else:
            success_count = 0
            with st.spinner("Aggiornamento in corso..."):
                for row_idx_str, updated_values in changes.items():
                    row_idx = int(row_idx_str)
                    # L'ID rimane accessibile nel dataframe originale anche se nascosto nella griglia
                    real_id = df_grid.iloc[row_idx]['id_team']
                    
                    if updated_values:
                        try:
                            supabase.table("dim_team")\
                                .update(updated_values)\
                                .eq("id_team", real_id)\
                                .execute()
                            success_count += 1
                        except Exception as e:
                            st.error(f"Errore sull'aggiornamento: {e}")

            if success_count > 0:
                st.success(f"✅ Aggiornati {success_count} team!")
                st.cache_data.clear()
                st.rerun()

except Exception as e:
    st.error(f"Errore caricamento dati: {e}")
