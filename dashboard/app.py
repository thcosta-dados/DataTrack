import streamlit as st
from database import get_filter_options, get_vagas_filtradas
from theme import apply_theme, theme_toggle

# -- Configuracao da pagina (primeiro comando Streamlit obrigatoriamente)
st.set_page_config(
    page_title="DataTrack -- Inteligencia de Vagas de Dados",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

apply_theme()


# ===== HELPER: monta o HTML de um card de vaga =====
def _modality_tag(row):
    """Retorna o HTML da tag de modalidade baseado nos flags da vaga."""
    if row["is_remote"]:
        return '<span class="tag tag-remote">Remoto</span>'
    if row["is_hybrid"]:
        return '<span class="tag tag-hybrid">Hibrido</span>'
    return '<span class="tag tag-onsite">Presencial</span>'


def _skills_badges(skills_list):
    """Renderiza badges de skills ou fallback."""
    if not isinstance(skills_list, list) or not skills_list:
        return '<span class="skill-badge">Nao mapeada</span>'
    return "".join(
        f'<span class="skill-badge">{s}</span>' for s in skills_list
    )


def _render_job_card(row, idx):
    """Monta o HTML completo de um card de vaga com detalhes expandidos."""
    title = row["title"]
    company = row["company"]
    location = row["location"]
    area = row["area"]
    seniority = row["seniority"]
    skills = row.get("skills", [])
    url = row["url"]
    posted = row["posted_at"]
    modality = _modality_tag(row)

    date_str = ""
    if posted:
        try:
            date_str = posted.strftime("%d/%m")
        except AttributeError:
            date_str = str(posted)[:10]

    card_html = f"""
    <div class="job-card" id="job-card-{idx}">
        <div class="job-card-header">
            <div>
                <div class="job-title">{title}</div>
                <div class="job-tags">
                    <span class="tag tag-company">{company}</span>
                    {modality}
                    <span class="tag tag-location">{location}</span>
                </div>
            </div>
            <div class="tag-date">{date_str}</div>
        </div>
        <div class="job-card-body">
            <div class="detail-grid">
                <div class="job-detail-left">
                    <strong>Vaga:</strong> {title}<br>
                    <strong>Local:</strong> {location}<br>
                    <strong>Area:</strong> {area}<br>
                    <strong>Senioridade:</strong> {seniority}<br>
                    <div class="skills-row">
                        {_skills_badges(skills)}
                    </div>
                </div>
                <div class="job-detail-right">
                    <div class="company-label">EMPRESA</div>
                    <div class="company-name">{company}</div>
                    <a class="cta-button" href="{url}" target="_blank" rel="noopener">
                        Candidatar-se
                    </a>
                    <a class="secondary-link" href="{url}" target="_blank" rel="noopener">
                        Ver Post Original
                    </a>
                </div>
            </div>
        </div>
    </div>
    """
    return card_html


# ===================================================================
# LAYOUT PRINCIPAL
# ===================================================================

# 1. Banner superior
st.markdown(
    '<div class="top-banner">Plataforma de inteligencia para vagas de dados. Dados coletados e deduplicados automaticamente.</div>',
    unsafe_allow_html=True
)

# 2. Header com badge + titulo
st.markdown(
    """
    <div class="header-section">
        <div class="badge">Vagas Atualizadas</div>
        <h1>Portal de <span class="accent">Oportunidades</span></h1>
        <div class="subtitle">As melhores vagas de Dados e BI curadas diariamente pelo DataTrack</div>
    </div>
    """,
    unsafe_allow_html=True
)

# 3. Filtros inline (horizontais no corpo, sem sidebar)
with st.spinner("Conectando ao Supabase e carregando filtros..."):
    try:
        filter_opts = get_filter_options()
    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados Supabase: {str(e)}")
        st.stop()

# Linha de busca
search_term = st.text_input(
    "Pesquise por cargo, tecnologia ou empresa...",
    placeholder="Ex: Engenheiro de Dados, Python, Itau",
    label_visibility="collapsed"
)

# Linha de filtros (3 colunas)
col_region, col_seniority, col_area = st.columns(3)

with col_region:
    selected_locations = st.multiselect(
        "Regiao",
        options=filter_opts["locations"],
        default=None,
        placeholder="Todas Regioes"
    )

with col_seniority:
    seniority_labels = {
        "estagio": "Estagio", "junior": "Junior", "pleno": "Pleno",
        "senior": "Senior", "especialista": "Especialista",
        "lead": "Lead", "unknown": "Nao Informado"
    }
    selected_seniorities_labels = st.multiselect(
        "Senioridade",
        options=list(seniority_labels.values()),
        default=None,
        placeholder="Todas Senioridades"
    )
    selected_seniorities = [
        k for k, v in seniority_labels.items()
        if v in selected_seniorities_labels
    ]

with col_area:
    area_mapping = {
        a["area_code"]: a["area_label"] for a in filter_opts["areas"]
    }
    selected_areas_labels = st.multiselect(
        "Area de Atuacao",
        options=list(area_mapping.values()),
        default=None,
        placeholder="Todas Areas"
    )
    selected_areas = [
        k for k, v in area_mapping.items()
        if v in selected_areas_labels
    ]

# Linha secundaria: skills + modalidade + periodo + tema
col_skills, col_modal, col_dias, col_theme = st.columns([2, 1.5, 1, 0.5])

with col_skills:
    selected_skills = st.multiselect(
        "Tecnologias / Skills",
        options=filter_opts["skills"],
        default=None,
        placeholder="Qualquer tecnologia"
    )

with col_modal:
    modal_options = ["Remoto", "Hibrido", "Presencial"]
    selected_modalities_raw = st.multiselect(
        "Modalidade",
        options=modal_options,
        default=modal_options,
        placeholder="Todas"
    )
    # Converte para formato esperado pelo database.py
    modality_map = {
        "Remoto": "🌐 Remoto",
        "Hibrido": "🏢 Híbrido",
        "Presencial": "🏢 Presencial"
    }
    selected_modalities = [modality_map[m] for m in selected_modalities_raw]

with col_dias:
    dias_option = st.slider(
        "Ultimos (dias)",
        min_value=1, max_value=30, value=7
    )

with col_theme:
    st.markdown("<br>", unsafe_allow_html=True)
    theme_toggle()


# 4. Busca no banco
vagas_df = get_vagas_filtradas(
    areas=selected_areas,
    seniorities=selected_seniorities,
    locations=selected_locations,
    selected_modalities=selected_modalities,
    selected_skills=selected_skills,
    dias=dias_option,
    search_term=search_term
)

total_vagas = len(vagas_df)
vagas_exibidas_texto = "200+" if total_vagas > 200 else str(total_vagas)

if total_vagas > 200:
    vagas_df = vagas_df.head(200)

# 5. Stats bar
st.markdown(
    f'<div class="stats-bar">'
    f'<div class="count"><span>{vagas_exibidas_texto}</span> vagas encontradas</div>'
    f'</div>',
    unsafe_allow_html=True
)

# 6. Resultados: cards de vagas
if vagas_df.empty:
    st.markdown(
        """
        <div class="empty-state">
            <div class="empty-icon">🔍</div>
            <div class="empty-title">Nenhuma vaga encontrada</div>
            <div class="empty-desc">Tente expandir o periodo ou reduzir os filtros para encontrar mais oportunidades.</div>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    # Monta o HTML de todos os cards de uma vez (mais eficiente que multiplos st.markdown)
    cards_html = ""
    for idx, row in vagas_df.iterrows():
        cards_html += _render_job_card(row, idx)

    st.markdown(cards_html, unsafe_allow_html=True)
