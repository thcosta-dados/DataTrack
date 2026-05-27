import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from database import get_kpis_mercado, get_distribuicao_area, get_distribuicao_senioridade, get_modalidade_por_area
from theme import apply_theme, theme_toggle

# 1. Configuração da página
st.set_page_config(
    page_title="DataTrack — Visão Geral do Mercado",
    page_icon="📊",
    layout="wide"
)

# 2. Aplica o Tema e importa CSS customizado
apply_theme()

# Cabeçalho Principal
st.markdown("<h1>📊 Visão Geral do Mercado</h1>", unsafe_allow_html=True)
st.markdown("<p class='subheader' style='margin-bottom: 25px;'>Principais indicadores de demanda e perfil das vagas da área de dados</p>", unsafe_allow_html=True)

# 3. Carrega KPIs
with st.spinner("Carregando indicadores..."):
    kpis = get_kpis_mercado()
    df_area = get_distribuicao_area()
    df_seniority = get_distribuicao_senioridade()
    df_modalidade = get_modalidade_por_area()

# 4. Renderiza KPIs no topo (4 colunas)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <small style="color: #94A3B8; text-transform: uppercase; font-weight: 600; font-size: 0.8em;">Total de Vagas</small>
            <h2 style="margin: 5px 0px; font-size: 2em; color: #6C63FF;">{kpis['total_vagas']:,}</h2>
            <small style="color: #64748B;">Vagas unificadas</small>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f"""
        <div class="metric-card">
            <small style="color: #94A3B8; text-transform: uppercase; font-weight: 600; font-size: 0.8em;">Trabalho Híbrido</small>
            <h2 style="margin: 5px 0px; font-size: 2em; color: #00F2FE;">{kpis['hibrido_percent']}%</h2>
            <small style="color: #64748B;">Vagas em modelo híbrido</small>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        f"""
        <div class="metric-card">
            <small style="color: #94A3B8; text-transform: uppercase; font-weight: 600; font-size: 0.8em;">Trabalho Remoto</small>
            <h2 style="margin: 5px 0px; font-size: 2em; color: #10B981;">{kpis['remoto_percent']}%</h2>
            <small style="color: #64748B;">Vagas 100% home office</small>
        </div>
        """,
        unsafe_allow_html=True
    )

with col4:
    st.markdown(
        f"""
        <div class="metric-card">
            <small style="color: #94A3B8; text-transform: uppercase; font-weight: 600; font-size: 0.8em;">Novas Vagas (24h)</small>
            <h2 style="margin: 5px 0px; font-size: 2em; color: #F59E0B;">+{kpis['vagas_hoje']}</h2>
            <small style="color: #64748B;">Adicionadas hoje</small>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# 5. Seção de Gráficos
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Vagas por Área de Atuação")
    if not df_area.empty:
        # Gráfico Plotly de Barras Horizontal
        fig_area = px.bar(
            df_area,
            x="vagas",
            y="area",
            orientation="h",
            color="vagas",
            color_continuous_scale="Viridis",
            labels={"vagas": "Quantidade de Vagas", "area": "Área de Dados"},
            text_auto=True
        )
        fig_area.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color="#94A3B8" if st.session_state["theme"] == "dark" else "#1E293B",
            coloraxis_showscale=False,
            height=350,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig_area, use_container_width=True)
    else:
        st.info("Sem dados de áreas disponíveis.")

with col_right:
    st.subheader("Distribuição por Senioridade")
    if not df_seniority.empty:
        # Gráfico Plotly de Rosca
        fig_seniority = px.pie(
            df_seniority,
            values="vagas",
            names="senioridade",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_seniority.update_traces(textposition='inside', textinfo='percent+label')
        fig_seniority.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            font_color="#94A3B8" if st.session_state["theme"] == "dark" else "#1E293B",
            height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False
        )
        st.plotly_chart(fig_seniority, use_container_width=True)
    else:
        st.info("Sem dados de senioridade disponíveis.")

st.markdown("<br>", unsafe_allow_html=True)

# Gráfico de Modalidade por Área (Larga Escala)
st.subheader("Modalidade de Trabalho por Área de Atuação")
if not df_modalidade.empty:
    fig_modalidade = go.Figure()
    fig_modalidade.add_trace(go.Bar(
        y=df_modalidade["area"],
        x=df_modalidade["remoto"],
        name="Remoto 🌐",
        orientation="h",
        marker=dict(color="#10B981")
    ))
    fig_modalidade.add_trace(go.Bar(
        y=df_modalidade["area"],
        x=df_modalidade["hybrido"],
        name="Híbrido 🏢",
        orientation="h",
        marker=dict(color="#00F2FE")
    ))
    fig_modalidade.add_trace(go.Bar(
        y=df_modalidade["area"],
        x=df_modalidade["presencial"],
        name="Presencial 🏢",
        orientation="h",
        marker=dict(color="#F59E0B")
    ))
    
    fig_modalidade.update_layout(
        barmode='stack',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color="#94A3B8" if st.session_state["theme"] == "dark" else "#1E293B",
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_modalidade, use_container_width=True)
else:
    st.info("Sem dados de modalidade disponíveis.")

# Toggle de Tema no Sidebar
theme_toggle()
