import streamlit as st
from supabase import create_client
import re
import pandas as pd

# 1. Configurazione
st.set_page_config(page_title="Upload Mass Results", layout="wide", page_icon="🏆")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def parse_results_v4(text):
    lines = text.split('\n')
    parsed_data = []
    current_entry = None
    last_time = "0:00:00"

    for line in lines:
        line = line.strip()
        if not line: continue

        # --- CASO A: Rank + Bib ---
        new_rider_match = re.match(r'^(\d+)\s+(\d+)\s+(.*)', line)
        # --- CASO B: DNF + Bib ---
        dnf_match = re.match(r'^DNF\s*(\d+)\s+(.*)', line, re.IGNORECASE)

        if new_rider_match:
            if current_entry: parsed_data.append(current_entry)
            rank = new_rider_match.group(1)
            bib = new_rider_match.group(2)
            rest = new_rider_match.group(3)
            initial_gap = "0:00:00" if rank == "1" else "st"
            
            current_entry = {
                "rank": rank,
                "bib": bib,
                "full_info": rest,
                "gap": initial_gap
            }

        elif dnf_match:
            if current_entry: parsed_data.append(current_entry)
            bib_dnf = dnf_match.group(1)
            rest_dnf = dnf_match.group(2)
            
            current_entry = {
                "rank": "DNF",
                "bib": bib_dnf,
                "full_info": rest_dnf,
                "gap": "" 
            }

        elif current_entry:
            time_match = re.search(r'(,,|\d{1,2}:\d{2}(?::\d{2})?)$', line)
            if time_match and current_entry["rank"] != "DNF":
                gap = time_match.group(1)
                if current_entry["rank"] == "1":
                    current_entry["gap"] = "0:00:00"
                elif gap == ",,":
                    current_entry["gap"] = last_time
                else:
                    current_entry["gap"] = gap
                    last_time = gap
                
                clean_extra = re.sub(r'\d+\s+\d+\s+(,,|\d{1,2}:\d{2}(?::\d{2})?)$', '', line).strip()
                current_entry["full_info"] += " " + clean_extra
            else:
                if not re.match(r'^\d+\s+\d+$', line):
                    current_entry["full_info"] += " " + line

    if current_entry:
        parsed_data.append(current_entry)
    return parsed_data

# --- INTERFACCIA ---
st.title("🏆 Caricamento Risultati in Staging")

try:
    # 1. Recupero Gare
    races = supabase.table("dim_race").select("id_race, name").execute().data
    race_options = {r['name']: r['id_race'] for r in races}
    
    c1, c2 = st.columns(2)
    with c1:
        sel_race_name = st.selectbox("Seleziona la gara:", list(race_options.keys()))
        id_race = race_options[sel_race_name]
    
    # 2. Recupero Tappe della gara selezionata
    stages = supabase.table("dim_race_stage").select("id_stage, id_stage_number").eq("id_race", id_race).order("id_stage_number").execute().data
    stage_options = {f"Tappa {s['id_stage_number']}": s['id_stage'] for s in stages}
    
    with c2:
        sel_stage_name = st.selectbox("Seleziona la tappa:", list(stage_options.keys()))
        id_stage = stage_options[sel_stage_name]

    st.divider()
    input_text = st.text_area("Incolla qui l'ordine d'arrivo (inclusi DNF):", height=300)

    if input_text:
        if st.button("Analizza Risultati 🔍"):
            results = parse_results_v4(input_text)
            if results:
                st.session_state.results_df = pd.DataFrame(results)
                st.success(f"Analisi completata: {len(results)} corridori trovati.")

    if 'results_df' in st.session_state:
        # Pulizia estetica spazi
        df_preview = st.session_state.results_df.copy()
        df_preview['full_info'] = df_preview['full_info'].str.replace(r'\s+', ' ', regex=True)
        st.table(df_preview)
        
        if st.button("SALVA IN STAGING 🚀", type="primary"):
            # Prepariamo i record aggiungendo id_race e id_stage
            final_records = []
            for _, row in df_preview.iterrows():
                final_records.append({
                    "id_race": str(id_race),
                    "id_stage": str(id_stage),
                    "rank": str(row['rank']),
                    "bib": str(row['bib']),
                    "full_info": str(row['full_info']),
                    "gap": str(row['gap'])
                })
            
            try:
                # OPTIONAL: Pulizia staging per questa tappa prima dell'insert
                supabase.table("stg_result").delete().eq("id_stage", id_stage).execute()
                
                # Inserimento massivo
                supabase.table("stg_result").insert(final_records).execute()
                
                st.success(f"✅ {len(final_records)} record salvati correttamente nella tabella stg_result!")
                st.balloons()
            except Exception as e:
                st.error(f"Errore durante il salvataggio in database: {e}")

except Exception as e:
    st.error(f"Errore generale: {e}")
