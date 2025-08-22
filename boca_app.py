from flask import Flask, request, jsonify
import os
import logging
import requests
import json
from jinja2 import Template
import tempfile
from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, ColorClip
import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Variáveis de ambiente
INSTAGRAM_ACCESS_TOKEN = os.getenv('PAGE_TOKEN', '')
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv('USER_ACCOUNT_ID', '')
CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', '')
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', '')
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '')

# Carregar template
with open('reel_template.html', 'r', encoding='utf-8') as f:
    template_html = f.read()

template = Template(template_html)

@app.route('/webbook-boca', methods=['POST'])
def handle_webhook():
    """Endpoint para receber webhooks do WordPress"""
    try:
        data = request.json
        logger.info(f"Webhook recebido: {json.dumps(data)}")
        
        # Extrair dados da notícia
        titulo = data.get('titulo', '')
        imagem_url = data.get('imagem_url', '')
        categoria = data.get('categoria', 'Geral')
        hashtags = data.get('hashtags', '#Noticias #LitoralNorte')
        
        # Gerar HTML do reel
        html_content = template.render(
            titulo=titulo,
            imagem_url=imagem_url,
            categoria=categoria,
            hashtags=hashtags
        )
        
        # Salvar HTML temporariamente
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_content)
            html_path = f.name
        
        # Converter HTML para imagem (usando uma abordagem simplificada)
        # Na prática, você precisaria de uma solução como playwright ou html2image
        image_path = generate_reel_image(html_path, titulo)
        
        # Criar vídeo a partir da imagem
        video_path = create_video_from_image(image_path)
        
        # Publicar no Instagram
        result = publish_to_instagram(video_path, titulo, hashtags)
        
        # Limpar arquivos temporários
        os.unlink(html_path)
        os.unlink(image_path)
        os.unlink(video_path)
        
        return jsonify({"status": "success", "message": "Reel publicado com sucesso", "id": result.get('id')})
        
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def generate_reel_image(html_path, titulo):
    """Gera imagem do reel a partir do HTML (implementação simplificada)"""
    # Esta é uma implementação simplificada
    # Na prática, use uma biblioteca como imgkit ou playwright para converter HTML em imagem
    import imgkit
    
    # Configurar caminho para wkhtmltoimage (depende do seu ambiente)
    config = imgkit.config(wkhtmltoimage='/usr/bin/wkhtmltoimage')
    
    # Gerar nome do arquivo de imagem
    image_path = f"/tmp/reel_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    
    # Converter HTML para imagem
    try:
        imgkit.from_file(html_path, image_path, config=config, options={
            'width': '1080',
            'height': '1920',
            'quality': '100'
        })
    except:
        # Fallback: criar uma imagem simples com texto
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (1080, 1920), color='black')
        d = ImageDraw.Draw(img)
        
        # Adicionar título (simplificado)
        try:
            font = ImageFont.truetype("Roboto-Bold.ttf", 48)
        except:
            font = ImageFont.load_default()
            
        d.text((100, 500), titulo, fill=(255, 255, 255), font=font)
        d.text((100, 100), "BOCA NO TROMBONE - ILHABELA", fill=(230, 0, 0), font=font)
        d.text((500, 1700), "@bocanotrombonelitoral", fill=(255, 204, 0), font=font)
        
        img.save(image_path)
    
    return image_path

def create_video_from_image(image_path, duration=15):
    """Cria vídeo a partir de uma imagem com duração especificada"""
    # Carregar imagem
    image_clip = ImageClip(image_path, duration=duration)
    
    # Criar vídeo com a imagem
    video_path = f"/tmp/reel_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    image_clip.write_videofile(
        video_path, 
        fps=24, 
        codec='libx264', 
        audio=False,
        verbose=False,
        logger=None
    )
    
    return video_path

def publish_to_instagram(video_path, caption, hashtags):
    """Publica vídeo no Instagram"""
    # Etapa 1: Fazer upload do vídeo
    upload_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
    
    # Na prática, você precisaria fazer upload do vídeo para um local acessível pela API
    # Esta é uma implementação simplificada
    payload = {
        'media_type': 'REELS',
        'video_url': 'https://exemplo.com/video.mp4',  # Substituir pelo URL real do vídeo
        'caption': f"{caption} {hashtags}",
        'access_token': INSTAGRAM_ACCESS_TOKEN,
        'thumb_offset': 0
    }
    
    response = requests.post(upload_url, data=payload)
    result = response.json()
    
    if 'id' in result:
        # Etapa 2: Publicar o vídeo
        creation_id = result['id']
        publish_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
        publish_payload = {
            'creation_id': creation_id,
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        publish_response = requests.post(publish_url, data=publish_payload)
        return publish_response.json()
    
    return result

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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info("🚀 Sistema de automação de Reels iniciado!")
    app.run(host='0.0.0.0', port=port, debug=False)
