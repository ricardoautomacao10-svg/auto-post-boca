from flask import Flask, request, jsonify
import os
import logging
import requests

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 🔥 VARIÁVEIS DE AMBIENTE 
INSTAGRAM_ACCESS_TOKEN = os.getenv('PAGE_TOK...', '')
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv('USER_ACC...', '')

@app.route('/')
def index():
    """Página inicial com status completo"""
    try:
        # Verificar se variáveis existem
        token_exists = bool(INSTAGRAM_ACCESS_TOKEN)
        business_id_exists = bool(INSTAGRAM_BUSINESS_ACCOUNT_ID)
        
        # Testar conexão com API
        test_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}?fields=name,instagram_business_account&access_token={INSTAGRAM_ACCESS_TOKEN}"
        response = requests.get(test_url, timeout=10)
        
        status = "✅" if response.status_code == 200 else "❌"
        
        return f"""
        <h1>🔧 Status do Sistema Boca no Trombone</h1>
        <p><b>Access Token:</b> {token_exists and '✅ Configurado' or '❌ Não configurado'}</p>
        <p><b>Business ID:</b> {business_id_exists and '✅ Configurado' or '❌ Não configurado'}</p>
        <p><b>Conexão API:</b> {status} Código: {response.status_code}</p>
        <p><b>Business Account ID:</b> {INSTAGRAM_BUSINESS_ACCOUNT_ID}</p>
        <p><b>Access Token (início):</b> {INSTAGRAM_ACCESS_TOKEN[:20] if INSTAGRAM_ACCESS_TOKEN else 'N/A'}...</p>
        <br>
        <p><a href="/verificar-detalhes">🔍 Ver detalhes completos</a></p>
        <p><a href="/testar-instagram">🧪 Testar publicação</a></p>
        """
        
    except Exception as e:
        return f"<h1>❌ Erro na verificação:</h1><p>{str(e)}</p>"

@app.route('/verificar-detalhes')
def verificar_detalhes():
    """Verificação detalhada da API"""
    try:
        test_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}?fields=name,instagram_business_account,connected_instagram_account&access_token={INSTAGRAM_ACCESS_TOKEN}"
        response = requests.get(test_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return f"""
            <h1>✅ Configuração OK!</h1>
            <pre>{json.dumps(data, indent=2, ensure_ascii=False)}</pre>
            <p><b>Business Account ID:</b> {INSTAGRAM_BUSINESS_ACCOUNT_ID}</p>
            <p><b>Access Token (início):</b> {INSTAGRAM_ACCESS_TOKEN[:20]}...</p>
            """
        else:
            return f"""
            <h1>❌ Erro na API</h1>
            <pre>{json.dumps(response.json(), indent=2)}</pre>
            <p><b>Business Account ID:</b> {INSTAGRAM_BUSINESS_ACCOUNT_ID}</p>
            <p><b>Access Token (início):</b> {INSTAGRAM_ACCESS_TOKEN[:20] if INSTAGRAM_ACCESS_TOKEN else 'N/A'}...</p>
            """
            
    except Exception as e:
        return f"<h1>❌ Erro:</h1><p>{str(e)}</p>"

@app.route('/testar-instagram')
def testar_instagram():
    """Teste simples de publicação"""
    try:
        # Testar apenas a criação de mídia (sem publicar)
        test_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
        payload = {
            'image_url': 'https://jornalvozdolitoral.com/wp-content/uploads/2025/08/image-59.png',
            'caption': '✅ Teste de publicação - Sistema Boca no Trombone',
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        response = requests.post(test_url, data=payload, timeout=30)
        result = response.json()
        
        return f"""
        <h1>🧪 Teste de Publicação</h1>
        <pre>{json.dumps(result, indent=2)}</pre>
        <p><b>Status:</b> {response.status_code}</p>
        """
        
    except Exception as e:
        return f"<h1>❌ Erro no teste:</h1><p>{str(e)}</p>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info("🚀 Sistema de verificação iniciado!")
    app.run(host='0.0.0.0', port=port, debug=False)
