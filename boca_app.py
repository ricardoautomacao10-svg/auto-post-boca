from flask import Flask, render_template, send_file
import os

app = Flask(__name__)

# Configurações
app.config['UPLOAD_FOLDER'] = 'uploads'

@app.route('/')
def index():
    return "Sistema Boca no Trombone - Gerador de Reels"

# Rota para gerar reel com dados dinâmicos
@app.route('/gerar_reel/<categoria>/<titulo>')
def gerar_reel(categoria, titulo):
    hashtags = "#Noticias #LitoralNorte #SãoSebastião"
    
    return render_template('reel_template.html', 
                         titulo=titulo,
                         categoria=categoria,
                         hashtags=hashtags)

# Rota para visualizar o reel base
@app.route('/visualizar_reel')
def visualizar_reel():
    return send_file('templates/reel_base.html')

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True)
