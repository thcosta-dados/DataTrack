import streamlit as st
import pandas as pd
from database import get_filter_options, get_vagas_filtradas
from theme import apply_theme, theme_toggle

# 1. Configuração da página (deve ser o primeiro comando Streamlit)
st.set_page_config(
    page_title="DataTrack — Inteligência de Vagas de Dados",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Aplica o Tema e importa CSS customizado
apply_theme()

# Cabeçalho Principal
st.markdown("<h1 style='margin-bottom: 0px;'>🔍 DataTrack</h1>", unsafe_allow_html=True)
st.markdown("<p class='subheader' style='margin-top: 0px; font-size: 1.1em;'>Busca inteligente de vagas de dados consolidadas e deduplicadas</p>", unsafe_allow_html=True)

# 3. Carrega opções dinâmicas para os filtros
with st.spinner("Conectando ao Supabase e carregando filtros..."):
    try:
        filter_opts = get_filter_options()
    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados Supabase: {str(e)}")
        st.stop()

# 4. Construção do Sidebar de Filtros
st.sidebar.markdown("<h3 style='margin-top: 0px;'>Filtros de Busca</h3>", unsafe_allow_html=True)

search_term = st.sidebar.text_input("Buscar por título ou empresa", placeholder="Ex: Engenheiro de Dados, Itaú")

# Formata áreas para exibição
area_mapping = {a["area_code"]: a["area_label"] for a in filter_opts["areas"]}
selected_areas_labels = st.sidebar.multiselect(
    "Área de Atuação",
    options=list(area_mapping.values()),
    default=None,
    help="Filtre por grandes famílias de cargos de dados"
)
selected_areas = [k for k, v in area_mapping.items() if v in selected_areas_labels]

# Formata senioridades
seniority_labels = {
    "estagio": "Estágio", "junior": "Júnior", "pleno": "Pleno",
    "senior": "Sênior", "especialista": "Especialista", "lead": "Lead", "unknown": "Não Informado"
}
selected_seniorities_labels = st.sidebar.multiselect(
    "Senioridade",
    options=list(seniority_labels.values()),
    default=None
)
selected_seniorities = [k for k, v in seniority_labels.items() if v in selected_seniorities_labels]

# Localização
selected_locations = st.sidebar.multiselect(
    "Cidade / Estado",
    options=filter_opts["locations"],
    default=None
)

# Modalidade de trabalho
selected_modalities = st.sidebar.multiselect(
    "Modalidade",
    options=["🌐 Remoto", "🏢 Híbrido", "🏢 Presencial"],
    default=["🌐 Remoto", "🏢 Híbrido", "🏢 Presencial"],
    help="Selecione as modalidades de trabalho desejadas"
)

# Skills
selected_skills = st.sidebar.multiselect(
    "Tecnologias / Skills",
    options=filter_opts["skills"],
    default=None,
    help="Vagas que exijam TODAS as tecnologias selecionadas"
)

# Período de publicação (Recência)
dias_option = st.sidebar.slider(
    "Publicadas há no máximo (dias)",
    min_value=1,
    max_value=30,
    value=7,
    help="Filtra a recência do post da vaga"
)

# Toggle de Aparência no Sidebar
theme_toggle()

# 5. Executa a busca no banco
vagas_df = get_vagas_filtradas(
    areas=selected_areas,
    seniorities=selected_seniorities,
    locations=selected_locations,
    selected_modalities=selected_modalities,
    selected_skills=selected_skills,
    dias=dias_option,
    search_term=search_term
)
# 6. Exibição dos resultados
total_vagas_coletadas = len(vagas_df)
vagas_exibidas_texto = "200+" if total_vagas_coletadas > 200 else str(total_vagas_coletadas)

# Trunca para 200 para a exibição na tabela e drill-down
if total_vagas_coletadas > 200:
    vagas_df = vagas_df.head(200)

col_kpi, _ = st.columns([1, 3])
with col_kpi:
    st.markdown(
        f"""
        <div class="metric-card">
            <small style="color: #94A3B8; text-transform: uppercase; font-weight: 600; font-size: 0.8em;">Vagas Encontradas</small>
            <h2 style="margin: 5px 0px; font-size: 2.2em; color: #6C63FF;">{vagas_exibidas_texto}</h2>
            <small style="color: #64748B;">Atendendo aos critérios selecionados</small>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

if vagas_df.empty:
    st.info("Nenhuma vaga encontrada para os filtros selecionados. Tente expandir o período ou reduzir os filtros.")
else:
    # Formata colunas para exibição na tabela interativa
    display_df = vagas_df.copy()
    
    # Converte array de skills em string amigável
    display_df["skills"] = display_df["skills"].apply(lambda s: ", ".join(s) if isinstance(s, list) else "Não mapeada")
    
    # Formata modalidades
    display_df["Modalidade"] = display_df.apply(
        lambda r: "🌐 Remoto" if r["is_remote"] else ("🏢 Híbrido" if r["is_hybrid"] else "🏢 Presencial"),
        axis=1
    )
    
    # Remove colunas auxiliares/IDs da visão principal
    display_df = display_df[["title", "company", "location", "Modalidade", "area", "seniority", "skills", "posted_at"]]
    display_df.columns = ["Título", "Empresa", "Localização", "Modalidade", "Área", "Senioridade", "Tecnologias", "Publicada em"]
    
    # Configuração de colunas interativas no dataframe
    st.subheader("Vagas Disponíveis")
    st.markdown("<p class='subheader' style='font-size: 0.9em; margin-bottom: 10px;'>Selecione uma vaga na tabela abaixo para abrir os detalhes de candidatura.</p>", unsafe_allow_html=True)
    
    # st.dataframe interativo
    event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun"
    )
    
    # 7. Drill-down: Mostrar detalhes se houver seleção
    if event and event.get("selection") and event["selection"].get("rows"):
        selected_row_idx = event["selection"]["rows"][0]
        vaga_selecionada = vagas_df.iloc[selected_row_idx]
        
        st.markdown("---")
        st.subheader("📍 Detalhes da Vaga Selecionada")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"### **{vaga_selecionada['title']}**")
            st.markdown(f"🏢 **Empresa:** {vaga_selecionada['company']} | 📍 **Local:** {vaga_selecionada['location']}")
            st.markdown(f"📂 **Área:** {vaga_selecionada['area']} | 🏷️ **Senioridade:** {vaga_selecionada['seniority']}")
            
            skills_list = vaga_selecionada['skills']
            if isinstance(skills_list, list) and skills_list:
                skills_badges = " ".join([f"<span style='background-color: rgba(108, 99, 255, 0.15); color: #6C63FF; padding: 4px 10px; border-radius: 20px; font-size: 0.85em; font-weight: 500; border: 1px solid rgba(108, 99, 255, 0.3); margin-right: 5px; margin-bottom: 5px; display: inline-block;'>{s}</span>" for s in skills_list])
                st.markdown(f"**Tecnologias Requeridas:**<br>{skills_badges}", unsafe_allow_html=True)
            else:
                st.markdown("**Tecnologias Requeridas:** Não mapeada na descrição")
                
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.link_button(
                "🔥 Ir para a Vaga / Candidatar-se",
                url=vaga_selecionada['url'],
                use_container_width=True
            )
            st.markdown(f"<p style='text-align: center; color: #64748B; font-size: 0.85em;'>Publicada em: {vaga_selecionada['posted_at'].strftime('%d/%m/%Y')}</p>", unsafe_allow_html=True)
