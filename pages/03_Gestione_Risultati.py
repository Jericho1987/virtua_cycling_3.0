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

st.title("⚙️ Inserimento Risultati Ufficiali")
st.caption("Step 2: Inserimento combinato Posizione + Time Gap per corse a tappe.")

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
    sel_tappa = st.selectbox("Tappa", tappe, format_func=lambda x: f"Tappa {x['id_stage_number']} (ID: {x['id_stage']})", key="sb_tappa")

st.divider()

# --- 2. CARICAMENTO DATI ---
res = supabase.table("view_admin_riders_to_score")\
    .select("*")\
    .eq("id_stage", sel_tappa['id_stage'])\
    .execute()

lista_payload = []

if not res.data:
    st.info("Nessun dato trovato per questa selezione.")
else:
    id_type_race = res.data[0].get('id_type_race', 3) 
    
    st.subheader(f"Ordine d'arrivo: {sel_gara['name']}")

    with st.form("form_gestione_results"):
        # Definiamo le colonne in base al tipo di gara
        if id_type_race == 3:
            h1, h2, h3 = st.columns([3, 1, 1])
        else:
            h1, h2, h3, h4 = st.columns([3, 1, 2, 1]) # Più spazio per i 3 input
            
        h1.write("**Ciclista**")
        
        if id_type_race == 3:
            h2.write("**Posizione**")
        else:
            h2.write("**Posizione**")
            sub_h_gap = h3.columns(2)
            sub_h_gap[0].caption("Minuti")
            sub_h_gap[1].caption("Secondi")
            
        h_last = h3 if id_type_race == 3 else h4
        h_last.write("**Ritirato?**")
        
        for r in res.data:
            if id_type_race == 3:
                c1, c2, c3 = st.columns([3, 1, 1])
            else:
                c1, c2, c3, c4 = st.columns([3, 1, 2, 1])
                
            c1.write(r['rider_name'])
            
            # --- GESTIONE POSIZIONE (Sempre presente) ---
            val_rank_db = int(r['current_rank']) if r.get('current_rank') is not None else 0
            nuovo_rank = c2.number_input(
                f"R_{r['id_rider']}", 0, 999, min(val_rank_db, 999), 
                key=f"in_rank_{r['id_rider']}", label_visibility="collapsed"
            )
            
            current_rank = nuovo_rank if nuovo_rank > 0 else None
            current_gap = None

            # --- GESTIONE TIME GAP (Solo se ID != 3) ---
            if id_type_race != 3:
                gap_db = r.get('time_gap') or "00:00"
                try:
                    m_val, s_val = map(int, gap_db.split(':'))
                except:
                    m_val, s_val = 0, 0

                col_min, col_sec = c3.columns(2)
                sel_m = col_min.number_input(f"m_{r['id_rider']}", 0, 59, m_val, format="%02d", key=f"m_{r['id_rider']}", label_visibility="collapsed")
                sel_s = col_sec.number_input(f"s_{r['id_rider']}", 0, 59, s_val, format="%02d", key=f"s_{r['id_rider']}", label_visibility="collapsed")
                current_gap = f"{sel_m:02d}:{sel_s:02d}"

            # --- GESTIONE RITIRATO ---
            c_last = c3 if id_type_race == 3 else c4
            is_dnf = c_last.checkbox("DNF", key=f"dnf_{r['id_rider']}", value=r.get('is_dnf', False))
            
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
            st.success("✅ Risultati e Distacchi salvati!")
            st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")

# DEBUG
with st.expander("Dati inviati (Debug)"):
    st.json(lista_payload)
