from flask import Flask, request
import requests
import os
import threading

app = Flask(__name__)

# 🔐 TOKEN SEGURO - Configurado APENAS no Render.com
PAGE_TOKEN_BOCA = os.getenv('PAGE_TOKEN_BOCA')

def publicar_somente_facebook(video_url, caption):
    """Publica apenas no Facebook - Mais simples"""
    try:
        print("📤 Publicando no Facebook...")
        
        if not PAGE_TOKEN_BOCA:
            print("❌ ERRO: PAGE_TOKEN_BOCA não configurado")
            print("💡 Configure a variável de ambiente PAGE_TOKEN_BOCA no Render.com")
            return
        
        print(f"📹 URL: {video_url}")
        print(f"📝 Legenda: {caption[:100]}...")
        
        # Formata URL do Cloudinary para MP4 (importante!)
        if '/upload/' in video_url and '/f_mp4/' not in video_url:
            video_url = video_url.replace('/upload/', '/upload/f_mp4/')
            print(f"🔧 URL formatada: {video_url}")
        
        # Publicação no Facebook
        facebook_params = {
            'access_token': PAGE_TOKEN_BOCA,
            'file_url': video_url,
            'description': caption[:1000]  # Limita tamanho
        }
        
        print("🌐 Enviando para API do Facebook...")
        response = requests.post(
            'https://graph.facebook.com/v23.0/213776928485804/videos',
            params=facebook_params,
            timeout=60
        )
        
        print(f"📡 Status Code: {response.status_code}")
        print(f"📡 Response: {response.text}")
        
        if response.status_code == 200:
            print("🎉 ✅ PUBLICAÇÃO NO FACEBOOK CONCLUÍDA!")
            video_id = response.json().get('id')
            print(f"📦 ID do vídeo: {video_id}")
            print(f"🔗 Link: https://facebook.com/{video_id}")
        else:
            print("❌ Erro na publicação")
            print(f"💬 Mensagem: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro crítico: {str(e)}")

@app.route('/webhook-boca', methods=['POST'])
def handle_webhook():
    try:
        print("📍 Webhook recebido do WordPress!")
        
        # 🔥 Dados REAIS do webhook (ajuste conforme seus dados)
        data = request.json
        video_url = data.get('video_url', '')
        caption = data.get('caption', '')
        
        if not video_url or not caption:
            return "❌ Dados incompletos", 400
        
        print(f"🎬 Vídeo: {video_url}")
        print(f"📋 Legenda: {caption}")
        
        # Publicação em background (só Facebook por enquanto)
        thread = threading.Thread(target=publicar_somente_facebook, args=(video_url, caption))
        thread.start()
        
        return "✅ Vídeo recebido! Publicação em andamento...", 200
        
    except Exception as e:
        print(f"❌ Erro no webhook: {str(e)}")
        return "Erro ao processar webhook", 500

@app.route('/teste')
def teste_publicacao():
    """Rota para teste manual"""
    # 🔥 Use um vídeo de teste GENÉRICO, não seu vídeo real
    video_url = "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4"
    caption = "TESTE MANUAL - Sistema de publicação automática"
    
    thread = threading.Thread(target=publicar_somente_facebook, args=(video_url, caption))
    thread.start()
    
    return "✅ Teste manual iniciado! Verifique os logs.", 200

@app.route('/')
def home():
    return "🚀 Boca no Trombone - Auto Publisher rodando! Use /webhook-boca ou /teste", 200

if __name__ == '__main__':
    print("🔄 Servidor iniciado")
    print("📍 Endpoints disponíveis:")
    print("   - /webhook-boca (POST) para WordPress")
    print("   - /teste (GET) para teste manual")
    
    # Verifica se o token está configurado
    if not PAGE_TOKEN_BOCA:
        print("❌ AVISO: PAGE_TOKEN_BOCA não está configurado")
        print("💡 Configure no Render.com: Settings > Environment Variables")
    else:
        print("✅ PAGE_TOKEN_BOCA configurado")
    
    app.run(host='0.0.0.0', port=10000)
