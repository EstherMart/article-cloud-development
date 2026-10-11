# 0. Preparação: Security Groups e variáveis

[Índice](README.md) | [1. RDS PostgreSQL →](01-rds.md)

Campos que este roteiro não cita ficam no valor padrão do console.

1. Inicie o Learner Lab e abra o console da AWS.
2. Confira a região **us-east-1** (N. da Virgínia) no canto superior direito.
3. Crie os Security Groups (grupos de segurança) como descrito abaixo. Crie nesta ordem, porque `sg-rds` e `sg-redis` apontam para o `sg-api`.

## O que é um Security Group
É o firewall de cada recurso. Ele diz **quem pode conectar** (regras de entrada) e **para onde o recurso pode conectar** (regras de saída). Sem uma regra de entrada, ninguém entra. Por isso o banco só aceita a EC2, e não a internet.

Caminho: EC2 > **Grupos de segurança** > **Criar grupo de segurança**. Em todos, escolha a **VPC padrão**. Crie nesta ordem: o `sg-rds` e o `sg-redis` apontam para o `sg-api`, então ele precisa existir antes.

Legenda das colunas das regras de entrada: **Tipo** é o protocolo conhecido, **Porta** é o "número da porta" do serviço, e **Origem** é quem pode conectar.

## `sg-api` (servidor da API)

| Campo | Valor |
|---|---|
| Nome do grupo de segurança | `sg-api` |
| Descrição | `API Django` |
| VPC | a padrão (default) |

Regras de entrada (**Adicionar regra**):

| Tipo | Protocolo | Intervalo de portas | Origem | Para quê |
|---|---|---|---|---|
| SSH | TCP | 22 | **Meu IP** | Você entrar na EC2 pelo terminal |
| TCP personalizado | TCP | 8000 | **Meu IP** | Você chamar a API no navegador e no `curl` |

Regras de saída: deixe a padrão (**Todo o tráfego**, `0.0.0.0/0`). A API precisa sair para o RDS, S3, DynamoDB, SNS e Redis.

## `sg-rds` (banco)

| Campo | Valor |
|---|---|
| Nome do grupo de segurança | `sg-rds` |
| Descrição | `PostgreSQL do projeto` |
| VPC | a padrão |

Regras de entrada:

| Tipo | Protocolo | Intervalo de portas | Origem | Para quê |
|---|---|---|---|---|
| PostgreSQL | TCP | 5432 | **Personalizado**, escolha `sg-api` | Só a EC2 da API acessa o banco |
| PostgreSQL | TCP | 5432 | **Meu IP** (opcional e temporária) | Rodar o `migrate` da sua máquina |

Regras de saída: padrão.

## `sg-redis` (cache)

| Campo | Valor |
|---|---|
| Nome do grupo de segurança | `sg-redis` |
| Descrição | `ElastiCache Redis` |
| VPC | a padrão |

Regras de entrada:

| Tipo | Protocolo | Intervalo de portas | Origem | Para quê |
|---|---|---|---|---|
| TCP personalizado | TCP | 6379 | **Personalizado**, escolha `sg-api` | Só a EC2 da API acessa o cache |

Regras de saída: padrão. Não há regra para "Meu IP": o Redis só é acessível de dentro da VPC.

## `sg-worker` (crie só na [etapa 7](07-ec2-worker.md))

| Campo | Valor |
|---|---|
| Nome do grupo de segurança | `sg-worker` |
| Descrição | `Worker SQS` |
| VPC | a padrão |

Regras de entrada:

| Tipo | Protocolo | Intervalo de portas | Origem |
|---|---|---|---|
| SSH | TCP | 22 | **Meu IP** |

Depois de criar, volte em `sg-rds` e `sg-redis` e adicione uma regra extra em cada, com origem `sg-worker` (porta 5432 no RDS e 6379 no Redis).

## Mapa das relações

```
Seu IP --22, 8000--> sg-api --5432--> sg-rds
                        +-----6379--> sg-redis
Seu IP --22-------> sg-worker --5432--> sg-rds
                        +-------6379--> sg-redis
```

## Cuidados com os Security Groups
- **"Meu IP" muda** quando você troca de rede ou o provedor renova o IP. Se a conexão parar, edite a regra e escolha **Meu IP** de novo.
- **EC2 Instance Connect:** o botão **Conectar** do console usa IPs da AWS. Com a porta 22 só do seu IP, ele não conecta. Use o SSH pelo terminal com a chave `vockey`. Ou libere a 22 para `0.0.0.0/0` por pouco tempo e restrinja de novo.
- **Demonstração para outra pessoa:** se o professor precisar chamar a API, a porta 8000 precisa permitir o IP dele. Abra `0.0.0.0/0` só durante a demonstração e feche depois.
- **Nunca abra 5432 ou 6379 para `0.0.0.0/0`.** Isso expõe o banco e o cache na internet.
- **Security Groups não têm custo.** Pode deixá-los criados até terça.

## Chave do Django e variáveis fixas

4. Gere a chave: `python -c "import secrets;print(secrets.token_urlsafe(50))"`.
5. Variáveis fixas do `.env`:

```
DJANGO_SECRET_KEY=<chave gerada>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<IP público da EC2>
CORS_ALLOWED_ORIGINS=<endereço do site do front, ex.: http://<bucket-do-site>.s3-website-us-east-1.amazonaws.com>
AWS_REGION=us-east-1
```

O `DJANGO_ALLOWED_HOSTS` só dá para preencher depois de criar a EC2 ([etapa 2](02-ec2-api.md)).

### Cuidados com o `.env` (o que pode dar errado)

| Risco | O que acontece | Como evitar |
|---|---|---|
| Os scripts usam `source .env` | Senha com `$`, `#`, `!`, espaço ou aspas quebra a leitura e o valor chega cortado | Gere a senha do RDS só com letras e números, ou coloque o valor entre aspas simples |
| `S3_BUCKET`, `DYNAMODB_TABLE` ou `SNS_TOPIC_ARN` vazios | Com `DJANGO_DEBUG=False` o Django **não sobe** e diz quais faltam (`Defina no .env: ...`). Com `DEBUG=True` (uso local), usa padrões que não são seus | Preencha as três. Se o `gunicorn` não subir, veja `journalctl -u api` |
| `REDIS_URL` vazio | O código tenta `127.0.0.1:6379`. A API funciona sem cache e grava erro no log | Preencha com o endpoint do ElastiCache |
| `DJANGO_DEBUG=False` sem `DJANGO_SECRET_KEY` | O Django não sobe (`ImproperlyConfigured`) | Defina a chave primeiro |
| `DJANGO_ALLOWED_HOSTS` sem o IP certo | Erro 400 `DisallowedHost`. Com o ALB (Parte 2), o health check chega com o IP **privado** da instância e falha | Na Parte 2, use `*` ou liste o DNS do ALB e a faixa da VPC |
| Chaves `AWS_ACCESS_KEY_ID` no `.env` da EC2 | Elas sobrepõem a LabRole e vencem junto com a sessão do lab | Não coloque chaves AWS no `.env` da EC2 |
| `DJANGO_SECRET_KEY` diferente entre instâncias | O token de login de uma instância é recusado pela outra (Parte 2) | Use a mesma chave em todas as instâncias da API |
| Worker sem `GEMINI_API_KEY` e `GEMINI_MODEL` | Todo artigo termina em `ERRO` | Preencha no `.env` do worker (ver [etapa 7](07-ec2-worker.md)) |

Modelo completo de `.env`: `backend/.env.example`. Dois extras do `migrate`: `SEED_DEMO_DATA=1` (padrão) cria 12 artigos de demonstração e `DEMO_USER_PASSWORD` (opcional) deixa entrar como o usuário `demo`.

Para os testes de integração, o `.env` aceita também os nomes dos recursos (`RDS_INSTANCE_ID`, `ELASTICACHE_ID`, `FRONT_URL`, `ASG_NAME`, `ALB_NAME`): ver `backend/articles/tests/integration/README.md`.

---
[Índice](README.md) | [1. RDS PostgreSQL →](01-rds.md)
