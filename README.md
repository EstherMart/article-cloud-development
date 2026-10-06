# Repositório de Artigos Acadêmicos

Trabalho Prático 1 de Desenvolvimento de Software para Nuvem. Alunos e pesquisadores cadastram trabalhos acadêmicos (título, autores, resumo, palavras-chave) e enviam o PDF. A aplicação usa os 6 serviços AWS exigidos (Parte 1) e escala com ALB e Auto Scaling (Parte 2).

**Entrega:** 10/10/2026 às 23h59. Link do git e vídeo da Parte 2 funcionando.

## Papel de cada serviço

| Serviço | Papel |
|---|---|
| EC2 | Roda a API (Parte 2: dentro do Auto Scaling Group) e o worker (EC2 própria) |
| S3 | Guarda o PDF (bucket privado, download por URL pré-assinada) |
| RDS (PostgreSQL) | Metadados dos artigos |
| ElastiCache (Redis) | Cache de consultas (metadados, listas, buscas). Nunca guarda PDF |
| DynamoDB | Log das ações de CRUD (tabela `logs_crud`) |
| SNS/SQS | Desacopla a API do worker que extrai o texto e traduz o resumo |
| ALB + Auto Scaling | Parte 2: elasticidade |

## Estrutura do repositório

```
.
├── backend/    API Django (ver backend/README.md)
├── frontend/   Telas estáticas HTML/Bootstrap (ver frontend/README.md)
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
