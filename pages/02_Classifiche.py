import streamlit as st
import pandas as pd
from supabase import create_client
from auth_utils import check_auth, render_sidebar # <--- 1. AGGIUNGI QUESTA RIGA

st.set_page_config(page_title="Classifiche e Risultati", layout="wide", page_icon="🏆")

# --- PROTEZIONE E SIDEBAR ---
check_auth()      # <--- 2. AGGIUNGI QUESTA (Blocca i non loggati e mette il CSS)
render_sidebar()  # <--- 3. AGGIUNGI QUESTA (Disegna i link e l'area utente)

if not st.session_state.get('id_user_loggato'):
    st.switch_page("Home.py")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("🏆 Risultati e Classifiche")

# --- FILTRI ---
col1, col2 = st.columns(2)
with col1:
    gare = supabase.table("dim_race").select("id_race, name").execute().data
    sel_gara = st.selectbox("Seleziona Gara", gare, format_func=lambda x: x['name'])
with col2:
    tappe = supabase.table("dim_race_stage").select("id_stage, id_stage_number").eq("id_race", sel_gara['id_race']).order("id_stage_number").execute().data
    sel_tappa = st.selectbox("Seleziona Tappa", tappe, format_func=lambda x: f"Tappa {x['id_stage_number']}")

tabs = st.tabs(["📊 Classifica Tappa", "📈 Classifica Generale", "🔍 Picks Tutti"])

# --- TAB 1: CLASSIFICA TAPPA (Usa la nuova View) ---
with tabs[0]:
    st.subheader(f"Punteggi: {sel_gara['name']} - Tappa {sel_tappa['id_stage_number']}")
    res_tappa = supabase.table("view_results_ranking")\
        .select("user_name, total_punti_base, malus_vincitore, bonus_top_10, punteggio_totale, dettaglio_quintetto")\
        .eq("id_stage", sel_tappa['id_stage'])\
        .order("punteggio_totale", desc=True)\
        .execute()
    
    if res_tappa.data:
        df_tappa = pd.DataFrame(res_tappa.data)
        df_tappa.columns = ["Utente", "Punti Base", "Malus Vinc.", "Bonus Top10", "TOTALE", "Dettaglio (Pos. Arrivo)"]
        st.dataframe(df_tappa, use_container_width=True, hide_index=True)
    else:
        st.info("Risultati non ancora disponibili per questa tappa.")

# --- TAB 2: CLASSIFICA GENERALE GARA ---
with tabs[1]:
    st.subheader(f"Classifica Generale: {sel_gara['name']}")
    res_gen = supabase.table("view_results_ranking")\
        .select("user_name, punteggio_totale")\
        .eq("id_race", sel_gara['id_race'])\
        .execute()
    
    if res_gen.data:
        df_gen = pd.DataFrame(res_gen.data)
        classifica = df_gen.groupby("user_name")["punteggio_totale"].sum().reset_index()
        classifica = classifica.sort_values(by="punteggio_totale", ascending=False)
        classifica.columns = ["Utente", "Punti Totali"]
        st.table(classifica)
    else:
        st.write("Nessun dato disponibile.")

# --- TAB 3: CONFRONTO FORMAZIONI ---
with tabs[2]:
    res_comp = supabase.table("view_all_picks_comparison")\
        .select("user_name, formazione")\
        .eq("id_stage", sel_tappa['id_stage'])\
        .execute()
    if res_comp.data:
        st.dataframe(pd.DataFrame(res_comp.data), use_container_width=True, hide_index=True)
