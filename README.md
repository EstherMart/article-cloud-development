# Repositório de Artigos Acadêmicos

Trabalho Prático 1 de Desenvolvimento de Software para Nuvem (professores Paulo A. L. Rego e Fernando A. M. Trinta).

**Equipe:**

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


## Modelo de dados

O RDS guarda os metadados em três tabelas e uma tabela de ligação para cada relação N:N. O app Django `articles` cria tudo pelas migrations.

```mermaid
erDiagram
    USER ||--o{ ARTICLE : "cadastra"
    ARTICLE }o--o{ AUTHOR : "tem"
    ARTICLE }o--o{ TAG : "tem"

    ARTICLE {
        bigint id PK
        varchar title UK "até 255"
        varchar area "até 255"
        text abstract "resumo digitado"
        text translated_abstract "preenchido pelo worker"
        varchar s3_key "artigos/{id}.pdf"
        varchar processing_status "PENDENTE, PROCESSANDO, PROCESSADO, ERRO"
        datetime upload_datetime "automático"
        int user_id FK
    }
    AUTHOR {
        bigint id PK
        varchar name
    }
    TAG {
        bigint id PK
        varchar name UK
    }
```

| Decisão | Motivo |
|---|---|
| `Author` é uma tabela própria (N:N) | A spec fala em "autores". Um autor pode ter vários artigos |
| `title` é único | Evita cadastro duplicado do mesmo trabalho |
| `s3_key` fica vazia até o upload | O id do RDS entra na chave do S3, então o registro nasce primeiro |
| `translated_abstract` só o worker escreve | A API nunca espera a tradução |
| Apagar o usuário apaga os artigos (`CASCADE`) | Simplifica o laboratório. Revise antes de usar em produção |

Fora do RDS: o DynamoDB guarda o log de cada CRUD (`logs_crud`), o S3 guarda o PDF e o Redis guarda cópias temporárias das consultas.

## Estrutura do repositório

```
.
├── backend/    API Django e testes unitários (ver backend/README.md)
│   └── articles/services/   camada por serviço AWS (esqueleto, ver services/README.md)
├── frontend/   Telas estáticas HTML/Bootstrap (ver frontend/README.md)
│   └── js/                  scripts das telas e acesso à API (ver js/README.md)
├── worker/     Consumidor SQS: extração e tradução (ver worker/README.md)
├── infra/      Parte 2: ALB e Auto Scaling, scripts de setup (ver infra/README.md)
└── docs/
    └── aws/   passo a passo de cada serviço AWS (ver docs/aws/README.md)
```

Cada pasta tem um README próprio com o que existe, o que falta e como rodar.

## Índice da documentação

| Documento | Para quê |
|---|---|
| [backend/README.md](backend/README.md) | API, rotas, modelo de dados, migrations e testes |
| [backend/articles/services/README.md](backend/articles/services/README.md) | Camada de cada serviço AWS |
| [backend/articles/tests/integration/README.md](backend/articles/tests/integration/README.md) | Testes de integração com a AWS real (desligados por padrão) |
| [frontend/README.md](frontend/README.md) e [frontend/js/README.md](frontend/js/README.md) | Telas e scripts |
| [worker/README.md](worker/README.md) | Processamento assíncrono |
| [infra/README.md](infra/README.md) | Parte 2 (ALB e Auto Scaling) |
| [docs/aws/README.md](docs/aws/README.md) | Criar, testar e apagar cada serviço AWS, mais o estudo para a arguição |

## Decisões técnicas

- **Redis não guarda PDF.** Um PDF tem vários MB e o ElastiCache é memória cara. Cacheie metadados, listas e buscas. O PDF sai do S3 por URL pré-assinada.
- **Ordem das gravações.** RDS primeiro para obter o id, depois S3 com o id na chave, depois `s3_key`, log e SNS. Se o upload falhar, apague o registro ou marque ERRO.
- **Invalidação do cache.** Todo CREATE, UPDATE e DELETE apaga as chaves afetadas (`artigo:{id}`, `artigos:recentes`, `busca:*`). O worker também invalida `artigo:{id}`. O TTL de 5 a 10 minutos é a rede de segurança.
- **Segurança.** Sem chaves no código, IAM Role na EC2 (LabRole), RDS e Redis em Security Groups que só aceitam as instâncias da aplicação, bucket S3 privado.
- **Stateless.** Sessão, uploads e cache vão para S3 e Redis, nunca para disco ou memória da EC2. Isso evita retrabalho na Parte 2.
- **Custos.** RDS e ElastiCache cobram por hora mesmo parados. Use t3.micro e cache.t3.micro, desligue ao fim do dia e apague tudo após a entrega.

## Pontos em aberto

- Chave e atributos da tabela `logs_crud` (a sugestão é partição `article_id` e ordenação `timestamp`).
- Formato final da mensagem SNS/SQS.
- Autenticação de usuários (o front tem login e cadastro, o back ainda não).

## Como rodar localmente

Requisitos: Python 3.12 ou mais novo (o Django 6.1 não roda em versões anteriores). Sem `DB_HOST` o backend usa SQLite, então não precisa de banco nem de AWS para ver as telas.

**1. Backend** (terminal 1)

```
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
set -a; source .env; set +a
python manage.py migrate
python manage.py runserver          # http://127.0.0.1:8000
```

**2. Frontend** (terminal 2)

```
cd frontend
python3 -m http.server 8080         # http://127.0.0.1:8080
```

Abra `http://127.0.0.1:8080`, crie uma conta em **Cadastro** e entre. A lista, a busca e o detalhe funcionam só com o SQLite.

**Trocar a porta do front.** Se a 8080 estiver ocupada, suba o front em outra porta e libere a origem no backend, porque o CORS só aceita as origens da lista:

```
python3 -m http.server 5500
export CORS_ALLOWED_ORIGINS=http://127.0.0.1:5500,http://localhost:5500   # antes do runserver
```

Use o mesmo endereço no navegador e no CORS (`127.0.0.1` e `localhost` são origens diferentes). Se a API não estiver em `127.0.0.1:8000`, ajuste `API_BASE_URL` em `frontend/js/config.js`.

**Com a AWS.** Criar artigo, baixar o PDF e excluir usam o S3. Para isso, defina no `.env` as credenciais e o bucket (`AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`). Passo a passo de cada serviço em [docs/aws/](docs/aws/README.md).

**Testes**

```
cd backend
python manage.py test               # unitários, sem AWS (os de integração ficam desligados)
```

**Problemas comuns**

| Sintoma | Causa |
|---|---|
| Tela abre, mas a lista fica vazia e o console mostra erro de CORS | A origem do front não está em `CORS_ALLOWED_ORIGINS` |
| "Não foi possível conectar à API" | O backend não está no ar, ou `API_BASE_URL` aponta para outra porta |
| Login redireciona sempre para `login.html` | Sessão expirou (token vale 7 dias) ou foi gerada com outra `DJANGO_SECRET_KEY` |
| Erro ao criar artigo | O S3 não está configurado |

Detalhes em `backend/README.md` e `frontend/README.md`.

## Status

| Item | Estado |
|---|---|
| Projeto Django, models, migrations | feito |
| Settings por variável de ambiente (RDS/SQLite) | feito |
| CRUD e busca no banco (`/articles/`) | feito, com testes |
| Telas do front (HTML/Bootstrap) | feito |
| Conexão com o RDS | pendente de validar na AWS |
| Upload no S3 e URL pré-assinada | pendente |
| Log no DynamoDB | pendente |
| Cache Redis | pendente |
| SNS/SQS e worker | pendente |
| Autenticação (hoje o POST recebe o `username` no JSON) | pendente |
| JavaScript do front integrado à API | pendente |
| Parte 2 (ALB e Auto Scaling) | pendente, a pesquisar |

## Regras do time
- RDS e ElastiCache cobram por hora. Use instâncias pequenas e apague tudo após a entrega.
