from flask import Flask, request, jsonify
import os
import logging
import requests
import time

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 🔥 VARIÁVEIS DE AMBIENTE (USE AS QUE VOCÊ JÁ TEM)
INSTAGRAM_ACCESS_TOKEN = os.getenv('PAGE_TOK...', '')
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv('USER_ACC...', '')

def extrair_categoria(data):
    """Extrai a categoria dos dados do WordPress"""
    try:
        taxonomies = data.get('taxonomies', {})
        categories = taxonomies.get('category', {})
        if categories:
            return list(categories.keys())[0].upper()
        return 'NOTÍCIAS'
    except:
        return 'NOTÍCIAS'

def publicar_no_instagram(titulo, imagem_url, categoria):
    """PUBLICA DIRETAMENTE NO INSTAGRAM - AGORA MESMO"""
    try:
        logger.info(f"🚀 TENTANDO PUBLICAR: {titulo}")
        
        # URL da API do Instagram
        create_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
        
        # Dados para publicação
        payload = {
            'image_url': imagem_url,
            'caption': f"📢 {titulo}\n\n📍 Categoria: {categoria}\n\n🔔 Siga para mais notícias!\n\n#Noticias #Brasil #LitoralNorte #Jornalismo",
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        # 1. Criar mídia
        response = requests.post(create_url, data=payload, timeout=30)
        result = response.json()
        
        logger.info(f"📦 Resposta da API: {result}")
        
        if 'id' in result:
            creation_id = result['id']
            logger.info(f"📦 Mídia criada: {creation_id}")
            
            # 2. Publicar a mídia
            time.sleep(3)
            
            publish_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
            publish_payload = {
                'creation_id': creation_id,
                'access_token': INSTAGRAM_ACCESS_TOKEN
            }
            
            publish_response = requests.post(publish_url, data=publish_payload, timeout=30)
            publish_result = publish_response.json()
            
            logger.info(f"📦 Resposta da publicação: {publish_result}")
            
            if 'id' in publish_result:
                logger.info(f"✅ PUBLICAÇÃO CONCLUÍDA! ID: {publish_result['id']}")
                return True
            else:
                logger.error(f"❌ Erro na publicação: {publish_result}")
                return False
        else:
            logger.error(f"❌ Erro ao criar mídia: {result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro na publicação: {str(e)}")
        return False

@app.route('/')
def index():
    return "✅ Sistema Boca no Trombone - PUBLICAÇÃO DIRETA"

@app.route('/webhook-boca', methods=['POST'])
def webhook_boca():
    try:
        data = request.get_json()
        logger.info("📍 Webhook recebido do WordPress!")
        
        # Extrair dados
        post_data = data.get('post', {})
        titulo = post_data.get('post_title', 'Título não disponível').strip()
        categoria = extrair_categoria(data)
        imagem_url = data.get('post_thumbnail', '').strip()
        
        # Log dos dados recebidos
        logger.info(f"📝 Título: {titulo}")
        logger.info(f"🏷️ Categoria: {categoria}")
        logger.info(f"🖼️ Imagem: {imagem_url}")
        
        # ✅ PUBLICAR DIRETAMENTE - SEM FILA, SEM THREAD!
        if titulo and imagem_url.startswith('http'):
            logger.info("🔥 PUBLICANDO DIRETAMENTE AGORA!")
            sucesso = publicar_no_instagram(titulo, imagem_url, categoria)
            
            if sucesso:
                logger.info("🎉 PUBLICAÇÃO REALIZADA COM SUCESSO!")
                return jsonify({'status': 'success', 'message': 'Publicado no Instagram'}), 200
            else:
                logger.warning("⚠️ Falha na publicação, mas webhook recebido")
                return jsonify({'status': 'success', 'message': 'Recebido - publicação falhou'}), 200
        else:
            logger.warning("⚠️ Dados incompletos recebidos")
            return jsonify({'status': 'success', 'message': 'Recebido - dados incompletos'}), 200
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook: {str(e)}")
        return jsonify({'status': 'success', 'message': 'Recebido'}), 200

@app.route('/testar-instagram')
def testar_instagram():
    """Testa a conexão com a API do Instagram"""
    try:
        test_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}?fields=name&access_token={INSTAGRAM_ACCESS_TOKEN}"
        response = requests.get(test_url, timeout=10)
        
        if response.status_code == 200:
            return f"✅ CONEXÃO OK! Conta: {response.json().get('name', 'Nome não disponível')}"
        else:
            return f"❌ ERRO: {response.json()}"
            
    except Exception as e:
        return f"❌ FALHA: {str(e)}"

@app.route('/testar-publicacao')
def testar_publicacao():
    """Testa uma publicação agora mesmo"""
    sucesso = publicar_no_instagram(
        "✅ TESTE: Sistema Boca no Trombone funcionando!",
        "https://jornalvozdolitoral.com/wp-content/uploads/2025/08/image-59.png",
        "TESTE"
    )
    
    if sucesso:
        return "✅ PUBLICAÇÃO REALIZADA!", 200
    else:
        return "❌ Falha na publicação. Verifique logs.", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info("🚀 SISTEMA INICIADO - PUBLICAÇÃO DIRETA!")
    app.run(host='0.0.0.0', port=port, debug=False)
