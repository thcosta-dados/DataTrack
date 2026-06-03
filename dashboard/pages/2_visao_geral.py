import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from database import get_kpis_mercado, get_distribuicao_area, get_distribuicao_senioridade, get_modalidade_por_area
from theme import apply_theme, theme_toggle

# Configuracao da pagina
st.set_page_config(
    page_title="DataTrack -- Visao Geral do Mercado",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

apply_theme()

# Header
st.markdown(
    """
    <div class="header-section">
        <div class="badge">Panorama do Mercado</div>
        <h1>Visao <span class="accent">Geral</span></h1>
        <div class="subtitle">Principais indicadores de demanda e perfil das vagas da area de dados</div>
    </div>
    """,
    unsafe_allow_html=True
)

# Carrega dados
with st.spinner("Carregando indicadores..."):
    kpis = get_kpis_mercado()
    df_area = get_distribuicao_area()
    df_seniority = get_distribuicao_senioridade()
    df_modalidade = get_modalidade_por_area()

# Cores da nova paleta
MINT = "#00D4AA"
CORAL = "#FF7B54"
GOLD = "#FFD93D"
TEAL = "#14B8A6"

is_dark = st.session_state.get("theme", "dark") == "dark"
text_color = "#8888A8" if is_dark else "#57534E"

# KPIs (4 colunas)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Total de Vagas</div>
            <div class="metric-value" style="color: {MINT};">{kpis['total_vagas']:,}</div>
            <div class="metric-desc">Vagas unificadas</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Trabalho Hibrido</div>
            <div class="metric-value" style="color: {GOLD};">{kpis['hibrido_percent']}%</div>
            <div class="metric-desc">Vagas em modelo hibrido</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Trabalho Remoto</div>
            <div class="metric-value" style="color: {TEAL};">{kpis['remoto_percent']}%</div>
            <div class="metric-desc">Vagas 100% home office</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Novas Vagas (24h)</div>
            <div class="metric-value" style="color: {CORAL};">+{kpis['vagas_hoje']}</div>
            <div class="metric-desc">Adicionadas hoje</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# Graficos
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Vagas por Area de Atuacao")
    if not df_area.empty:
        fig_area = px.bar(
            df_area, x="vagas", y="area", orientation="h",
            color="vagas",
            color_continuous_scale=["#1C1C32", MINT] if is_dark else ["#E7E5E4", "#0D9488"],
            labels={"vagas": "Quantidade de Vagas", "area": "Area de Dados"},
            text_auto=True
        )
        fig_area.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color=text_color,
            coloraxis_showscale=False,
            height=350,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig_area, use_container_width=True)
    else:
        st.info("Sem dados de areas disponiveis.")

with col_right:
    st.subheader("Distribuicao por Senioridade")
    if not df_seniority.empty:
        palette_donut = [MINT, CORAL, GOLD, TEAL, "#A78BFA", "#FB923C"]
        fig_seniority = px.pie(
            df_seniority, values="vagas", names="senioridade",
            hole=0.45,
            color_discrete_sequence=palette_donut
        )
        fig_seniority.update_traces(textposition="inside", textinfo="percent+label")
        fig_seniority.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font_color=text_color,
            height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False
        )
        st.plotly_chart(fig_seniority, use_container_width=True)
    else:
        st.info("Sem dados de senioridade disponiveis.")

st.markdown("<br>", unsafe_allow_html=True)

# Grafico de Modalidade por Area (stacked bar)
st.subheader("Modalidade de Trabalho por Area de Atuacao")
if not df_modalidade.empty:
    fig_modalidade = go.Figure()
    fig_modalidade.add_trace(go.Bar(
        y=df_modalidade["area"], x=df_modalidade["remoto"],
        name="Remoto", orientation="h",
        marker=dict(color=MINT)
    ))
    fig_modalidade.add_trace(go.Bar(
        y=df_modalidade["area"], x=df_modalidade["hybrido"],
        name="Hibrido", orientation="h",
        marker=dict(color=GOLD)
    ))
    fig_modalidade.add_trace(go.Bar(
        y=df_modalidade["area"], x=df_modalidade["presencial"],
        name="Presencial", orientation="h",
        marker=dict(color=CORAL)
    ))
    fig_modalidade.update_layout(
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=text_color,
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_modalidade, use_container_width=True)
else:
    st.info("Sem dados de modalidade disponiveis.")

# Toggle de tema no rodape
st.markdown("<br>", unsafe_allow_html=True)
theme_toggle()
