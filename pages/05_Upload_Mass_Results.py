import streamlit as st
from supabase import create_client
import re
import pandas as pd

# 1. Configurazione
st.set_page_config(page_title="Upload Mass Results", layout="wide", page_icon="🏆")

# Connessione (Assicurati che i secrets siano corretti)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_and_parse(raw_text):
    # Dividiamo il testo in linee e puliamo spazi extra
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    parsed_data = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # --- CASO DNF ---
        if "DNF" in line.upper():
            # Spesso il formato è: DNF / Numero / Nome
            bib = ""
            name = "Sconosciuto"
            if i + 1 < len(lines) and lines[i+1].isdigit():
                bib = lines[i+1]
                name = lines[i+2] if i+2 < len(lines) else "Sconosciuto"
                i += 3
            else:
                name = lines[i+1] if i+1 < len(lines) else "Sconosciuto"
                i += 2
            parsed_data.append({"rank": "DNF", "bib": bib, "full_info": name, "gap": "-"})
            continue

        # --- CASO CLASSIFICA (Rank Numerico) ---
        # Se la riga è un numero, è probabilmente il RANK
        if line.isdigit() and len(line) < 4:
            rank = line
            bib = ""
            name_info = ""
            gap = "0:00:00"
            
            # Avanziamo per cercare BIB e NOME
            i += 1
            if i < len(lines):
                # Se la riga dopo il rank è un numero, è il BIB (pettorale)
                if lines[i].isdigit():
                    bib = lines[i]
                    i += 1
                
                # La riga successiva DEVE essere il nome dell'atleta
                if i < len(lines):
                    name_info = lines[i]
                    
                    # Controlliamo se nelle righe successive c'è il Team o il Tempo
                    # Solitamente il tempo contiene ":" o ",,"
                    look_ahead = 1
                    while i + look_ahead < len(lines):
                        next_l = lines[i + look_ahead]
                        # Se troviamo il rank successivo (un numero piccolo), ci fermiamo
                        if next_l.isdigit() and len(next_l) < 4:
                            break
                        # Se è un tempo, lo salviamo come GAP
                        if ":" in next_l or ",," in next_l:
                            gap = next_l
                        # Altrimenti lo aggiungiamo alle info (Team, UCI points, ecc)
                        else:
                            name_info += f" {next_l}"
                        look_ahead += 1
                    
                    i += (look_ahead - 1)
            
            # Pulizia finale del nome (rimuoviamo numeri di punti UCI incollati)
            name_info = re.sub(r'\d{2,}\s*$', '', name_info).strip()
            
            parsed_data.append({
                "rank": rank,
                "bib": bib,
                "full_info": name_info,
                "gap": gap
            })
        
        i += 1
    return parsed_data

# --- INTERFACCIA ---
st.title("🏆 Caricamento Risultati (Parser Avanzato)")

try:
    # Caricamento gare per il selectbox
    races = supabase.table("dim_race").select("id_race, name").execute().data
    race_options = {r['name']: r['id_race'] for r in races}
    sel_race = st.selectbox("Seleziona la gara di riferimento:", list(race_options.keys()))
    
    st.info("💡 Incolla il testo così come viene copiato dal sito mobile (una colonna lunga).")
    input_text = st.text_area("Copia e incolla qui:", height=300)

    if input_text and st.button("Analizza Flusso Dati 🧪", use_container_width=True):
        results = clean_and_parse(input_text)
        if results:
            st.session_state.results_df = pd.DataFrame(results)
            st.success(f"Analisi completata! Trovati {len(results)} atleti.")
        else:
            st.error("Non sono riuscito a leggere i dati. Controlla il formato.")

    if 'results_df' in st.session_state:
        st.subheader("Verifica i dati estratti")
        # Usiamo data_editor così puoi correggere i nomi o i tempi a mano!
        edited_df = st.data_editor(
            st.session_state.results_df, 
            num_rows="dynamic",
            use_container_width=True,
            key="result_editor"
        )
        
        if st.button("SALVA DEFINITIVAMENTE 🚀", type="primary", use_container_width=True):
            # Preparazione dati per Supabase
            data_to_save = edited_df.to_dict(orient='records')
            # Aggiungiamo l'id_race a ogni riga
            for row in data_to_save:
                row['id_race'] = race_options[sel_race]
            
            # Inserimento (Assicurati che la tabella si chiami stg_results)
            supabase.table("stg_results").insert(data_to_save).execute()
            st.success("Dati inviati con successo al database!")
            del st.session_state.results_df

except Exception as e:
    st.error(f"Si è verificato un errore: {e}")
