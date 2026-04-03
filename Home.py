# --- DASHBOARD (Utente loggato) ---
check_auth()
render_sidebar()

from datetime import datetime

logo = "https://github.com/Jericho1987/virtua_cycling_3.0/blob/main/logo_pwa.png?raw=true"
st.markdown(f"""
    <div style="background-color: #1e1e1e; padding: 10px 18px; border-radius: 12px; border-left: 5px solid #ff4b4b; margin-bottom: 15px; display: flex; align-items: center;">
        <img src="{logo}" style="width: 50px; margin-right: 18px;">
        <div style="flex-grow: 1;">
            <h3 style="margin: 0; font-size: 1.5rem; color: white; line-height: 1.1;">👋 Ciao, {st.session_state.nome_user_loggato}!</h3>
            <p style="margin: 2px 0 0 0; color: #b0b0b0; font-size: 0.85rem;">Bentornato in gruppo. Ecco i tuoi aggiornamenti.</p>
        </div>
    </div>
""", unsafe_allow_html=True)

try:
    p_d = supabase.table("view_stage_to_pick").select("*").execute().data
    c_d = supabase.table("view_stage_current").select("*").execute().data
    l_d = supabase.table("view_stage_last_results").select("*").execute().data
    u_d = supabase.table("view_races_upcoming").select("*").execute().data

    c_tl, c_tr = st.columns(2, gap="medium")
    
    with c_tl:
        st.subheader("✍️ Pick da fare")
        with st.container(border=True):
            if p_d:
                for p in p_d:
                    # Logica nome: se id_type_race è 3, nascondiamo (Tappa)
                    nome_mostrato = p['race_name'] if p.get('id_type_race') == 3 else f"{p['race_name']} (T{p['stage']})"
                    
                    # Logica Countdown "Fighetto"
                    # Assumiamo che nella view ci sia un campo 'deadline' o 'start_time'
                    # In mancanza, usiamo un placeholder stilizzato o cerchiamo il campo orario
                    deadline_str = p.get('start_time') # Verifica se il campo si chiama così nella tua view
                    countdown_html = ""
                    
                    if deadline_str:
                        try:
                            # Pulizia stringa per formati diversi di Supabase/Postgres
                            deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
                            now = datetime.now(deadline.tzinfo)
                            diff = deadline - now
                            
                            if diff.total_seconds() > 0:
                                giorni = diff.days
                                ore = diff.seconds // 3600
                                minuti = (diff.seconds // 60) % 60
                                
                                if giorni > 0:
                                    color = "#FFA500" # Arancione se mancano giorni
                                    testo = f"{giorni}d {ore}h"
                                else:
                                    color = "#FF4B4B" # Rosso se mancano poche ore
                                    testo = f"{ore}h {minuti}m"
                                
                                countdown_html = f"""<span style="background-color: {color}; color: white; padding: 2px 8px; border-radius: 20px; font-size: 0.7rem; font-weight: bold; margin-left: 10px;">⏳ {testo}</span>"""
                        except: pass

                    col_info, col_btn = st.columns([0.7, 0.3])
                    col_info.markdown(f"**{nome_mostrato}** {countdown_html}", unsafe_allow_html=True)
                    
                    if col_btn.button("Vai", key=f"p_{p['id_stage']}", use_container_width=True):
                        st.session_state.gara_selezionata_id = p['id_race']
                        st.session_state.tappa_selezionata_id = p['id_stage']
                        st.switch_page("pages/01_Inserimento.py")
                    st.write("---") # Separatore tra gare
            else: 
                st.success("Non ci sono gare aperte al momento ✅")

    with c_tr:
        st.subheader("🏆 Ultimi risultati")
        with st.container(border=True):
            if l_d:
                for l in l_d: st.write(f"✅ {l['race_name']}")
                st.button("CLASSIFICHE 🏆", use_container_width=True, type="primary", on_click=lambda: st.switch_page("pages/02_Classifiche.py"))
            else: st.info("Nessuno.")

    # ... (restante codice per "In corso" e "Prossime gare" rimane invariato)
