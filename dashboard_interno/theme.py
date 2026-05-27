import streamlit as st

def apply_theme():
    """Injeta estilos CSS personalizados de acordo com o tema selecionado."""
    if "theme" not in st.session_state:
        st.session_state["theme"] = "dark"
        
    theme = st.session_state["theme"]
    
    font_import = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Fontes mono para logs e códigos de auditoria */
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
            background-color: #06090F !important;
            color: #E2E8F0 !important;
        }
        
        div.metric-card {
            background: linear-gradient(135deg, #0F1622 0%, #0B0E17 100%);
            border: 1px solid rgba(0, 242, 254, 0.15);
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            margin-bottom: 15px;
        }
        
        [data-testid="stSidebar"] {
            background-color: #0A0D14 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.04) !important;
        }
        
        h1, h2, h3 {
            color: #FFFFFF !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
        }
        
        /* Acento Ciano de Telemetria */
        .telemetry-title {
            color: #00F2FE !important;
            text-shadow: 0 0 10px rgba(0, 242, 254, 0.2);
        }
        
        .stButton>button {
            background: linear-gradient(90deg, #00F2FE 0%, #4FACFE 100%) !important;
            color: #06090F !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 700 !important;
            padding: 8px 16px !important;
            box-shadow: 0 4px 12px rgba(0, 242, 254, 0.2);
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(0, 242, 254, 0.4);
        }
        
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(0, 242, 254, 0.1) !important;
            border-radius: 8px !important;
            overflow: hidden;
        }
        </style>
        """
        st.markdown(dark_css, unsafe_allow_html=True)
    else:
        light_css = """
        <style>
        .stApp {
            background-color: #F8FAFC !important;
            color: #1E293B !important;
        }
        
        div.metric-card {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.03);
            margin-bottom: 15px;
        }
        
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0 !important;
        }
        
        h1, h2, h3 {
            color: #0F172A !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
        }
        
        .telemetry-title {
            color: #0EA5E9 !important;
        }
        
        .stButton>button {
            background-color: #0EA5E9 !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 8px 16px !important;
            box-shadow: 0 2px 8px rgba(14, 165, 233, 0.1);
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #0284C7 !important;
            transform: translateY(-1px);
        }
        
        div[data-testid="stDataFrame"] {
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            overflow: hidden;
        }
        </style>
        """
        st.markdown(light_css, unsafe_allow_html=True)

def theme_toggle():
    """Renderiza o toggle de tema na barra lateral do painel operacional."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("Aparência")
    
    is_dark = st.sidebar.toggle(
        "Modo Escuro 🌙", 
        value=(st.session_state.get("theme", "dark") == "dark"),
        help="Alterne entre o tema Claro e Escuro."
    )
    
    new_theme = "dark" if is_dark else "light"
    if st.session_state.get("theme") != new_theme:
        st.session_state["theme"] = new_theme
        st.rerun()
