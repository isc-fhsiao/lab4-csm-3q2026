# Lab 4 CSM: Codificação com perdas de áudio e imagem (Grupo 3)

Relatório do Lab 4 de ESFI001 Comunicações e Sistemas Multimídia (CSM), UFABC, 3º quadrimestre de 2026.

Autores: Fernando Hsiao, Isabella Pierina, Pedro Ricardo Cantu Benedetti e Yasmin Ribeiro Santos.

- Gravações do Lab 3 codificadas em MP3, AAC e Ogg Vorbis a 48 e 128 kbit/s.
- Fotos da webcam comprimidas em JPEG com `-q:v` 2, 20 e 31.
- Avaliação MUSHRA-like de áudio e comparação de imagens por pares, feitas por 18 participantes externos como ação extensionista.
- Teste cego e comparador de imagem no próprio navegador.

Outros relatórios do grupo: [Lab 1](https://lab3-csm-3q2026.netlify.app/lab1/), [Lab 2](https://lab3-csm-3q2026.netlify.app/lab2/), [Lab 3](https://lab3-csm-3q2026.netlify.app/lab3/).

## Estrutura

Site estático, sem build: HTML, CSS e JavaScript puros.

```
index.html          portal do grupo, com os links dos labs 1 a 4
css/portal.css      estilos do portal
lab4/               relatório do Lab 4
  index.html        relatório
  css/style.css     estilos
  js/dados.js       dados gerados por lab4/codigo/analise_lab4.py
  js/imagens.js     foto e JPEGs em data URI para o comparador
  js/app.js         tabelas, gráfico de espectro, teste cego e comparador
  img/              foto coletiva, JPEGs e gráficos
  audio/G1 a G4     referência, âncora e versões codificadas (FLAC)
  dados/            respostas da avaliação externa (CSV)
  codigo/           script de análise em Python
```

Os labs 1 a 3 continuam publicados em https://lab3-csm-3q2026.netlify.app; o portal aponta para lá.

## Publicação

O Netlify publica a raiz do repositório (`netlify.toml`). Também dá para arrastar a pasta em app.netlify.com/drop.
