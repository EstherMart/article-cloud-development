# Análise do projeto frente à especificação

Base: *Especificação do Trabalho Prático 1* (Desenvolvimento de Software para Nuvem), tema "Repositório de artigos científicos". Prazo da spec: 10/10/2026. **O grupo informou que foi adiado para 12/10/2026.** A arguição é na terça, 13/10.
Escopo: a `main` local (que inclui a `funcoes-worker`) comparada com `origin/main` (`000391e`) e `origin/backend-AWS` (seção 1).
Atualizada em 11/10/2026, depois de mesclar a `funcoes-worker` na `main` local e corrigir os itens 1 a 11 da seção 3.1. Os 29 testes unitários passam (6 de integração pulados). As alterações estão no working tree, sem commit e sem push.

## 0. Resumo

- **A `main` local agora carrega e os testes passam** (29 unitários, 6 de integração pulados). O import quebrado veio com o merge da `funcoes-worker`; o `presigned_url` e os testes foram corrigidos à mão.
- **Implementado, mas nunca rodado na AWS:** S3, Redis, DynamoDB, SNS e worker, front e autenticação.
- **Corrigidos hoje (3.1 itens 1 a 11):** download do PDF, testes, `error` e `read_json` duplicados, log de READ, variáveis de ambiente, validação do PDF, erros sem vazar exceção, ordem do DELETE e limpeza do upload órfão.
- **Também corrigidos:** `/health/`, `download_url` e `ALLOWED_HOSTS` (itens 12, 13 e 15). A paginação ficou fora (item 14).
- **Também feitos:** limpeza de estilo (item 16), `gunicorn` e `GEMINI_*`.
- **Falha do SNS resolvida:** rota de reprocessamento `POST /articles/<id>/reprocess/`; falta só o botão no front.
- **Nada aberto no código da 3.1**, além dos itens opcionais 17, 18 e 22.
- **Falta a Parte 2 inteira** (ALB, Auto Scaling, vídeo) e criar e validar todos os recursos na AWS.
- **Git:** a `main` local está 1 commit à frente da `origin/main` (o da `funcoes-worker`), mais as alterações sem commit.

## 1. Branches remotas e `main`

| Branch remota | Situação | Ação |
|---|---|---|
| `origin/main` (`000391e`) | Tem front, `accounts`, S3, DynamoDB e Redis, mas **não importa** (`from services...`) | Atualizar com o push da `main` local |
| `origin/funcoes-worker` (`2f77982`) | **Mesclada na `main` local** (fast-forward). Traz o worker completo, a publicação no SNS no POST e o import corrigido | Fazer push da `main` e apagar a branch |
| `origin/backend-AWS` (`607930a`) | Mesmo conteúdo do commit `000391e` (cache), com outro hash. O merge dá conflito em `views.py` e não acrescenta nada | Apagar sem mesclar |

As branches `backend`, `backend-S3`, `django_init` e `telas` já foram apagadas do remoto. O front, o `accounts` e o CORS já estão commitados na `main`.

## 2. Estado por requisito da especificação

Legenda: ✅ pronto · 🟡 parcial · ❌ não existe.

| # | Requisito | Estado | O que falta |
|---|---|---|---|
| 1 | Interface Web ou API REST na **EC2** | 🟡 API, autenticação, CORS, `/health/` e `gunicorn` prontos; o app carrega e os testes passam. Front decidido (S3 estático). Nada rodou na EC2 | Criar a EC2 com `systemd`, `DJANGO_ALLOWED_HOSTS`, publicar o front (`infra/publicar_front.sh`) |
| 2 | Dados no **RDS** | 🟡 Código pronto (PostgreSQL por `DB_*`, 4 migrations). Nunca validado na AWS | Criar o RDS, `migrate`, `test_rds.py` |
| 3 | PDF no **S3** | 🟡 `services/s3.py` implementado e usado pela view; `presigned_url` corrigido; PDF validado (tipo e 10 MB). Nunca testado na AWS | Criar o bucket, testar |
| 4 | **ElastiCache** (Redis) como cache | 🟡 `cache.py` implementado (`get_or_set`, `invalidate_article`), usado em lista, detalhe e busca, invalidado em POST, PUT e DELETE. O worker também invalida. Nenhum cluster criado | Criar o cluster, `REDIS_URL`, `test_redis.py`, testar `ping` da EC2 |
| 5 | CRUD logado no **DynamoDB** (ação, dados, hora) | 🟡 `dynamo_log.log_action`, chamado em CREATE, UPDATE e DELETE (READ saiu, 3.1 item 5). Falha de log é registrada e ignorada. Tabela `logs_crud` não criada | Criar a tabela, testar |
| 6 | Processamento **desacoplado por SNS/SQS** | 🟡 Na `main` local: API publica no SNS; worker faz long polling, baixa o PDF do S3, extrai texto, traduz com Gemini, grava no RDS e invalida o Redis. Nada rodou. Tópico, fila, DLQ e EC2 do worker não existem | Criar a infra, decidir Gemini ou Amazon Translate (3.3), testar ponta a ponta |
| 7 | **Interface gráfica** (−1,0 se faltar) | ✅ 8 telas com JS ligado à API. Fluxo completo no navegador depende do S3 e de a API subir | Testar no navegador contra o backend |
| P2 | **ALB + Auto Scaling** (1 a 3 instâncias, CPU >70% sobe, <25% desce) | ❌ `infra/README.md` é só uma lista de tarefas | Launch template, target group com health check, ASG, duas políticas de CPU, vídeo |
| E | **Entrega:** link do git e **vídeo da Parte 2** | ❌ | Gravar o vídeo mostrando a escala subindo e descendo |

Penalidade de cada serviço ausente: −1,5 ponto. Em código, só **Auto Scaling** está zerado (−1,5). Os outros cinco serviços (RDS, S3, ElastiCache, DynamoDB, SNS/SQS) têm código, mas **só contam se rodarem na AWS**; hoje nenhum rodou.

## 3. Pontos de código que PRECISAM melhorar

### 3.1 Na `main`

**Resolvidos**

| # | Antes | Agora |
|---|---|---|
| — | `views.py` ignorava `services/` e criava o boto3 em 3 lugares | ✅ A view chama `upload_pdf`, `delete_pdf` e `presigned_url` |
| — | Credenciais explícitas no boto3 (quebrava a IAM Role) | ✅ Usa `services/aws.py`; `AWS_ACCESS_KEY_ID` e afins saíram do `settings.py` |
| — | Chave `artigos/{id}-{nome}`; sem `ContentType` | ✅ `artigos/{id}.pdf` com `application/pdf` |
| — | Cache e DynamoDB eram stubs | ✅ Implementados |
| 1 | `generate_pressigned_url` e `'get-object'` | ✅ Corrigidos em `services/s3.py` |
| 2 | Import `from services...` | ✅ `from .services...` (veio com a `funcoes-worker`) |
| 3 | 33 testes falhavam | ✅ `tests/unit/base.py` simula os clientes S3 e SNS, o log, o cache e a invalidação. 74 passam |
| 4 | `error` e `read_json` duplicados em `views.py` | ✅ Cópia removida; a view importa de `article_cloud/http.py` |
| 5 | Log READ síncrono em todo GET | ✅ Só escrita é logada (CREATE, UPDATE, DELETE). **A spec diz "toda ação do CRUD": explicar na arguição** |
| 6 | Variáveis divergentes | ✅ `S3_BUCKET`, `DYNAMODB_TABLE` (padrão `logs_crud`) e `AWS_REGION`, como no `.env.example` |
| 7 | PDF sem validação | ✅ 415 se não for `application/pdf`, 413 acima de 10 MB. O `Content-Type` vem do cliente |
| 8 e 9 | `str(e)` vazado; `except Exception` | ✅ `ClientError` e `BotoCoreError` viram 502 com mensagem fixa e `logger.exception` |
| 12 | Sem `/health/` | ✅ `GET /health/` responde 200 sem tocar em banco, Redis ou AWS (não detecta RDS fora do ar, de propósito: o ASG não recria instâncias em loop). O health check chega com o IP da instância: ele precisa estar em `DJANGO_ALLOWED_HOSTS` |
| 13 | `'download URL'` | ✅ `download_url` na API e no front |
| 15 | `ALLOWED_HOSTS` | ✅ Já lido de `DJANGO_ALLOWED_HOSTS`; `.env.example` documenta o uso na EC2/ALB. `DEBUG=True` por padrão só vale localmente; com `DJANGO_DEBUG=False` a chave secreta é obrigatória |
| 10 e 11 | DELETE apagava o PDF antes; upload órfão no POST | ✅ DELETE apaga o registro e depois o PDF (falha só loga); POST apaga o PDF se o banco falhar |

**Abertos**

| # | Problema | Local | Correção |
|---|---|---|---|
| 14 | **Decidido deixar fora:** sem paginação em `GET /articles/`; "Meus artigos" filtra no front. O cache guarda a lista inteira numa chave só | `ArticleView.get` | Registrar como limitação conhecida |
| 16 | ✅ Estilo limpo em `views.py`, `cache.py`, `s3.py`, `dynamo_log.py`, `settings.py` (espaços, imports, newline final). Docstring do `dynamo_log.py` atualizada | — | — |
| 17 | `get_or_set` cacheia `None` (artigo inexistente) como `"null"`: vira cache miss a cada GET de id errado | `cache.py` | Opcional |
| 23 | ✅ O cliente Redis agora tem `socket_connect_timeout` e `socket_timeout` de 2 s. Antes, um endpoint errado travava cada requisição pelo timeout padrão do sistema | `cache.py` | — |
| 18 | `invalidate_article` apaga `busca:*` com `scan_iter`; o custo cresce com o número de buscas | `cache.py` | Anotar para a arguição |
| 22 | O POST não valida a assinatura `%PDF` do arquivo, só o `Content-Type` | `ArticleView.post` | Opcional |

**Introduzidos pela autenticação** (sem mudança desde a análise anterior)

| # | Ponto | Observação |
|---|---|---|
| 19 | Todas as instâncias do Auto Scaling precisam da **mesma `DJANGO_SECRET_KEY`**, senão o token de uma instância é recusado por outra | Colocar a chave no user data ou launch template |
| 20 | O token não pode ser revogado antes dos 7 dias e o login não tem limite de tentativas | Anotar para a arguição |
| 21 | O mesmo `User` do Django guarda login e dono do artigo; `CASCADE` apaga os artigos com o usuário | Já documentado no README da raiz |

### 3.2 Worker e SNS (já na `main` local)

| # | Problema | Correção |
|---|---|---|
| 1 | ✅ Resolvido: os testes simulam o SNS e o S3 em `tests/unit/base.py` | — |
| 2 | ✅ Resolvido: a resposta 503 do POST traz `article_id` e a rota `POST /articles/<id>/reprocess/` (só o dono, só status `ERRO`) republica o evento no SNS. **Falta o botão no front** (opcional) | — |
| 3 | ✅ Resolvido: `GEMINI_API_KEY` e `GEMINI_MODEL` estão no `.env.example` e a tradução ficou com o Gemini (3.3) | — |
| 4 | **O worker acessa o RDS por SQL direto** (`UPDATE articles_article`), não pelo Django. Se o modelo mudar de nome de tabela ou coluna, quebra sem aviso | Anotar como decisão. O teste `test_pipeline_e2e.py` cobre |
| 5 | **Uma instância só do worker e uma mensagem por vez** (`MaxNumberOfMessages=1`). Suficiente para o trabalho | Anotar |
| 6 | **`SQS_DLQ_URL` e redrive** não aparecem no código. A DLQ vem da configuração da fila | Configurar `maxReceiveCount` na fila (ver `docs/aws/06-sns-sqs.md`) |
| 7 | O `README.md` do worker ainda traz instruções de tarefa | Limpar (seção 9) |
| 8 | O worker invalida o cache **depois** de gravar. Entre o `save_result` e o `delete`, um GET pode servir o artigo antigo por até 300 s | Aceitável (TTL). Anotar |

### 3.3 Tradução: Gemini (decidido)

O worker usa Gemini (`google-genai`). Precisa de `GEMINI_API_KEY` e `GEMINI_MODEL` no `.env` do worker, de saída HTTPS pela internet e de cota na chave. A chave nunca vai para o git. Na arguição: o serviço de tradução não é da AWS; o requisito de desacoplamento (SNS/SQS) continua cumprido.

### 3.4 Roteiro `docs/aws/` revisado contra o código final

Revisado em 11/10 contra a `main` local. Armadilhas encontradas e corrigidas nos arquivos:

| Onde | Problema | Correção |
|---|---|---|
| `04-dynamodb.md` | Chave `article_id` como **Número**. O código grava texto: toda gravação falharia e o erro seria engolido (sem log, sem aviso) | Tipo **String**, com aviso e passo de conferir o item |
| `02-ec2-api.md` | `runserver` e API morrendo com o SSH | `gunicorn` e unidade `systemd`; nota do front e CORS |
| `00-preparacao.md` | Sem lista de riscos do `.env` | Tabela: senha com caractere especial, `S3_BUCKET` vazio, `ALLOWED_HOSTS` com o ALB, `SECRET_KEY` igual nas instâncias |
| `03-s3.md` | Instruções de "implementar", limite de 20 MB | Descreve o código atual (10 MB, 415, 413, 502) e os sintomas de erro |
| `05-elasticache.md` | Sem diagnóstico de cache lento | Tabela de sintomas; timeouts de 2 s no código |
| `06-sns-sqs.md` | Formato sem `event`; falha do SNS sem tratamento | Formato atual, 503 com `article_id`, rota `reprocess` |
| `07-ec2-worker.md` | Citava Translate; faltava Gemini, internet, `systemd` | Gemini, variáveis, tabela de erros |
| `08` e `09` | Teste sem UPDATE, download e reprocesso; Translate | Teste completo de 11 passos; Gemini |
| `01-rds.md` | Criar usuário pelo shell | Usa `/auth/register/` |

Riscos que ficam e não têm correção de código:

- **Falha de log do DynamoDB é silenciosa**, por decisão. Só aparece em `journalctl`.
- ✅ **Variável esquecida agora derruba a subida:** com `DJANGO_DEBUG=False`, o Django exige `S3_BUCKET`, `DYNAMODB_TABLE` e `SNS_TOPIC_ARN`. Com `DEBUG=True` seguem os padrões locais.
- **Credenciais do Learner Lab expiram**: URL assinada e o CLI deixam de funcionar.
- **O Redis fora do ar custa ~2 s por requisição** até o cache voltar.
- **O front depende de CORS e do DNS do ALB:** se o ALB for recriado, o endereço muda e é preciso publicar o front de novo (`infra/publicar_front.sh`).
- **O Learner Lab pode bloquear bucket público:** se não deixar desmarcar o Block Public Access, o plano B é nginx na EC2.

### 3.5 Testes: o que saiu dos unitários e o que mudou na integração

**Unitários: de 81 para 29.** Ficaram só os imprescindíveis; o resto repetia o óbvio, o que o Django já garante ou o que um teste de integração cobre melhor.

| Área | Ficaram | Saíram (exemplos) |
|---|---|---|
| Cadastro (`POST /articles/`) | 10: artigo `PENDENTE`, 401 sem token, dono vem do token, campos obrigatórios, envio ao S3, evento no SNS, falha do SNS (503 com `article_id`, status `ERRO`), título duplicado (409), não-PDF (415), falha do S3 (502 sem vazar detalhe) | autores/tags em formato errado, nomes repetidos, tag reaproveitada, autor órfão, PDF acima do limite |
| Reprocessamento | 3: reenvia e volta a `PENDENTE`, recusa se não está em `ERRO` (409), 403 de outro usuário | falha de novo, 401 |
| Leitura e busca | 3: detalhe inexistente (404, passa pelo cache), busca não duplica, `/articles/search/` não é lida como id | lista, detalhe, busca por título, autor, área e tag, número de consultas |
| Atualizar e apagar | 6: atualiza, 409 e 403 no PUT; apaga o registro, apaga o PDF e 403 no DELETE | campos ausentes, JSON inválido, tags mantidas, 401 |
| Cliente AWS | 1: Signature v4 (sem ela a URL assinada falha) | região, timeouts, cache do cliente |
| Contas | 6: cria usuário, usuário repetido (409), login devolve token, senha errada (401), token adulterado, `/health/` | campo ausente, e-mail e senha fracos, mensagem de erro, usuário apagado |
| Modelo | 0 | cascata e unicidade (cobertas pelos testes de API e pelo RDS real) |

Cobertura que sai com isso: validação de campos, nomes repetidos, N+1 e `CASCADE` deixam de ter teste automático. Aceito de propósito.

**Integração (AWS real): reescrita para o código final.** Os testes antigos passariam com a configuração errada:

| Arquivo | O que estava infiel | Agora |
|---|---|---|
| `test_pipeline_e2e.py` | Enviava o campo `user` e `authors` como texto, sem token (hoje dá 401 ou 400); conferia o DynamoDB com `scan` (lê só o primeiro MB) | Login e token, autores em JSON, `query` por artigo; cobre CREATE, UPDATE (com cache invalidado), download, 415 e DELETE; exige a tradução preenchida e para com mensagem clara se o worker marcar `ERRO` |
| `test_dynamodb.py` | Aceitava chave Número ou String e exigia que o serviço convertesse `float` (o código não converte) | Exige `article_id` String e `timestamp` String; usa o formato real do artigo; prova que falha de log não levanta exceção |
| `test_redis.py` | O teste de Redis fora do ar usava um cliente próprio, sem os timeouts do código | Usa `get_client` de verdade contra um endereço inalcançável e exige resposta em poucos segundos |
| `test_sns_sqs.py` | Não conferia o campo `event` nem o `bucket` | Confere os 4 campos da mensagem |
| `test_rds.py` | Não conferia a restrição que gera o 409 | Confere o índice único em `articles_article.title` |

Nenhum teste de integração foi executado na AWS. Localmente eles são pulados (`skipped=6`) e compilam.

## 4. Código que PRECISA ser entregue (e o que já testa na AWS)

### 4.1 Código a entregar

| Prioridade | Entrega | Arquivo | Estado |
|---|---|---|---|
| 1 | User data da EC2 (`gunicorn` já está no `requirements.txt`) | `infra/` | não existe |
| 2 | Botão "Reprocessar" no front para artigos em `ERRO` (opcional) | `frontend/` | aberto |
| 3 | `GEMINI_*` no `.env.example` feito; Gemini decidido (3.3) | `worker/` | ✅ feito |
| 4 | ALB, Launch Template, ASG, políticas de CPU, vídeo | `infra/` | não existe |
| 5 | Limpeza de estilo (3.1 item 16) | vários | ✅ feito |
| 6 | Paginação e filtro `?user=` | `views.py`, `meus_artigos.js` | opcional |
| ✅ | Front, auth, CORS, Redis, DynamoDB, S3, SNS, worker e os itens 1 a 11 da 3.1 | vários | na `main` local, sem push |

### 4.2 O que já pode ser testado na AWS hoje

| Integração | Testável hoje? | Como |
|---|---|---|
| **RDS** | **Sim.** Código e teste prontos | Criar o RDS, `DB_*` no `.env`, `RUN_AWS_INTEGRATION=1 python manage.py test articles.tests.integration.test_rds` |
| **S3** | **Sim.** Upload, download e delete prontos | Criar o bucket, `S3_BUCKET`, rodar `test_s3.py` e testar pelo front |
| **DynamoDB** | **Sim.** `services/dynamo_log.py` está implementado | Criar a tabela `logs_crud` (partição `article_id`, ordenação `timestamp`), rodar `test_dynamodb.py`, criar um artigo e olhar a tabela |
| **ElastiCache** | **Sim, depois de criar o cluster.** `cache.py` está pronto | `REDIS_URL`, `ping` da EC2, `test_redis.py` |
| **SNS/SQS** | **Sim.** Criar tópico, fila e DLQ | `SNS_TOPIC_ARN`, `SQS_QUEUE_URL`, `test_sns_sqs.py` |
| Ponta a ponta | Depende de tudo acima | `test_pipeline_e2e.py` |
| ALB + ASG | Não testável sem a API estável na EC2 | Depende de `/health/`, do `gunicorn` e da mesma `DJANGO_SECRET_KEY` |

## 5. O que falta por parte

### 5.1 Frontend (spec: interface gráfica, −1,0 se faltar)

| Item | Estado | O que falta |
|---|---|---|
| Telas | ✅ `index`, `login`, `cadastro`, `artigos`, `artigo`, `meus_artigos`, `criar_artigo`, `editar_artigo` | — |
| JavaScript e API | ✅ `api.js` com token e erro da API; um script por tela | — |
| Formulário de artigo | ✅ Chips para autores e palavras-chave, área, resumo e PDF | — |
| Status e tradução | ✅ Badge de status e tradução no detalhe, sem polling | Opcional: polling na demo do worker |
| Teste | 🟡 Testado com API simulada | Testar criar, editar e excluir no navegador contra o back com S3 |
| Hospedagem do front | 🟡 Decidido: bucket S3 de site estático (`docs/aws/03b-front-s3.md`). Script `infra/publicar_front.sh` pronto; nada criado na AWS | Criar o bucket, publicar com o DNS do ALB, `CORS_ALLOWED_ORIGINS` na API |
| "Meus artigos" | 🟡 Filtra no cliente | Filtro `?user=` no back (3.1 item 14) |

### 5.2 Backend (API + worker)

| Item | Estado |
|---|---|
| CRUD, busca, RDS, modelos, migrations | ✅ |
| Autenticação por token e CORS | ✅ |
| S3 (upload, download, delete, validação) | 🟡 pronto, sem validação na AWS |
| DynamoDB (CREATE, UPDATE, DELETE) | 🟡 pronto, sem validação na AWS |
| Redis | 🟡 pronto, sem validação na AWS |
| SNS e worker | 🟡 pronto, sem validação na AWS; reprocessamento por rota |
| Testes unitários | ✅ 29 passam |
| `/health/` | ✅ |
| `gunicorn`, paginação | ❌ |

### 5.3 Integração e infraestrutura

| Item | Estado |
|---|---|
| Front ↔ API (URL base, CORS, token, FormData) | 🟡 funciona localmente; falta testar com S3 e na EC2 |
| Nenhum recurso AWS validado (RDS, bucket, tabela, cluster, tópico, fila, EC2) | ❌ |
| API ↔ Redis, SNS | 🟡 código escrito, não executado |
| SQS → worker → RDS e Redis | 🟡 código escrito, não executado |
| EC2 da API e EC2 do worker | ❌ |
| ALB, ASG, políticas de 70% e 25% | ❌ |
| Vídeo da Parte 2 | ❌ |
| Testes de integração escritos (6 arquivos) | ✅ escritos; agora todos têm implementação para chamar |

## 6. Porcentagem de conclusão

Critério: peso igual por item dentro de cada etapa. "Pronto" = código escrito e coberto por teste local que passa. Nada vale como integrado sem rodar na AWS.

| Etapa | Cálculo | Análise de 10/10 | Hoje |
|---|---|---|---|
| **Backend** (RDS 100 · API e autenticação 100 · S3 85 · Redis 80 · DynamoDB 80 · SNS e worker 75; testes 100% verdes) | média de 6 | ~46% | **~87%** |
| **Frontend** (layout 95 · JS e fluxos 85 · validado no navegador com S3 pendente) | média | ~85% | **~85%** |
| **Integração e infra** (nenhum recurso AWS validado; Parte 2 zerada; `/health/` e `gunicorn` faltam) | | ~15% | **~15%** |
| **Projeto no total** | média das três | ~49% | **~62%** |

O total engana: o que falta é quase todo ligado à AWS (criar e validar os serviços, ALB, Auto Scaling, vídeo) e vale mais pontos na spec do que o código. O código está bem mais adiantado que a infra: **o maior risco é não ter nenhum serviço validado na AWS**. Em penalidade, só o **Auto Scaling** está zerado; os outros cinco dependem de rodar.

A documentação em `docs/aws/` cobre o passo a passo de todos os serviços. Ela não entra na conta porque a spec avalia a aplicação rodando.

## 7. Decisões

**Fechadas**

| Decisão | Resultado |
|---|---|
| Prazo | Adiado para 12/10 |
| Autenticação | Completa, com senha e token |
| Criar artigo | Chips de autores e tags, PDF, área e resumo; campo `conteudo` removido |
| Detalhe do artigo | Página completa com download |
| Erros no front | Alerta Bootstrap com a mensagem da API |
| Front | Bucket S3 separado, site estático público (só telas; PDFs seguem em bucket privado). Publicado por `infra/publicar_front.sh`; CORS na API |
| Tradução | Gemini (API externa; chave só no `.env` do worker) |
| Variáveis obrigatórias | Em produção, `S3_BUCKET`, `DYNAMODB_TABLE` e `SNS_TOPIC_ARN` faltando impedem a subida |
| Falha de log do DynamoDB | Continua silenciosa (decidido); conferida no ensaio de ponta a ponta |
| Redis fora do ar | Aceito: API fica ~2 s mais lenta por requisição até o Redis voltar |
| Falha do SNS | Artigo fica em `ERRO`; o dono reenvia por `POST /articles/<id>/reprocess/` |
| Log no DynamoDB | `services/dynamo_log.py`, tabela única `logs_crud`, falha de log não derruba o CRUD. **Só escrita é logada** (leitura fora, para o cache valer) |
| Cache | Redis, TTL de 300 s, invalidação em POST, PUT, DELETE e no worker |
| Validação do PDF | `Content-Type` e 10 MB, sem validar a assinatura |
| Erros da AWS | 502 com mensagem fixa; detalhe só no log |
| Variáveis | `S3_BUCKET`, `DYNAMODB_TABLE`, `AWS_REGION` |

**Abertas**

1. **Fora do escopo (decidido):** paginação e filtro `?user=`.

## 8. Ordem sugerida até o prazo (12/10)

1. Commitar as alterações, fazer push da `main` e apagar as branches `funcoes-worker` e `backend-AWS`.
2. ✅ Itens pequenos fechados: `gunicorn` no `requirements.txt`, `GEMINI_*` no `.env.example`, limpeza de estilo.
3. ✅ Falha do SNS resolvida (rota de reprocessamento).
4. Criar RDS, bucket, tabela do DynamoDB e cluster Redis. Subir a API numa EC2. Testar o fluxo no front.
5. Criar tópico, fila e DLQ. Subir a EC2 do worker. Teste ponta a ponta (`test_pipeline_e2e.py`).
6. Parte 2: launch template, ALB, ASG, políticas de 70% e 25%. Teste de carga e vídeo.
7. Limpar os READMEs (seção 9) e entregar.

## 9. O que remover dos READMEs

Regra: README é conhecimento público (o que é, como rodar, como usar). Conhecimento da equipe (status, pendências, decisões, branches, custos, "como implementar") sai. **`docs/aws/` fica inteira**, por ser o passo a passo das etapas ainda por fazer.

| Arquivo | Remover | Manter |
|---|---|---|
| `README.md` (raiz) | Linha vazia `**Equipe:**` (preencher ou apagar). Parágrafo sobre "Parte 1 / Parte 2 da spec". Seção **Status** (desatualizada: ainda diz que Redis, SNS e worker não existem). Seção **Pontos em aberto**. Seção **Regras do time**. Seção **Decisões técnicas** (custos, Learner Lab, LabRole). Nota "simplifica o laboratório" no modelo de dados. Coluna "Exigência da spec". **Índice da documentação**. Diagramas de sequência e de estados | O que é, como funciona (resumido), tabela de serviços, diagrama de componentes, modelo de dados (ER), estrutura do repositório (falta `accounts/`), como rodar |
| `backend/README.md` | Tabela de **Migrations**. "Crescimento previsto". "Ao implementar um serviço, escreva primeiro o teste…". Descrição dos arquivos de teste um a um | Estrutura, rotas, erros, modelo de dados, como rodar testes, variáveis de ambiente (`CORS_ALLOWED_ORIGINS`, `REDIS_URL`, `SNS_TOPIC_ARN`) |
| `backend/articles/services/README.md` | **Apagar o arquivo.** Só tem branches, estado de esqueleto e regras para quem implementa | |
| `worker/README.md` | Texto de tarefa e estado de implementação | O que faz, decisão de ser independente do Django (uma linha), variáveis, como rodar |
| `worker/README_INTEGRACAO_FUNCOES.md` | **Apagar o arquivo.** É lista de pendências da equipe; o conteúdo útil (variáveis e permissões) vai para o `worker/README.md` | |
| `infra/README.md` | **Apagar o arquivo** (lista de tarefas "a pesquisar"). Recriar quando a Parte 2 existir | |
| `backend/articles/tests/integration/README.md` | Seção **Estado**. Regra 4 (custos). Regra 6. Nota "dependem de services implementado" | Como rodar, variáveis por arquivo |
| `backend/articles/tests/fixtures/README.md` | "depois que o POST aceitar PDF", "ainda será definido", e o exemplo `curl` sem token | Tabela de PDFs e como regerar |
| `docs/aws/*` | **Nada.** | Tudo |

Fora dos READMEs:

- **Docstrings "Como fazer:"** que sobraram em `services/*.py` (`messaging.py` e o cabeçalho de `cache.py`, `dynamo_log.py`, `s3.py`) e em `worker.py`: viram comentário normal agora que o código existe.
- **Branches remotas** `funcoes-worker` e `backend-AWS` (seção 1).
