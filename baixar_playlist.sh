#!/bin/bash

# ==============================================================================
# Script de Download de Playlists do YouTube (Áudio MP3 - Alta Qualidade)
# ==============================================================================

# 1. DIRETÓRIO PADRÃO DE DOWNLOAD
# Altere o caminho abaixo para onde deseja salvar os arquivos por padrão.
DOWNLOAD_DIR="$HOME/Documents/Music/All/Downloads"

# Cria a pasta caso ela não exista
mkdir -p "$DOWNLOAD_DIR"

# 2. VERIFICAÇÃO DE ARGUMENTOS
if [ -z "$1" ]; then
    echo "Erro: Nenhuma URL fornecida!"
    echo "Uso: ./baixar_playlist.sh <URL_DA_PLAYLIST>"
    exit 1
fi

PLAYLIST_URL="$1"

# 3. VERIFICAÇÃO DE DEPENDÊNCIAS (macOS)
if ! command -v yt-dlp &> /dev/null; then
    echo "Erro: yt-dlp não está instalado. Instale usando: brew install yt-dlp"
    exit 1
fi

if ! command -v ffmpeg &> /dev/null; then
    echo "Erro: ffmpeg não está instalado. Instale usando: brew install ffmpeg"
    exit 1
fi

# 4. EXECUÇÃO DO DOWNLOAD
echo "Iniciando o download da playlist..."
echo "Salvando em: $DOWNLOAD_DIR"
echo "------------------------------------------------------------"

# -x: extrai áudio
# --audio-format mp3: converte para mp3
# --audio-quality 0: VBR de melhor qualidade (equivalente a ~320kbps)
# -P: especifica o diretório de saída mantendo o nome do vídeo padrão
yt-dlp \
  -x \
  --audio-format mp3 \
  --audio-quality 0 \
  -P "$DOWNLOAD_DIR" \
  "$PLAYLIST_URL"

echo "------------------------------------------------------------"
echo "Download concluído com sucesso!"

