import streamlit as st
from supabase import create_client
import re
import pandas as pd

# 1. Configurazione
st.set_page_config(page_title="Upload Mass Results", layout="wide", page_icon="🏆")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def parse_results_compact(text):
    # Rimuoviamo i ritorni a capo per trattarlo come un unico blocco di testo
    flat_text = text.replace('\n', ' ').strip()
    # Puliamo spazi multipli
    flat_text = re.sub(r'\s+', ' ', flat_text)
    
    parsed_data = []
    last_time = "0:00:00"
    
    # Identifichiamo i DNF separatamente prima di processare la classifica
    # Perché spesso sono in fondo e non hanno un numero progressivo
    main_part = flat_text.split("DNF")[0]
    dnf_part = "DNF" + "DNF".join(flat_text.split("DNF")[1:]) if "DNF" in flat_text else ""

    # --- PARSING CLASSIFICA ---
    # Logica: Cerchiamo (Rank) (Bib) (Testo) 
    # Usiamo un'espressione che "guarda avanti" per trovare il numero successivo
    # Ma attenzione: il rank aumenta di 1 ogni volta.
    
    current_rank = 1
    while True:
        # Cerchiamo l'inizio del rank corrente (es: "1 ")
        # Seguito dal Bib (2 o 3 cifre)
        # Seguito da tutto fino al rank successivo (es: " 2 ") o alla fine del testo
        next_rank = current_rank + 1
        pattern = rf'({current_rank})\s*(\d{{1,3}})\s+(.*?)(?=\s+{next_rank}\s+\d+|$)'
        
        match = re.search(pattern, main_part)
        if not match:
            break
            
        rank = match.group(1)
        bib = match.group(2)
        content = match.group(3).strip()
        
        # Estrazione tempo dalla fine della stringa content
        # Cerchiamo ,, o un formato orario (es: 3:48:27 o 0:11)
        time_match = re.search(r'(,,|\d{1,2}:\d{2}(?::\d{2})?)$', content)
        
        if time_match:
            gap = time_match.group(1)
            if rank == "1":
                gap = "0:00:00"
            elif gap == ",,":
                gap = last_time
            else:
                last_time = gap # Memorizziamo per i successivi ,,
            
            # Puliamo il nome/team togliendo il tempo e i punti UCI finali
            clean_info = re.sub(r'\d+\s+\d+\s+(,,|\d{1,2}:\d{2}(?::\d{2})?)$', '', content).strip()
        else:
            gap = "st" if rank != "1" else "0:00:00"
            clean_info = content

        parsed_data.append({
            "rank": rank,
            "bib": bib,
            "full_info": clean_info,
            "gap": gap
        })
        current_rank += 1

    # --- PARSING DNF ---
    if dnf_part:
        dnf_matches = re.findall(r'DNF\s*(\d+)\s+(.*?)(?=DNF|$)', dnf_part)
        for d_bib, d_info in dnf_matches:
            parsed_data.append({
                "rank": "DNF",
                "bib": d_bib,
                "full_info": d_info.strip(),
                "gap": ""
            })
            
    return parsed_data

# --- INTERFACCIA ---
st.title("🏆 Risultati Mobile-Ready")

try:
    races = supabase.table("dim_race").select("id_race, name").execute().data
    race_options = {r['name']: r['id_race'] for r in races}
    sel_race = st.selectbox("Seleziona gara:", list(race_options.keys()))
    
    input_text = st.text_area("Incolla il blocco di testo qui:", height=350)

    if input_text and st.button("Elabora Flusso Dati 🧪"):
        results = parse_results_compact(input_text)
        if results:
            df = pd.DataFrame(results)
            st.session_state.results_df = df
            st.success(f"Analisi completata! Processati {len(results)} elementi.")

    if 'results_df' in st.session_state:
        st.table(st.session_state.results_df)
        
        if st.button("SALVA 🚀", type="primary"):
            df_final = st.session_state.results_df.copy()
            df_final['race_name'] = sel_race
            supabase.table("stg_results").insert(df_final.to_dict(orient='records')).execute()
            st.success("Salvataggio completato!")

except Exception as e:
    st.error(f"Errore: {e}")
