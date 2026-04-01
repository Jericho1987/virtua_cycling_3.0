import streamlit as st
from supabase import create_client
import re
import pandas as pd

# 1. Configurazione
st.set_page_config(page_title="Upload Mass Results", layout="wide", page_icon="🏆")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def parse_ultra_compact(text):
    # 1. Pulizia preliminare: trasformiamo tutto in una riga singola con spazi regolari
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    
    parsed_data = []
    
    # --- PARSING ARRIVATI ---
    # Cerchiamo il pattern: (Posizione) (Pettorale) (Nome Atleta - Testo fino a tempo o posizione successiva)
    # Esempio: "1 51 Ganna Filippo INEOS Grenadiers 4002253:48:27"
    # Il pattern cerca: Numero -> Numero -> Testo -> (Tempo o Numero Successivo)
    regex_winners = r'(\d{1,3})\s+(\d{1,3})\s+([A-Za-zÀ-ÿ\s\|\-\.\']+)'
    
    matches = re.finditer(regex_winners, text)
    
    last_pos = 0
    for match in matches:
        pos = match.group(1)
        bib = match.group(2)
        info = match.group(3).strip()
        
        # Se la posizione è coerente (es: 1, 2, 3...) la prendiamo
        if int(pos) == last_pos + 1 or last_pos == 0:
            # Pulizia: se nel nome sono finiti pezzi di numeri (es. punti UCI), li togliamo
            clean_name = re.sub(r'\d+.*$', '', info).strip()
            
            parsed_data.append({
                "rank": pos,
                "bib": bib,
                "full_info": clean_name,
                "gap": "0:00:00" # Il gap lo sistemerai a mano nell'editor se serve
            })
            last_pos = int(pos)

    # --- PARSING DNF ---
    # Cerca "DNF" seguito dal numero pettorale e il nome
    dnf_matches = re.findall(r'DNF\s*(\d+)\s+([A-Za-zÀ-ÿ\s\|\-\.\']+?)(?=DNF|\d{1,3}\s+\d{1,3}|$)', text)
    for d_bib, d_name in dnf_matches:
        parsed_data.append({
            "rank": "DNF",
            "bib": d_bib,
            "full_info": d_name.strip(),
            "gap": "-"
        })
            
    return parsed_data

# --- INTERFACCIA ---
st.title("🏆 Parser Risultati Mobile v4")

try:
    # Caricamento gare
    races = supabase.table("dim_race").select("id_race, name").execute().data
    race_options = {r['name']: r['id_race'] for r in races}
    sel_race = st.selectbox("Gara:", list(race_options.keys()))
    
    input_text = st.text_area("Incolla qui il testo (anche se tutto attaccato):", height=300)

    if input_text and st.button("Elabora Risultati 🧪"):
        data = parse_ultra_compact(input_text)
        if data:
            st.session_state.results_df = pd.DataFrame(data)
            st.success(f"Trovati {len(data)} atleti!")
        else:
            st.error("Nessun dato trovato. Prova a copiare una porzione più pulita.")

    if 'results_df' in st.session_state:
        # L'EDITOR è fondamentale qui per correggere i "residui" del parsing
        edited_df = st.data_editor(
            st.session_state.results_df,
            num_rows="dynamic",
            use_container_width=True
        )
        
        if st.button("SALVA SU DATABASE 🚀"):
            final_data = edited_df.to_dict(orient='records')
            for row in final_data:
                row['id_race'] = race_options[sel_race]
            
            supabase.table("stg_results").insert(final_data).execute()
            st.success("Salvataggio completato!")
            del st.session_state.results_df

except Exception as e:
    st.error(f"Errore: {e}")
