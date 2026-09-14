# DJCode
Util code projects to automate DJ Portfolio maintenance


# Exemplos

- `python3 organizador_musicas.py`
    - Percorre recursivamente o diretorio e modifica tags/nome de arquivo, alterando pra "Artista - Titulo".
    - Guarda na pasta selecionada um historico de mudancas de forma que se a pasta for selecionada mais de uma vez, ele nao re-analiza musicas previamente analizadas, agilizando manutencao do repositorio
- `./baixar_playlist.sh --test https://www.youtube.com/watch?v=vaEI-DLdpj8&list=RDvaEI-DLdpj8&start_radio=1`
    - Baixa a musica do link na pasta de teste
    - Sem a flag ele baixa na pasta "~/Documents/Music/Downloads"