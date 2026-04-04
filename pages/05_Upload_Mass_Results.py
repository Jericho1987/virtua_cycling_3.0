import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar, restore_session_from_cookie
import re
import pandas as pd

st.set_page_config(page_title="Upload Mass Results", layout="wide", page_icon="🏆")

# --- INIZIALIZZAZIONE SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- RIPRISTINO SESSIONE ---
restore_session_from_cookie(supabase)

# --- CONTROLLO AUTH ---
if not st.session_state.get("id_user_loggato"):
    st.warning("Sessione scaduta. Torna alla Home.")
    st.switch_page("Home.py")
    st.stop()

check_auth()
render_sidebar()

# --- FUNZIONE PARSING PC (INVARIATA) ---
def parse_results_v4(text):
    lines = text.split('\n')
    parsed_data = []
    current_entry = None
    last_time = "0:00:00"
    for line in lines:
        line = line.strip()
        if not line: continue
        new_rider_match = re.match(r'^(\d+)\s+(\d+)\s+(.*)', line)
        dnf_match = re.match(r'^DNF\s*(\d+)\s+(.*)', line, re.IGNORECASE)
        if new_rider_match:
            if current_entry: parsed_data.append(current_entry)
            rank = new_rider_match.group(1)
            bib = new_rider_match.group(2)
            rest = new_rider_match.group(3)
            initial_gap = "0:00:00" if rank == "1" else "st"
            current_entry = {"rank": rank, "bib": bib, "full_info": rest, "gap": initial_gap}
        elif dnf_match:
            if current_entry: parsed_data.append(current_entry)
            bib_dnf = dnf_match.group(1)
            rest_dnf = dnf_match.group(2)
            current_entry = {"rank": "DNF", "bib": bib_dnf, "full_info": rest_dnf, "gap": ""}
        elif current_entry:
            time_match = re.search(r'(,,|\d{1,2}:\d{2}(?::\d{2})?)$', line)
            if time_match and current_entry["rank"] != "DNF":
                gap = time_match.group(1)
                if current_entry["rank"] == "1": current_entry["gap"] = "0:00:00"
                elif gap == ",,": current_entry["gap"] = last_time
                else:
                    current_entry["gap"] = gap
                    last_time = gap
                clean_extra = re.sub(r'\d+\s+\d+\s+(,,|\d{1,2}:\d{2}(?::\d{2})?)$', '', line).strip()
                current_entry["full_info"] += " " + clean_extra
            else:
                if not re.match(r'^\d+\s+\d+$', line):
                    current_entry["full_info"] += " " + line
    if current_entry: parsed_data.append(current_entry)
    return parsed_data

# --- FUNZIONE PARSING MOBILE (LOGICA A 3 RIGHE) ---
def parse_results_mobile(text):
    # Rimuoviamo righe vuote e puliamo gli spazi
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    parsed_data = []
    last_time = "0:00:00"

    # Iteriamo saltando di 3 righe alla volta
    for i in range(0, len(lines), 3):
        try:
            # RIGA 1: Rank e Bib (es: "1 51 Ganna Filippo" oppure "DNF 12 Nome")
            line1 = lines[i]
            # RIGA 2: Team (es: "INEOS Grenadiers")
            line2 = lines[i+1] if (i+1) < len(lines) else ""
            # RIGA 3: Dati tecnici e Tempo (es: "400 22 3:48:27")
            line3 = lines[i+2] if (i+2) < len(lines) else ""

            # Estrazione Rank e Bib dalla riga 1
            rank = ""
            bib = ""
            full_info = ""
            
            if line1.upper().startswith("DNF"):
                m = re.match(r'^DNF\s*(\d+)\s*(.*)', line1, re.IGNORECASE)
                rank = "DNF"
                bib = m.group(1) if m else ""
                full_info = m.group(2) if m else line1
            else:
                m = re.match(r'^(\d+)\s+(\d+)\s+(.*)', line1)
                if m:
                    rank = m.group(1)
                    bib = m.group(2)
                    full_info = m.group(3)
                else:
                    continue # Se la prima riga non ha rank/bib, salta il blocco

            # Aggiungiamo la riga 2 (Team) alla full_info
            full_info += f" {line2}"

            # Estrazione Tempo dalla riga 3 (cerchiamo l'ultimo elemento a destra)
            gap = ""
            time_match = re.search(r'(,,|\d{1,2}:\d{2}(?::\d{2})?)$', line3)
            
            if rank == "DNF":
                gap = ""
            elif time_match:
                extracted_gap = time_match.group(1)
                if rank == "1":
                    gap = "0:00:00"
                elif extracted_gap == ",,":
                    gap = last_time
                else:
                    gap = extracted_gap
                    last_time = extracted_gap
                
                # Aggiungiamo i dati tecnici (es. 400 225) alla full_info
                tech_data = re.sub(r'(,,|\d{1,2}:\d{2}(?::\d{2})?)$', '', line3).strip()
                if tech_data:
                    full_info += f" {tech_data}"
            else:
                gap = "st" # Fallback se non trova il tempo

            parsed_data.append({
                "rank": rank,
                "bib": bib,
                "full_info": full_info.strip(),
                "gap": gap
            })
        except Exception as e:
            continue # Salta il blocco in caso di errore di formato

    return parsed_data

# --- INTERFACCIA STREAMLIT ---
st.title("🏆 Caricamento Risultati in Staging")

try:
    races = supabase.table("dim_race").select("id_race, name").execute().data
    race_options = {r['name']: r['id_race'] for r in races}
    c1, c2 = st.columns(2)
    with c1:
        sel_race_name = st.selectbox("Seleziona la gara:", list(race_options.keys()))
        id_race = race_options[sel_race_name]
    stages = supabase.table("dim_race_stage").select("id_stage, id_stage_number").eq("id_race", id_race).order("id_stage_number").execute().data
    stage_options = {f"Tappa {s['id_stage_number']}": s['id_stage'] for s in stages}
    with c2:
        sel_stage_name = st.selectbox("Seleziona la tappa:", list(stage_options.keys()))
        id_stage = stage_options[sel_stage_name]

    st.divider()
    tab_pc, tab_mobile = st.tabs(["💻 Incolla da PC/iOS", "📱 Incolla da Android solo FIREFOX"])

    with tab_pc:
        input_pc = st.text_area("Formato riga singola:", height=300, key="pc_in")
        if st.button("Analizza PC 🔍"):
            results = parse_results_v4(input_pc)
            st.session_state.results_df = pd.DataFrame(results)
            st.session_state.results_id_stage = id_stage
            st.session_state.results_id_race = id_race

    with tab_mobile:
        input_mobile = st.text_area("Formato 3 righe (Mobile):", height=300, key="mob_in")
        if st.button("Analizza Mobile 📱"):
            results = parse_results_mobile(input_mobile)
            st.session_state.results_df = pd.DataFrame(results)
            st.session_state.results_id_stage = id_stage
            st.session_state.results_id_race = id_race

    if 'results_df' in st.session_state:
        st.divider()
        df_preview = st.session_state.results_df.copy()
        df_preview['full_info'] = df_preview['full_info'].str.replace(r'\s+', ' ', regex=True)
        st.table(df_preview)
        
        if st.button("SALVA IN STAGING 🚀", type="primary"):
            final_records = [{"id_race": str(id_race), "id_stage": str(id_stage), "rank": str(row['rank']), "bib": str(row['bib']), "full_info": str(row['full_info']), "gap": str(row['gap'])} for _, row in df_preview.iterrows()]
            try:
                supabase.table("stg_result").delete().eq("id_stage", id_stage).execute()
                supabase.table("stg_result").insert(final_records).execute()
                st.success("Salvataggio completato!")
                st.balloons()
                del st.session_state.results_df
            except Exception as e:
                st.error(f"Errore: {e}")

except Exception as e:
    st.error(f"Errore generale: {e}")
