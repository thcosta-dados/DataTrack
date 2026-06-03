import streamlit as st

def apply_theme():
    """Injeta estilos CSS personalizados para o painel operacional.

    Paleta alinhada com o dashboard publico:
      - Dark: midnight (#0F0F1A), cards indigo (#1C1C32), acentos mint/coral
      - Light: warm off-white (#F5F3EF), cards brancos, acentos teal/coral
    """
    if "theme" not in st.session_state:
        st.session_state["theme"] = "dark"

    theme = st.session_state["theme"]

    font_import = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif !important;
    }

    /* Fontes mono para logs e codigos de auditoria */
    code, pre, .logs-text {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.9em !important;
    }
    </style>
    """
    st.markdown(font_import, unsafe_allow_html=True)

    if theme == "dark":
        dark_css = """
        <style>
        .stApp {
            background-color: #0F0F1A !important;
            color: #D4D4E8 !important;
        }

        div.metric-card {
            background: linear-gradient(135deg, #1C1C32 0%, #24243E 100%);
            border: 1px solid rgba(0, 212, 170, 0.15);
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
            margin-bottom: 15px;
        }

        [data-testid="stSidebar"] {
            background-color: #141428 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.04) !important;
        }

        h1, h2, h3 {
            color: #EDEDF4 !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
        }

        /* Acento Mint de Telemetria */
        .telemetry-title {
            color: #00D4AA !important;
            text-shadow: 0 0 10px rgba(0, 212, 170, 0.2);
        }

        .stButton>button {
            background: linear-gradient(90deg, #00D4AA 0%, #00B894 100%) !important;
            color: #0F0F1A !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 700 !important;
            padding: 8px 16px !important;
            box-shadow: 0 4px 12px rgba(0, 212, 170, 0.2);
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(0, 212, 170, 0.35);
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(0, 212, 170, 0.1) !important;
            border-radius: 10px !important;
            overflow: hidden;
        }
        </style>
        """
        st.markdown(dark_css, unsafe_allow_html=True)
    else:
        light_css = """
        <style>
        .stApp {
            background-color: #F5F3EF !important;
            color: #2D2D3A !important;
        }

        div.metric-card {
            background-color: #FFFFFF;
            border: 1px solid #E7E5E4;
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 1px 8px rgba(0, 0, 0, 0.03);
            margin-bottom: 15px;
        }

        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E7E5E4 !important;
        }

        h1, h2, h3 {
            color: #1C1917 !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
        }

        .telemetry-title {
            color: #0D9488 !important;
        }

        .stButton>button {
            background-color: #0D9488 !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 8px 16px !important;
            box-shadow: 0 2px 8px rgba(13, 148, 136, 0.1);
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #0F766E !important;
            transform: translateY(-1px);
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid #E7E5E4 !important;
            border-radius: 10px !important;
            overflow: hidden;
        }
        </style>
        """
        st.markdown(light_css, unsafe_allow_html=True)

def theme_toggle():
    """Renderiza o toggle de tema na barra lateral do painel operacional."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("Aparencia")

    is_dark = st.sidebar.toggle(
        "Modo Escuro",
        value=(st.session_state.get("theme", "dark") == "dark"),
        help="Alterne entre o tema Claro e Escuro."
    )

    new_theme = "dark" if is_dark else "light"
    if st.session_state.get("theme") != new_theme:
        st.session_state["theme"] = new_theme
        st.rerun()
