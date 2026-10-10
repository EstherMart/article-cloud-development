# Passo a passo na AWS (Parte 1)

Roteiro para criar, testar no console e apagar cada serviço da Parte 1. A Parte 2 (ALB e Auto Scaling) fica fora deste roteiro.

Região: **us-east-1**. Role: **LabRole**. O Learner Lab não permite criar roles IAM.

Cada etapa tem o seu arquivo, com: o que é o serviço, a configuração campo a campo, como testar no console, como apagar e o estudo para a arguição.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| [00-preparacao.md](00-preparacao.md) | Security Groups, chave do Django e variáveis fixas do `.env` |
| [01-rds.md](01-rds.md) | Banco PostgreSQL |
| [02-ec2-api.md](02-ec2-api.md) | Servidor da API |
| [03-s3.md](03-s3.md) | Armazenamento dos PDFs |
| [04-dynamodb.md](04-dynamodb.md) | Log das ações |
| [05-elasticache.md](05-elasticache.md) | Cache Redis |
| [06-sns-sqs.md](06-sns-sqs.md) | Mensageria e DLQ |
| [07-ec2-worker.md](07-ec2-worker.md) | Servidor do worker |
| [08-ponta-a-ponta-e-custos.md](08-ponta-a-ponta-e-custos.md) | Teste do fluxo completo e conferência final de custos |
| [09-estudo-geral.md](09-estudo-geral.md) | Visão geral, boto3 e perguntas para a arguição |

## Ordem de implementação

A ordem abaixo segue o fluxo do cadastro. Cada etapa depende da anterior e termina com algo testável.

| # | Etapa | Serviço | Variável do `.env` | Cobra por hora? | Fase |
|---|---|---|---|---|---|
| [0](00-preparacao.md) | Preparação | Security Groups | (nenhuma) | Não | - |
| [1](01-rds.md) | Banco | RDS PostgreSQL | `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT` | Sim | A |
| [2](02-ec2-api.md) | Servidor da API | EC2 | (roda o código) | Sim | A |
| [3](03-s3.md) | PDF | S3 | `S3_BUCKET` | Não | B |
| [4](04-dynamodb.md) | Log | DynamoDB | `DYNAMODB_TABLE` | Não (on-demand) | B |
| [5](05-elasticache.md) | Cache | ElastiCache Redis | `REDIS_URL` | Sim | C |
| [6](06-sns-sqs.md) | Mensageria | SNS e SQS | `SNS_TOPIC_ARN`, `SQS_QUEUE_URL` | Não | D |
| [7](07-ec2-worker.md) | Processamento | EC2 do worker | (roda o worker) | Sim | D |

O que cada fase entrega:
- **A (etapas 1 e 2):** CRUD funcionando na nuvem. Requisitos 1 e 2 da spec.
- **B (etapas 3 e 4):** cadastro com PDF e log. Requisitos 3 e 5.
- **C (etapa 5):** leituras com cache. Requisito 4.
- **D (etapas 6 e 7):** processamento assíncrono. Requisito 6.

Por que essa ordem:
- O RDS é a base de tudo, porque o id do artigo nasce nele.
- A EC2 é onde o código roda.
- O S3 e o DynamoDB entram no cadastro logo depois.
- O Redis só otimiza leituras que já funcionam.
- A mensageria e o worker usam todos os anteriores, por isso vêm por último.

Custo: RDS, ElastiCache e EC2 cobram por hora. S3, DynamoDB, SNS e SQS não têm custo fixo. Faça uma fase por sessão. Apague RDS, ElastiCache e EC2 ao terminar o dia.

## Plano de custo até a arguição (dia 13)

Regra: o que cobra por hora liga só durante o teste e apaga no mesmo dia. O que custa centavos fica criado.

| Grupo | Serviços | O que fazer |
|---|---|---|
| Fica criado | S3, DynamoDB (on-demand), SNS, SQS e DLQ | Crie uma vez. Parados, custam praticamente zero. Esvazie o bucket de PDFs de teste grandes |
| Liga, testa e apaga no mesmo dia | RDS, EC2 (API e worker), ElastiCache | Crie na sessão do teste. Apague ao terminar |

Valores aproximados, só para dar ordem de grandeza (confira o gasto real no painel do Learner Lab):

| Recurso | Por hora | Se ficasse 4 dias ligado |
|---|---|---|
| RDS `db.t3.micro` + 20 GB | ~US$ 0,02 | ~US$ 2 |
| ElastiCache `cache.t3.micro` | ~US$ 0,02 | ~US$ 2 |
| EC2 `t3.micro` (cada uma) | ~US$ 0,01 | ~US$ 1 |
| S3, DynamoDB, SNS, SQS | centavos | quase zero |

Cronograma sugerido:

| Quando | O que fazer |
|---|---|
| Sex 09 e sáb 10 | Crie S3, DynamoDB, SNS, SQS e DLQ (etapas 3, 4 e 6). Teste cada um pelo console. Anote nomes e ARNs no `.env` local, fora do git |
| Dom 11 | Ensaio completo: crie RDS, EC2 e ElastiCache (etapas 1, 2, 5 e 7), rode o teste de ponta a ponta e **apague os três ao terminar** |
| Seg 12 | Ensaio final, com vídeo ou prints de cada serviço funcionando (plano B). Apague tudo o que cobra por hora |
| Ter 13 | Manhã: confirme que S3, DynamoDB, SNS e SQS continuam lá. Recrie RDS, EC2 e ElastiCache (RDS leva de 5 a 10 minutos) e suba a API e o worker antes da arguição |
| Ter 13, depois | Apague tudo (ver "Conferência final de custos") |

Cuidados:
- **RDS parado em vez de apagado:** o Stop do RDS não cobra a instância, só o armazenamento. A AWS religa o RDS sozinha após 7 dias. O ElastiCache não tem Stop: apague.
- **Worker rodando:** ele consulta a fila sem parar e fica numa EC2 que cobra. Encerre quando terminar o teste.
- **DynamoDB:** mantenha o modo **on-demand**. O modo provisionado cobra por hora mesmo parado.
- **Reset do Learner Lab:** se o lab reiniciar ou o orçamento acabar, a AWS pode apagar os recursos. Por isso você anota nomes e ARNs, para recriar rápido.
- **Credenciais expiram** a cada sessão. Os recursos continuam, mas o CLI local precisa das credenciais novas.
- **IP público da EC2 muda** quando ela para e volta. Atualize `DJANGO_ALLOWED_HOSTS` e o endereço que você abre no navegador.
- **Antes de fechar cada sessão:** confira as telas de EC2, RDS e ElastiCache e olhe o valor gasto no painel do lab.
