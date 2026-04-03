import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar
from datetime import datetime, time

# 1. Configurazione pagina
st.set_page_config(page_title="Admin - Gestione Date", layout="wide", page_icon="📅")

# 2. Protezione e Sidebar (Solo Admin)
check_auth()
render_sidebar()

if not st.session_state.get('is_admin', False):
    st.error("Non hai i permessi per accedere a questa pagina.")
    st.stop()

# 3. Connessione Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("📅 Gestione Date e Orari Tappe")
st.markdown("Modifica rapidamente la pianificazione delle gare attive.")

# --- 4. CARICAMENTO DATI ---
try:
    # Recuperiamo i dati dalla view
    res = supabase.table("view_race_admin").select("*").order("stage_date").execute()
    df_data = res.data

    if not df_data:
        st.info("Nessuna tappa trovata nel database.")
        st.stop()

    # --- 5. INTERFACCIA DI EDITING ---
    # Usiamo un approccio riga per riga o un filtro per gara per non appesantire la UI
    races = sorted(list(set([d['race_name'] for d in df_data])))
    sel_race = st.selectbox("Filtra per Gara", ["Tutte"] + races)

    display_data = df_data if sel_race == "Tutte" else [d for d in df_data if d['race_name'] == sel_race]

    for item in display_data:
        # Creiamo un container per ogni tappa per pulizia visiva
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                st.markdown(f"**{item['race_name']}**")
                st.caption(f"Tappa {item['id_stage_number']} - {item['stage_type_desc']}")
            
            with col2:
                # Gestione data (gestisce i null se presenti)
                current_date = datetime.strptime(item['stage_date'], '%Y-%m-%d').date() if item['stage_date'] else datetime.now().date()
                new_date = st.date_input(f"Data", value=current_date, key=f"date_{item['id_stage']}")
            
            with col3:
                # Gestione orario (gestisce i null o formati stringa)
                try:
                    current_time = datetime.strptime(item['stage_time'], '%H:%M:%S').time() if item['stage_time'] else time(12, 0)
                except:
                    current_time = time(12, 0)
                
                new_time = st.time_input(f"Orario", value=current_time, key=f"time_{item['id_stage']}")
            
            with col4:
                st.write("") # Spaziamento
                st.write("") 
                if st.button("Salva ✅", key=f"btn_{item['id_stage']}", use_container_width=True):
                    # --- 6. LOGICA DI UPDATE ---
                    update_data = {
                        "stage_date": new_date.strftime('%Y-%m-%d'),
                        "stage_time": new_time.strftime('%H:%M:%S')
                    }
                    
                    try:
                        resp = supabase.table("dim_race_stage")\
                            .update(update_data)\
                            .eq("id_stage", item['id_stage'])\
                            .execute()
                        
                        if resp.data:
                            st.toast(f"Tappa {item['id_stage_number']} aggiornata!", icon="🚀")
                        else:
                            st.error("Errore durante l'aggiornamento.")
                    except Exception as e:
                        st.error(f"Errore: {e}")

except Exception as e:
    st.error(f"Errore nel caricamento dati: {e}")

# --- 7. NOTA PER L'ADMIN ---
st.divider()
st.caption("Nota: Le modifiche hanno effetto immediato sulla visibilità delle tappe per i pick degli utenti.")
