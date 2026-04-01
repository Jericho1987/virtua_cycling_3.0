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

        # --- CASO A: Nuovo Corridore in classifica (Inizia con Rank + Bib) ---
        new_rider_match = re.match(r'^(\d+)\s+(\d+)\s+(.*)', line)
        
        # --- CASO B: Ritirato (Inizia con DNF + Bib) ---
        dnf_match = re.match(r'^DNF\s*(\d+)\s+(.*)', line, re.IGNORECASE)

        if new_rider_match:
            if current_entry: parsed_data.append(current_entry)
            
            rank = new_rider_match.group(1)
            bib = new_rider_match.group(2)
            rest = new_rider_match.group(3)
            
            # Se è il primo, il tempo è sempre zero
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
                "gap": "" # Nessun tempo per i ritirati
            }

        elif current_entry:
            # --- AGGIORNAMENTO INFO O TEMPO ---
            # Cerchiamo il tempo/distacco (,, o XX:XX)
            time_match = re.search(r'(,,|\d{1,2}:\d{2}(?::\d{2})?)$', line)
            
            if time_match and current_entry["rank"] != "DNF":
                gap = time_match.group(1)
                
                # Se è il primo, ignoriamo il tempo trovato e mettiamo 0:00:00
                if current_entry["rank"] == "1":
                    current_entry["gap"] = "0:00:00"
                elif gap == ",,":
                    current_entry["gap"] = last_time
                else:
                    current_entry["gap"] = gap
                    last_time = gap
                
                # Pulizia dai punti UCI (es: 400 225) prima del tempo
                clean_extra = re.sub(r'\d+\s+\d+\s+(,,|\d{1,2}:\d{2}(?::\d{2})?)$', '', line).strip()
                current_entry["full_info"] += " " + clean_extra
            else:
                # Aggiungiamo testo al nome/team se non sono solo numeri (punti UCI)
                if not re.match(r'^\d+\s+\d+$', line):
                    current_entry["full_info"] += " " + line

    if current_entry:
        parsed_data.append(current_entry)
            
    return parsed_data

# --- INTERFACCIA ---
st.title("🏆 Caricamento Risultati (Gara + DNF)")

try:
    races = supabase.table("dim_race").select("id_race, name").execute().data
    race_options = {r['name']: r['id_race'] for r in races}
    sel_race = st.selectbox("Seleziona la gara:", list(race_options.keys()))
    
    st.divider()
    input_text = st.text_area("Incolla qui l'ordine d'arrivo (inclusi DNF):", height=400)

    if input_text:
        if st.button("Analizza Risultati 🔍"):
            results = parse_results_v4(input_text)
            if results:
                st.session_state.results_df = pd.DataFrame(results)
                st.success(f"Analisi completata: {len(results)} corridori processati.")

    if 'results_df' in st.session_state:
        # Pulizia estetica spazi
        st.session_state.results_df['full_info'] = st.session_state.results_df['full_info'].str.replace(r'\s+', ' ', regex=True)
        st.table(st.session_state.results_df)
        
        if st.button("SALVA IN STAGING 🚀", type="primary"):
            df_to_save = st.session_state.results_df.copy()
            df_to_save['race_name'] = sel_race
            records = df_to_save.to_dict(orient='records')
            
            try:
                supabase.table("stg_results").insert(records).execute()
                st.success("✅ Risultati (inclusi DNF) salvati in stg_results!")
                # Qui potresti aggiungere la chiamata alla function rpc se ne hai una pronta
            except Exception as e:
                st.error(f"Errore durante il salvataggio: {e}")

except Exception as e:
    st.error(f"Errore: {e}")
