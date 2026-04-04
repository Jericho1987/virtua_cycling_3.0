import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar, restore_session_from_cookie
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(page_title="PCS Scraper Results", layout="wide", page_icon="🌐")

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

# --- FUNZIONE SCRAPING (ADATTATA PER SUPABASE) ---
def scrape_pcs_to_list(url_pcs):
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url_pcs, timeout=10)
        if response.status_code != 200:
            return None, f"Errore PCS: {response.status_code}"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='results')
        if not table:
            return None, "Tabella non trovata."

        parsed_data = []
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 10: continue
            
            rank = cols[0].text.strip()
            if not rank or (not rank.isdigit() and rank not in ['DNF', 'DNS', 'OTL', 'DSQ']):
                continue

            bib = cols[1].text.strip()
            rider_link = cols[5].find('a')
            rider_name = rider_link.text.strip() if rider_link else cols[5].text.strip()
            team = cols[6].text.strip()

            # Logica Tempo/Gap
            if rank == "1":
                gap = "0:00:00"
            elif not rank.isdigit():
                gap = rank
            else:
                time_cell = cols[9]
                hidden = time_cell.find('span', class_='hide')
                if hidden: hidden.decompose()
                time_font = time_cell.find('font')
                if time_font and ",," in time_font.text:
                    gap = ",,"
                else:
                    val = time_cell.text.strip().replace('+', '').strip()
                    gap = val if val else ",,"

            parsed_data.append({
                "rank": rank,
                "bib": bib,
                "full_info": f"{rider_name} {team}",
                "gap": gap
            })
        return parsed_data, None
    except Exception as e:
        return None, str(e)

# --- INTERFACCIA ---
st.title("🌐 PCS Direct Scraper")
st.info("Piano A: Inserisci l'URL di ProCyclingStats per estrarre i dati automaticamente.")

try:
    # Selezione Gara/Tappa (identica alla pagina 05)
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

    # Input URL
    url_input = st.text_input("URL Risultati PCS:", placeholder="https://www.procyclingstats.com/race/...")
    
    if st.button("Estrai Dati 🚀"):
        if url_input:
            with st.spinner("Scraping in corso..."):
                data, err = scrape_pcs_to_list(url_input)
                if err:
                    st.error(f"Errore: {err}")
                else:
                    st.session_state.pcs_results_df = pd.DataFrame(data)
                    st.session_state.pcs_id_stage = id_stage
                    st.success("Dati estratti correttamente!")
        else:
            st.warning("Inserisci un URL valido.")

    # Preview e Salvataggio (stile pagina 05)
    if 'pcs_results_df' in st.session_state:
        st.divider()
        st.table(st.session_state.pcs_results_df)
        
        if st.button("SALVA IN STAGING 🚀", type="primary"):
            final_records = [
                {
                    "id_race": str(id_race), 
                    "id_stage": str(id_stage), 
                    "rank": str(row['rank']), 
                    "bib": str(row['bib']), 
                    "full_info": str(row['full_info']), 
                    "gap": str(row['gap'])
                } for _, row in st.session_state.pcs_results_df.iterrows()
            ]
            try:
                supabase.table("stg_result").delete().eq("id_stage", id_stage).execute()
                supabase.table("stg_result").insert(final_records).execute()
                st.success("Salvataggio completato!")
                st.balloons()
                del st.session_state.pcs_results_df
            except Exception as e:
                st.error(f"Errore salvataggio: {e}")

except Exception as e:
    st.error(f"Errore generale: {e}")
