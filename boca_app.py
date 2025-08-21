from flask import Flask, request, jsonify
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def extrair_categoria(data):
    """Extrai a categoria dos dados do WordPress"""
    try:
        taxonomies = data.get('taxonomies', {})
        categories = taxonomies.get('category', {})
        if categories:
            first_category = list(categories.keys())[0]
            return first_category.upper()
        return 'GERAL'
    except:
        return 'UBATUBA'

def gerar_html_reel(titulo, categoria, imagem_url, hashtags):
    """Gera o HTML do reel PRONTO para Instagram"""
    return f'''
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Boca no Trombone - Reel</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: Arial, sans-serif; }}
        body {{ display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #000; padding: 20px; }}
        .reel-container {{ width: 360px; height: 640px; background: #000; position: relative; overflow: hidden; }}
        
        .header {{ position: absolute; top: 20px; left: 20px; right: 20px; display: flex; justify-content: space-between; z-index: 10; }}
        .category {{ background: #e60000; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold; font-size: 14px; }}
        .brand {{ color: white; font-weight: bold; font-size: 16px; }}
        
        .image-section {{ height: 35%; background: #2c3e50; display: flex; justify-content: center; align-items: center; color: white; }}
        .logo-section {{ height: 30%; display: flex; justify-content: center; align-items: center; }}
        .logo {{ width: 120px; height: 120px; background: #e60000; border-radius: 50%; display: flex; justify-content: center; align-items: center; color: white; font-weight: bold; border: 4px solid white; }}
        
        .content-section {{ height: 35%; display: flex; flex-direction: column; justify-content: flex-end; padding: 20px; }}
        .red-box {{ background: #e60000; padding: 15px; border-radius: 12px; }}
        .white-box {{ background: white; padding: 15px; border-radius: 8px; text-align: center; }}
        .headline {{ color: #000; font-weight: 800; font-size: 18px; line-height: 1.3; }}
        
        .hashtags {{ position: absolute; bottom: 15px; left: 20px; color: #ffcc00; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="reel-container">
        <div class="header">
            <div class="category">{categoria}</div>
            <div class="brand">BOCA NO TROMBONE</div>
        </div>
        
        <div class="image-section">
            {imagem_url if imagem_url else "IMAGEM DO WP"}
        </div>
        
        <div class="logo-section">
            <div class="logo">LOGO</div>
        </div>
        
        <div class="content-section">
            <div class="red-box">
                <div class="white-box">
                    <div class="headline">{titulo}</div>
                </div>
            </div>
        </div>
        
        <div class="hashtags">{hashtags}</div>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    return "Sistema Boca no Trombone - Gerador de Reels ✅"

@app.route('/webhook-boca', methods=['POST'])
def webhook_boca():
    try:
        data = request.get_json()
        logger.info("📍 Webhook recebido!")
        
        # Extrair dados do WordPress
        post_data = data.get('post', {})
        titulo = post_data.get('post_title', 'Título não disponível')
        categoria = extrair_categoria(data)
        imagem_url = data.get('post_thumbnail', '')
        
        logger.info(f"📝 Título: {titulo}")
        logger.info(f"🏷️ Categoria: {categoria}")
        logger.info(f"🖼️ Imagem: {imagem_url}")
        
        # Gerar HTML do reel
        html_content = gerar_html_reel(titulo, categoria, imagem_url, "#Noticias #LitoralNorte #Brasil")
        
        # ✅ AQUI VOCÊ CONECTA COM A API DO INSTAGRAM!
        # publicar_no_instagram(html_content)
        
        return html_content, 200, {'Content-Type': 'text/html'}
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        return jsonify({'status': 'success', 'message': 'Recebido - em processamento'}), 200

@app.route('/teste')
def teste():
    """Teste do reel - ACESSE: https://seu-app.onrender.com/teste"""
    html = gerar_html_reel(
        "🚨 PALMEIRAS É FRANCO FAVORITO contra o Universitario!",
        "ESPORTES", 
        "https://jornalvozdolitoral.com/wp-content/uploads/2025/08/image-59.png",
        "#Palmeiras #Futebol #Esportes"
    )
    return html, 200, {'Content-Type': 'text/html'}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
