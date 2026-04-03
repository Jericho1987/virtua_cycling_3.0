import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar 

st.set_page_config(page_title="Gestione Risultati", layout="wide", page_icon="⚙️")

# --- PROTEZIONE E SIDEBAR ---
check_auth()      
render_sidebar()  

# Inizializzazione Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

if not st.session_state.get('id_user_loggato'):
    st.error("Effettua il login per accedere a questa pagina.")
    st.stop()

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
res = supabase.table("view_admin_riders_to_score")\
    .select("*")\
    .eq("id_stage", sel_tappa['id_stage'])\
    .execute()

if not res.data:
    st.info(f"Nessun pick trovato per {sel_gara['name']} - Tappa {sel_tappa['id_stage_number']}. Assicurati che gli utenti abbiano inserito le formazioni.")
else:
    st.subheader(f"Ordine d'arrivo: {sel_gara['name']}")
    
    # Inizializziamo la lista payload fuori dal form per il debug
    lista_payload = []
    
    with st.form("form_gestione_risultati"):
        # Header Tabella
        h1, h2, h3 = st.columns([3, 1, 1])
        h1.write("**Ciclista (Scelto dagli utenti)**")
        h2.write("**Posizione Arrivo**")
        h3.write("**Ritirato?**")
        
        for r in res.data:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(r['rider_name'])
            
            # --- FIX ERRORE VALORE MASSIMO ---
            # Se il valore nel DB è > 300, lo forziamo a 999 per evitare il crash di Streamlit
            val_db = int(r['current_rank']) if r['current_rank'] is not None else 0
            val_iniziale = min(val_db, 999)
            
            # Input numerico
            nuovo_rank = c2.number_input(
                f"Rank {r['id_rider']}", 
                min_value=0, 
                max_value=999, 
                value=val_iniziale, 
                key=f"in_{r['id_rider']}", 
                label_visibility="collapsed"
            )
            
            # Checkbox DNF
            is_dnf = c3.checkbox("DNF", key=f"dnf_{r['id_rider']}")
            
            lista_payload.append({
                "id_race": r['id_race'],
                "id_stage": r['id_stage'],
                "id_rider": r['id_rider'],
                "id_team": r['id_team'],
                "rank_stage": nuovo_rank if nuovo_rank > 0 else None,
                "is_dnf": is_dnf
            })
        
        st.write("")
        # --- FIX MISSING SUBMIT BUTTON ---
        # Il bottone deve essere l'ultimo elemento DENTRO il blocco 'with st.form'
        invio = st.form_submit_button("💾 SALVA E AGGIORNA CLASSIFICHE", use_container_width=True, type="primary")

    # --- 3. LOGICA DI SALVATAGGIO (eseguita solo al submit) ---
    if invio:
        try:
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
