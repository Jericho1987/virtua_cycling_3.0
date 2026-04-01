import streamlit as st
from supabase import create_client
import re
import pandas as pd

# 1. Configurazione Pagina
st.set_page_config(page_title="Upload Mass Results", layout="wide", page_icon="🏆")

# 2. Inizializzazione Client Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def parse_ultra_compact(text):
    # Trasformiamo tutto in una riga singola per gestire i copia-incolla "sporchi" da mobile
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    
    parsed_data = []
    last_gap = "0:00:00"
    
    # Identifichiamo tutte le coppie "Posizione Pettorale" (es: "1 51", "2 25", ecc.)
    # Questo ci serve come ancora per dividere il blocco di testo atleta per atleta
    positions = re.findall(r'\b\d{1,3}\s+\d{1,3}\b', text)
    
    for i in range(len(positions)):
        start_val = positions[i]
        # Definiamo dove finisce il blocco corrente (all'inizio della posizione successiva o alla fine del testo)
        end_val = positions[i+1] if i+1 < len(positions) else "$"
        
        # Estraiamo il blocco di testo relativo a un singolo corridore
        pattern = f"{re.escape(start_val)}(.*?)(?={re.escape(end_val) if end_val != '$' else '$'})"
        content_match = re.search(pattern, text)
        
        if content_match:
            rank, bib = start_val.split()
            info_block = content_match.group(1).strip()
            
            # --- RICERCA DEL GAP (TEMPO) ---
            # Cerchiamo formati tipo 0:11, 3:48:27 o le virgolette ,,
            gap_match = re.search(r'(\d{1,2}:\d{2}(?::\d{2})?|,,)', info_block)
            
            if gap_match:
                current_gap = gap_match.group(1)
                if current_gap == ",,":
                    gap = last_gap
                else:
                    gap = current_gap
                    last_gap = current_gap
            else:
                # Se non c'è tempo, assumiamo sia lo stesso del precedente (st) o 0 per il primo
                gap = "0:00:00" if rank == "1" else "st"
            
            # --- PULIZIA INFO (NOME + TEAM) ---
            # 1. Togliamo il tempo o i simboli ,,
            clean_info = re.sub(r'(\d{1,2}:\d{2}(?::\d{2})?|,,)', '', info_block)
            # 2. Togliamo i numeri sparsi finali (spesso punti UCI come "8 5" o "4 5")
            clean_info = re.sub(r'\s\d+\s+\d+\s*$', '', clean_info).strip()
            # 3. Rimuoviamo eventuali altri numeri residui isolati alla fine
            clean_info = re.sub(r'\s\d+$', '', clean_info).strip()
            
            parsed_data.append({
                "rank": rank,
                "bib": bib,
                "full_info": clean_info,
                "gap": gap
            })

    # --- PARSING DNF (RITIRATI) ---
    # Cerchiamo DNF seguito da numero e nome
    dnf_matches = re.findall(r'DNF\s*(\d+)\s+([A-Za-zÀ-ÿ\s\|\-\.\']+?)(?=DNF|\d{1,3}\s+\d{1,3}|$)', text)
    for d_bib, d_name in dnf_matches:
        parsed_data.append({
            "rank": "DNF",
            "bib": d_bib,
            "full_info": d_name.strip(),
            "gap": "-"
        })
            
    return parsed_data

# --- INTERFACCIA UTENTE ---
st.title("🏆 Parser Risultati Mobile v5")
st.markdown("Copia l'intera tabella dal sito e incollala qui sotto. Il sistema estrarrà Rank, Pettorale, Nome e Distacchi.")

try:
    # Caricamento dinamico delle gare dal DB
    races_query = supabase.table("dim_race").select("id_race, name").execute()
    races = races_query.data
    race_options = {r['name']: r['id_race'] for r in races}
    
    col_a, col_b = st.columns([2, 1])
    with col_a:
        sel_race_name = st.selectbox("Seleziona Gara/Tappa di riferimento:", list(race_options.keys()))
    
    input_text = st.text_area("Incolla qui il testo:", height=300, placeholder="Incolla qui il blocco di testo da ProCyclingStats o siti simili...")

    if input_text and st.button("Elabora Risultati 🧪", use_container_width=True):
        data = parse_ultra_compact(input_text)
        if data:
            st.session_state.results_df = pd.DataFrame(data)
            st.success(f"Analisi completata! Trovati {len(data)} atleti.")
        else:
            st.error("Nessun dato trovato. Assicurati di aver copiato la parte con Rank e Pettorale.")

    if 'results_df' in st.session_state:
        st.divider()
        st.subheader("Verifica e correggi i dati")
        st.info("Puoi modificare le celle direttamente se vedi errori di pulizia del nome.")
        
        # Editor per correzioni manuali dell'ultimo secondo
        edited_df = st.data_editor(
            st.session_state.results_df,
            num_rows="dynamic",
            use_container_width=True,
            key="main_data_editor"
        )
        
        if st.button("SALVA DEFINITIVAMENTE SU DATABASE 🚀", type="primary", use_container_width=True):
            final_data = edited_df.to_dict(orient='records')
            # Aggiungiamo l'ID gara selezionato a ogni riga
            selected_id = race_options[sel_race_name]
            for row in final_data:
                row['id_race'] = selected_id
            
            # Invio a Supabase
            supabase.table("stg_results").insert(final_data).execute()
            
            st.balloons()
            st.success(f"Salvati correttamente {len(final_data)} risultati per: {sel_race_name}")
            # Pulizia per evitare doppi invii
            del st.session_state.results_df

except Exception as e:
    st.error(f"Errore durante l'operazione: {e}")
