# ==============================================================================
# BLOCO 1: IMPORTAÇÕES
# ==============================================================================
import os
import io
import requests
import textwrap
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from base64 import b64encode
# IMPORTAÇÃO PARA USAR A API DO CREATOMATE
import creatomate

# ==============================================================================
# BLOCO 2: CONFIGURAÇÃO INICIAL
# ==============================================================================
load_dotenv()
app = Flask(__name__)

print("🚀 INICIANDO APLICAÇÃO BOCA NO TROMBONE v2.0 (Creatomate Edition)")

# Configs do WordPress
WP_URL = os.getenv('WP_URL')
WP_USER = os.getenv('WP_USER')
WP_PASSWORD = os.getenv('WP_PASSWORD')
if all([WP_URL, WP_USER, WP_PASSWORD]):
    credentials = f"{WP_USER}:{WP_PASSWORD}"
    token_wp = b64encode(credentials.encode())
    HEADERS_WP = {'Authorization': f'Basic {token_wp.decode("utf-8")}'}
    print("✅ [CONFIG] Variáveis do WordPress carregadas.")
else:
    print("❌ [ERRO DE CONFIG] Faltando variáveis de ambiente do WordPress.")
    HEADERS_WP = {}

# Configs da API do Meta (BOCA NO TROMBONE)
BOCA_META_API_TOKEN = os.getenv('BOCA_META_API_TOKEN')
BOCA_INSTAGRAM_ID = os.getenv('BOCA_INSTAGRAM_ID')
BOCA_FACEBOOK_PAGE_ID = os.getenv('BOCA_FACEBOOK_PAGE_ID')
GRAPH_API_VERSION = 'v19.0'

# Configs da API do Creatomate (BOCA NO TROMBONE)
BOCA_CREATOMATE_API_KEY = os.getenv('BOCA_CREATOMATE_API_KEY')
BOCA_CREATOMATE_TEMPLATE_ID = os.getenv('BOCA_CREATOMATE_TEMPLATE_ID')

if all([BOCA_META_API_TOKEN, BOCA_INSTAGRAM_ID, BOCA_FACEBOOK_PAGE_ID, BOCA_CREATOMATE_API_KEY, BOCA_CREATOMATE_TEMPLATE_ID]):
    print("✅ [CONFIG] Variáveis do Boca No Trombone e Creatomate carregadas.")
else:
    print("⚠️ [AVISO DE CONFIG] Faltando uma ou mais variáveis do Boca No Trombone ou Creatomate.")

# ==============================================================================
# BLOCO 3: FUNÇÕES AUXILIARES
# ==============================================================================
def criar_video_com_creatomate(titulo_post, url_imagem_destaque):
    """
    Chama a API do Creatomate para gerar um vídeo a partir de um template.
    """
    print("🎬 [ETAPA 1/4] Solicitando criação de vídeo ao Creatomate...")
    if not BOCA_CREATOMATE_API_KEY or not BOCA_CREATOMATE_TEMPLATE_ID:
        print("❌ [ERRO] Chave da API ou ID do Template do Creatomate não configurados.")
        return None
        
    try:
        client = creatomate.Client(BOCA_CREATOMATE_API_KEY)

        # Dados que você quer enviar para o seu template no Creatomate.
        # IMPORTANTE: As chaves ('titulo-noticia', 'imagem-fundo') devem corresponder
        # exatamente aos nomes dos elementos dinâmicos no seu template do Creatomate.
        modifications = {
            'titulo-noticia': titulo_post,
            'imagem-fundo': url_imagem_destaque,
        }

        print(f"    - Enviando dados para o template ID: {BOCA_CREATOMATE_TEMPLATE_ID}")
        # Inicia a renderização do vídeo
        renders = client.render({
            'template_id': BOCA_CREATOMATE_TEMPLATE_ID,
            'modifications': modifications,
        })

        print("    - Aguardando a finalização da renderização...")
        # O resultado é uma lista, pegamos o primeiro item
        video_renderizado = renders[0]

        print(f"✅ [ETAPA 1/4] Vídeo criado com sucesso! URL: {video_renderizado.url}")
        return video_renderizado.url

    except Exception as e:
        print(f"❌ [ERRO] Falha crítica na comunicação com o Creatomate: {e}")
        return None


def upload_para_wordpress(url_video, nome_arquivo):
    """
    Baixa o vídeo do Creatomate e faz o upload para o WordPress.
    """
    print(f"⬆️  [ETAPA 2/4] Fazendo upload do vídeo para o WordPress...")
    try:
        # Baixa o vídeo gerado pelo Creatomate
        print("    - Baixando vídeo do Creatomate...")
        response_video = requests.get(url_video, stream=True, timeout=60)
        response_video.raise_for_status()
        video_bytes = response_video.content

        # Faz o upload para o WordPress
        print("    - Enviando para o WordPress...")
        url_wp_media = f"{WP_URL}/wp-json/wp/v2/media"
        headers_upload = HEADERS_WP.copy()
        headers_upload['Content-Disposition'] = f'attachment; filename={nome_arquivo}'
        headers_upload['Content-Type'] = 'video/mp4'
        
        response_wp = requests.post(url_wp_media, headers=headers_upload, data=video_bytes, timeout=60)
        response_wp.raise_for_status()
        link_video_publico = response_wp.json()['source_url']
        
        print(f"✅ [ETAPA 2/4] Vídeo salvo no WordPress!")
        return link_video_publico
    except Exception as e:
        print(f"❌ [ERRO] Falha ao fazer upload para o WordPress: {e}")
        return None

# As funções de publicar no Instagram e Facebook não mudam, pois elas já recebem uma URL pública
# ... (as funções publicar_reel_no_instagram e publicar_video_no_facebook continuam as mesmas do código anterior) ...
# COPIE E COLE AS FUNÇÕES `publicar_reel_no_instagram` E `publicar_video_no_facebook` AQUI

# ==============================================================================
# BLOCO 4: O MAESTRO (RECEPTOR DO WEBHOOK)
# ==============================================================================
@app.route('/webhook-boca', methods=['POST'])
def webhook_boca_receiver():
    print("\n" + "="*50)
    print("🔔 [WEBHOOK BOCA] Webhook recebido do app Voz do Litoral!")
    
    try:
        dados_brutos = request.json
        post_info = dados_brutos.get('post', {})
        post_id = post_info.get('ID')
        post_type = post_info.get('post_type')
        post_parent = post_info.get('post_parent')

        if post_type == 'revision' and post_parent: post_id = post_parent
        elif not post_id: post_id = dados_brutos.get('post_id')
        if not post_id: raise ValueError("ID do post não encontrado.")

        print(f"✅ [WEBHOOK BOCA] ID do post extraído: {post_id}")
        
        url_api_post = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
        response_post = requests.get(url_api_post, headers=HEADERS_WP, timeout=15); response_post.raise_for_status()
        post_data = response_post.json()

        titulo_noticia = BeautifulSoup(post_data.get('title', {}).get('rendered', ''), 'html.parser').get_text()
        resumo_noticia = BeautifulSoup(post_data.get('excerpt', {}).get('rendered', ''), 'html.parser').get_text(strip=True)
        id_imagem_destaque = post_data.get('featured_media')

        if not id_imagem_destaque or id_imagem_destaque == 0:
            return jsonify({"status": "ignorado_sem_imagem"}), 200
            
        url_api_media = f"{WP_URL}/wp-json/wp/v2/media/{id_imagem_destaque}"
        response_media = requests.get(url_api_media, headers=HEADERS_WP, timeout=15); response_media.raise_for_status()
        url_imagem_destaque = response_media.json().get('source_url')
            
    except Exception as e:
        print(f"❌ [ERRO CRÍTICO BOCA] Falha ao processar dados do webhook: {e}")
        return jsonify({"status": "erro_processamento_wp_boca"}), 500

    print("\n🚀 INICIANDO FLUXO DE PUBLICAÇÃO (BOCA via Creatomate)...")
    
    # ETAPA 1: Criar vídeo com Creatomate
    url_video_creatomate = criar_video_com_creatomate(titulo_noticia, url_imagem_destaque)
    if not url_video_creatomate: return jsonify({"status": "erro_criacao_video_creatomate"}), 500
    
    # ETAPA 2: Fazer upload do vídeo para o WordPress
    nome_do_arquivo = f"reel_boca_{post_id}.mp4"
    link_wp_video = upload_para_wordpress(url_video_creatomate, nome_do_arquivo)
    if not link_wp_video: return jsonify({"status": "erro_upload_wordpress_boca"}), 500

    # ETAPAS 3 e 4: Publicar nas redes sociais
    legenda_final = f"{titulo_noticia}\n\n{resumo_noticia}\n\nLeia a matéria completa em nosso site. Link na bio!\n\n#noticias #litoralnorte #bocanotrombone #jornalismo #reels"
    
    sucesso_ig = publicar_reel_no_instagram(link_wp_video, legenda_final)
    sucesso_fb = publicar_video_no_facebook(link_wp_video, legenda_final)

    if sucesso_ig or sucesso_fb:
        print("🎉 [SUCESSO] Automação do Boca no Trombone concluída!")
        return jsonify({"status": "sucesso_publicacao_boca"}), 200
    else:
        print("😭 [FALHA] Nenhuma publicação do Boca no Trombone foi bem-sucedida.")
        return jsonify({"status": "erro_publicacao_redes_boca"}), 500

# ... (O resto do código, incluindo a rota '/' e o if __name__ == '__main__', continua igual) ...
# COPIE E COLE O BLOCO 5 (INICIALIZAÇÃO) AQUI
