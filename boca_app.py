from flask import Flask, request
import requests
import os
import cloudinary
import cloudinary.uploader
import threading
import time

app = Flask(__name__)

# Configurações
PAGE_TOKEN_BOCA = os.getenv('PAGE_TOKEN_BOCA')
USER_ACCESS_TOKEN = os.getenv('USER_ACCESS_TOKEN')

# 🔥 FUNÇÃO ASSÍNCRONA para publicar (evita timeout)
def publicar_async(video_url, caption):
    try:
        print("📤 Iniciando publicação assíncrona...")
        
        # 1. Publicar no Facebook
        print("📤 Publicando no Facebook...")
        facebook_api_url = "https://graph.facebook.com/v23.0/213776928485804/videos"
        facebook_params = {
            'access_token': PAGE_TOKEN_BOCA,
            'file_url': video_url,
            'description': caption[:1000]  # Limita descrição
        }
        
        facebook_response = requests.post(facebook_api_url, params=facebook_params, timeout=30)
        if facebook_response.status_code == 200:
            print("✅ Facebook publicado!")
        else:
            print(f"❌ Erro Facebook: {facebook_response.text}")
        
        # 2. Publicar no Instagram
        print("📤 Publicando no Instagram...")
        instagram_params = {
            'access_token': USER_ACCESS_TOKEN,
            'media_type': 'REELS',
            'video_url': video_url,
            'caption': caption[:2200]  # Limita legenda para Instagram
        }
        
        instagram_response = requests.post(
            'https://graph.facebook.com/v23.0/17841464327364824/media',
            params=instagram_params,
            timeout=30
        )
        
        if instagram_response.status_code == 200:
            print("✅ Container Instagram criado!")
        else:
            print(f"❌ Erro Instagram: {instagram_response.text}")
            
    except Exception as e:
        print(f"❌ Erro na publicação: {str(e)}")

@app.route('/webhook-boca', methods=['POST'])
def handle_webhook():
    try:
        # ... (seu código de processamento de vídeo) ...
        
        video_url = "https://res.cloudinary.com/.../video.mp4"
        caption = "Legenda curtapara teste"
        
        # 🔥 Inicia publicação em background (não bloqueia)
        thread = threading.Thread(target=publicar_async, args=(video_url, caption))
        thread.start()
        
        # 🔥 Resposta imediata para evitar timeout
        return "✅ Vídeo recebido. Publicação em background...", 200
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return "Erro interno", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
