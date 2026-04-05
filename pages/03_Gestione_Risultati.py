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
st.caption("Piattaforma di inserimento per gli amministratori. I dati salvati aggiornano le classifiche in tempo reale.")

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
# Nota: Assicurati che 'id_type_race' e 'time_gap' siano presenti nella view
res = supabase.table("view_admin_riders_to_score")\
    .select("*")\
    .eq("id_stage", sel_tappa['id_stage'])\
    .execute()

lista_payload = []

if not res.data:
    st.info(f"Nessun pick trovato per {sel_gara['name']} - Tappa {sel_tappa['id_stage_number']}. Assicurati che gli utenti abbiano inserito le formazioni.")
else:
    # Identifichiamo il tipo di gara dal primo record disponibile
    id_type_race = res.data[0].get('id_type_race', 3) 
    
    st.subheader(f"Ordine d'arrivo: {sel_gara['name']}")
    if id_type_race != 3:
        st.info("Modalità Classifica Generale: Inserisci i distacchi temporali (Time Gap).")

    with st.form("form_gestione_risultati"):
        h1, h2, h3 = st.columns([3, 1, 1])
        h1.write("**Ciclista (Scelto dagli utenti)**")
        
        # Header dinamico basato su id_type_race
        if id_type_race == 3:
            h2.write("**Posizione Arrivo**")
        else:
            h2.write("**Time Gap**")
            
        h3.write("**Ritirato?**")
        
        for r in res.data:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(r['rider_name'])
            
            # --- LOGICA DI INPUT DIFFERENZIATA ---
            current_rank = 0
            current_gap = ""
            
            if id_type_race == 3:
                # Logica Originale (ID 3)
                val_db = int(r['current_rank']) if r.get('current_rank') is not None else 0
                val_iniziale = min(val_db, 999)
                
                nuovo_valore = c2.number_input(
                    f"Rank {r['id_rider']}", 
                    min_value=0, 
                    max_value=999, 
                    value=val_iniziale, 
                    key=f"in_{r['id_rider']}", 
                    label_visibility="collapsed"
                )
                current_rank = nuovo_valore if nuovo_valore > 0 else None
                current_gap = None
            else:
                # Nuova Logica (Diverso da 3)
                val_gap_db = r.get('time_gap') if r.get('time_gap') is not None else ""
                
                current_gap = c2.text_input(
                    f"Gap {r['id_rider']}", 
                    value=val_gap_db,
                    key=f"gap_{r['id_rider']}",
                    label_visibility="collapsed",
                    placeholder="00:00"
                )
                current_rank = None # O mantieni r['current_rank'] se serve comunque

            is_dnf = c3.checkbox("DNF", key=f"dnf_{r['id_rider']}", value=r.get('is_dnf', False))
            
            # Costruzione payload
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

    # --- 3. LOGICA DI SALVATAGGIO ---
    if invio:
        try:
            # Assicurati che la tabella fact_results abbia la colonna time_gap
            response = supabase.table("fact_results").upsert(
                lista_payload, 
                on_conflict="id_stage, id_rider"
            ).execute()
            
            if response.data:
                st.success(f"✅ Ottimo! Aggiornati {len(response.data)} record nel database.")
                st.balloons()
                st.rerun()
            else:
                st.error("Il database non ha confermato il salvataggio. Controlla le policy di sicurezza (RLS).")
        
        except Exception as e:
            st.error(f"Errore tecnico durante il salvataggio: {e}")

# --- 4. DEBUG ---
with st.expander("Dati inviati (Debug)"):
    if lista_payload:
        st.json(lista_payload)
