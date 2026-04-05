import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar, restore_session_from_cookie

st.set_page_config(page_title="Gestione Risultati", layout="wide", page_icon="⚙️")

# --- INIZIALIZZAZIONE SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

restore_session_from_cookie(supabase)

if not st.session_state.get("id_user_loggato"):
    st.warning("Sessione scaduta. Torna alla Home.")
    st.switch_page("Home.py")
    st.stop()

check_auth()
render_sidebar()

# --- PREPARAZIONE OPZIONI TIME GAP (00:00 -> 59:59) ---
# Creiamo la lista una sola volta per performance
opzioni_gap = [f"{m:02d}:{s:02d}" for m in range(60) for s in range(60)]

st.title("⚙️ Inserimento Risultati Ufficiali")

# --- 1. FILTRI DI SELEZIONE ---
col1, col2 = st.columns(2)
with col1:
    gare = supabase.table("dim_race").select("id_race, name").execute().data
    sel_gara = st.selectbox("Gara", gare, format_func=lambda x: x['name'], key="sb_gara")

with col2:
    tappe = supabase.table("dim_race_stage")\
        .select("id_stage, id_stage_number")\
        .eq("id_race", sel_gara['id_race'])\
        .order("id_stage_number")\
        .execute().data
    sel_tappa = st.selectbox("Tappa", tappe, format_func=lambda x: f"Tappa {x['id_stage_number']}", key="sb_tappa")

st.divider()

# --- 2. CARICAMENTO DATI ---
res = supabase.table("view_admin_riders_to_score")\
    .select("*")\
    .eq("id_stage", sel_tappa['id_stage'])\
    .execute()

lista_payload = []

if not res.data:
    st.info("Nessun pick trovato.")
else:
    id_type_race = res.data[0].get('id_type_race', 3) 
    
    with st.form("form_gestione_risultati"):
        h1, h2, h3 = st.columns([3, 1, 1])
        h1.write("**Ciclista**")
        h2.write("**Risultato (MM:SS)**")
        h3.write("**Ritirato?**")
        
        for r in res.data:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(r['rider_name'])
            
            current_rank = None
            current_gap = None

            if id_type_race == 3:
                # MODALITÀ RANK (Identica a prima)
                val_db = int(r['current_rank']) if r.get('current_rank') is not None else 0
                nuovo_rank = c2.number_input(f"R_{r['id_rider']}", 0, 999, min(val_db, 999), key=f"in_{r['id_rider']}", label_visibility="collapsed")
                current_rank = nuovo_rank if nuovo_rank > 0 else None
            
            else:
                # MODALITÀ TIME GAP (Selectbox Guidata)
                gap_db = r.get('time_gap') or "00:00"
                # Se il valore nel DB non è tra le opzioni (es. un valore vecchio sporco), lo forziamo a 00:00
                index_default = opzioni_gap.index(gap_db) if gap_db in opzioni_gap else 0
                
                current_gap = c2.selectbox(
                    f"G_{r['id_rider']}", 
                    options=opzioni_gap,
                    index=index_default,
                    key=f"gap_{r['id_rider']}",
                    label_visibility="collapsed"
                )

            is_dnf = c3.checkbox("DNF", key=f"dnf_{r['id_rider']}", value=r.get('is_dnf', False))
            
            lista_payload.append({
                "id_race": r['id_race'], 
                "id_stage": r['id_stage'], 
                "id_rider": r['id_rider'],
                "id_team": r['id_team'], 
                "rank_stage": current_rank, 
                "time_gap": current_gap, 
                "is_dnf": is_dnf
            })
        
        invio = st.form_submit_button("💾 SALVA E AGGIORNA CLASSIFICHE", use_container_width=True, type="primary")

    if invio:
        try:
            supabase.table("fact_results").upsert(lista_payload, on_conflict="id_stage, id_rider").execute()
            st.success("✅ Risultati aggiornati con successo!")
            st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")

# DEBUG
with st.expander("Dati inviati (Debug)"):
    st.json(lista_payload)
