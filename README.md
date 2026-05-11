# Canvas Report Processor

API FastAPI hospedada no Vercel para baixar e processar relatórios CSV `student_analysis` do Canvas LMS. O serviço resolve a limitação do Power Automate com URLs temporárias do Canvas que redirecionam via HTTP `302` para CDNs externas.

## Produção

URL base:

```text
https://canvas-report-processor.vercel.app
```

Documentação Swagger:

```text
https://canvas-report-processor.vercel.app/docs
```

Health check:

```text
https://canvas-report-processor.vercel.app/health
```

Endpoint principal:

```text
https://canvas-report-processor.vercel.app/reports/student-analysis/process
```

## Uso Rápido

Envie uma URL temporária do Canvas no corpo JSON:

```bash
curl -X POST https://canvas-report-processor.vercel.app/reports/student-analysis/process \
  -H "Content-Type: application/json" \
  -d '{
    "download_url": "https://pucminas.instructure.com/files/123456/download?download_frd=1&verifier=TOKEN"
  }'
```

Resposta padrão, otimizada para IA Hub:

```json
{
  "comentarios": [
    {
      "submitted": "2026-05-06",
      "grade": "10",
      "comment": "Excelente material didático."
    },
    {
      "submitted": "2026-05-07",
      "grade": "8",
      "comment": "O conteúdo do curso está antigo."
    }
  ]
}
```

## Endpoints

| Método | Caminho | URL completa | Finalidade |
| --- | --- | --- | --- |
| `GET` | `/` | `https://canvas-report-processor.vercel.app/` | Mostra status e caminhos principais da API |
| `GET` | `/health` | `https://canvas-report-processor.vercel.app/health` | Verifica se a API está online |
| `GET` | `/docs` | `https://canvas-report-processor.vercel.app/docs` | Abre a documentação Swagger |
| `POST` | `/reports/student-analysis/process` | `https://canvas-report-processor.vercel.app/reports/student-analysis/process` | Baixa, processa e extrai comentários do CSV Canvas |

## Endpoint Principal

```http
POST /reports/student-analysis/process
Content-Type: application/json
```

### Entrada com URL temporária

Use este formato quando o Power Automate já tiver a URL completa retornada pelo Canvas:

```json
{
  "download_url": "https://pucminas.instructure.com/files/123456/download?download_frd=1&verifier=TOKEN"
}
```

### Entrada com file_id

Use este formato quando o fluxo tiver apenas o `file_id` e o `verifier`:

```json
{
  "file_id": "123456",
  "verifier": "TOKEN"
}
```

## Formatos de Retorno

### Padrão: IA Hub

Sem informar `output_format`, o retorno traz somente os comentários:

```json
{
  "comentarios": [
    {
      "submitted": "2026-05-06",
      "grade": "10",
      "comment": "Excelente material didático."
    },
    {
      "submitted": "2026-05-07",
      "grade": "8",
      "comment": "O conteúdo do curso está antigo."
    }
  ]
}
```

Este é o formato recomendado para enviar diretamente a um fluxo de IA. A chave `comentarios` continua sendo o ponto principal da resposta, agora com cada comentário acompanhado do respectivo `submitted`.

### Compacto: nota e comentário

Para retornar nota e comentário:

```json
{
  "download_url": "https://pucminas.instructure.com/files/123456/download?download_frd=1&verifier=TOKEN",
  "output_format": "compact"
}
```

Resposta:

```json
{
  "success": true,
  "total_linhas": 25,
  "total_comentarios": 21,
  "linhas_invalidas": 4,
  "respostas": [
    {
      "nota": "10",
      "comentario": "Excelente material didático.",
      "submitted": "2026-05-06"
    }
  ]
}
```

### JSON técnico

Para depuração:

```json
{
  "download_url": "https://pucminas.instructure.com/files/123456/download?download_frd=1&verifier=TOKEN",
  "output_format": "json"
}
```

Neste modo, `comments` retorna apenas:

```json
{
  "submitted": "2026-05-06",
  "grade": "10",
  "comment": "Excelente material didático."
}
```

### Summary

Para metadados técnicos e contagens:

```json
{
  "download_url": "https://pucminas.instructure.com/files/123456/download?download_frd=1&verifier=TOKEN",
  "output_format": "summary"
}
```

## Contexto do Problema

O Canvas retorna URLs temporárias neste formato:

```text
https://pucminas.instructure.com/files/{file_id}/download?download_frd=1&verifier={token}
```

Essas URLs normalmente não entregam o CSV diretamente. Primeiro respondem com HTTP `302 Found` e redirecionam para CDNs como:

```text
canvas-user-content.com
inscloudgate.net
```

Esse comportamento gera falhas recorrentes no Power Automate e em Custom Connectors por causa de redirects, troca de domínio, conteúdo binário, `Content-Disposition` e URLs assinadas temporárias. Esta API centraliza o download e devolve um JSON simples para os fluxos.

## Fluxo de Integração

```text
Power Automate
  -> Canvas LMS
  -> obtém file_id ou download_url
  -> POST na API hospedada no Vercel
  -> API baixa o CSV seguindo redirects
  -> API extrai comentários qualitativos
  -> IA Hub / Dataverse / próxima etapa do fluxo
```

## Pipeline Interno

1. Valida `download_url` ou `file_id`.
2. Monta URL Canvas quando necessário.
3. Faz download com redirects habilitados.
4. Valida status HTTP e conteúdo vazio.
5. Decodifica em UTF-8, UTF-8 com BOM ou latin1.
6. Detecta delimitador CSV.
7. Normaliza colunas.
8. Identifica perguntas abertas do relatório `student_analysis`.
9. Remove linhas vazias ou sem comentário.
10. Retorna JSON no formato solicitado.

## Tratamento de Erros

| Situação | HTTP | Descrição |
| --- | --- | --- |
| Sem `download_url` e sem `file_id` | `422` | Entrada inválida |
| Timeout no download | `502` | Canvas/CDN demorou para responder |
| Redirects excedidos | `502` | Cadeia de redirects acima do limite |
| Canvas/CDN com erro HTTP | status original quando aplicável | Erro retornado pelo Canvas ou CDN |
| Arquivo vazio | `502` | Download sem conteúdo |
| CSV sem cabeçalho | `422` | Arquivo inválido |
| Encoding inválido | `422` | Falha de decodificação |

## Variáveis de Ambiente

Todas usam o prefixo `CANVAS_PROCESSOR_`.

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `APP_NAME` | `Canvas Report Processor` | Nome da API |
| `CANVAS_BASE_URL` | `https://pucminas.instructure.com` | URL base do Canvas |
| `REQUEST_TIMEOUT_SECONDS` | `30` | Timeout HTTP |
| `MAX_REDIRECTS` | `10` | Limite de redirects |
| `DEFAULT_ENCODING` | `utf-8` | Encoding primário |
| `FALLBACK_ENCODING` | `latin1` | Encoding de fallback |
| `LOG_LEVEL` | `INFO` | Nível de logs |

## Deploy no Vercel

O projeto usa:

```text
api/index.py
vercel.json
```

O `api/index.py` expõe a instância FastAPI para o runtime Python serverless do Vercel. O `vercel.json` roteia todas as chamadas para essa função.

Deploy manual:

```bash
npx vercel deploy --prod --yes
```

Branch de produção:

```text
prod.v1.0
```

## Setup Local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Local:

```text
http://127.0.0.1:8000
```

Swagger local:

```text
http://127.0.0.1:8000/docs
```

## Testes

```bash
pytest
```

A suíte cobre:

- download/processamento orquestrado;
- parser CSV UTF-8 e latin1;
- extração de comentários por colunas de perguntas abertas;
- retorno mínimo para IA Hub;
- retorno compacto com nota e comentário;
- retorno técnico `json` e `summary`.

## Estrutura

```text
.
├── api/
│   └── index.py
├── app/
│   ├── controllers/
│   ├── models/
│   ├── parsers/
│   ├── services/
│   ├── utils/
│   └── main.py
├── docs/
├── tests/
├── pyproject.toml
├── requirements.txt
├── vercel.json
└── README.md
```
