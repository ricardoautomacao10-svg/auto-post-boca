#!/usr/bin/env bash
# exit on error
set -o errexit

echo "--- Iniciando processo de build simplificado ---"

# 1. Instalação do FFmpeg
echo "--> Instalando FFmpeg..."
apt-get update && apt-get install -y ffmpeg
echo "--> FFmpeg instalado com sucesso."

# 2. Instalação das dependências Python
echo "--> Instalando pacotes Python..."
pip install -r requirements.txt

echo "--- Build finalizado com sucesso! ---"
