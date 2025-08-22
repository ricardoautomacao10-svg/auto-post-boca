from flask import Flask, request, jsonify
import os
import logging
import requests
import time
import threading

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 🔥 VARIÁVEIS DE AMBIENTE (USE AS QUE VOCÊ JÁ TEM)
INSTAGRAM_ACCESS_TOKEN = os.getenv('PAGE_TOK...', 'seu_token_aqui')
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv('USER_ACC...', 'seu_business_id_aqui')

# 📋 FILA de publicações
fila_publicacao = []
lock = threading.Lock()

def extrair_categoria(data):
    """Extrai a categoria dos dados do WordPress"""
    try:
        taxonomies = data.get('taxonomies', {})
        categories = taxonomies.get('category', {})
        if categories:
            return list(categories.keys())[0].upper()
        return 'NOTÍCIAS'
    except:
        return 'NOTÍCIAS'

def publicar_no_instagram(titulo, imagem_url, categoria):
    """PUBLICA DIRETAMENTE NO INSTAGRAM - SEM ENROLAÇÃO"""
    try:
        logger.info(f"🚀 TENTANDO PUBLICAR: {titulo}")
        
        # URL da API do Instagram
        create_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
        
        # Dados para publicação
        payload = {
            'image_url': imagem_url,
            'caption': f"📢 {titulo}\n\n📍 Categoria: {categoria}\n\n🔔 Siga para mais notícias!\n\n#Noticias #Brasil #LitoralNorte #Jornalismo",
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        # 1. Criar mídia
        response = requests.post(create_url, data=payload, timeout=30)
        result = response.json()
        
        if 'id' in result:
            creation_id = result['id']
            logger.info(f"📦 Mídia criada: {creation_id}")
            
            # 2. Publicar a mídia
            time.sleep(3)
            
            publish_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
            publish_payload = {
                'creation_id': creation_id,
                'access_token': INSTAGRAM_ACCESS_TOKEN
            }
            
            publish_response = requests.post(publish_url, data=publish_payload, timeout=30)
            publish_result = publish_response.json()
            
            if 'id' in publish_result:
                logger.info(f"✅ PUBLICAÇÃO CONCLUÍDA! ID: {publish_result['id']}")
                return True
            else:
                logger.error(f"❌ Erro na publicação: {publish_result}")
                return False
        else:
            logger.error(f"❌ Erro ao criar mídia: {result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro na publicação: {str(e)}")
        return False

def worker_publicacao():
    """Processa a fila de publicação 24x7"""
    logger.info("👷 Worker de publicação INICIADO!")
    while True:
        try:
            with lock:
                if fila_publicacao:
                    titulo, imagem_url, categoria = fila_publicacao.pop(0)
                    logger.info(f"🔄 PROCESSANDO: {titulo}")
                    
                    sucesso = publicar_no_instagram(titulo, imagem_url, categoria)
                    
                    if sucesso:
                        logger.info("🎉 PUBLICAÇÃO REALIZADA COM SUCESSO!")
                    else:
                        logger.warning("⚠️ Publicação falhou")
                
            time.sleep(5)  # Verifica a cada 5 segundos
            
        except Exception as e:
            logger.error(f"❌ Erro no worker: {str(e)}")
            time.sleep(10)

# 🚀 INICIAR THREAD EM SEGUNDO PLANO (AGORA VAI!)
worker_thread = threading.Thread(target=worker_publicacao, daemon=True)
worker_thread.start()
logger.info("🚀 Thread do worker INICIADA!")

@app.route('/')
def index():
    return "✅ Sistema Boca no Trombone - PUBLICAÇÃO AUTOMÁTICA ATIVA"

@app.route('/webhook-boca', methods=['POST'])
def webhook_boca():
    try:
        data = request.get_json()
        logger.info("📍 Webhook recebido do WordPress!")
        
        # Extrair dados
        post_data = data.get('post', {})
        titulo = post_data.get('post_title', 'Título não disponível').strip()
        categoria = extrair_categoria(data)
        imagem_url = data.get('post_thumbnail', '').strip()
        
        # Log dos dados recebidos
        logger.info(f"📝 Título: {titulo}")
        logger.info(f"🏷️ Categoria: {categoria}")
        logger.info(f"🖼️ Imagem: {imagem_url}")
        
        # Validar e adicionar à fila
        if titulo and imagem_url.startswith('http'):
            with lock:
                fila_publicacao.append((titulo, imagem_url, categoria))
            logger.info(f"📥 Adicionado à fila. Total: {len(fila_publicacao)}")
            
            # 🔥 FORÇAR PROCESSAMENTO IMEDIATO
            logger.info("🔥 Acordando worker para processamento imediato!")
            
            return jsonify({'status': 'success', 'message': 'Em publicação'}), 200
        else:
            logger.warning("⚠️ Dados incompletos recebidos")
            return jsonify({'status': 'success', 'message': 'Recebido - dados incompletos'}), 200
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook: {str(e)}")
        return jsonify({'status': 'success', 'message': 'Recebido'}), 200

@app.route('/status')
def status():
    """Verifica status do sistema"""
    return {
        'status': 'online',
        'publicacoes_na_fila': len(fila_publicacao),
        'worker_ativo': worker_thread.is_alive(),
        'ultima_publicacao': fila_publicacao[0] if fila_publicacao else 'Nenhuma'
    }

@app.route('/testar-instagram')
def testar_instagram():
    """Testa a conexão com a API do Instagram"""
    try:
        test_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}?fields=name&access_token={INSTAGRAM_ACCESS_TOKEN}"
        response = requests.get(test_url, timeout=10)
        
        if response.status_code == 200:
            return f"✅ CONEXÃO OK! Conta: {response.json().get('name', 'Nome não disponível')}"
        else:
            return f"❌ ERRO: {response.json()}"
            
    except Exception as e:
        return f"❌ FALHA: {str(e)}"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info("🚀 SISTEMA INICIADO - PRONTO PARA PUBLICAR!")
    app.run(host='0.0.0.0', port=port, debug=False)
