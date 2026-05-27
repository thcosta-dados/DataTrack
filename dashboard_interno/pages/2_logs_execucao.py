import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_pipeline_logs
from theme import apply_theme, theme_toggle

# 1. Configuração da página
st.set_page_config(
    page_title="DataTrack — Histórico de Logs",
    page_icon="📋",
    layout="wide"
)

# 2. Aplica o Tema Operacional
apply_theme()

# Cabeçalho Principal
st.markdown("<h1>📋 Histórico de Logs de Execução</h1>", unsafe_allow_html=True)
st.markdown("<p class='subheader' style='margin-bottom: 25px;'>Drill-down detalhado sobre o histórico de rodadas e diagnósticos de erros</p>", unsafe_allow_html=True)

# 3. Sidebar de Filtros
st.sidebar.markdown("### Filtros de Auditoria")
status_filter = st.sidebar.selectbox("Filtrar por Status", options=["Todos", "SUCCESS", "FAILED", "RUNNING"])
dias_filter = st.sidebar.slider("Janela de Histórico (Dias)", min_value=7, max_value=90, value=30)

selected_status = None if status_filter == "Todos" else status_filter

# Carrega os dados
with st.spinner("Buscando logs históricos..."):
    df_logs = get_pipeline_logs(dias=dias_filter, status_filter=selected_status)

# 4. Renderização
if df_logs is not None and not df_logs.empty:
    # Gráfico de Latência Operacional
    df_sucesso = df_logs[df_logs["status"] == "SUCCESS"].copy()
    if not df_sucesso.empty:
        df_sucesso = df_sucesso.sort_values(by="data")
        df_sucesso["data_dt"] = pd.to_datetime(df_sucesso["data"])
        fig_duracao = px.line(
            df_sucesso,
            x="data_dt",
            y="duracao_segundos",
            markers=True,
            labels={"data_dt": "Data de Execução", "duracao_segundos": "Duração (segundos)"}
        )
        fig_duracao.update_traces(
            line_color="#00F2FE",
            marker=dict(size=6, color="#00F2FE")
        )
        fig_duracao.update_layout(
            title={
                "text": "⏱️ Histórico de Latência do Pipeline (Execuções bem-sucedidas)",
                "font": {"size": 16}
            },
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color="#94A3B8" if st.session_state["theme"] == "dark" else "#1E293B",
            height=280,
            margin=dict(l=10, r=10, t=50, b=10),
            xaxis=dict(
                showgrid=True, 
                gridcolor="rgba(148, 163, 184, 0.1)",
                tickformat="%d/%m/%Y"
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor="rgba(148, 163, 184, 0.1)"
            )
        )
        st.plotly_chart(fig_duracao, use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
    display_df = df_logs.copy()
    
    # Formatação das Datas para visualização
    display_df["data"] = pd.to_datetime(display_df["data"]).dt.strftime('%d/%m/%Y')
    display_df["inicio"] = pd.to_datetime(display_df["inicio"]).dt.strftime('%d/%m/%Y %H:%M:%S')
    
    # Previne erros se a coluna 'fim' contiver nulos (ex: execução em andamento)
    display_df["fim"] = pd.to_datetime(display_df["fim"]).apply(
        lambda x: x.strftime('%d/%m/%Y %H:%M:%S') if pd.notnull(x) else "Em Execução..."
    )
    
    # Exibe tabela interativa
    st.subheader("Auditoria de Execuções")
    st.markdown("<p class='subheader' style='font-size: 0.9em; margin-bottom: 10px;'>Selecione qualquer linha para inspecionar erros ou métricas de tempo detalhadas.</p>", unsafe_allow_html=True)
    
    event = st.dataframe(
        display_df[["data", "inicio", "fim", "status", "bruto", "novos", "duplicados", "classificados"]],
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun"
    )
    
    # 5. Inspeciona a linha selecionada (Drill-down)
    if event and event.get("selection") and event["selection"].get("rows"):
        selected_row_idx = event["selection"]["rows"][0]
        log_selecionado = df_logs.iloc[selected_row_idx]
        
        st.markdown("---")
        st.subheader(f"🔍 Detalhes da Carga de {pd.to_datetime(log_selecionado['data']).strftime('%d/%m/%Y')}")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 📊 Métricas de Volume")
            st.markdown(f"📥 **Ingeridos na Bronze:** {log_selecionado['bruto']} registros brutos")
            st.markdown(f"✨ **Identificados como novos:** {log_selecionado['novos']} vagas")
            st.markdown(f"🛡️ **Identificados como duplicados:** {log_selecionado['duplicados']} registros")
            st.markdown(f"🏷️ **Classificados na Silver:** {log_selecionado['classificados']} vagas")
            
        with col2:
            st.markdown("### ⏱️ Auditoria Temporal")
            st.markdown(f"🚀 **Horário de início:** {pd.to_datetime(log_selecionado['inicio']).strftime('%H:%M:%S')}")
            
            if pd.notnull(log_selecionado['fim']):
                duracao = pd.to_datetime(log_selecionado['fim']) - pd.to_datetime(log_selecionado['inicio'])
                segundos = int(duracao.total_seconds())
                st.markdown(f"🏁 **Horário de término:** {pd.to_datetime(log_selecionado['fim']).strftime('%H:%M:%S')}")
                st.markdown(f"⏱️ **Duração total:** `{segundos}` segundos")
            else:
                st.markdown("🏁 **Horário de término:** N/A")
                st.markdown("⏱️ **Duração total:** Em execução...")
        
        # Se falhou, renderiza a mensagem de erro física com destaque
        if log_selecionado["status"] == "FAILED":
            st.markdown("### ❌ Rastreamento do Erro (Error Stack)")
            erro_msg = log_selecionado["erro"] or "Sem log de erro detalhado disponível."
            st.error(erro_msg)
else:
    st.info("Nenhum log encontrado para a combinação de filtros selecionada.")

# Toggle de Aparência no Sidebar
theme_toggle()
