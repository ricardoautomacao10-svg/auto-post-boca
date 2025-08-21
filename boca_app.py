from flask import Flask, request
import requests
import os
import threading
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

PAGE_TOKEN_BOCA = os.getenv('PAGE_TOKEN_BOCA')
WORDPRESS_URL = "https://jornalvozdolitoral.com/wp-json/wp/v2/media/"

def get_image_url_from_wordpress(image_id):
    """Busca a URL da imagem no WordPress usando a API REST"""
    try:
        logger.info(f"📡 Buscando imagem {image_id} no WordPress...")
        
        response = requests.get(f"{WORDPRESS_URL}{image_id}", timeout=10)
        
        if response.status_code == 200:
            media_data = response.json()
            image_url = media_data.get('source_url')  # URL completa da imagem
            logger.info(f"✅ Imagem encontrada: {image_url}")
            return image_url
        else:
            logger.error(f"❌ Erro ao buscar imagem: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Erro na busca da imagem: {str(e)}")
        return None

def publicar_facebook(video_url, caption):
    """Publica vídeo no Facebook"""
    try:
        logger.info("📤 Publicando no Facebook...")
        
        if not PAGE_TOKEN_BOCA:
            logger.error("❌ Token não configurado")
            return False
            
        # Formata URL para MP4
        if '/upload/' in video_url and '/f_mp4/' not in video_url:
            video_url = video_url.replace('/upload/', '/upload/f_mp4/')
        
        params = {
            'access_token': PAGE_TOKEN_BOCA,
            'file_url': video_url,
            'description': caption[:1000] + "\n\nLeia a matéria completa no site! 📖"
        }
        
        response = requests.post(
            'https://graph.facebook.com/v23.0/213776928485804/videos',
            params=params,
            timeout=60
        )
        
        if response.status_code == 200:
            logger.info("🎉 ✅ VÍDEO PUBLICADO NO FACEBOOK!")
            return True
        else:
            logger.error(f"❌ Erro: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro na publicação: {str(e)}")
        return False

@app.route('/webhook-boca', methods=['POST'])
def handle_webhook():
    try:
        logger.info("📍 Recebendo dados do WordPress...")
        
        data = request.json
        logger.info("📦 Dados recebidos com sucesso!")
        
        # 🔥 EXTRAIR ID DA IMAGEM do post_meta
        post_meta = data.get('post_meta', {})
        thumbnail_id = post_meta.get('_thumbnail_id', [None])[0]  # Pega o primeiro valor do array
        
        if not thumbnail_id:
            logger.error("❌ Nenhum ID de imagem encontrado")
            return "❌ ID da imagem não encontrado", 400
        
        caption = data.get('post', {}).get('post_title') or data.get('post', {}).get('post_excerpt')
        
        logger.info(f"🖼️ ID da Imagem: {thumbnail_id}")
        logger.info(f"📋 Legenda: {caption}")
        
        if not caption:
            logger.error("❌ Legenda não encontrada")
            return "❌ Legenda não encontrada", 400
        
        # 🔥 BUSCAR URL DA IMAGEM no WordPress
        image_url = get_image_url_from_wordpress(thumbnail_id)
        
        if not image_url:
            logger.error("❌ Não foi possível obter a URL da imagem")
            return "❌ Erro ao buscar imagem", 500
        
        logger.info(f"✅ URL da imagem: {image_url}")
        
        # 🔥 AQUI VOCÊ CRIARIA O VÍDEO COM A IMAGEM
        # Por enquanto, teste com vídeo existente
        video_url_test = "https://res.cloudinary.com/dj1h27ueg/video/upload/v1755717469/boca_reels/i6pys2w5cwwu1t1zfvs4.mp4"
        
        logger.info("✅ Dados válidos - Publicando...")
        
        # Publicar em background
        thread = threading.Thread(target=publicar_facebook, args=(video_url_test, caption))
        thread.start()
        
        return "✅ Recebido! Publicação em andamento...", 200
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        return "Erro", 500

@app.route('/teste-imagem/<image_id>')
def teste_imagem(image_id):
    """Teste manual de busca de imagem"""
    image_url = get_image_url_from_wordpress(image_id)
    if image_url:
        return {"image_url": image_url}, 200
    else:
        return {"error": "Imagem não encontrada"}, 404

@app.route('/')
def home():
    return "🚀 Sistema Funcionando! Buscando imagens do WordPress...", 200

if __name__ == '__main__':
    logger.info("✅ Servidor pronto - Buscando imagens do WordPress!")
    app.run(host='0.0.0.0', port=10000)
