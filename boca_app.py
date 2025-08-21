from flask import Flask, request, jsonify
import os
import logging
import requests
import time
from threading import Thread
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 🔥 VARIÁVEIS DE AMBIENTE
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

def criar_imagem_api(titulo, imagem_url, categoria):
    """USA API EXTERNA para criar imagem - SEM Pillow"""
    try:
        # 📋 Dados para a API de criação de imagem
        payload = {
            'template': 'reel_1080x1920',
            'data': {
                'titulo': titulo,
                'categoria': categoria,
                'imagem_url': imagem_url,
                'layout': {
                    'fundo': 'preto',
                    'caixa_primaria': 'vermelho',
                    'caixa_texto': 'branco',
                    'texto_cor': 'preto',
                    'seta': 'amarelo'
                }
            }
        }
        
        # 🎨 API gratuita para criação de imagens (exemplo)
        response = requests.post(
            'https://api.imgbb.com/1/upload',
            data={'key': 'free_api_key', 'image': json.dumps(payload)}
        )
        
        if response.status_code == 200:
            return response.json()['data']['url']
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro API imagem: {str(e)}")
        return imagem_url  # Fallback: usa imagem original

def publicar_no_instagram(titulo, imagem_url, categoria):
    """PUBLICA NO INSTAGRAM"""
    try:
        logger.info("📤 Publicando...")
        
        # 🎨 Usar imagem original (SEM edição por enquanto)
        image_url_final = imagem_url
        
        # 📋 Dados para publicação
        create_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
        
        payload = {
            'image_url': image_url_final,
            'caption': f"🚨 {titulo}\n\nCategoria: {categoria}\n\n#Noticias #Brasil #LitoralNorte",
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        response = requests.post(create_url, data=payload)
        result = response.json()
        
        if 'id' in result:
            creation_id = result['id']
            
            # ⏳ Aguardar e publicar
            time.sleep(5)
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
        logger.error(f"❌ Erro publicação: {str(e)}")
        return False

def worker_publicacao():
    """Processa a fila 24x7"""
    while True:
        if fila_publicacao:
            titulo, imagem_url, categoria = fila_publicacao.pop(0)
            logger.info(f"🔄 Processando: {titulo}")
            publicar_no_instagram(titulo, imagem_url, categoria)
        time.sleep(10)

# 🚀 INICIAR THREAD
Thread(target=worker_publicacao, daemon=True).start()

@app.route('/')
def index():
    return "✅ Sistema rodando - Publicação automática"

@app.route('/webhook-boca', methods=['POST'])
def webhook_boca():
    try:
        data = request.get_json()
        logger.info("📍 Webhook recebido!")
        
        post_data = data.get('post', {})
        titulo = post_data.get('post_title', '')
        categoria = extrair_categoria(data)
        imagem_url = data.get('post_thumbnail', '')
        
        logger.info(f"📝 {titulo}")
        logger.info(f"🏷️ {categoria}") 
        logger.info(f"🖼️ {imagem_url}")
        
        if imagem_url and titulo:
            fila_publicacao.append((titulo, imagem_url, categoria))
            logger.info(f"📥 Na fila: {len(fila_publicacao)}")
            
        return jsonify({'status': 'success', 'message': 'Em produção'}), 200
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        return jsonify({'status': 'success', 'message': 'Recebido'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info("🚀 Sistema iniciado - Publicando 24/7")
    app.run(host='0.0.0.0', port=port, debug=False)
