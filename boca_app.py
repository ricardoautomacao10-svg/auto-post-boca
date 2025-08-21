from flask import Flask, render_template, request, jsonify
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configurações
app.config['UPLOAD_FOLDER'] = 'uploads'

@app.route('/')
def index():
    return "Sistema Boca no Trombone - Gerador de Reels"

# Rota para webhook do WordPress
@app.route('/webhook-boca', methods=['POST'])
def webhook_boca():
    try:
        data = request.get_json()
        logger.info(f"Dados recebidos do webhook: {data}")
        
        # Processar dados do WordPress
        titulo = data.get('titulo', 'Título não disponível')
        categoria = data.get('categoria', 'Geral')
        imagem_url = data.get('imagem_url', '')
        
        # Aqui você geraria o reel com esses dados
        logger.info(f"Reel gerado para: {titulo}")
        
        return jsonify({
            'status': 'success',
            'message': 'Reel processado com sucesso',
            'data': {
                'titulo': titulo,
                'categoria': categoria,
                'imagem_url': imagem_url
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Rota para gerar reel com dados dinâmicos
@app.route('/gerar_reel')
def gerar_reel():
    categoria = request.args.get('categoria', 'SÃO PAULO')
    titulo = request.args.get('titulo', 'Título padrão')
    hashtags = "#Noticias #LitoralNorte #SãoSebastião"
    
    return render_template('reel_template.html', 
                         titulo=titulo,
                         categoria=categoria,
                         hashtags=hashtags)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))  # Usar porta do Render
    app.run(host='0.0.0.0', port=port, debug=True)
