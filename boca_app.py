from flask import Flask, request, jsonify
import os
import logging
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configurações
app.config['UPLOAD_FOLDER'] = 'uploads'

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
    """Gera o HTML do reel diretamente sem usar templates"""
    return f'''
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Boca no Trombone - Reel</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Arial, sans-serif; }}
        body {{ display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #1a1a1a; padding: 20px; }}
        .reel-container {{ width: 360px; height: 640px; background-color: #000; border-radius: 20px; overflow: hidden; position: relative; box-shadow: 0 0 30px rgba(255, 0, 0, 0.4); display: flex; flex-direction: column; }}
        
        .image-section {{ height: 35%; background: #2c3e50; display: flex; justify-content: center; align-items: center; color: white; font-size: 18px; font-weight: bold; text-align: center; padding: 20px; border-bottom: 2px solid #333; }}
        .logo-section {{ height: 30%; display: flex; justify-content: center; align-items: center; padding: 20px; }}
        .logo {{ width: 140px; height: 140px; background: #e60000; border-radius: 50%; display: flex; justify-content: center; align-items: center; color: white; font-weight: bold; font-size: 18px; text-align: center; border: 5px solid white; box-shadow: 0 0 25px rgba(230, 0, 0, 0.8); }}
        .content-section {{ height: 35%; display: flex; flex-direction: column; justify-content: flex-end; padding: 20px; }}
        .red-box {{ background-color: #e60000; padding: 15px; border-radius: 12px; margin-bottom: 15px; }}
        .white-box {{ background-color: white; padding: 15px; border-radius: 8px; text-align: center; }}
        .headline {{ color: #000; font-weight: 800; font-size: 18px; line-height: 1.3; }}
        .category {{ position: absolute; top: 20px; left: 20px; background: #e60000; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold; font-size: 14px; }}
        .brand {{ position: absolute; top: 20px; right: 20px; color: white; font-weight: bold; font-size: 16px; }}
        .hashtag {{ position: absolute; bottom: 20px; left: 20px; color: #ffcc00; font-weight: bold; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="reel-container">
        <div class="category">{categoria}</div>
        <div class="brand">BOCA NO TROMBONE</div>
        
        <div class="image-section">
            {imagem_url if imagem_url else "IMAGEM FORNECIDA PELO WP"}
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
        
        <div class="hashtag">{hashtags}</div>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    return "Sistema Boca no Trombone - Gerador de Reels"

@app.route('/webhook-boca', methods=['POST'])
def webhook_boca():
    try:
        data = request.get_json()
        logger.info("Webhook recebido com sucesso")
        
        if not data:
            return jsonify({'status': 'error', 'message': 'Dados vazios'}), 400
        
        # Extrair dados corretamente da estrutura do WordPress
        post_data = data.get('post', {})
        titulo = post_data.get('post_title', 'Título não disponível')
        categoria = extrair_categoria(data)
        imagem_url = data.get('post_thumbnail', '')
        hashtags = "#Noticias #LitoralNorte #Ubatuba"
        
        logger.info(f"Processando: {titulo}")
        logger.info(f"Categoria: {categoria}")
        logger.info(f"Imagem: {imagem_url}")
        
        # Gerar HTML diretamente (SEM templates)
        html_content = gerar_html_reel(titulo, categoria, imagem_url, hashtags)
        
        return html_content, 200, {'Content-Type': 'text/html'}
        
    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Erro interno no servidor'}), 500

@app.route('/teste')
def teste():
    """Rota para testar se está funcionando"""
    try:
        html_content = gerar_html_reel(
            "TESTE: Prepare o bolso: Conta de luz da Elektro sobe no Litoral Norte",
            "DESTAQUES", 
            "https://jornalvozdolitoral.com/wp-content/uploads/2025/08/image-58.png",
            "#Teste #Noticias"
        )
        return html_content, 200, {'Content-Type': 'text/html'}
    except Exception as e:
        return f"Erro: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
