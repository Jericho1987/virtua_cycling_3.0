import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar, restore_session_from_cookie, save_session_to_cookie, inject_token_persistence
import pandas as pd

# 1. Configurazione pagina (DEVE essere la prima istruzione Streamlit)
st.set_page_config(page_title="Inserimento Formazione", layout="wide", page_icon="📝")

# --- INIZIALIZZAZIONE E RIPRISTINO SESSIONE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# Tenta il ripristino della sessione se l'utente ha il token nell'URL o ha ricaricato
restore_session_from_cookie(supabase)

# --- CONTROLLO AUTH ---
if not st.session_state.get("id_user_loggato"):
    st.warning("Sessione scaduta o non valida. Torna alla Home per accedere.")
    if st.button("Vai alla Home 🏠"):
        st.switch_page("Home.py")
    st.stop()

# 2. Protezione e Sidebar (Popola lo stile e il menu)
check_auth()
render_sidebar()
inject_token_persistence()  # <-- aggiunge questa riga

# --- STILE CSS ---
st.markdown("""
    <style>
        div[data-baseweb="select"] > div { font-size: 0.9rem !important; min-height: 42px !important; }
        div[data-baseweb="popover"] li { font-size: 0.85rem !important; }
        div[data-testid="stSelectbox"] { margin-bottom: 10px !important; }
    </style>
""", unsafe_allow_html=True)

# 3. Contenuto della pagina
st.title("📝 Inserimento Formazione")

# Recuperiamo i dati corretti dallo session_state aggiornato
user_id = st.session_state.id_user_loggato
user_display_name = st.session_state.get('nome_user_loggato') # Corretto refuso nome_user_loggato
t_race = st.session_state.get('gara_selezionata_id')
t_stage = st.session_state.get('tappa_selezionata_id')

# --- 1. CARICAMENTO DATI PALINSESTO ---
try:
    res_to_pick = supabase.table("view_stage_to_pick").select("*").execute()
    data_to_pick = res_to_pick.data if res_to_pick.data else []

    res_current = supabase.table("view_stage_current").select("*").execute()
    data_current = res_current.data if res_current.data else []

    all_data = data_to_pick + data_current
    current_ids = [d['id_stage'] for d in data_current]

    if not all_data:
        st.warning("Non ci sono gare disponibili al momento.")
        st.stop()

    # --- 2. LOGICA DI SELEZIONE GARA ---
    gare_opzioni = []
    seen_races = set()
    for d in all_data:
        if d['id_race'] not in seen_races:
            suffix = " 🟢 (In corso)" if d['id_stage'] in current_ids else ""
            gare_opzioni.append({
                'id': d['id_race'],
                'name': f"{d['race_name']}{suffix}",
                'type': d.get('id_type_race')
            })
            seen_races.add(d['id_race'])

    idx_g = next((i for i, g in enumerate(gare_opzioni) if g['id'] == t_race), 0)
    sel_gara = st.selectbox("Seleziona Gara", gare_opzioni, format_func=lambda x: x['name'], index=idx_g, key="sb_gara_main")

    # --- 3. LOGICA DI SELEZIONE TAPPA ---
    tappe_gara = [t for t in all_data if t['id_race'] == sel_gara['id']]

    if sel_gara['type'] == 3:
        sel_tappa = tappe_gara[0]
    else:
        idx_t = next((i for i, t in enumerate(tappe_gara) if t['id_stage'] == t_stage), 0)
        sel_tappa = st.selectbox(
            "Seleziona Tappa",
            tappe_gara,
            format_func=lambda x: f"Tappa {x['stage']}" + (" (LIVE)" if x['id_stage'] in current_ids else ""),
            index=idx_t if idx_t < len(tappe_gara) else 0,
            key=f"sb_tappa_{sel_gara['id']}"
        )

    # --- 4. CONTROLLO SE LA TAPPA È IN CORSO (Visualizzazione formazioni globali) ---
    if sel_tappa['id_stage'] in current_ids:
        st.info(f"🚀 Formazioni schierate per: **{sel_tappa['race_name']}**")
        res_global = supabase.table("view_user_pick_race").select("display_name, rider_name_short, id_slot").eq("id_stage", sel_tappa['id_stage']).execute()
        if res_global.data:
            df_raw = pd.DataFrame(res_global.data)
            df_pivot = df_raw.pivot(index='display_name', columns='id_slot', values='rider_name_short')
            df_pivot.columns = [f"Pos. {int(col)}" for col in df_pivot.columns]
            df_final = df_pivot.fillna("-").reset_index()
            df_final.rename(columns={'display_name': 'Partecipante'}, inplace=True)
            df_final = df_final.sort_values(by='Partecipante', key=lambda col: col.str.lower())
            
            def highlight_me(row):
                if str(row['Partecipante']).lower() == str(user_display_name).lower():
                    return ['background-color: #1f3d33; color: white; font-weight: bold'] * len(row)
                return [''] * len(row)
            
            st.dataframe(df_final.style.apply(highlight_me, axis=1), use_container_width=True, hide_index=True)
        else:
            st.write("Nessuna formazione inviata per questa tappa.")
        st.stop()

    # --- 5. LOGICA TAB (Inserimento o Riepilogo) ---
    if sel_gara['type'] != 3:
        tab_ins, tab_riep = st.tabs(["✍️ Inserimento Pick", "📊 Riepilogo Pick"])
    else:
        tab_ins = st.container()
        tab_riep = None

    with tab_ins:
        res_existing = supabase.table("fact_user_pick").select("id_slot, id_rider").eq("id_user", user_id).eq("id_stage", sel_tappa['id_stage']).execute()
        existing_picks = {p['id_slot']: p['id_rider'] for p in res_existing.data}

        res_riders = supabase.table("view_start_list_display").select("id_rider, rider_name, id_team").eq("id_race", sel_gara['id']).order("rider_name").execute()
        riders_list = [{"id": None, "nome": "-", "id_team": None}] + [{"id": r['id_rider'], "nome": r['rider_name'], "id_team": r['id_team']} for r in res_riders.data]

        limit = int(sel_tappa['pick_limit']) if sel_tappa.get('pick_limit') else (5 if sel_gara['type'] == 3 else 1)
        st.divider()
        st.info(f"Regolamento: **{limit} pick richieste**")

        picks = []
        for i in range(limit):
            slot_number = i + 1
            saved_rider_id = existing_picks.get(slot_number)
            default_idx = 0
            if saved_rider_id:
                for idx, rider in enumerate(riders_list):
                    if rider['id'] == saved_rider_id:
                        default_idx = idx
                        break
            p = st.selectbox(f"Pos. {slot_number}", options=riders_list, format_func=lambda x: x['nome'], index=default_idx, key=f"pick_{sel_tappa['id_stage']}_{i}")
            picks.append(p)

        if st.button("🚀 CONFERMA PICK", use_container_width=True, type="primary"):
            selected_ids = [p['id'] for p in picks if p['id'] is not None]
            if len(selected_ids) < limit:
                st.error(f"Devi completare tutti i {limit} slot.")
            elif len(set(selected_ids)) < len(selected_ids):
                st.error("Hai inserito dei corridori duplicati!")
            else:
                # Controllo duplicati per i Tour (Gare a tappe)
                if sel_gara['type'] != 3:
                    res_dupes = supabase.table("view_check_duplicate_tour").select("id_rider").eq("id_user", user_id).eq("id_race", sel_gara['id']).neq("id_stage", sel_tappa['id_stage']).execute()
                    used_riders = [r['id_rider'] for r in res_dupes.data]
                    dupe_found = False
                    for rid in selected_ids:
                        if rid in used_riders:
                            nome_rider = next((p['nome'] for p in picks if p['id'] == rid), "Corridore")
                            st.error(f"🚫 Errore: **{nome_rider}** è già stato schierato in una tappa precedente!")
                            dupe_found = True
                            break
                    if dupe_found: st.stop()

                # Salvataggio
                supabase.table("fact_user_pick").delete().eq("id_user", user_id).eq("id_stage", sel_tappa['id_stage']).execute()
                to_insert = [{"id_user": user_id, "id_race": sel_gara['id'], "id_stage": sel_tappa['id_stage'], "id_rider": p['id'], "id_team": p['id_team'], "id_slot": i + 1} for i, p in enumerate(picks)]
                supabase.table("fact_user_pick").insert(to_insert).execute()
                st.success("Salvataggio completato!")
                st.balloons()

    if tab_riep:
        with tab_riep:
            st.subheader(f"I tuoi pick per {sel_gara['name']}")
            res_summary = supabase.table("view_check_duplicate_tour")\
                .select("id_stage_number, id_slot, rider_name")\
                .eq("id_user", user_id)\
                .eq("id_race", sel_gara['id'])\
                .order("id_stage_number")\
                .order("id_slot").execute()
            
            if res_summary.data:
                df_summary = pd.DataFrame(res_summary.data)
                df_summary.columns = ["Tappa", "Pos.", "Corridore"]
                st.dataframe(df_summary, use_container_width=True, hide_index=True)
            else:
                st.info("Nessun pick salvato per questa gara.")

except Exception as e:
    st.error(f"Si è verificato un errore: {e}")
