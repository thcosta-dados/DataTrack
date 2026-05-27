import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_pipeline_status_atual, get_pipeline_evolucao_diaria, get_pipeline_logs
from theme import apply_theme, theme_toggle

# 1. Configuração da página
st.set_page_config(
    page_title="DataTrack — Telemetria do Pipeline",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Aplica o Tema Operacional
apply_theme()

# Cabeçalho Principal com classe de destaque de telemetria
st.markdown("<h1 class='telemetry-title' style='margin-bottom: 0px;'>⚡ DataTrack Telemetry</h1>", unsafe_allow_html=True)
st.markdown("<p class='subheader' style='margin-top: 0px; font-size: 1.1em;'>Monitoramento de integridade das cargas, volumes e saúde do pipeline de dados</p>", unsafe_allow_html=True)

# 3. Carrega os dados operacionais
with st.spinner("Buscando status de telemetria..."):
    status_atual = get_pipeline_status_atual()
    df_evolucao = get_pipeline_evolucao_diaria(dias=30)
    df_recent_logs = get_pipeline_logs(dias=5)

# 4. KPIs no topo
if status_atual:
    col1, col2, col3, col4 = st.columns(4)
    
    # Status Dinâmico (Verde para sucesso, vermelho para falha)
    status_color = "#10B981" if status_atual["status"] == "SUCCESS" else "#EF4444"
    status_emoji = "✅" if status_atual["status"] == "SUCCESS" else "❌"
    
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <small style="color: #94A3B8; text-transform: uppercase; font-weight: 600; font-size: 0.8em;">Status da Execução</small>
                <h2 style="margin: 5px 0px; font-size: 1.8em; color: {status_color};">{status_emoji} {status_atual['status']}</h2>
                <small style="color: #64748B;">Data: {status_atual['execution_date'].strftime('%d/%m/%Y')}</small>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <small style="color: #94A3B8; text-transform: uppercase; font-weight: 600; font-size: 0.8em;">Registros Brutos</small>
                <h2 style="margin: 5px 0px; font-size: 1.8em; color: #00F2FE;">{status_atual['raw_inserted']}</h2>
                <small style="color: #64748B;">Ingeridos na Bronze</small>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <small style="color: #94A3B8; text-transform: uppercase; font-weight: 600; font-size: 0.8em;">Novas Vagas (Silver)</small>
                <h2 style="margin: 5px 0px; font-size: 1.8em; color: #4FACFE;">{status_atual['dedup_new']}</h2>
                <small style="color: #64748B;">Registradas pós-dedup</small>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    # Calcula taxa de deduplicação
    total = status_atual['raw_inserted']
    duplicates = status_atual['dedup_duplicates']
    dedup_rate = round((duplicates * 100.0) / total, 1) if total > 0 else 0.0

    with col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <small style="color: #94A3B8; text-transform: uppercase; font-weight: 600; font-size: 0.8em;">Taxa de Deduplicação</small>
                <h2 style="margin: 5px 0px; font-size: 1.8em; color: #F59E0B;">{dedup_rate}%</h2>
                <small style="color: #64748B;">{duplicates} duplicadas detectadas</small>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.info("Nenhum log de execução de pipeline encontrado no banco de dados. Execute a DAG para popular as tabelas.")

st.markdown("<br>", unsafe_allow_html=True)

# 5. Gráfico de Evolução Diária (Deteção de quebras ou rate limits)
st.subheader("Volumetria de Ingestão por Fonte (Últimos 30 dias)")
st.markdown("<p class='subheader' style='font-size: 0.9em; margin-bottom: 10px;'>Monitore se alguma API ou scraper parou de retornar dados para manter a integridade operacional do data lake.</p>", unsafe_allow_html=True)

if df_evolucao is not None and not df_evolucao.empty:
    # Transforma dados para Plotly Line
    df_melted = df_evolucao.melt(id_vars=["data"], value_vars=["adzuna", "jooble", "remoteok", "gupy"], 
                                  var_name="Fonte", value_name="Vagas")
    df_melted["Fonte"] = df_melted["Fonte"].map({"adzuna": "Adzuna", "jooble": "Jooble", "remoteok": "RemoteOK", "gupy": "Gupy"})
    
    fig_evolucao = px.line(
        df_melted,
        x="data",
        y="Vagas",
        color="Fonte",
        markers=True,
        color_discrete_sequence=["#6C63FF", "#3B82F6", "#10B981", "#F59E0B"]
    )
    
    fig_evolucao.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color="#94A3B8" if st.session_state["theme"] == "dark" else "#1E293B",
        height=350,
        margin=dict(l=10, r=10, t=10, b=10)
    )
    st.plotly_chart(fig_evolucao, use_container_width=True)
else:
    st.info("Dados de evolução insuficientes.")

st.markdown("<br><br>", unsafe_allow_html=True)

# 6. Tabela rápida das últimas execuções
st.subheader("Últimas Execuções Registradas")
if df_recent_logs is not None and not df_recent_logs.empty:
    # Formata colunas para visualização operacional
    display_logs = df_recent_logs.copy()
    display_logs["inicio"] = pd.to_datetime(display_logs["inicio"]).dt.strftime('%d/%m/%Y %H:%M:%S')
    display_logs["fim"] = pd.to_datetime(display_logs["fim"]).dt.strftime('%d/%m/%Y %H:%M:%S')
    # Seleciona e ordena colunas explicitamente
    display_logs = display_logs[["data", "inicio", "fim", "duracao_segundos", "status", "bruto", "novos", "duplicados", "classificados", "erro"]]
    display_logs.columns = ["Data", "Início", "Término", "Duração (s)", "Status", "Bruto", "Novos", "Duplicados", "Classificados", "Mensagem de Erro"]
    
    st.dataframe(
        display_logs,
        use_container_width=True,
        hide_index=True
    )

# Toggle de Aparência no Sidebar
theme_toggle()
