import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar
from datetime import datetime

# 1. Configurazione pagina
st.set_page_config(page_title="Admin - Gestione Date", layout="wide", page_icon="📅")

# 2. Protezione e Sidebar
check_auth()
render_sidebar()

if not st.session_state.get('is_admin', False):
    st.error("Accesso negato.")
    st.stop()

# 3. Connessione Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("📅 Gestione Rapida Tappe")

# Generiamo la lista degli orari (ogni 15 minuti) per la selectbox
TIME_OPTIONS = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 15, 30, 45)]

try:
    # Caricamento dati
    res = supabase.table("view_race_admin").select("*").order("stage_date").execute()
    res_types = supabase.table("dim_stage_type").select("id_stage_type, description").execute()
    
    df_data = res.data
    type_options = {t['description']: t['id_stage_type'] for t in res_types.data}
    
    if not df_data:
        st.info("Nessuna tappa trovata.")
        st.stop()

    # Filtro Gara
    races = sorted(list(set([d['race_name'] for d in df_data])))
    sel_race = st.selectbox("Filtra per Gara", ["Tutte"] + races)
    display_data = df_data if sel_race == "Tutte" else [d for d in df_data if d['race_name'] == sel_race]

    # --- HEADER TABELLA ---
    h1, h2, h3, h4, h5, h6 = st.columns([2, 0.6, 1.2, 1, 1.5, 0.8])
    h1.caption("GARA / DESCRIZIONE")
    h2.caption("T.")
    h3.caption("DATA")
    h4.caption("ORARIO")
    h5.caption("TIPOLOGIA")
    h6.caption("AZIONE")
    st.write("") # Spaziatore

    # --- RIGHE TABELLA ---
    for item in display_data:
        sid = item['id_stage']
        
        # Pulizia orario dal DB (es. da "12:00:00" a "12:00")
        current_time_db = item['stage_time'][:5] if item['stage_time'] else "12:00"
        if current_time_db not in TIME_OPTIONS:
            TIME_OPTIONS.append(current_time_db)
            TIME_OPTIONS.sort()

        with st.container():
            c1, c2, c3, c4, c5, c6 = st.columns([2, 0.6, 1.2, 1, 1.5, 0.8])
            
            # 1. Info Gara
            c1.markdown(f"**{item['race_name']}**")
            c1.caption(item.get('stage_type_desc', ''))

            # 2. Numero Tappa
            c2.write(f"#{item['id_stage_number']}")
            
            # 3. Data (Widget standard, molto compatto)
            curr_date = datetime.strptime(item['stage_date'], '%Y-%m-%d').date() if item['stage_date'] else datetime.now().date()
            new_date = c3.date_input("Data", value=curr_date, key=f"d_{sid}", label_visibility="collapsed")
            
            # 4. Orario (CON LA FRECCINA - Selectbox)
            idx_time = TIME_OPTIONS.index(current_time_db) if current_time_db in TIME_OPTIONS else 0
            new_time_str = c4.selectbox("Ora", options=TIME_OPTIONS, index=idx_time, key=f"t_{sid}", label_visibility="collapsed")
            
            # 5. Tipo Tappa (CON LA FRECCINA - Selectbox)
            type_list = list(type_options.keys())
            current_type_desc = item['stage_type_desc']
            idx_type = type_list.index(current_type_desc) if current_type_desc in type_list else 0
            new_type_desc = c5.selectbox("Tipo", options=type_list, index=idx_type, key=f"s_{sid}", label_visibility="collapsed")
            
            # 6. Bottone Salva
            if c6.button("Salva ✅", key=f"b_{sid}", use_container_width=True):
                update_payload = {
                    "stage_date": new_date.strftime('%Y-%m-%d'),
                    "stage_time": f"{new_time_str}:00",
                    "id_stage_type": type_options[new_type_desc]
                }
                
                res_upd = supabase.table("dim_race_stage").update(update_payload).eq("id_stage", sid).execute()
                
                if res_upd.data:
                    st.toast(f"Tappa {item['id_stage_number']} aggiornata!", icon="🚀")
                else:
                    st.error("Errore nell'aggiornamento")

        st.divider()

except Exception as e:
    st.error(f"Errore caricamento: {e}")
