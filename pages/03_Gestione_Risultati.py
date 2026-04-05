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
st.caption("Allineato allo schema public.fact_results (gap_stage as interval)")

# --- 1. FILTRI DI SELEZIONE ---
col1, col2 = st.columns(2)
with col1:
    gare = supabase.table("dim_race").select("id_race, name").execute().data
    sel_gara = st.selectbox("Gara", gare, format_func=lambda x: x['name'], key="sb_gara")

with col2:
    # Quando la gara cambia, questa query si aggiorna automaticamente
    tappe = supabase.table("dim_race_stage")\
        .select("id_stage, id_stage_number")\
        .eq("id_race", sel_gara['id_race'])\
        .order("id_stage_number")\
        .execute().data
    
    if tappe:
        sel_tappa = st.selectbox("Tappa", tappe, format_func=lambda x: f"Tappa {x['id_stage_number']}", key="sb_tappa")
    else:
        st.info("Nessuna tappa trovata per questa gara.")
        st.stop()

st.divider()

# --- 2. CARICAMENTO DATI ---
# Questa parte ora dipende direttamente da sel_tappa, che si aggiorna appena cambia la gara
res = supabase.table("view_admin_riders_to_score")\
    .select("*")\
    .eq("id_stage", sel_tappa['id_stage'])\
    .execute()

lista_payload = []

if not res.data:
    st.info(f"Nessun pick trovato per la Tappa {sel_tappa['id_stage_number']}.")
else:
    id_type_race = res.data[0].get('id_type_race', 3) 
    
    with st.form("form_gestione_results"):
        if id_type_race == 3:
            h1, h2, h3 = st.columns([3, 1.5, 1])
        else:
            h1, h2, h3, h4 = st.columns([3, 1.2, 2.5, 1])
            
        h1.write("**Ciclista**")
        h2.write("**Posizione (Rank)**")
        
        if id_type_race != 3:
            sub_h_gap = h3.columns(2)
            sub_h_gap[0].caption("Minuti (+/-)")
            sub_h_gap[1].caption("Secondi (+/-)")
            
        h_last = h3 if id_type_race == 3 else h4
        h_last.write("**DNF**")
        
        for r in res.data:
            if id_type_race == 3:
                c1, c2, c3 = st.columns([3, 1.5, 1])
            else:
                c1, c2, c3, c4 = st.columns([3, 1.2, 2.5, 1])
                
            c1.write(r['rider_name'])
            
            # --- POSIZIONE (RANK) ---
            val_rank_db = int(r['current_rank']) if r.get('current_rank') is not None else 0
            nuovo_rank = c2.number_input(
                f"R_{r['id_rider']}", 0, 999, min(val_rank_db, 999), 
                step=1, key=f"in_rank_{r['id_rider']}", label_visibility="collapsed"
            )
            
            # --- DISTACCO (GAP) ---
            current_gap = '00:00:00'
            m_val, s_val = 0, 0 
            
            if id_type_race != 3:
                raw_gap = r.get('gap_stage')
                if raw_gap:
                    try:
                        if hasattr(raw_gap, 'total_seconds'):
                            tot_seconds = int(raw_gap.total_seconds())
                            m_val = (tot_seconds // 60) % 60
                            s_val = tot_seconds % 60
                        else:
                            gap_clean = str(raw_gap).split('.')[0]
                            parts = gap_clean.split(':')
                            if len(parts) >= 3:
                                m_val = int(parts[-2])
                                s_val = int(parts[-1])
                            elif len(parts) == 2:
                                m_val = int(parts[0])
                                s_val = int(parts[1])
                            else:
                                s_val = int(parts[0])
                    except:
                        m_val, s_val = 0, 0

                col_min, col_sec = c3.columns(2)
                sel_m = col_min.number_input(f"m_{r['id_rider']}", 0, 59, int(m_val), step=1, format="%02d", key=f"m_{r['id_rider']}", label_visibility="collapsed")
                sel_s = col_sec.number_input(f"s_{r['id_rider']}", 0, 59, int(s_val), step=1, format="%02d", key=f"s_{r['id_rider']}", label_visibility="collapsed")
                current_gap = f"00:{sel_m:02d}:{sel_s:02d}"

            # --- RITIRO (DNF) ---
            c_last = c3 if id_type_race == 3 else c4
            is_dnf = c_last.checkbox("Ritr.", key=f"dnf_{r['id_rider']}", value=r.get('is_dnf', False))
            
            lista_payload.append({
                "id_race": r['id_race'],
                "id_stage": r['id_stage'],
                "id_rider": r['id_rider'],
                "id_team": r['id_team'],
                "rank_stage": nuovo_rank if nuovo_rank > 0 else None,
                "gap_stage": current_gap,
                "is_dnf": is_dnf,
                "updated_at": "now()"
            })
        
        invio = st.form_submit_button("💾 SALVA E AGGIORNA RISULTATI", use_container_width=True, type="primary")

    if invio:
        try:
            response = supabase.table("fact_results").upsert(
                lista_payload, 
                on_conflict="id_stage, id_rider"
            ).execute()
            
            if response.data:
                st.success(f"✅ Risultati aggiornati con successo!")
                st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")

# DEBUG
with st.expander("Ispeziona Dati Grezzi (Debug)"):
    st.write(res.data)
