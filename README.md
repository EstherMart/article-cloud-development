# Repositório de Artigos Acadêmicos

Trabalho Prático 1 de Desenvolvimento de Software para Nuvem (professores Paulo A. L. Rego e Fernando A. M. Trinta).

**Entrega:** 10/10/2026 às 23h59. Link do git e vídeo da Parte 2 funcionando.

## O que é

Um repositório onde alunos e pesquisadores cadastram trabalhos acadêmicos (título, autores, resumo, palavras-chave, área) e enviam o PDF do artigo. Qualquer pessoa pode listar, buscar e baixar os trabalhos. Depois do envio, o sistema extrai o texto do PDF e traduz o resumo automaticamente, sem travar quem fez o upload.

A aplicação cumpre os dois requisitos da spec:

- **Parte 1:** usar 6 serviços da AWS (EC2, S3, RDS, ElastiCache, DynamoDB e SNS/SQS), com CRUD, um arquivo binário (o PDF) e processamento desacoplado.
- **Parte 2:** tornar a API elástica com Load Balancer e Auto Scaling Group (de 1 a 3 instâncias, escalando por CPU).

## Como funciona

Cada serviço tem um papel único. O PDF vai para o S3, os metadados para o RDS, o cache para o Redis, os logs para o DynamoDB e o processamento pesado roda fora da API, via SNS/SQS.

1. **Cadastro.** O usuário preenche o formulário e anexa o PDF. A API valida, grava os metadados no RDS com status `PENDENTE`, envia o PDF ao S3, registra o log no DynamoDB e publica um evento no SNS. Responde logo, sem esperar a tradução.
2. **Processamento.** O SNS entrega o evento numa fila SQS. O worker baixa o PDF, extrai o texto, traduz o resumo, grava no RDS, marca o artigo como `PROCESSADO` e invalida o cache. Só então apaga a mensagem da fila.
3. **Consulta.** A API procura no Redis. Se achar, devolve direto. Se não, consulta o RDS, grava no Redis com TTL e devolve. O PDF é baixado do S3 por URL pré-assinada, nunca passa pelo Redis.

## Serviços AWS

| Serviço | Papel | Exigência da spec |
|---|---|---|
| EC2 | Roda a API e, em outra instância, o worker | Requisito 1 |
| RDS (PostgreSQL) | Metadados dos artigos | Requisito 2 |
| S3 | Guarda o PDF (bucket privado, download por URL pré-assinada) | Requisito 3 |
| ElastiCache (Redis) | Cache de consultas frequentes: metadados, listas, buscas. Nunca guarda PDF | Requisito 4 |
| DynamoDB | Log das ações de CRUD: tipo da ação, dados manipulados e hora (`logs_crud`) | Requisito 5 |
| SNS/SQS | Desacopla a API do worker que extrai e traduz | Requisito 6 |
| ALB + Auto Scaling | Elasticidade horizontal da API | Parte 2 |

Cada serviço ausente desconta 1,5 ponto. Sem interface gráfica, desconta 1,0.

## Diagramas

### Visão geral (componentes)

```mermaid
flowchart LR
    U[Usuário] --> F[Frontend<br/>HTML/Bootstrap]
    F -->|HTTP| ALB[ALB<br/>Parte 2]
    ALB --> API

    subgraph ASG[Auto Scaling Group · 1 a 3 instâncias]
        API[API Django<br/>EC2]
    end

    API -->|metadados| RDS[(RDS<br/>PostgreSQL)]
    API -->|PDF| S3[(S3)]
    API <-->|cache| REDIS[(ElastiCache<br/>Redis)]
    API -->|log CRUD| DDB[(DynamoDB<br/>logs_crud)]
    API -->|publica evento| SNS[[SNS]]
    SNS --> SQS[[SQS]]
    SQS -.->|mensagens que falham| DLQ[[DLQ]]
    SQS --> W[Worker<br/>EC2 própria]
    W -->|baixa PDF| S3
    W -->|resumo traduzido, status| RDS
    W -->|invalida cache| REDIS
```

### Cadastro e processamento (sequência)

```mermaid
sequenceDiagram
    actor U as Usuário
    participant API as API (EC2)
    participant RDS
    participant S3
    participant DDB as DynamoDB
    participant SNS
    participant SQS
    participant W as Worker (EC2)
    participant R as Redis

    U->>API: POST /articles/ (formulário + PDF)
    API->>API: valida dados e arquivo
    API->>RDS: grava metadados (PENDENTE)
    RDS-->>API: id
    API->>S3: envia PDF (chave com o id)
    alt falha no upload
        API->>RDS: apaga registro ou marca ERRO
        API-->>U: erro
    else sucesso
        API->>RDS: atualiza s3_key
        API->>DDB: log CREATE (ação, dados, hora)
        API->>R: invalida artigos:recentes e busca:*
        API->>SNS: publica evento
        API-->>U: 201 (artigo PENDENTE)
    end

    SNS->>SQS: entrega mensagem
    W->>SQS: long polling (20 s)
    SQS-->>W: mensagem
    W->>RDS: status PROCESSANDO
    W->>S3: baixa PDF
    W->>W: extrai texto e traduz resumo
    W->>RDS: grava tradução, status PROCESSADO
    W->>R: invalida artigo:{id}
    W->>SQS: apaga mensagem
    Note over W,SQS: Se falhar: marca ERRO e a mensagem volta à fila.<br/>Após 3 tentativas vai para a DLQ.
```

### Consulta com cache (sequência)

```mermaid
sequenceDiagram
    actor U as Usuário
    participant API
    participant R as Redis
    participant RDS
    participant S3

    U->>API: GET /articles/{id}/
    API->>R: busca artigo:{id}
    alt hit
        R-->>API: dados
    else miss
        API->>RDS: consulta
        RDS-->>API: dados
        API->>R: grava com TTL (5 a 10 min)
    end
    API-->>U: metadados

    U->>API: GET /articles/{id}/download/
    API->>S3: gera URL pré-assinada
    API-->>U: URL (o download vai direto ao S3)
```

### Estados de um artigo

```mermaid
stateDiagram-v2
    [*] --> PENDENTE: cadastro na API
    PENDENTE --> PROCESSANDO: worker recebe a mensagem
    PROCESSANDO --> PROCESSADO: tradução salva no RDS
    PROCESSANDO --> ERRO: falha no worker
    ERRO --> PROCESSANDO: nova tentativa da fila
    PENDENTE --> ERRO: falha no upload ao S3
```

Os diagramas usam Mermaid e aparecem renderizados no GitHub.

## Estrutura do repositório

```
.
├── backend/    API Django (ver backend/README.md)
│   └── articles/services/   camada por serviço AWS (esqueleto, ver services/README.md)
├── frontend/   Telas estáticas HTML/Bootstrap (ver frontend/README.md)
│   └── js/                  scripts das telas e acesso à API (ver js/README.md)
├── worker/     Consumidor SQS: extração e tradução (ver worker/README.md)
├── infra/      Parte 2: ALB e Auto Scaling, scripts de setup (ver infra/README.md)
└── docs/
    ├── arquitetura.md   fluxos, modelo de dados, decisões técnicas
    ├── aws-setup.md     passo a passo de criação dos recursos AWS
    └── fluxo-git.md     branches, PRs e convenções
```

Cada pasta tem um README próprio com o que existe, o que falta e como rodar.

## Como começar

```
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # preencha; sem DB_HOST usa SQLite local
set -a; source .env; set +a
python manage.py makemigrations && python manage.py migrate
python manage.py runserver
```

O front abre direto no navegador (`frontend/index.html`). Detalhes em `backend/README.md` e `frontend/README.md`.

## Status

| Item | Estado |
|---|---|
| Projeto Django, models, GET `/articles/` | feito |
| Settings por variável de ambiente (RDS/SQLite) | feito |
| Telas do front (sem JavaScript) | feito |
| Conexão com o RDS | pendente |
| CRUD real, validação | pendente |
| Upload no S3 e URL pré-assinada | pendente |
| Log no DynamoDB | pendente |
| Cache Redis | pendente |
| SNS/SQS e worker | pendente |
| JavaScript do front integrado à API | pendente |
| Parte 2 (ALB e Auto Scaling) | pendente, a pesquisar |

## Regras do time

- Ninguém commita direto na `main`. Use branch `feat/...` e PR revisado (ver `docs/fluxo-git.md`).
- Nenhuma credencial no código ou no chat. Use `.env` (ignorado pelo git) e, na EC2, a IAM Role (LabRole).
- A API é stateless: nada de uploads em disco local, sessão em memória ou cache no processo.
- RDS e ElastiCache cobram por hora. Use instâncias pequenas e apague tudo após a entrega.
