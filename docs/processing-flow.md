# Fluxo de processamento

Este documento resume o papel do módulo dentro da automação institucional.

## Entrada

O Power Automate deve enviar uma das opções:

- `download_url`: URL temporária completa do Canvas.
- `file_id` e, quando existir, `verifier`: dados usados para montar a URL de download.

## Download

O serviço usa cliente HTTP assíncrono com redirects habilitados. Isso permite atravessar o `302` do domínio `pucminas.instructure.com` até a CDN temporária que hospeda o arquivo CSV.

## Parsing

O conteúdo baixado é tratado como bytes. O parser tenta decodificar em UTF-8, depois `utf-8-sig`, e por fim latin1. O CSV é lido com suporte a vírgula, ponto e vírgula e tabulação.

## Saída

A resposta contém contagens, colunas normalizadas, comentários válidos e metadados técnicos do download.
