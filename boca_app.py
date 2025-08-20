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

def testar_tokens():
    """Testa se os tokens estão válidos"""
    print("🧪 Testando tokens...")
    
    # Testar token do Facebook
    try:
        test_url = f"https://graph.facebook.com/v23.0/me/accounts?access_token={PAGE_TOKEN_BOCA}"
        response = requests.get(test_url, timeout=10)
        print(f"✅ Token Facebook: {response.status_code}")
    except Exception as e:
        print(f"❌ Token Facebook inválido: {str(e)}")
    
    # Testar token do Instagram
    try:
        test_url = f"https://graph.facebook.com/v23.0/me?access_token={USER_ACCESS_TOKEN}"
        response = requests.get(test_url, timeout=10)
        print(f"✅ Token Instagram: {response.status_code}")
    except Exception as e:
        print(f"❌ Token Instagram inválido: {str(e)}")

def publicar_async(video_url, caption):
    try:
        print("📤 Iniciando publicação assíncrona...")
        
        # 1. Primeiro testar os tokens
        testar_tokens()
        
        # 2. Publicar no Facebook (com URL formatada)
        print("📤 Publicando no Facebook...")
        facebook_api_url = "https://graph.facebook.com/v23.0/213776928485804/videos"
        
        # 🔥 URL formatada para Cloudinary - FORÇANDO MP4
        video_url_mp4 = video_url.replace('/upload/', '/upload/f_mp4/')
        
        facebook_params = {
            'access_token': PAGE_TOKEN_BOCA,
            'file_url': video_url_mp4,  # Usa URL formatada
            'description': caption[:1000]
        }
        
        print(f"📹 URL do vídeo: {video_url_mp4}")
        facebook_response = requests.post(facebook_api_url, params=facebook_params, timeout=60)
        
        if facebook_response.status_code == 200:
            print("✅ Facebook publicado com sucesso!")
            print(f"📦 ID: {facebook_response.json().get('id')}")
        else:
            print(f"❌ Erro Facebook: {facebook_response.text}")
        
        # 3. Só tenta Instagram se o token estiver válido
        if USER_ACCESS_TOKEN and "EAA" in USER_ACCESS_TOKEN:
            print("📤 Publicando no Instagram...")
            instagram_params = {
                'access_token': USER_ACCESS_TOKEN,
                'media_type': 'REELS',
                'video_url': video_url_mp4,  # Usa mesma URL formatada
                'caption': caption[:2200]
            }
            
            instagram_response = requests.post(
                'https://graph.facebook.com/v23.0/17841464327364824/media',
                params=instagram_params,
                timeout=60
            )
            
            if instagram_response.status_code == 200:
                print("✅ Container Instagram criado!")
                print(f"📦 Container ID: {instagram_response.json().get('id')}")
            else:
                print(f"❌ Erro Instagram: {instagram_response.text}")
        else:
            print("⚠️ Pulando Instagram - Token inválido")
            
    except Exception as e:
        print(f"❌ Erro na publicação: {str(e)}")

@app.route('/webhook-boca', methods=['POST'])
def handle_webhook():
    try:
        # ... (seu código de processamento de vídeo) ...
        
        video_url = "https://res.cloudinary.com/dj1h27ueg/video/upload/v1755717469/boca_reels/i6pys2w5cwwu1t1zfvs4.mp4"
        caption = "Teste de publicação - vídeo curto"
        
        # Inicia publicação em background
        thread = threading.Thread(target=publicar_async, args=(video_url, caption))
        thread.start()
        
        return "✅ Vídeo recebido. Publicação em background...", 200
        
    except Exception as e:
        print(f"❌ Erro no webhook: {str(e)}")
        return "Erro interno", 500

@app.route('/')
def home():
    return "🚀 Servidor Boca no Trombone rodando!", 200

if __name__ == '__main__':
    print("🔄 Iniciando servidor...")
    testar_tokens()  # Testa tokens ao iniciar
    app.run(host='0.0.0.0', port=10000)
