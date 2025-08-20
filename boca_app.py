from flask import Flask, request
import requests
import os
import threading
import logging
import json
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import cloudinary
import cloudinary.uploader

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configurações
PAGE_TOKEN_BOCA = os.getenv('PAGE_TOKEN_BOCA')
cloudinary.config(
    cloud_name="dj1h27ueg",
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

def criar_video_da_imagem(image_url, caption):
    """Cria um vídeo a partir de uma imagem e legenda"""
    try:
        logger.info("🎬 Criando vídeo a partir da imagem...")
        
        # 1. Baixar a imagem
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
        
        # 2. Redimensionar para formato Reel (9:16)
        reel_width, reel_height = 1080, 1920
        img = img.resize((reel_width, reel_height), Image.LANCZOS)
        
        # 3. Adicionar legenda na imagem (opcional)
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 60)
        except:
            font = ImageFont.load_default()
        
        # Adicionar texto (simplificado)
        draw.text((50, 50), caption[:100], fill="white", font=font)
        
        # 4. Salvar como MP4 (imagem estática com 10 segundos)
        video_path = "/tmp/video_reel.mp4"
        img.save(video_path, format='MP4', duration=10000)  # 10 segundos
        
        # 5. Fazer upload para Cloudinary
        upload_result = cloudinary.uploader.upload(
            video_path,
            resource_type="video",
            folder="boca_reels",
            public_id=f"reel_{int(time.time())}"
        )
        
        logger.info(f"✅ Vídeo criado: {upload_result['secure_url']}")
        return upload_result['secure_url']
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar vídeo: {str(e)}")
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
        logger.info("📍 Recebendo dados do WordPress...")
        
        # Debug dos dados recebidos
        logger.info(f"📦 Dados recebidos: {request.data}")
        
        # Tenta parsear os dados
        data = request.json if request.json else {}
        logger.info(f"🎯 Dados JSON: {data}")
        
        # Extrai imagem e texto (campos do WordPress)
        image_url = data.get('image_url') or data.get('url') or data.get('featured_image')
        caption = data.get('caption') or data.get('title') or data.get('content') or data.get('excerpt')
        
        logger.info(f"🖼️ Imagem: {image_url}")
        logger.info(f"📋 Texto: {caption}")
        
        if not image_url or not caption:
            logger.error("❌ Dados incompletos: precisa de image_url e caption")
            return "❌ Envie image_url e caption", 400
        
        # Cria vídeo da imagem
        video_url = criar_video_da_imagem(image_url, caption)
        
        if not video_url:
            return "❌ Erro ao criar vídeo", 500
        
        # Publica no Facebook
        success = publicar_facebook(video_url, caption)
        
        if success:
            return "✅ Reel criado e publicado com sucesso!", 200
        else:
            return "❌ Erro ao publicar", 500
            
    except Exception as e:
        logger.error(f"❌ Erro no webhook: {str(e)}")
        return "Erro interno", 500

@app.route('/teste-imagem')
def teste_imagem():
    """Teste com imagem real"""
    image_url = "https://exemplo.com/imagem.jpg"  # URL de uma imagem real
    caption = "Teste de Reel com imagem - Sistema funcionando! 🎉"
    
    video_url = criar_video_da_imagem(image_url, caption)
    if video_url:
        success = publicar_facebook(video_url, caption)
        if success:
            return "🎉 Reel criado e publicado!", 200
    
    return "❌ Erro no teste", 400

@app.route('/')
def home():
    return "🚀 Sistema pronto para transformar imagens em Reels!", 200

if __name__ == '__main__':
    logger.info("🎉 Sistema de criação de Reels pronto!")
    app.run(host='0.0.0.0', port=10000)
