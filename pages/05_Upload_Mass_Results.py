import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar, restore_session_from_cookie
import re
import pandas as pd

# ... (Configurazione iniziale e Auth rimangono invariati) ...

def parse_results_mobile(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    parsed_data = []
    current_entry = None
    last_time = "0:00:00"
    
    # Regex per i vari pezzi
    rank_bib_re = r'^(\d+)\s+(\d+)'
    time_re = r'(,,|\d{1,2}:\d{2}(?::\d{2})?)$'
    dnf_re = r'^DNF\s*(\d+)'

    for line in lines:
        # 1. Controllo se inizia un nuovo corridore (Rank + Bib)
        new_rider = re.match(rank_bib_re, line)
        dnf_rider = re.match(dnf_re, line, re.IGNORECASE)

        if new_rider or dnf_rider:
            if current_entry:
                parsed_data.append(current_entry)
            
            if new_rider:
                rank, bib = new_rider.groups()
                # Rimuoviamo rank e bib dal resto della riga se c'è altro
                rest = line[new_rider.end():].strip()
                current_entry = {"rank": rank, "bib": bib, "full_info": rest, "gap": "st"}
            else:
                bib_dnf = dnf_rider.group(1)
                rest_dnf = line[dnf_rider.end():].strip()
                current_entry = {"rank": "DNF", "bib": bib_dnf, "full_info": rest_dnf, "gap": ""}
            continue

        if current_entry:
            # 2. Cerchiamo se in questa riga c'è il tempo/gap
            time_match = re.search(time_re, line)
            if time_match and current_entry["rank"] != "DNF":
                gap = time_match.group(1)
                if current_entry["rank"] == "1":
                    current_entry["gap"] = "0:00:00"
                elif gap == ",,":
                    current_entry["gap"] = last_time
                else:
                    current_entry["gap"] = gap
                    last_time = gap
                
                # Rimuoviamo il tempo dal testo e aggiungiamo il resto a full_info
                clean_line = re.sub(time_re, '', line).strip()
                if clean_line:
                    current_entry["full_info"] += " " + clean_line
            else:
                # 3. Se non è un tempo, è un pezzo di info (nome squadra, ecc.)
                current_entry["full_info"] += " " + line

    if current_entry:
        parsed_data.append(current_entry)
    return parsed_data

# --- INTERFACCIA ---
st.title("🏆 Caricamento Risultati")

# ... (Codice selezione Race e Stage rimane invariato) ...

st.divider()

# CREAZIONE DEI TAB
tab_pc, tab_mobile = st.tabs(["💻 Incolla da PC", "📱 Incolla da Mobile"])

with tab_pc:
    input_pc = st.text_area("Formato standard (una riga per atleta):", height=300, key="pc_input")
    if st.button("Analizza PC 🔍"):
        if input_pc:
            # Usa la tua funzione originale parse_results_v4
            results = parse_results_v4(input_pc)
            st.session_state.results_df = pd.DataFrame(results)
            st.session_state.results_id_stage = id_stage
            st.session_state.results_id_race = id_race

with tab_mobile:
    input_mobile = st.text_area("Formato multiriga (copia da smartphone):", height=300, key="mobile_input")
    if st.button("Analizza Mobile 📱"):
        if input_mobile:
            results = parse_results_mobile(input_mobile)
            st.session_state.results_df = pd.DataFrame(results)
            st.session_state.results_id_stage = id_stage
            st.session_state.results_id_race = id_race

# --- ANTEPRIMA E SALVATAGGIO ---
# (Il resto del codice per visualizzare la tabella e salvare su Supabase rimane uguale)
