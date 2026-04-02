import streamlit as st
from supabase import create_client
from auth_utils import check_auth, render_sidebar # <--- 1. AGGIUNGI QUESTA RIGA

import re
import pandas as pd

# 1. Configurazione e Connessione
st.set_page_config(page_title="Upload Startlist", layout="wide", page_icon="📑")

# --- PROTEZIONE E SIDEBAR ---
check_auth()      # <--- 2. AGGIUNGI QUESTA (Blocca i non loggati e mette il CSS)
render_sidebar()  # <--- 3. AGGIUNGI QUESTA (Disegna i link e l'area utente)


url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- FUNZIONE DI PARSING DEL TESTO ---
def parse_startlist_text(text):
    """
    Analizza il testo tipo: 11. TVL VAN AERT Wout BEL19940915
    """
    lines = text.strip().split('\n')
    parsed_data = []
    
    for line in lines:
        if not line.strip(): continue
        
        try:
            # Estraggo Bib (es. 11)
            bib_match = re.search(r'^(\d+)\.', line)
            bib = bib_match.group(1) if bib_match else ""
            
            # Rimuovo il bib e il punto per pulire la riga
            clean_line = re.sub(r'^\d+\.\s+', '', line)
            parts = clean_line.split()
            
            if len(parts) < 3: continue # Salta righe troppo corte
            
            team = parts[0] 
            ucicode = parts[-1] 
            
            # Gestione Cognome (MAIUSCOLO) e Nome (Mix)
            name_parts = parts[1:-1]
            surnames = [p for p in name_parts if p.isupper()]
            names = [p for p in name_parts if not p.isupper()]
            
            surname_str = " ".join(surnames)
            name_str = " ".join(names)
            
            parsed_data.append({
                "bib": bib,
                "team": team,
                "surname": surname_str,
                "name": name_str,
                "ucicode": ucicode
            })
        except Exception as e:
            st.error(f"Errore nel processare la riga: {line} -> {e}")
            
    return parsed_data

# --- INTERFACCIA ---
st.title("📑 Caricamento Starting List")

try:
    # 1. Selezione Gara (Colonna 'name')
    races_query = supabase.table("dim_race").select("id_race, name").execute()
    races = races_query.data
    
    if races:
        race_options = {r['name']: r['id_race'] for r in races}
        selected_race_name = st.selectbox("Seleziona la gara per cui caricare i dati:", list(race_options.keys()))
        id_selected_race = race_options[selected_race_name]
        
        st.divider()

        # 2. Visualizzazione Startlist Attuale (View)
        st.subheader(f"Lista attuale nel sistema: {selected_race_name}")
        current_sl = supabase.table("view_start_list_display").select("rider_name, uci_code, bib").eq("id_race", id_selected_race).execute().data

        if current_sl:
            st.dataframe(pd.DataFrame(current_sl), use_container_width=True)
        else:
            st.warning("⚠️ Nessuna starting list presente per questa gara.")

        st.divider()

        # 3. Input Testo Massivo
        st.subheader("📥 Inserimento Massivo")
        st.caption("Copia e incolla la lista qui sotto. Il sistema riconoscerà Bib, Team, Cognome, Nome e UCI Code.")
        input_text = st.text_area("Pasto qui il testo della startlist:", height=250, placeholder="11. TVL VAN AERT Wout BEL19940915...")

        if input_text:
            if st.button("Analizza Dati 🔍", use_container_width=True):
                data_to_preview = parse_startlist_text(input_text)
                if data_to_preview:
                    st.session_state.preview_df = pd.DataFrame(data_to_preview)
                    # La colonna 'race' serve alla stg_start_list per identificare la gara
                    st.session_state.preview_df['race'] = selected_race_name
                    st.success(f"Analisi completata: trovati {len(data_to_preview)} corridori.")

        # 4. Tabella di Preview e Salvataggio Finale
        if 'preview_df' in st.session_state:
            st.markdown("### Anteprima dei dati pronti per l'invio")
            st.dataframe(st.session_state.preview_df, use_container_width=True)
            
            col_save, col_clear = st.columns([3, 1])
            
            if col_save.button("CONFERMA E CARICA NEL DATABASE 🚀", type="primary", use_container_width=True):
                records = st.session_state.preview_df.to_dict(orient='records')
                try:
                    # STEP A: Inserimento in Staging
                    supabase.table("stg_start_list").insert(records).execute()
                    st.info("📦 Step 1/2: Dati caricati in staging...")

                    # STEP B: Esecuzione Function SQL
                    supabase.rpc('load_start_list', {}).execute()
                    
                    st.success(f"✅ Step 2/2: Funzione load_start_list() eseguita! {len(records)} corridori aggiornati.")
                    
                    # Pulizia della sessione dopo il successo
                    del st.session_state.preview_df
                    st.balloons()
                    
                    if st.button("Aggiorna Tabella in alto 🔄"):
                        st.rerun()

                except Exception as e:
                    st.error(f"❌ Errore durante il processo: {e}")
            
            if col_clear.button("Annulla 🗑️", use_container_width=True):
                del st.session_state.preview_df
                st.rerun()

    else:
        st.error("Nessuna gara trovata nella tabella dim_race.")

except Exception as e:
    st.error(f"Errore critico: {e}")
