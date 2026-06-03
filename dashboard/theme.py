import streamlit as st


def apply_theme():
    """Injeta estilos CSS personalizados no estilo portal de vagas premium.

    Paleta:
      - Dark: fundo midnight, cards indigo escuro, acentos mint + coral + gold
      - Light: fundo warm off-white, cards brancos, acentos teal + coral
    """
    if "theme" not in st.session_state:
        st.session_state["theme"] = "dark"

    theme = st.session_state["theme"]

    # Base: Google Fonts + Reset estrutural
    base_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif !important;
    }

    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 1200px !important;
    }

    /* Esconde sidebar (filtros ficam inline no corpo) */
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }

    /* === TOP BANNER === */
    div.top-banner {
        text-align: center;
        padding: 10px 20px;
        font-size: 0.85em;
        font-weight: 500;
        border-radius: 0;
        margin: -1rem -1rem 0 -1rem;
        letter-spacing: 0.02em;
    }

    /* === HEADER === */
    div.header-section {
        text-align: center;
        padding: 35px 0 20px 0;
    }
    div.header-section .badge {
        display: inline-block;
        font-size: 0.75em;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        padding: 6px 16px;
        border-radius: 20px;
        margin-bottom: 12px;
    }
    div.header-section h1 {
        font-size: 2.4em !important;
        font-weight: 800 !important;
        margin: 8px 0 6px 0 !important;
        letter-spacing: -0.03em !important;
        line-height: 1.1 !important;
    }
    div.header-section h1 span.accent {
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    div.header-section .subtitle {
        font-size: 1.05em;
        font-weight: 400;
        margin-top: 4px;
    }

    /* === SEARCH === */
    div.search-container {
        max-width: 800px;
        margin: 20px auto 10px auto;
    }

    /* === FILTER BAR === */
    div.filter-bar {
        max-width: 860px;
        margin: 0 auto 15px auto;
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
        justify-content: center;
    }

    /* === TOGGLE ROW === */
    div.toggle-row {
        display: flex;
        align-items: center;
        gap: 18px;
        justify-content: center;
        margin: 8px auto 25px auto;
        max-width: 860px;
    }
    div.toggle-row .toggle-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.88em;
        font-weight: 500;
    }

    /* === STATS BAR === */
    div.stats-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        max-width: 860px;
        margin: 0 auto 18px auto;
        padding: 0 4px;
    }
    div.stats-bar .count {
        font-size: 0.95em;
        font-weight: 600;
    }

    /* === JOB CARDS === */
    div.job-card {
        border-radius: 14px;
        padding: 0;
        margin-bottom: 16px;
        overflow: hidden;
        transition: all 0.25s ease;
        max-width: 860px;
        margin-left: auto;
        margin-right: auto;
    }
    div.job-card:hover {
        transform: translateY(-2px);
    }

    div.job-card-header {
        padding: 18px 22px;
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        cursor: pointer;
    }
    div.job-card-header .job-title {
        font-size: 1.1em;
        font-weight: 700;
        margin: 0 0 8px 0;
    }
    div.job-card-header .job-tags {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        align-items: center;
    }
    div.job-card-header .tag {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 0.78em;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 6px;
    }

    /* Tags com cores temáticas (independentes do tema dark/light) */
    .tag-company {
        background: rgba(0, 212, 170, 0.1);
        color: #00D4AA;
        border: 1px solid rgba(0, 212, 170, 0.25);
    }
    .tag-location {
        background: rgba(255, 123, 84, 0.08);
        color: #FF7B54;
        border: 1px solid rgba(255, 123, 84, 0.2);
    }
    .tag-remote {
        background: rgba(0, 212, 170, 0.1);
        color: #00D4AA;
        border: 1px solid rgba(0, 212, 170, 0.2);
    }
    .tag-hybrid {
        background: rgba(255, 217, 61, 0.1);
        color: #D4A800;
        border: 1px solid rgba(255, 217, 61, 0.25);
    }
    .tag-onsite {
        background: rgba(255, 123, 84, 0.08);
        color: #FF7B54;
        border: 1px solid rgba(255, 123, 84, 0.2);
    }
    .tag-salary {
        background: rgba(0, 212, 170, 0.1);
        color: #00D4AA;
        font-weight: 700;
        border: 1px solid rgba(0, 212, 170, 0.2);
    }
    .tag-date {
        font-size: 0.78em;
        font-weight: 500;
    }

    /* Card body / expanded */
    div.job-card-body {
        padding: 0 22px 20px 22px;
    }
    div.job-card-body .detail-grid {
        display: grid;
        grid-template-columns: 1.4fr 0.6fr;
        gap: 20px;
    }
    div.job-detail-left {
        font-size: 0.92em;
        line-height: 1.7;
    }
    div.job-detail-right {
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    div.job-detail-right .company-label {
        font-size: 0.72em;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
        margin-bottom: 2px;
    }
    div.job-detail-right .company-name {
        font-size: 1.05em;
        font-weight: 700;
        margin-bottom: 12px;
    }

    /* Skills badges */
    div.skills-row {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 10px;
    }
    div.skills-row .skill-badge {
        display: inline-block;
        font-size: 0.78em;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 20px;
    }

    /* CTA */
    a.cta-button {
        display: block;
        text-align: center;
        padding: 12px 24px;
        border-radius: 10px;
        font-weight: 700;
        font-size: 0.95em;
        text-decoration: none;
        margin-top: 12px;
        transition: all 0.2s ease;
        letter-spacing: 0.01em;
    }
    a.cta-button:hover {
        transform: translateY(-1px);
    }
    a.secondary-link {
        display: block;
        text-align: center;
        padding: 8px;
        font-size: 0.82em;
        font-weight: 500;
        text-decoration: none;
        margin-top: 6px;
    }

    /* === KPI CARDS === */
    div.metric-card {
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 12px;
        text-align: center;
        transition: transform 0.2s ease;
    }
    div.metric-card:hover {
        transform: translateY(-2px);
    }
    div.metric-card .metric-label {
        text-transform: uppercase;
        font-weight: 700;
        font-size: 0.72em;
        letter-spacing: 0.08em;
        margin-bottom: 6px;
    }
    div.metric-card .metric-value {
        font-size: 2.2em;
        font-weight: 800;
        margin: 4px 0;
        line-height: 1;
    }
    div.metric-card .metric-desc {
        font-size: 0.8em;
        font-weight: 400;
    }

    /* === EMPTY STATE === */
    div.empty-state {
        text-align: center;
        padding: 60px 20px;
        max-width: 500px;
        margin: 0 auto;
    }
    div.empty-state .empty-icon { font-size: 3em; margin-bottom: 12px; }
    div.empty-state .empty-title { font-size: 1.2em; font-weight: 700; margin-bottom: 8px; }
    div.empty-state .empty-desc { font-size: 0.92em; font-weight: 400; }
    </style>
    """
    st.markdown(base_css, unsafe_allow_html=True)

    # ------------------------------------------------------------------ DARK
    if theme == "dark":
        st.markdown("""
        <style>
        .stApp {
            background-color: #0F0F1A !important;
            color: #D4D4E8 !important;
        }

        div.top-banner {
            background: linear-gradient(90deg, #141428 0%, #1C1C38 100%);
            color: #A5A5C0;
            border-bottom: 1px solid rgba(255,255,255,0.04);
        }

        div.header-section h1 { color: #EDEDF4 !important; }
        div.header-section .subtitle { color: #8888A8; }
        div.header-section .badge {
            background: rgba(0, 212, 170, 0.1);
            color: #00D4AA;
            border: 1px solid rgba(0, 212, 170, 0.2);
        }
        div.header-section h1 span.accent {
            background: linear-gradient(135deg, #00D4AA, #00E6B8);
        }

        h1, h2, h3 { color: #EDEDF4 !important; font-weight: 700 !important; }

        /* Cards */
        div.job-card {
            background: #1C1C32;
            border: 1px solid rgba(255,255,255,0.05);
            box-shadow: 0 2px 12px rgba(0,0,0,0.25);
        }
        div.job-card:hover {
            border-color: rgba(0, 212, 170, 0.3);
            box-shadow: 0 6px 24px rgba(0,0,0,0.35);
        }
        div.job-card-header .job-title { color: #EDEDF4; }
        .tag-date { color: #5C5C7A; }

        div.job-detail-right {
            background: #24243E;
            border: 1px solid rgba(255,255,255,0.04);
        }
        div.job-detail-right .company-label { color: #5C5C7A; }
        div.job-detail-right .company-name { color: #EDEDF4; }

        div.skills-row .skill-badge {
            background: rgba(0, 212, 170, 0.1);
            color: #5EEAD4;
            border: 1px solid rgba(0, 212, 170, 0.2);
        }

        /* CTA */
        a.cta-button {
            background: linear-gradient(135deg, #00D4AA 0%, #00B894 100%);
            color: #0F0F1A !important;
            box-shadow: 0 4px 16px rgba(0, 212, 170, 0.25);
        }
        a.cta-button:hover {
            box-shadow: 0 6px 22px rgba(0, 212, 170, 0.35);
        }
        a.secondary-link { color: #5C5C7A; }

        /* Metrics */
        div.metric-card {
            background: linear-gradient(135deg, #1C1C32 0%, #24243E 100%);
            border: 1px solid rgba(255,255,255,0.04);
            box-shadow: 0 2px 12px rgba(0,0,0,0.18);
        }
        div.metric-card .metric-label { color: #5C5C7A; }
        div.metric-card .metric-desc { color: #5C5C7A; }

        div.stats-bar .count { color: #8888A8; }
        div.stats-bar .count span { color: #00D4AA; font-weight: 700; }

        div.empty-state .empty-title { color: #D4D4E8; }
        div.empty-state .empty-desc { color: #5C5C7A; }

        /* Streamlit widget overrides */
        .stSelectbox label, .stMultiSelect label, .stTextInput label,
        .stSlider label, .stToggle label {
            color: #8888A8 !important;
            font-weight: 600 !important;
            font-size: 0.85em !important;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(255,255,255,0.05) !important;
            border-radius: 10px !important;
            overflow: hidden;
        }

        /* Plotly transparent */
        .js-plotly-plot .plotly .bg { fill: transparent !important; }
        </style>
        """, unsafe_allow_html=True)

    # ------------------------------------------------------------------ LIGHT
    else:
        st.markdown("""
        <style>
        .stApp {
            background-color: #F5F3EF !important;
            color: #2D2D3A !important;
        }

        div.top-banner {
            background: linear-gradient(90deg, #1A3C40 0%, #1D6B5C 100%);
            color: #D1FAE5;
        }

        div.header-section h1 { color: #1C1917 !important; }
        div.header-section .subtitle { color: #78716C; }
        div.header-section .badge {
            background: rgba(13, 148, 136, 0.08);
            color: #0D9488;
            border: 1px solid rgba(13, 148, 136, 0.2);
        }
        div.header-section h1 span.accent {
            background: linear-gradient(135deg, #0D9488, #14B8A6);
        }

        h1, h2, h3 { color: #1C1917 !important; font-weight: 700 !important; }

        /* Cards */
        div.job-card {
            background: #FFFFFF;
            border: 1px solid #E7E5E4;
            box-shadow: 0 1px 6px rgba(0,0,0,0.04);
        }
        div.job-card:hover {
            border-color: rgba(13, 148, 136, 0.4);
            box-shadow: 0 4px 16px rgba(0,0,0,0.07);
        }
        div.job-card-header .job-title { color: #1C1917; }
        .tag-date { color: #A8A29E; }

        div.job-detail-right {
            background: #FAFAF9;
            border: 1px solid #E7E5E4;
        }
        div.job-detail-right .company-label { color: #A8A29E; }
        div.job-detail-right .company-name { color: #1C1917; }

        div.skills-row .skill-badge {
            background: rgba(13, 148, 136, 0.07);
            color: #0D9488;
            border: 1px solid rgba(13, 148, 136, 0.18);
        }

        /* CTA */
        a.cta-button {
            background: linear-gradient(135deg, #0D9488 0%, #0F766E 100%);
            color: #FFFFFF !important;
            box-shadow: 0 4px 14px rgba(13, 148, 136, 0.2);
        }
        a.cta-button:hover {
            box-shadow: 0 6px 20px rgba(13, 148, 136, 0.3);
        }
        a.secondary-link { color: #A8A29E; }

        /* Metrics */
        div.metric-card {
            background: #FFFFFF;
            border: 1px solid #E7E5E4;
            box-shadow: 0 1px 6px rgba(0,0,0,0.03);
        }
        div.metric-card .metric-label { color: #A8A29E; }
        div.metric-card .metric-desc { color: #A8A29E; }

        div.stats-bar .count { color: #57534E; }
        div.stats-bar .count span { color: #0D9488; font-weight: 700; }

        div.empty-state .empty-title { color: #1C1917; }
        div.empty-state .empty-desc { color: #78716C; }

        .stSelectbox label, .stMultiSelect label, .stTextInput label,
        .stSlider label, .stToggle label {
            color: #57534E !important;
            font-weight: 600 !important;
            font-size: 0.85em !important;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid #E7E5E4 !important;
            border-radius: 10px !important;
            overflow: hidden;
        }
        </style>
        """, unsafe_allow_html=True)


def theme_toggle():
    """Renderiza o controle de alternancia de tema no corpo da pagina."""
    current = st.session_state.get("theme", "dark")
    label = "Modo Claro" if current == "dark" else "Modo Escuro"
    if st.button(label, key="theme_toggle_btn"):
        st.session_state["theme"] = "light" if current == "dark" else "dark"
        st.rerun()
