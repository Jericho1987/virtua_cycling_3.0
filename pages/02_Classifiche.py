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

st.title("📊 Classifica")

# --- 1. RECUPERO PARAMETRI E LOGICA DEFAULT ---
target_race = st.session_state.get('gara_selezionata_id')
target_stage = st.session_state.get('tappa_selezionata_id')

if target_race is None or target_stage is None:
    last_data_query = supabase.table("view_simulazione_punti")\
        .select("id_stage")\
        .order("id_stage", desc=True)\
        .limit(1)\
        .execute()
    
    if last_data_query.data:
        target_stage = last_data_query.data[0]['id_stage']
        race_info = supabase.table("dim_race_stage")\
            .select("id_race")\
            .eq("id_stage", target_stage)\
            .single()\
            .execute()
        if race_info.data:
            target_race = race_info.data['id_race']

# --- 2. FILTRI ---
col_f1, col_f2 = st.columns(2)

with col_f1:
    gare = supabase.table("dim_race").select("id_race, name, id_type_race").execute().data
    
    idx_g = 0
    if target_race is not None:
        for i, g in enumerate(gare):
            if str(g['id_race']) == str(target_race):
                idx_g = i
                break
    
    sel_gara = st.selectbox("Seleziona Gara", gare, index=idx_g, format_func=lambda x: x['name'])

is_one_day_race = sel_gara.get('id_type_race') == 3

with col_f2:
    if is_one_day_race:
        tappa_data = supabase.table("dim_race_stage")\
            .select("id_stage, id_stage_number")\
            .eq("id_race", sel_gara['id_race'])\
            .limit(1)\
            .execute().data
        sel_tappa = tappa_data[0] if tappa_data else None
    else:
        tappe = supabase.table("dim_race_stage").select("id_stage, id_stage_number").eq("id_race", sel_gara['id_race']).order("id_stage_number").execute().data
        
        idx_t = 0
        if target_stage is not None:
            for i, t in enumerate(tappe):
                if str(t['id_stage']) == str(target_stage):
                    idx_t = i
                    break
                    
        sel_tappa = st.selectbox("Seleziona Tappa", tappe, index=idx_t, format_func=lambda x: f"Tappa {x['id_stage_number']}")

st.markdown("---")

# Funzione di supporto per le icone posizione
def make_pretty_pos(pos):
    icons = {1: "🥇", 2: "🥈", 3: "🥉"}
    return icons.get(pos, str(pos))

# --- 3. RECUPERO DATI E VISUALIZZAZIONE ---
if sel_tappa:
    # Se NON è una corsa di un giorno, mostriamo i Tab
    if not is_one_day_race:
        tab_tappa, tab_generale = st.tabs(["⏱️ Classifica Tappa", "🏆 Classifica Generale"])
    else:
        # Per le corse singole usiamo un solo "contenitore" fittizio per riusare la logica
        tab_tappa = st.container()

    # --- TAB CLASSIFICA TAPPA ---
    with tab_tappa:
        res_tappa = supabase.table("view_classifica_tappa")\
            .select("posizione, display_name, gap_stage")\
            .eq("id_stage", sel_tappa['id_stage'])\
            .order("posizione")\
            .execute()

        if res_tappa.data:
            df_t = pd.DataFrame(res_tappa.data)
            
            # Podio Tappa
            st.subheader("🏆 Podio di Tappa")
            p_cols = st.columns(3)
            for i in range(3):
                with p_cols[i]:
                    if len(df_t) > i:
                        u = df_t.iloc[i]
                        med = ["🥇 1° Posto", "🥈 2° Posto", "🥉 3° Posto"]
                        st.metric(label=med[i], value=f"+{u['gap_stage']}″", delta=u['display_name'], delta_color="off")

            # Tabella Tappa
            df_t['Rank'] = df_t['posizione'].apply(make_pretty_pos)
            df_t_view = df_t[['Rank', 'display_name', 'gap_stage']].copy()
            df_t_view.columns = ["Pos.", "Giocatore", "Distacco"]
            st.dataframe(df_t_view, use_container_width=True, hide_index=True)
        else:
            st.info("Nessun dato disponibile per questa tappa.")

    # --- TAB CLASSIFICA GENERALE (Solo se id_type_race != 3) ---
    if not is_one_day_race:
        with tab_generale:
            res_gc = supabase.table("view_classifica_generale")\
                .select("posizione_gc, display_name, gap_totale")\
                .eq("id_stage", sel_tappa['id_stage'])\
                .order("posizione_gc")\
                .execute()

            if res_gc.data:
                df_gc = pd.DataFrame(res_gc.data)
                
                # Podio Generale
                st.subheader("👕 Leader Classifica Generale")
                g_cols = st.columns(3)
                for i in range(3):
                    with g_cols[i]:
                        if len(df_gc) > i:
                            u_gc = df_gc.iloc[i]
                            st.metric(label=f"Posizione {i+1}", value=f"{u_gc['gap_totale']}″", delta=u_gc['display_name'], delta_color="off")

                # Tabella Generale
                df_gc['Rank'] = df_gc['posizione_gc'].apply(make_pretty_pos)
                df_gc_view = df_gc[['Rank', 'display_name', 'gap_totale']].copy()
                df_gc_view.columns = ["Pos.", "Giocatore", "Gap Totale"]
                st.dataframe(df_gc_view, use_container_width=True, hide_index=True)
            else:
                st.info("Dati della classifica generale non ancora disponibili.")

else:
    st.warning("Nessuna tappa trovata per questa gara.")

# --- 4. CANCELLAZIONE PARAMETRI DI NAVIGAZIONE ---
if 'gara_selezionata_id' in st.session_state:
    del st.session_state['gara_selezionata_id']
if 'tappa_selezionata_id' in st.session_state:
    del st.session_state['tappa_selezionata_id']
