from flask import Flask, request, jsonify
import os
import logging
import requests
import time
from threading import Thread
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import io
import textwrap

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

def criar_imagem_reel(titulo, imagem_url, categoria):
    """CRIA IMAGEM ESTILIZADA NO FORMATO REEL 1080x1920"""
    try:
        # 📏 Dimensões do Reel
        width, height = 1080, 1920
        
        # 🎨 Criar imagem de fundo PRETO
        imagem = Image.new('RGB', (width, height), color='black')
        draw = ImageDraw.Draw(imagem)
        
        # 📥 Baixar imagem do WordPress
        if imagem_url and imagem_url.startswith('http'):
            response = requests.get(imagem_url)
            img_wp = Image.open(io.BytesIO(response.content))
            
            # Redimensionar e posicionar a imagem
            img_wp = img_wp.resize((900, 600), Image.LANCZOS)
            imagem.paste(img_wp, (90, 200))
        
        # 🟥 CAIXA PRIMÁRIA VERMELHA
        draw.rectangle([100, 1000, 980, 1200], fill='#e60000')
        
        # ⬜ CAIXA BRANCA INTERNA
        draw.rectangle([120, 1020, 960, 1180], fill='white')
        
        # ✏️ TEXTO DA MANCHETE (preto)
        try:
            font = ImageFont.truetype("Arial", 36)
        except:
            font = ImageFont.load_default()
        
        # Quebrar texto em múltiplas linhas
        lines = textwrap.wrap(titulo, width=40)
        y_text = 1040
        for line in lines:
            draw.text((140, y_text), line, font=font, fill='black')
            y_text += 40
        
        # 🏷️ CATEGORIA (canto superior esquerdo)
        draw.rectangle([50, 50, 250, 100], fill='#e60000')
        draw.text((70, 60), categoria, font=font, fill='white')
        
        # 🔴 LOGO CENTRALIZADO
        draw.ellipse([490, 1300, 590, 1400], fill='#e60000')
        draw.text((510, 1320), "BOCA", font=font, fill='white')
        
        # ⬇️ SETA AMARELA
        draw.polygon([1020, 1800, 1040, 1820, 1060, 1800], fill='yellow')
        
        # 💾 Salvar imagem temporária
        img_path = f"/tmp/reel_{int(time.time())}.jpg"
        imagem.save(img_path, 'JPEG')
        
        return img_path
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar imagem: {str(e)}")
        return None

def publicar_no_instagram(titulo, imagem_url, categoria):
    """PUBLICA NO INSTAGRAM COM IMAGEM ESTILIZADA"""
    try:
        logger.info("🎨 Criando imagem estilizada...")
        
        # 1. CRIAR IMAGEM ESTILIZADA
        img_path = criar_imagem_reel(titulo, imagem_url, categoria)
        
        if not img_path:
            return False
        
        # 2. Upload para servidor temporário ( necessário para API do Instagram)
        upload_url = "https://api.imgbb.com/1/upload"  # Servidor de imagens gratuito
        with open(img_path, 'rb') as f:
            response = requests.post(upload_url, files={'image': f})
        
        if response.status_code == 200:
            image_url = response.json()['data']['url']
            
            # 3. PUBLICAR NO INSTAGRAM
            create_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
            
            payload = {
                'image_url': image_url,
                'caption': f"🚨 {titulo}\n\n#Noticias #Brasil #LitoralNorte",
                'access_token': INSTAGRAM_ACCESS_TOKEN
            }
            
            response = requests.post(create_url, data=payload)
            result = response.json()
            
            if 'id' in result:
                creation_id = result['id']
                
                # 4. PUBLICAR EFETIVAMENTE
                time.sleep(5)
                publish_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
                publish_payload = {
                    'creation_id': creation_id,
                    'access_token': INSTAGRAM_ACCESS_TOKEN
                }
                
                publish_response = requests.post(publish_url, data=publish_payload)
                publish_result = publish_response.json()
                
                if 'id' in publish_result:
                    logger.info(f"✅ REEL PUBLICADO! ID: {publish_result['id']}")
                    return True
        
        logger.error("❌ Erro na publicação")
        return False
            
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        return False

def worker_publicacao():
    """Processa a fila de publicação 24x7"""
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
    return "✅ Sistema rodando - Gerando Reels 1080x1920"

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
            
        return jsonify({'status': 'success', 'message': 'Reel em produção'}), 200
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        return jsonify({'status': 'success', 'message': 'Recebido'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info("🚀 Sistema de Reels iniciado!")
    app.run(host='0.0.0.0', port=port, debug=False)
