from flask import Flask, render_template, request, jsonify
import os
import logging

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

@app.route('/')
def index():
    return "Sistema Boca no Trombone - Gerador de Reels"

@app.route('/webhook-boca', methods=['POST'])
def webhook_boca():
    try:
        data = request.get_json()
        logger.info("Webhook recebido com sucesso")
        
        # Extrair dados corretamente da estrutura do WordPress
        post_data = data.get('post', {})
        titulo = post_data.get('post_title', 'Título não disponível')
        categoria = extrair_categoria(data)
        imagem_url = data.get('post_thumbnail', '')
        
        logger.info(f"Processando: {titulo}")
        logger.info(f"Categoria: {categoria}")
        logger.info(f"Imagem: {imagem_url}")
        
        # Renderizar o template com os dados
        return render_template('reel_template.html', 
                             titulo=titulo,
                             categoria=categoria,
                             imagem_url=imagem_url,
                             hashtags="#Noticias #LitoralNorte #Ubatuba")
        
    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/gerar_reel')
def gerar_reel():
    categoria = request.args.get('categoria', 'UBATUBA')
    titulo = request.args.get('titulo', 'Título padrão')
    imagem_url = request.args.get('imagem_url', '')
    hashtags = "#Noticias #LitoralNorte #Ubatuba"
    
    return render_template('reel_template.html', 
                         titulo=titulo,
                         categoria=categoria,
                         imagem_url=imagem_url,
                         hashtags=hashtags)

@app.route('/teste')
def teste():
    """Rota para testar se o template está funcionando"""
    return render_template('reel_template.html', 
                         titulo="TESTE: São Sebastião depois do caos, ônibus emergenciais começam a circular",
                         categoria="SÃO PAULO",
                         imagem_url="",
                         hashtags="#Teste #Noticias")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
