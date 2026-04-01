import streamlit as st
from supabase import create_client
import pandas as pd
import re

# 1. Configurazione
st.set_page_config(page_title="Upload Mass Results", layout="wide", page_icon="🏆")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def simple_line_parser(raw_text):
    # Dividiamo il testo riga per riga, pulendo gli spazi
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    parsed_data = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # GESTIONE DNF
        if "DNF" in line.upper():
            bib = ""
            if i+1 < len(lines) and lines[i+1].isdigit():
                bib = lines[i+1]
                name = lines[i+2] if i+2 < len(lines) else "Sconosciuto"
                i += 3
            else:
                name = lines[i+1] if i+1 < len(lines) else "Sconosciuto"
                i += 2
            parsed_data.append({"rank": "DNF", "bib": bib, "full_info": name, "gap": "-"})
            continue

        # GESTIONE CLASSIFICA (Se la riga è un numero <= 200 è una posizione)
        if line.isdigit() and int(line) < 500:
            rank = line
            bib = ""
            name_parts = []
            gap = "0:00:00"
            
            i += 1 # Passiamo alla riga successiva
            
            # Esaminiamo le righe successive finché non troviamo la PROSSIMA posizione
            while i < len(lines):
                current_l = lines[i]
                
                # Se la riga successiva è la posizione dopo (es. siamo alla 1 e troviamo "2")
                if current_l.isdigit() and int(current_l) == int(rank) + 1:
                    break # Passiamo al prossimo corridore
                
                # Se è un tempo (contiene : o ,,)
                if ":" in current_l or ",," in current_l:
                    gap = current_l
                # Se è il pettorale (numero che segue immediatamente il rank)
                elif current_l.isdigit() and not name_parts:
                    bib = current_l
                # Altrimenti è parte del nome o del team
                else:
                    # Evitiamo di aggiungere i punti UCI (numeri singoli piccoli in fondo)
                    if not (current_l.isdigit() and len(current_l) < 3):
                        name_parts.append(current_l)
                
                i += 1
            
            parsed_data.append({
                "rank": rank,
                "bib": bib,
                "full_info": " ".join(name_parts),
                "gap": gap
            })
            # Non incrementiamo i qui perché lo facciamo nel loop esterno o siamo già al break
            continue
            
        i += 1
    return parsed_data

# --- INTERFACCIA ---
st.title("🏆 Parser Risultati (Versione Riga-per-Riga)")

try:
    races = supabase.table("dim_race").select("id_race, name").execute().data
    race_options = {r['name']: r['id_race'] for r in races}
    sel_race = st.selectbox("Seleziona Gara:", list(race_options.keys()))
    
    input_text = st.text_area("Incolla qui il testo (assicurati che i dati siano su righe diverse):", height=300)

    if input_text and st.button("Elabora 🧪"):
        data = simple_line_parser(input_text)
        if data:
            st.session_state.results_df = pd.DataFrame(data)
            st.success(f"Trovati {len(data)} atleti.")

    if 'results_df' in st.session_state:
        # Mostriamo l'editor per correggere i residui
        edited_df = st.data_editor(st.session_state.results_df, num_rows="dynamic", use_container_width=True)
        
        if st.button("SALVA SU DATABASE 🚀"):
            final_data = edited_df.to_dict(orient='records')
            for row in final_data:
                row['id_race'] = race_options[sel_race]
            
            supabase.table("stg_results").insert(final_data).execute()
            st.success("Dati salvati!")
            del st.session_state.results_df

except Exception as e:
    st.error(f"Errore: {e}")
