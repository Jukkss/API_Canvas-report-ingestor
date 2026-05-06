# Canvas Report Processor

Microservico FastAPI para baixar, tratar e converter relatórios CSV `student_analysis` do Canvas LMS usados no fluxo de automação de avaliações institucionais do IEC/PUC Minas.

## Contexto do problema

O Power Automate já cria reports no Canvas, consulta status e obtém `file_id`, URLs e metadados. A falha recorrente ocorre na etapa de download do CSV, porque o Canvas retorna uma URL temporária como:

```text
https://pucminas.instructure.com/files/{file_id}/download?download_frd=1&verifier={token}
```

Essa URL não entrega necessariamente o arquivo de imediato. Ela responde com HTTP `302 Found` e redireciona para uma CDN externa, normalmente domínios como `canvas-user-content.com` ou `inscloudgate.net`. Em integrações low-code, esse comportamento costuma quebrar por troca de domínio, autenticação no redirect, stream binário, `Content-Disposition` e tempo de vida curto das URLs assinadas.

## Solução

Este módulo isola o problema de download/processamento fora do Power Automate:

1. Recebe `download_url` temporária ou `file_id`.
2. Monta a URL do Canvas quando necessário.
3. Segue redirects HTTP automaticamente.
4. Baixa o conteúdo CSV.
5. Decodifica com UTF-8 e fallback latin1.
6. Faz parsing do CSV.
7. Normaliza nomes de colunas.
8. Remove linhas vazias ou sem comentário.
9. Retorna JSON estruturado para gravação no Dataverse.

## Arquitetura

```text
Power Automate
  -> Canvas LMS reports API
  -> Canvas Report Processor
       -> downloader HTTP
       -> parser CSV
       -> normalizador
       -> resposta JSON
  -> Dataverse
```

Responsabilidades principais:

- `controllers`: endpoints FastAPI.
- `services`: download Canvas e orquestração do processamento.
- `parsers`: parsing e normalização de CSV.
- `models`: contratos Pydantic de entrada e saída.
- `utils`: logging e tratamento de erros.

## Estrutura do projeto

```text
canvas-report-processor/
├── app/
│   ├── controllers/
│   ├── services/
│   ├── parsers/
│   ├── utils/
│   ├── models/
│   └── main.py
├── tests/
├── docs/
├── requirements.txt
├── README.md
└── .env.example
```

O arquivo de tasks fica fora desta pasta, em `../PROJECT_TASKS.md`.

## Setup local

```bash
cd canvas-report-processor
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

API local:

```text
http://127.0.0.1:8000
```

Documentação automática:

```text
http://127.0.0.1:8000/docs
```

## Variáveis de ambiente

Todas usam o prefixo `CANVAS_PROCESSOR_`.

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `APP_NAME` | `Canvas Report Processor` | Nome exibido pela API |
| `CANVAS_BASE_URL` | `https://pucminas.instructure.com` | Base URL do Canvas |
| `REQUEST_TIMEOUT_SECONDS` | `30` | Timeout de download |
| `MAX_REDIRECTS` | `10` | Limite de redirects HTTP |
| `DEFAULT_ENCODING` | `utf-8` | Encoding primário |
| `FALLBACK_ENCODING` | `latin1` | Fallback de encoding |
| `LOG_LEVEL` | `INFO` | Nível de logs |

Exemplo real no `.env`:

```env
CANVAS_PROCESSOR_REQUEST_TIMEOUT_SECONDS=45
CANVAS_PROCESSOR_MAX_REDIRECTS=10
CANVAS_PROCESSOR_LOG_LEVEL=INFO
```

## Endpoints

### Health check

```http
GET /health
```

Resposta:

```json
{
  "status": "ok",
  "service": "Canvas Report Processor"
}
```

### Processar student_analysis

```http
POST /reports/student-analysis/process
Content-Type: application/json
```

Com URL temporária:

```json
{
  "download_url": "https://pucminas.instructure.com/files/123456/download?download_frd=1&verifier=TOKEN"
}
```

Com `file_id`:

```json
{
  "file_id": "123456",
  "verifier": "TOKEN"
}
```

Resposta mínima padrão para IA Hub:

```json
{
  "comentarios": [
    "Excelente material didático.",
    "O conteúdo do curso está antigo."
  ]
}
```

Esse é o formato recomendado para enviar diretamente ao IA Hub quando o objetivo é analisar apenas comentários qualitativos.

Para retornar contagens e pares `nota`/`comentario`, use `output_format: "compact"`:

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
      "comentario": "Excelente material didático."
    }
  ]
}
```

Para depuração, use `output_format: "json"`:

```json
{
  "success": true,
  "total_rows": 2,
  "valid_comments": 1,
  "invalid_rows": 1,
  "columns": ["student_id", "student_name", "comment"],
  "comments": [
    {
      "student_id": "123",
      "student_name": "Ana Silva",
      "course_id": null,
      "course_name": null,
      "section": null,
      "question": null,
      "grade": "10",
      "comment": "Excelente orientação do professor.",
      "raw": {
        "student_id": "123",
        "student_name": "Ana Silva",
        "comment": "Excelente orientação do professor."
      }
    }
  ],
  "metadata": {
    "source_url": "https://pucminas.instructure.com/files/123456/download?download_frd=1&verifier=TOKEN",
    "final_url": "https://canvas-user-content.com/report.csv",
    "status_code": 200,
    "content_type": "text/csv",
    "content_disposition": "attachment; filename=\"report.csv\"",
    "encoding": "utf-8",
    "redirect_count": 1,
    "size_bytes": 2048
  }
}
```

Para retornar apenas metadados técnicos e contagens, use:

```json
{
  "download_url": "https://pucminas.instructure.com/files/123456/download?download_frd=1&verifier=TOKEN",
  "output_format": "summary"
}
```

Nesse modo, `comments` retorna vazio, mas `valid_comments`, `invalid_rows` e `metadata` continuam preenchidos.

## Pipeline de processamento

1. Validação da entrada: exige `download_url` ou `file_id`.
2. Construção da URL quando o fluxo envia `file_id`.
3. Download com `httpx.AsyncClient`.
4. Redirects habilitados com limite configurável.
5. Validação de status HTTP e conteúdo vazio.
6. Decoding em UTF-8, `utf-8-sig` e latin1.
7. Detecção simples de delimitador CSV: vírgula, ponto e vírgula ou tab.
8. Normalização de colunas para `snake_case` ASCII.
9. Extração de comentários por aliases em inglês e português.
10. Retorno estruturado.

## Tratamento de erros

| Situação | HTTP | Resposta |
| --- | --- | --- |
| Sem `download_url` e sem `file_id` | `422` | Validação Pydantic |
| Timeout no download | `502` | `Timeout ao baixar o arquivo Canvas.` |
| Redirects excedidos | `502` | `Limite de redirects excedido.` |
| Canvas/CDN com erro HTTP | status original quando aplicável | `Canvas/CDN retornou status HTTP ...` |
| Arquivo vazio | `502` | `Download concluido, mas o arquivo esta vazio.` |
| CSV sem cabeçalho | `422` | `CSV sem cabecalho.` |
| Encoding inválido | `422` | `Nao foi possivel decodificar o CSV...` |

## Testes

```bash
cd canvas-report-processor
pytest
```

A suíte cobre:

- extração de comentários UTF-8;
- fallback latin1;
- remoção de linhas vazias ou sem comentário;
- processamento por `file_id`;
- modo `summary`.
