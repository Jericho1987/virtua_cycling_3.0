import streamlit as st
import pandas as pd
from supabase import create_client
from auth_utils import check_auth, render_sidebar

st.set_page_config(page_title="Simulazione Punti", layout="wide", page_icon="📊")

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
st.markdown("---")

# --- FILTRI ---
col1, col2 = st.columns(2)
with col1:
    gare = supabase.table("dim_race").select("id_race, name").execute().data
    sel_gara = st.selectbox("Seleziona Gara", gare, format_func=lambda x: x['name'])
with col2:
    tappe = supabase.table("dim_race_stage").select("id_stage, id_stage_number").eq("id_race", sel_gara['id_race']).order("id_stage_number").execute().data
    sel_tappa = st.selectbox("Seleziona Tappa", tappe, format_func=lambda x: f"Tappa {x['id_stage_number']}")

# --- RECUPERO DATI DALLA VIEW ---
# Filtriamo per id_stage che arriva dal selectbox sopra
res = supabase.table("view_simulazione_punti")\
    .select("posizione_classifica, display_name, punti_totali")\
    .eq("id_stage", sel_tappa['id_stage'])\
    .order("posizione_classifica")\
    .execute()

if res.data:
    df = pd.DataFrame(res.data)

    # --- LOGICA PER LE COPPETTE ---
    # Funzione per aggiungere icone alle prime posizioni
    def add_trophy(pos):
        if pos == 1: return "🥇"
        if pos == 2: return "🥈"
        if pos == 3: return "🥉"
        return str(pos)

    df['Pos.'] = df['posizione_classifica'].apply(add_trophy)
    
    # Rinominiamo le colonne per renderle "carine"
    df_display = df[['Pos.', 'display_name', 'punti_totali']].copy()
    df_display.columns = ["Rank", "Giocatore", "Punti Totali"]

    # --- RENDERING TABELLA ---
    st.subheader(f"Classifica Simulazione: {sel_gara['name']} - T {sel_tappa['id_stage_number']}")
    
    # Usiamo un container per lo stile
    st.dataframe(
        df_display, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Rank": st.column_config.TextColumn("Pos.", width="small"),
            "Giocatore": st.column_config.TextColumn("Utente"),
            "Punti Totali": st.column_config.NumberColumn("Punteggio", format="%d pt")
        }
    )
    
    # Tip: Mostriamo il podio in alto con dei widget metrici se vuoi un tocco extra
    st.markdown("### 🏆 Il Podio")
    podio_cols = st.columns(3)
    
    for i, col in enumerate(podio_cols):
        if len(df) > i:
            nome = df.iloc[i]['display_name']
            punti = df.iloc[i]['punti_totali']
            icone = ["🥇 1°", "🥈 2°", "🥉 3°"]
            col.metric(label=icone[i], value=f"{punti} pt", delta=nome, delta_color="off")

else:
    st.info("Nessun dato di simulazione disponibile per questa tappa.")
