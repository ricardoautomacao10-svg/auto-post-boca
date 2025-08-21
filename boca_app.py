from flask import Flask, request, jsonify
import os
import logging
import requests
import time
from threading import Thread

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 🔥 VARIÁVEIS DE AMBIENTE (já configuradas no Render)
INSTAGRAM_ACCESS_TOKEN = os.getenv('PAGE_TOK...', '')
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv('USER_ACC...', '')

# 📋 FILA de publicações
fila_publicacao = []

def extrair_categoria(data):
    """Extrai a categoria dos dados do WordPress"""
    try:
        taxonomies = data.get('taxonomies', {})
        categories = taxonomies.get('category', {})
        if categories:
            return list(categories.keys())[0].upper()
        return 'GERAL'
    except:
        return 'UBATUBA'

def publicar_no_instagram(titulo, imagem_url, categoria):
    """PUBLICA EFETIVAMENTE NO INSTAGRAM"""
    try:
        logger.info("📤 Publicando no Instagram...")
        
        # 1. Criar contêiner de mídia
        create_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
        
        payload = {
            'image_url': imagem_url,
            'caption': f"🚨 {titulo}\n\nCategoria: {categoria}\n\n#Noticias #Brasil #LitoralNorte",
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        response = requests.post(create_url, data=payload)
        result = response.json()
        
        if 'id' in result:
            creation_id = result['id']
            logger.info(f"📦 Mídia criada: {creation_id}")
            
            # 2. Publicar o contêiner
            time.sleep(5)  # Aguardar processamento
            
            publish_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
            publish_payload = {
                'creation_id': creation_id,
                'access_token': INSTAGRAM_ACCESS_TOKEN
            }
            
            publish_response = requests.post(publish_url, data=publish_payload)
            publish_result = publish_response.json()
            
            if 'id' in publish_result:
                logger.info(f"✅ PUBLICADO! ID: {publish_result['id']}")
                return True
            
        logger.error(f"❌ Erro: {result}")
        return False
            
    except Exception as e:
        logger.error(f"❌ Erro na publicação: {str(e)}")
        return False

def worker_publicacao():
    """Processa a fila de publicação 24x7"""
    while True:
        if fila_publicacao:
            titulo, imagem_url, categoria = fila_publicacao.pop(0)
            publicar_no_instagram(titulo, imagem_url, categoria)
        time.sleep(10)  # Verifica a cada 10 segundos

# 🚀 INICIAR THREAD EM SEGUNDO PLANO
Thread(target=worker_publicacao, daemon=True).start()

@app.route('/')
def index():
    return "✅ Sistema rodando 24x7 - Boca no Trombone"

@app.route('/webhook-boca', methods=['POST'])
def webhook_boca():
    try:
        data = request.get_json()
        logger.info("📍 Webhook recebido!")
        
        # Extrair dados
        post_data = data.get('post', {})
        titulo = post_data.get('post_title', '')
        categoria = extrair_categoria(data)
        imagem_url = data.get('post_thumbnail', '')
        
        logger.info(f"📝 {titulo}")
        logger.info(f"🏷️ {categoria}")
        logger.info(f"🖼️ {imagem_url}")
        
        # ✅ ADICIONAR À FILA DE PUBLICAÇÃO
        if imagem_url and titulo:
            fila_publicacao.append((titulo, imagem_url, categoria))
            logger.info(f"📥 Adicionado à fila. Total: {len(fila_publicacao)}")
            
        return jsonify({'status': 'success', 'message': 'Em processamento'}), 200
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        return jsonify({'status': 'success', 'message': 'Recebido'}), 200

@app.route('/status')
def status():
    """Verificar status do sistema"""
    return {
        'status': 'online',
        'fila_publicacao': len(fila_publicacao),
        'ultimas_publicacoes': fila_publicacao[-5:] if fila_publicacao else []
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info("🚀 Sistema iniciado - Rodando 24x7")
    app.run(host='0.0.0.0', port=port, debug=False)
