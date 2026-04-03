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

# --- FILTRI ---
col_f1, col_f2 = st.columns(2)
with col_f1:
    gare = supabase.table("dim_race").select("id_race, name").execute().data
    sel_gara = st.selectbox("Seleziona Gara", gare, format_func=lambda x: x['name'])
with col_f2:
    tappe = supabase.table("dim_race_stage").select("id_stage, id_stage_number").eq("id_race", sel_gara['id_race']).order("id_stage_number").execute().data
    sel_tappa = st.selectbox("Seleziona Tappa", tappe, format_func=lambda x: f"Tappa {x['id_stage_number']}")

st.markdown("---")

# --- RECUPERO DATI ---
res = supabase.table("view_simulazione_punti")\
    .select("posizione_classifica, display_name, punti_totali")\
    .eq("id_stage", sel_tappa['id_stage'])\
    .order("posizione_classifica")\
    .execute()

if res.data:
    df = pd.DataFrame(res.data)
    
    # --- 1. IL PODIO (SPOSTATO SOPRA) ---
    st.subheader("🏆 Il Podio")
    podio_cols = st.columns(3)
    
    # Definiamo i primi 3 per i widget
    for i in range(3):
        with podio_cols[i]:
            if len(df) > i:
                user = df.iloc[i]
                medaglie = ["🥇 1° Posto", "🥈 2° Posto", "🥉 3° Posto"]
                st.metric(label=medaglie[i], value=f"{user['punti_totali']} pt", delta=user['display_name'], delta_color="off")
            else:
                st.empty()

    st.write("") # Spaziatore

    # --- 2. IL TABELLONE COMPLETO ---
    st.subheader(f"Classifica Completa: {sel_gara['name']} - T{sel_tappa['id_stage_number']}")
    
    # Trasformazione icone per la tabella
    def make_pretty_pos(pos):
        if pos == 1: return "🥇"
        if pos == 2: return "🥈"
        if pos == 3: return "🥉"
        return str(pos)

    df['Rank'] = df['posizione_classifica'].apply(make_pretty_pos)
    
    # Prepariamo il DF per la visualizzazione
    df_view = df[['Rank', 'display_name', 'punti_totali']].copy()
    df_view.columns = ["Pos.", "Giocatore", "Punteggio"]

    # Visualizzazione con stile
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
