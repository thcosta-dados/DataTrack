import streamlit as st
import pandas as pd
from database import get_unmapped_skills_ranking, get_recent_jobs_for_unmapped_skill
from theme import apply_theme, theme_toggle

# 1. Configuração da página
st.set_page_config(
    page_title="DataTrack — Novas Skills",
    page_icon="🧠",
    layout="wide"
)

# 2. Aplica o Tema Operacional
apply_theme()

# Cabeçalho Principal
st.markdown("<h1>🧠 Monitoramento de Novas Skills & Governança</h1>", unsafe_allow_html=True)
st.markdown("<p class='subheader' style='margin-bottom: 25px;'>Termos não mapeados identificados nas descrições das vagas para calibração de taxonomia</p>", unsafe_allow_html=True)

# 3. Informações didáticas de governança
st.markdown(
    """
    > **Estratégia de Governança de Dados (Skills Monitoring):**
    > O classificador de vagas utiliza um dicionário estático de termos conhecidos. Caso novas tecnologias ou siglas surjam no mercado,
    > a pipeline as captura automaticamente por meio de regras sintáticas (palavras capitalizadas não mapeadas) e as armazena no banco de dados.
    > Esta página permite que o time de engenharia de dados audite e adicione termos valiosos ao dicionário.
    """
)

# 4. Carrega os dados de skills não mapeadas
with st.spinner("Carregando ranking de termos não mapeados..."):
    df_ranking = get_unmapped_skills_ranking(limit=50)

# 5. Renderização
col_left, col_right = st.columns([1, 1])

event = None

with col_left:
    st.subheader("Sugestões de Novas Skills")
    st.markdown("<p class='subheader' style='font-size: 0.9em; margin-bottom: 10px;'>Selecione um termo na tabela para inspecionar em quais vagas ele foi citado.</p>", unsafe_allow_html=True)
    
    if df_ranking is not None and not df_ranking.empty:
        # Formata datas
        display_ranking = df_ranking.copy()
        display_ranking["vista_pela_ultima_vez"] = pd.to_datetime(display_ranking["vista_pela_ultima_vez"]).dt.strftime('%d/%m/%Y')
        display_ranking.columns = ["Tecnologia / Termo", "Ocorrências", "Última Aparição"]
        
        event = st.dataframe(
            display_ranking,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun"
        )
    else:
        st.info("Nenhum termo não mapeado foi coletado até o momento.")

with col_right:
    st.subheader("🔍 Contexto Semântico do Termo")
    
    if df_ranking is not None and not df_ranking.empty and event and event.get("selection") and event["selection"].get("rows"):
        selected_row_idx = event["selection"]["rows"][0]
        term_selecionado = df_ranking.iloc[selected_row_idx]["skill_sugerida"]
        
        st.markdown(f"Exemplos de vagas reais contendo o termo: `<span style='color:#00F2FE; font-weight:bold;'>{term_selecionado}</span>`", unsafe_allow_html=True)
        
        with st.spinner("Buscando exemplos de vagas..."):
            df_examples = get_recent_jobs_for_unmapped_skill(term_selecionado)
            
        if df_examples is not None and not df_examples.empty:
            for _, r in df_examples.iterrows():
                st.markdown(
                    f"""
                    <div style="background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); padding: 10px; border-radius: 6px; margin-bottom: 8px;">
                        <b>{r['title']}</b><br>
                        <small style="color: #64748B;">Empresa: {r['company']}</small><br>
                        <a href="{r['url']}" target="_blank" style="color: #00F2FE; font-size: 0.85em; text-decoration: none;">🔗 Ver Vaga Original</a>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("Nenhum exemplo de vaga disponível.")
    else:
        st.info("Selecione um termo na tabela ao lado para ver o contexto e as vagas de onde ele foi extraído.")

# Toggle de Aparência no Sidebar
theme_toggle()
