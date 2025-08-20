from flask import Flask, request
import requests
import os
import threading
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Token da página (configure no Render.com)
PAGE_TOKEN_BOCA = os.getenv('PAGE_TOKEN_BOCA')

def publicar_facebook(video_url, caption):
    """Publica vídeo no Facebook"""
    try:
        logger.info("📤 Iniciando publicação no Facebook...")
        
        if not PAGE_TOKEN_BOCA:
            logger.error("❌ Token não configurado")
            return False
            
        # Formata URL para MP4
        if '/upload/' in video_url and '/f_mp4/' not in video_url:
            video_url = video_url.replace('/upload/', '/upload/f_mp4/')
        
        # Parâmetros da API
        params = {
            'access_token': PAGE_TOKEN_BOCA,
            'file_url': video_url,
            'description': caption[:1000]
        }
        
        # Publicar
        response = requests.post(
            'https://graph.facebook.com/v23.0/213776928485804/videos',
            params=params,
            timeout=60
        )
        
        if response.status_code == 200:
            logger.info("🎉 ✅ VÍDEO PUBLICADO NO FACEBOOK!")
            logger.info(f"📦 ID: {response.json().get('id')}")
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
        logger.info("📍 Recebendo vídeo do WordPress...")
        
        data = request.json
        video_url = data.get('video_url', '')
        caption = data.get('caption', '')
        
        if not video_url or not caption:
            return "❌ Dados incompletos", 400
        
        # Publicar em background
        thread = threading.Thread(target=publicar_facebook, args=(video_url, caption))
        thread.start()
        
        return "✅ Vídeo recebido! Publicando...", 200
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook: {str(e)}")
        return "Erro", 500

@app.route('/teste')
def teste():
    """Teste manual"""
    video_url = "https://res.cloudinary.com/dj1h27ueg/video/upload/v1755717469/boca_reels/i6pys2w5cwwu1t1zfvs4.mp4"
    caption = "TESTE FINAL - Sistema funcionando perfeitamente! 🎉"
    
    success = publicar_facebook(video_url, caption)
    
    if success:
        return "🎉 PUBLICAÇÃO CONCLUÍDA COM SUCESSO!", 200
    else:
        return "❌ Erro na publicação. Verifique os logs.", 400

@app.route('/')
def home():
    return "🚀 PublicadorBocaFinal - SISTEMA FUNCIONANDO! 🎉", 200

if __name__ == '__main__':
    logger.info("🎉 SISTEMA APROVADO E FUNCIONANDO!")
    app.run(host='0.0.0.0', port=10000)
