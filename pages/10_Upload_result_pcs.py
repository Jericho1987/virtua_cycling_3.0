import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar, restore_session_from_cookie
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="PCS Scraper Results", layout="wide", page_icon="🌐")

# 2. INIZIALIZZAZIONE SUPABASE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# 3. RIPRISTINO SESSIONE E AUTH
restore_session_from_cookie(supabase)

if not st.session_state.get("id_user_loggato"):
    st.warning("Sessione scaduta. Torna alla Home.")
    st.switch_page("Home.py")
    st.stop()

check_auth()
render_sidebar()

# 4. FUNZIONE SCRAPING AVANZATA (Piano A)
def scrape_pcs_to_list(url_pcs):
    try:
        # Camuffamento browser
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

        # Headers per simulare un utente reale ed evitare il 403
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.procyclingstats.com/',
            'Connection': 'keep-alive'
        }

        response = scraper.get(url_pcs, headers=headers, timeout=20)

        if response.status_code == 403:
            return None, "Errore 403: Cloudflare ha bloccato il server. Usa il Piano B (Pagina 05)."
        
        if response.status_code != 200:
            return None, f"Errore PCS: {response.status_code}"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='results')
        
        if not table:
            return None, "Tabella non trovata. Controlla che l'URL sia corretto e la gara conclusa."

        parsed_data = []
        rows = table.find_all('tr')
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 10: 
                continue
            
            rank = cols[0].text.strip()
            # Accettiamo Rank numerici o sigle (DNF, DNS, etc.)
            if not rank or (not rank.isdigit() and rank not in ['DNF', 'DNS', 'OTL', 'DSQ', 'OTL']):
                continue

            bib = cols[1].text.strip()
            
            # Estrazione pulita del Rider (evita lo span del team)
            rider_link = cols[5].find('a')
            rider_name = rider_link.text.strip() if rider_link else cols[5].text.strip()
            
            # Team dalla colonna dedicata
            team = cols[6].text.strip()

            # Logica Tempo/Gap
            if rank == "1":
                gap = "0:00:00"
            elif not rank.isdigit():
                gap = rank # Scrive DNF, DNS ecc. nella colonna gap
            else:
                time_cell = cols[9]
                # Pulizia span nascosti (evita il raddoppio dei tempi 0:110:11)
                hidden = time_cell.find('span', class_='hide')
                if hidden: 
                    hidden.decompose()
                
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
        return None, f"Errore imprevisto: {str(e)}"

# 5. INTERFACCIA UTENTE
st.title("🌐 PCS Direct Scraper")
st.markdown("### Piano A: Estrazione Automatica")
st.info("Inserisci l'URL della gara conclusa per popolare automaticamente lo staging.")

try:
    # Selezione Gara e Tappa da Supabase
    races = supabase.table("dim_race").select("id_race, name").execute().data
    race_options = {r['name']: r['id_race'] for r in races}
    
    col_race, col_stage = st.columns(2)
    
    with col_race:
        sel_race_name = st.selectbox("Seleziona la gara:", list(race_options.keys()))
        id_race = race_options[sel_race_name]
    
    stages = supabase.table("dim_race_stage").select("id_stage, id_stage_number").eq("id_race", id_race).order("id_stage_number").execute().data
    stage_options = {f"Tappa {s['id_stage_number']}": s['id_stage'] for s in stages}
    
    with col_stage:
        sel_stage_name = st.selectbox("Seleziona la tappa:", list(stage_options.keys()))
        id_stage = stage_options[sel_stage_name]

    st.divider()

    # Input URL e Tasto Azione
    url_input = st.text_input("Incolla URL PCS:", placeholder="https://www.procyclingstats.com/race/...")
    
    if st.button("🚀 Estrai Risultati", type="secondary", use_container_width=True):
        if url_input:
            with st.spinner("Interrogando ProCyclingStats..."):
                data, err = scrape_pcs_to_list(url_input)
                if err:
                    st.error(f"Attenzione: {err}")
                elif not data:
                    st.warning("Nessun dato estratto. Verifica l'URL.")
                else:
                    st.session_state.pcs_results_df = pd.DataFrame(data)
                    st.success(f"Estratti {len(data)} corridori!")
        else:
            st.warning("Inserisci un URL prima di continuare.")

    # 6. ANTEPRIMA E SALVATAGGIO
    if 'pcs_results_df' in st.session_state:
        st.divider()
        st.subheader("Anteprima Dati Estratti")
        
        # Mostriamo la tabella pulita
        st.table(st.session_state.pcs_results_df)
        
        if st.button("SALVA IN STAGING 🚀", type="primary", use_container_width=True):
            # Preparazione record per Supabase
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
                # 1. Pulizia staging esistente per questa tappa
                supabase.table("stg_result").delete().eq("id_stage", id_stage).execute()
                
                # 2. Inserimento nuovi dati
                if final_records:
                    supabase.table("stg_result").insert(final_records).execute()
                    st.success(f"Successo! {len(final_records)} righe salvate in staging.")
                    st.balloons()
                    # Puliamo la sessione per evitare salvataggi doppi accidentali
                    del st.session_state.pcs_results_df
            except Exception as e:
                st.error(f"Errore durante il salvataggio su Supabase: {e}")

except Exception as e:
    st.error(f"Errore nell'inizializzazione della pagina: {e}")
