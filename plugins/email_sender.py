import os
import logging
from silver.db import get_connection
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger(__name__)

def send_daily_digest(**kwargs):
    """
    Função principal executada pelo Airflow.
    Busca novas vagas coletadas e envia um e-mail resumo diário para os assinantes.
    """
    # Recupera execution_date do Airflow (ds) ou usa a data atual como fallback
    execution_date = kwargs.get("ds") or kwargs.get("execution_date")
    if not execution_date:
        from datetime import datetime
        execution_date = datetime.now().strftime("%Y-%m-%d")
        
    logger.info("Iniciando processo de E-mail Digest para a data: %s", execution_date)
    
    conn = get_connection()
    query = """
        SELECT 
            f.job_title as title,
            c.company_name as company,
            l.location_name as location,
            a.area_label as area,
            -- Formata modalidade
            CASE 
                WHEN f.is_remote = true THEN 'Remoto 🌐'
                WHEN f.is_hybrid = true THEN 'Híbrido 🏢'
                ELSE 'Presencial 🏢'
            END as modalidade,
            f.job_url as url
        FROM gold.fact_job_posting f
        JOIN gold.dim_company c ON f.company_id = c.company_id
        JOIN gold.dim_location l ON f.location_id = l.location_id
        JOIN gold.dim_area a ON f.area_code = a.area_code
        -- Filtra vagas publicadas no último dia (mesmo dia da rodada)
        WHERE f.posted_date = %s::date
        ORDER BY f.posted_date DESC, f.job_id
        LIMIT 10
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(query, (execution_date,))
            vagas = cur.fetchall()
    except Exception as e:
        logger.error("Erro ao buscar vagas na Gold Layer para e-mail: %s", str(e))
        raise
    finally:
        conn.close()
        
    if not vagas:
        logger.info("Nenhuma nova vaga encontrada na data %s. E-mail digest cancelado.", execution_date)
        return "skipped_no_jobs"
        
    logger.info("%d novas vagas encontradas. Construindo HTML...", len(vagas))
    
    # 2. Constrói template HTML Premium
    vagas_html = ""
    for v in vagas:
        vagas_html += f"""
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 15px; border-radius: 8px; margin-bottom: 12px;">
            <h3 style="margin: 0px 0px 5px 0px; color: #1E293B; font-family: sans-serif;">{v[0]}</h3>
            <p style="margin: 0px; font-size: 0.9em; color: #64748B; font-family: sans-serif;">
                🏢 <b>{v[1]}</b> | 📍 {v[2]} | 💼 {v[4]}
            </p>
            <p style="margin: 5px 0px 0px 0px; font-size: 0.85em; color: #6C63FF; font-family: sans-serif; font-weight: bold;">
                Categoria: {v[3]}
            </p>
            <div style="margin-top: 10px;">
                <a href="{v[5]}" target="_blank" style="background-color: #4F46E5; color: white; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-size: 0.85em; font-family: sans-serif; font-weight: bold; display: inline-block;">
                    Candidatar-se / Ver Origem
                </a>
            </div>
        </div>
        """
        
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="margin: 0; padding: 20px; background-color: #F1F5F9; font-family: sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #FFFFFF; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); overflow: hidden; border: 1px solid #E2E8F0;">
            <div style="background: linear-gradient(90deg, #6C63FF 0%, #4F46E5 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0px; font-size: 24px; letter-spacing: -0.5px;">🔍 DataTrack Digest</h1>
                <p style="color: rgba(255,255,255,0.8); margin: 5px 0px 0px 0px; font-size: 14px;">As melhores vagas de dados consolidadas nas últimas 24 horas</p>
            </div>
            <div style="padding: 25px;">
                <p style="font-size: 15px; color: #334155; line-height: 1.5;">
                    Olá Thiago!<br>
                    Aqui está a sua dose diária de inteligência do mercado de dados de <b>{execution_date}</b>.
                </p>
                
                <h2 style="font-size: 18px; color: #0F172A; margin: 25px 0px 15px 0px; border-bottom: 2px solid #E2E8F0; padding-bottom: 5px;">
                    🔥 Destaques de Vagas de Dados
                </h2>
                
                {vagas_html}
                
                <br>
                <div style="text-align: center; margin-top: 15px;">
                    <a href="https://share.streamlit.io/thiago/datatrack" target="_blank" style="background-color: #10B981; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-size: 15px; font-weight: bold; display: inline-block; box-shadow: 0 4px 8px rgba(16, 185, 129, 0.2);">
                        📊 Acessar Dashboard Completo
                    </a>
                </div>
            </div>
            <div style="background-color: #F8FAFC; padding: 15px; text-align: center; border-top: 1px solid #E2E8F0; font-size: 12px; color: #94A3B8;">
                DataTrack © 2026. Projeto de Portfólio.
            </div>
        </div>
    </body>
    </html>
    """

    # 3. Disparo do e-mail via SendGrid
    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        logger.warning("SENDGRID_API_KEY não configurada no ambiente. Fallback ativo: exibindo corpo HTML de auditoria.")
        # Salva o arquivo de e-mail na pasta logs para inspeção de portfólio
        local_log_path = "logs/last_email_digest.html"
        try:
            with open(local_log_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info("HTML de e-mail salvo com sucesso para auditoria em: %s", local_log_path)
        except Exception as write_err:
            logger.error("Falha ao salvar HTML de e-mail localmente: %s", str(write_err))
        return "skipped_no_key"
        
    message = Mail(
        from_email='alerts@datatrack.com',
        to_emails='thiago@exemplo.com', # O e-mail do Thiago (ou configurado via env)
        subject=f'DataTrack Digest — {execution_date}',
        html_content=html_content
    )
    
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        logger.info("E-mail enviado via SendGrid com status: %d", response.status_code)
        return "sent"
    except Exception as send_err:
        logger.error("Falha ao enviar e-mail via SendGrid: %s", str(send_err))
        raise
