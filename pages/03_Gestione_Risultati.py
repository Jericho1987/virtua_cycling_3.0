import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar, restore_session_from_cookie

st.set_page_config(page_title="Gestione Risultati", layout="wide", page_icon="⚙️")

# --- INIZIALIZZAZIONE SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- RIPRISTINO SESSIONE ---
restore_session_from_cookie(supabase)

# --- CONTROLLO AUTH ---
if not st.session_state.get("id_user_loggato"):
    st.warning("Sessione scaduta. Torna alla Home.")
    st.switch_page("Home.py")
    st.stop()

# --- PROTEZIONE E SIDEBAR ---
check_auth()
render_sidebar()

st.title("⚙️ Inserimento Risultati Ufficiali")
st.caption("I dati salvati aggiornano le classifiche in tempo reale.")

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

# --- 2. CARICAMENTO DATI DALLA VIEW ---
res = supabase.table("view_admin_riders_to_score")\
    .select("*")\
    .eq("id_stage", sel_tappa['id_stage'])\
    .execute()

lista_payload = []

if not res.data:
    st.info(f"Nessun pick trovato per {sel_gara['name']}.")
else:
    # Identifichiamo il tipo di gara
    id_type_race = res.data[0].get('id_type_race', 3) 
    
    st.subheader(f"Ordine d'arrivo: {sel_gara['name']}")
    
    with st.form("form_gestione_risultati"):
        # Header dinamico
        if id_type_race == 3:
            h1, h2, h3 = st.columns([3, 1, 1])
        else:
            # Più spazio per i due selettori minuti/secondi
            h1, h2, h3 = st.columns([3, 2, 1])
            
        h1.write("**Ciclista**")
        h2.write("**Risultato**")
        h3.write("**Ritirato?**")
        
        for r in res.data:
            if id_type_race == 3:
                c1, c2, c3 = st.columns([3, 1, 1])
            else:
                c1, c2, c3 = st.columns([3, 2, 1])
                
            c1.write(r['rider_name'])
            
            # --- GESTIONE INPUT ---
            current_rank = None
            current_gap = None

            if id_type_race == 3:
                # MODALITÀ POSIZIONE (Standard)
                val_db = int(r['current_rank']) if r.get('current_rank') is not None else 0
                nuovo_rank = c2.number_input(
                    f"R_{r['id_rider']}", min_value=0, max_value=999, value=min(val_db, 999),
                    key=f"in_{r['id_rider']}", label_visibility="collapsed"
                )
                current_rank = nuovo_rank if nuovo_rank > 0 else None
            
            else:
                # MODALITÀ TIME GAP (Guidata)
                # Proviamo a splittare il gap esistente (formato "MM:SS")
                gap_esistente = r.get('time_gap') or "00:00"
                try:
                    m_init, s_init = map(int, gap_esistente.split(':'))
                except:
                    m_init, s_init = 0, 0

                # Creiamo due mini-colonne dentro la colonna c2
                sub_min, sub_sec = c2.columns(2)
                mins = sub_min.number_input("Min", 0, 500, m_init, key=f"min_{r['id_rider']}", label_visibility="collapsed")
                secs = sub_sec.number_input("Sec", 0, 59, s_init, key=f"sec_{r['id_rider']}", label_visibility="collapsed")
                
                # Formattiamo come stringa "MM:SS" (es. 02:05)
                current_gap = f"{mins:02d}:{secs:02d}"

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
            response = supabase.table("fact_results").upsert(
                lista_payload, on_conflict="id_stage, id_rider"
            ).execute()
            if response.data:
                st.success(f"Aggiornati {len(response.data)} record.")
                st.balloons()
                st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")

# DEBUG
with st.expander("Dati inviati (Debug)"):
    st.json(lista_payload)
