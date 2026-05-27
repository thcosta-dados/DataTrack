import streamlit as st

def apply_theme():
    """Injeta estilos CSS personalizados de acordo com o tema selecionado."""
    # Garante a existência do estado do tema
    if "theme" not in st.session_state:
        st.session_state["theme"] = "dark"
        
    theme = st.session_state["theme"]
    
    # Importa a fonte Inter do Google Fonts
    font_import = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif !important;
    }
    </style>
    """
    st.markdown(font_import, unsafe_allow_html=True)
    
    if theme == "dark":
        # Tema Dark Premium: quase preto, tons de cinza azulado, bordas discretas e acentos neon
        dark_css = """
        <style>
        /* Fundo geral da aplicação */
        .stApp {
            background-color: #0B0E14 !important;
            color: #E2E8F0 !important;
        }
        
        /* Cards customizados */
        div.metric-card {
            background: linear-gradient(135deg, #161D2A 0%, #101622 100%);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
            margin-bottom: 15px;
        }
        
        /* Modificações do Sidebar */
        [data-testid="stSidebar"] {
            background-color: #0F131C !important;
            border-right: 1px solid rgba(255, 255, 255, 0.04) !important;
        }
        
        /* Títulos de seção */
        h1, h2, h3 {
            color: #FFFFFF !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
        }
        
        /* Subtítulos */
        .subheader {
            color: #94A3B8 !important;
            font-weight: 500;
        }
        
        /* Botões primários */
        .stButton>button {
            background: linear-gradient(90deg, #6C63FF 0%, #4F46E5 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 8px 16px !important;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.2);
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(79, 70, 229, 0.3);
        }
        
        /* Customização de Tabelas */
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            border-radius: 8px !important;
            overflow: hidden;
        }
        </style>
        """
        st.markdown(dark_css, unsafe_allow_html=True)
    else:
        # Tema Light Premium: clean, neutro moderno com cinzas azulados leves e foco no conteúdo
        light_css = """
        <style>
        /* Fundo geral da aplicação */
        .stApp {
            background-color: #F8FAFC !important;
            color: #1E293B !important;
        }
        
        /* Cards customizados */
        div.metric-card {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.03);
            margin-bottom: 15px;
        }
        
        /* Modificações do Sidebar */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0 !important;
        }
        
        /* Títulos de seção */
        h1, h2, h3 {
            color: #0F172A !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
        }
        
        /* Subtítulos */
        .subheader {
            color: #64748B !important;
            font-weight: 500;
        }
        
        /* Botões primários */
        .stButton>button {
            background-color: #4F46E5 !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 8px 16px !important;
            box-shadow: 0 2px 8px rgba(79, 70, 229, 0.1);
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #4338CA !important;
            transform: translateY(-1px);
        }
        
        /* Customização de Tabelas */
        div[data-testid="stDataFrame"] {
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            overflow: hidden;
        }
        </style>
        """
        st.markdown(light_css, unsafe_allow_html=True)

def theme_toggle():
    """Renderiza o toggle de tema na barra lateral."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("Aparência")
    
    # Toggle switch
    is_dark = st.sidebar.toggle(
        "Modo Escuro 🌙", 
        value=(st.session_state.get("theme", "dark") == "dark"),
        help="Alterne entre o tema Claro e Escuro."
    )
    
    # Atualiza o estado
    new_theme = "dark" if is_dark else "light"
    if st.session_state.get("theme") != new_theme:
        st.session_state["theme"] = new_theme
        st.rerun()
