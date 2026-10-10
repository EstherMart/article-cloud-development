# Análise do projeto frente à especificação

Base: *Especificação do Trabalho Prático 1* (Desenvolvimento de Software para Nuvem). Prazo da spec: 10/10/2026. **O grupo informou que foi adiado para 12/10/2026.** A arguição é na terça, 13/10.
Escopo: `main` (commit `75ebb7c`) mais as alterações locais ainda não commitadas (front, autenticação, CORS, testes) e o conteúdo remoto não mesclado (seção 1).
Atualizada em 10/10/2026, depois de implementar o front e a autenticação.

## 1. O que existe fora da `main`

| Branch remota | Situação | Ação |
|---|---|---|
| `origin/backend-AWS` | **Única com trabalho novo.** Log no DynamoDB (`log_dynamoDB`) em CREATE, UPDATE, DELETE e em todos os erros, com tabela de erros separada. Foi escrita antes das alterações de hoje em `views.py`, então vai dar conflito ao mesclar | Mesclar depois de corrigir a seção 3.2 |
| `origin/backend-S3` | Mesma mudança de S3 que a `main` já contém (`fe09aac`) | Apagar |
| `origin/django_init` | Histórico antigo, já incorporado. Só traz `guia_p_testar.txt` (POST antigo em JSON, obsoleto) | Apagar |
| `origin/telas` | Telas HTML/CSS antigas, já incorporadas e substituídas | Apagar |
| `origin/backend` | Commit inicial do Django, já incorporado | Apagar |

**Alterações locais ainda sem commit:** front inteiro (`frontend/`), app `accounts` (cadastro, login, token), `article_cloud/http.py`, CORS, testes unitários reescritos, READMEs e esta análise. Quem mesclar `backend-AWS` precisa resolver o conflito em `views.py`.

## 2. Estado por requisito da especificação

Legenda: ✅ pronto · 🟡 parcial · ❌ não existe.

| # | Requisito | Estado | O que falta |
|---|---|---|---|
| 1 | Interface Web ou API REST na **EC2** | 🟡 API, autenticação, CORS e telas prontas e funcionando localmente. Nada rodou na EC2 | Criar a EC2; `gunicorn` (não está no `requirements.txt`); `DJANGO_ALLOWED_HOSTS`; `/health/`; servir o front (S3 ou nginx) |
| 2 | Dados no **RDS** | 🟡 Código pronto (PostgreSQL por `DB_*`, 4 migrations). Nunca validado na AWS | Criar o RDS, rodar `migrate`, rodar `test_rds.py` |
| 3 | PDF no **S3** | 🟡 Upload, delete e URL pré-assinada em `views.py`, com testes unitários usando S3 simulado. Nunca testados na AWS | Criar o bucket, corrigir variáveis e credenciais (3.1), testar |
| 4 | **ElastiCache** (Redis) como cache | ❌ `cache.py` é só stub. Nenhuma view usa cache | Implementar `get_or_set` e `invalidate_article`, usar em GET lista, detalhe e busca, invalidar em POST, PUT e DELETE. Criar o cluster |
| 5 | CRUD logado no **DynamoDB** (ação, dados, hora) | 🟡 Só na branch `backend-AWS`. `dynamo_log.py` da `main` é stub | Mesclar a branch, criar as tabelas, corrigir 3.2 |
| 6 | Processamento **desacoplado por SNS/SQS** | ❌ `messaging.py` é stub. `worker.py` tem só `translate` (Gemini); `receive_messages`, `extract_text`, `save_result`, `process` e `main` lançam `NotImplementedError` | Publicar no SNS no POST, implementar o worker inteiro, criar tópico, fila, DLQ e EC2 do worker |
| 7 | **Interface gráfica** (−1,0 se faltar) | ✅ 8 telas com JS ligado à API, visual refeito. Testado com API simulada e smoke test do backend. Fluxo completo no navegador (criar, editar, excluir) depende do S3 | Testar no navegador contra o backend com S3 |
| P2 | **ALB + Auto Scaling** (1 a 3 instâncias, CPU >70% sobe, <25% desce) | ❌ `infra/README.md` é só uma lista de tarefas | Launch template, target group com health check, ASG, duas políticas de CPU, vídeo |
| E | **Entrega:** link do git e **vídeo da Parte 2** | ❌ | Gravar o vídeo mostrando a escala subindo e descendo |

Penalidade de cada serviço ausente: −1,5 ponto. Hoje, sem ajuste, ficariam zerados: **ElastiCache, SNS/SQS, Auto Scaling** (−4,5) e, na `main`, **DynamoDB** (−1,5). A interface gráfica (−1,0) deixou de ser risco.

## 3. Pontos de código que PRECISAM melhorar

### 3.1 Na `main` e no trabalho local

**Resolvidos hoje**

| # | Antes | Agora |
|---|---|---|
| 1 | 25 dos 48 testes unitários falhavam | ✅ 69 testes passam (6 de integração pulados). POST multipart com PDF e S3 simulado |
| 12 | Sem autenticação; o POST confiava no campo `user` | ✅ Token assinado (`accounts/`). POST, PUT e DELETE exigem token; PUT e DELETE só do dono (403). O campo `user` saiu |
| 13 (CORS) | Sem CORS | ✅ `django-cors-headers`, origens em `CORS_ALLOWED_ORIGINS` |
| 14 | Front quebrava com `'download URL'` | ✅ O front aceita `download_url` e `'download URL'`. A API ainda devolve a chave com espaço |

**Ainda abertos (bloqueantes primeiro)**

| # | Problema | Local | Correção |
|---|---|---|---|
| 2 | **`views.py` ignora a camada `services/`.** Cria o cliente boto3 em 3 lugares, copiado e colado, e os `services/*.py` ficam como stub | `ArticleView.post`, `ArticleDetailsView.delete`, `ArticleDownloadView.get` | Implementar `services/s3.py` e chamar de lá. Apagar `import boto3` e `settings` das views |
| 3 | **Credenciais passadas explicitamente, inclusive como string vazia.** Com `aws_access_key_id=''`, o boto3 não usa a IAM Role da EC2. Provável falha em produção (não validado na AWS) | `views.py`, `settings.py` | Remover os argumentos de credencial. `services/aws.py` já faz isso certo |
| 4 | **Variáveis de ambiente divergentes.** O código lê `AWS_STORAGE_BUCKET_NAME` e `AWS_S3_REGION_NAME`. O `.env.example`, os testes de integração e `services/aws.py` usam `S3_BUCKET` e `AWS_REGION`. Quem seguir o `.env.example` grava no bucket padrão `article-cloud` | `settings.py` vs `.env.example` | Uma só convenção (`S3_BUCKET`, `AWS_REGION`) |
| 5 | **Chave do S3 diferente da documentada.** O código usa `artigos/{id}-{nome do arquivo}`. Docs e testes esperam `artigos/{id}.pdf`. O nome enviado entra na chave sem tratamento | `ArticleView.post` | Usar `KEY_TEMPLATE` de `services/s3.py` |
| 6 | **PDF não é validado no back** (tipo e tamanho). O front valida só para ajudar. A fixture `invalido_nao_e_pdf.pdf` existe para isso | `ArticleView.post` | Recusar o que não for `application/pdf` ou passar do limite |
| 7 | **Sem `ContentType` no upload.** O teste `test_objeto_fica_com_content_type_pdf` falharia | `ArticleView.post` | `ExtraArgs={'ContentType': 'application/pdf'}` |
| 8 | **Erro interno vazado ao cliente.** `error(f"Erro {str(e)} identificado!", 500)` devolve a exceção do boto3 | POST, DELETE e download | Registrar com `logging` e devolver mensagem genérica |
| 9 | **`except Exception` largo** no POST e no DELETE | `views.py` | Capturar `ClientError` e `BotoCoreError` |
| 10 | **DELETE apaga o PDF antes do registro.** Se o `delete()` do banco falhar, o artigo fica sem arquivo | `ArticleDetailsView.delete` | Apagar o registro primeiro, o objeto depois |
| 11 | **POST faz upload ao S3 dentro de `transaction.atomic`.** Se algo falhar depois do upload, o objeto fica órfão | `ArticleView.post` | Apagar o objeto no `except` |
| 13 | **Sem `/health/`** para o health check do ALB | `urls.py` | Rota que responde 200 sem tocar no banco |
| 14 | Chave `'download URL'` com espaço na resposta | `ArticleDownloadView.get` | `download_url` |
| 15 | **Download com `ExpiresIn=3000`** (50 min). A doc diz 300 s | `ArticleDownloadView.get` | 300 |
| 16 | **Sem paginação** em `GET /articles/`. O "Meus artigos" filtra no front por `user`, o que não escala | `ArticleView.get` | Paginar e aceitar `?user=` |
| 17 | `ALLOWED_HOSTS` vazio e `DEBUG=True` por padrão | `settings.py` | Documentar a configuração da EC2 |
| 18 | Estilo: espaços em volta de `=` em argumentos nomeados, parênteses em `if (article.s3_key)`, linhas em branco soltas, arquivo sem newline final | `views.py`, `settings.py` | Limpar |
| 19 | **Docstring de `worker.py` cita Amazon Translate, o código usa Gemini.** `GEMINI_API_KEY` e `GEMINI_MODEL` não estão no `.env.example`. Chave de API externa na EC2 | `worker.py` | Decidir: Amazon Translate (sem chave, usa a LabRole) ou Gemini (documentar variáveis) |
| 20 | `worker/requirements.txt` sem newline final; `worker.py` importa `google.genai` no topo, o que quebra os outros passos se o pacote faltar | `worker.py` | Corrigir |

**Novos, introduzidos pela autenticação**

| # | Ponto | Observação |
|---|---|---|
| 21 | Todas as instâncias do Auto Scaling precisam da **mesma `DJANGO_SECRET_KEY`**, senão o token de uma instância é recusado por outra | Colocar a chave no user data ou launch template |
| 22 | O token não pode ser revogado antes dos 7 dias e o login não tem limite de tentativas | Aceitável para o trabalho. Anotar para a arguição |
| 23 | O mesmo `User` do Django guarda login e dono do artigo; `CASCADE` apaga os artigos com o usuário | Já documentado no README da raiz |

### 3.2 Na branch `backend-AWS` (corrigir antes de mesclar)

| # | Problema | Correção |
|---|---|---|
| 1 | `log_dynamoDB` **devolve** `error(...)` em caso de falha, mas as views **ignoram o retorno**. Falha de log some em silêncio | Capturar, registrar com `logging`, não devolver `JsonResponse` de função auxiliar |
| 2 | O mesmo bloco `error_details = {...}` + `log_dynamoDB('ERROR', ...)` se repete **cerca de 20 vezes**. É o maior problema de código limpo do projeto | Uma função `fail(message, status, local)` que loga e devolve o `error()` |
| 3 | `log_dynamoDB` cria um `boto3.resource` **a cada chamada**, com credenciais explícitas | Usar `services/dynamo_log.py` + `aws.resource()` (já feito e testado) |
| 4 | Registra **erros de validação (400/404/409)** como ação. A spec pede "ação, dados e hora" do CRUD, não log de erros | Manter só se o grupo quiser, na tabela separada |
| 5 | **GET (READ) não é logado.** A spec fala em "toda ação do CRUD" | Logar READ em detalhe e lista, ou decidir e documentar que só escrita é logada |
| 6 | `manipulated_data` guardado como **string JSON**, não como mapa | Gravar `dict` (cuidado com `Decimal`) |
| 7 | Fuso `-3` fixo no código. O Django já usa UTC | `datetime.now(timezone.utc)` |
| 8 | Chave da tabela: `log_id` (uuid). Sem `article_id`, não dá para consultar o histórico de um artigo | Partição `article_id`, ordenação `timestamp`, como em `dynamo_log.py` |
| 9 | Variáveis novas: `AWS_REGION_NAME`, `AWS_DYNAMODB_TABLE_NAME`, `AWS_DYNAMODB_TABLE_NAME_ERROR`. Agora são **três** nomes de região. Bucket padrão virou `article-cloud2` | Uma só convenção (3.1 item 4) |
| 10 | O CREATE é logado **depois** da transação. Se o log falhar, o cadastro segue | Documentar como decisão |
| 11 | **Conflito com o trabalho local:** a branch usa `request.POST['user']` e `error` definido em `views.py`; hoje o usuário vem do token e `error` vem de `article_cloud/http.py` | Resolver o merge mantendo o token. O DynamoDB deve registrar `request.user.username` |

## 4. Código que PRECISA ser entregue (e o que já testa na AWS)

### 4.1 Código a entregar

| Prioridade | Entrega | Arquivo | Estado |
|---|---|---|---|
| 1 | Cache Redis (`get_client`, `get_or_set`, `invalidate_article`) e uso nas views | `services/cache.py`, `views.py` | stub |
| 2 | Publicação no SNS (`publish_article_created`) e chamada no POST | `services/messaging.py`, `views.py` | stub |
| 3 | Worker completo: `receive_messages`, `extract_text`, `save_result`, `process`, `main` | `worker/worker.py` | 1 de 6 funções |
| 4 | Log DynamoDB (mesclar `backend-AWS` e limpar) | `services/dynamo_log.py`, `views.py` | só na branch |
| 5 | Mover S3 para `services/s3.py` e corrigir 3.1 itens 2 a 11 | `services/s3.py`, `views.py` | em `views.py` |
| 6 | `/health/`, `gunicorn`, user data da EC2 | `backend`, `infra/` | não existe |
| 7 | ALB, Launch Template, ASG, políticas de CPU, vídeo | `infra/` | não existe |
| 8 | Paginação e filtro `?user=` | `views.py`, `meus_artigos.js` | não existe |
| ✅ | Front completo, cadastro, login, token, CORS, testes unitários | `frontend/`, `accounts/` | feito (sem commit) |

### 4.2 O que já pode ser testado na AWS hoje

| Integração | Testável hoje? | Como |
|---|---|---|
| **RDS** | **Sim.** Código e teste prontos | Criar o RDS, `DB_*` no `.env`, `RUN_AWS_INTEGRATION=1 python manage.py test articles.tests.integration.test_rds` |
| **S3 (upload, download, delete)** | **Sim, pela API e pelo front.** O `test_s3.py` **não** roda: ele chama `services/s3.py`, que é stub | Subir a API com o bucket, entrar no front e criar, baixar e excluir um artigo. Para usar `test_s3.py`, implementar `services/s3.py` |
| **DynamoDB** | **Só na branch `backend-AWS`**, pela API. `test_dynamodb.py` depende do stub | Mesclar, criar as tabelas, criar um artigo e olhar a tabela |
| ElastiCache | Não. Só cria o cluster e testa `ping` da EC2 | Depende de `cache.py` |
| SNS/SQS | Parcial. Dá para criar tópico, fila e DLQ e testar a assinatura pelo console. `test_sns_sqs.py` depende do stub | Depende de `messaging.py` e do worker |
| Ponta a ponta | Não | Depende de tudo |
| ALB + ASG | Não testável sem a API estável na EC2 | Depende de `/health/`, do `gunicorn` e da mesma `DJANGO_SECRET_KEY` nas instâncias |

## 5. O que falta por parte

### 5.1 Frontend (spec: interface gráfica, −1,0 se faltar)

| Item | Estado | O que falta |
|---|---|---|
| Telas | ✅ `index`, `login`, `cadastro`, `artigos`, `artigo`, `meus_artigos`, `criar_artigo`, `editar_artigo`. `perfil.html` removida | — |
| JavaScript e API | ✅ `api.js` com token e erro da API; `auth.js`, `ui.js`, `nav.js` e um script por tela | — |
| Formulário de artigo | ✅ Chips para autores e palavras-chave, área, resumo e PDF | — |
| Status e tradução | ✅ Badge de status e tradução no detalhe. Atualiza ao recarregar, sem polling | Opcional: polling na demo do worker |
| Visual | ✅ Refeito (tema, hero, cards, painéis) | Conferir a versão mobile |
| Teste | 🟡 Lista, detalhe e erro testados com API simulada; backend validado por smoke test (login, CORS, 401) | Testar criar, editar e excluir no navegador com o S3 |
| Hospedagem do front | ❌ Hoje roda em `python -m http.server` | Decidir onde o front fica na AWS (S3 estático ou nginx na EC2) e definir `API_BASE_URL` com o DNS do ALB |
| "Meus artigos" | 🟡 Filtra no cliente | Filtro `?user=` no back (3.1 item 16) |

### 5.2 Backend (API + worker)

| Item | Estado |
|---|---|
| CRUD, busca, RDS, modelos, migrations | ✅ |
| Autenticação por token | ✅ |
| CORS | ✅ |
| S3 | 🟡 funciona em `views.py`, sem camada `services/` e sem validação (3.1) |
| DynamoDB | 🟡 só na branch |
| Redis | ❌ |
| SNS e worker | ❌ |
| `/health/`, `gunicorn`, paginação | ❌ |

### 5.3 Integração e infraestrutura

| Item | Estado |
|---|---|
| Front ↔ API (URL base, CORS, token, FormData) | 🟡 funciona localmente; falta testar com o S3 e na EC2 |
| Nenhum recurso AWS validado (RDS, bucket, tabela, cluster, tópico, fila, EC2) | ❌ |
| API ↔ Redis, SNS | ❌ |
| SQS → worker → RDS e Redis | ❌ |
| EC2 da API e EC2 do worker | ❌ |
| ALB, ASG, políticas de 70% e 25% | ❌ |
| Vídeo da Parte 2 | ❌ |
| Testes de integração escritos (6 arquivos) | ✅ escritos, 4 de 6 dependem de stubs |

## 6. Porcentagem de conclusão

Critério: peso igual por item dentro de cada etapa. "Pronto" = código escrito e coberto por teste local. Nada vale como integrado sem rodar na AWS.

| Etapa | Cálculo | Antes (10/10 manhã) | `main` + trabalho local | Com `backend-AWS` |
|---|---|---|---|---|
| **Backend** (RDS 100 · API e autenticação 100 · S3 70 · Redis 0 · SNS e worker 8 · DynamoDB 0, ou 60 com a branch) | média de 6 | ~36% | **~46%** | **~56%** |
| **Frontend** (layout 95 · JS e fluxos 85 · validado no navegador com S3 pendente) | média | ~35% | **~85%** | ~85% |
| **Integração e infra** (front ↔ API local feito; nenhum recurso AWS validado; Parte 2 zerada) | | ~10% | **~15%** | ~17% |
| **Projeto no total** | média das três | ~25% | **~49%** | **~53%** |

O total engana por um motivo: o que falta é quase todo ligado à AWS (Redis, SNS, worker, ALB, Auto Scaling, vídeo) e vale mais pontos na spec do que o front. Em pontos de penalidade, os serviços zerados continuam sendo os mesmos da seção 2.

A documentação em `docs/aws/` (833 linhas) está completa e cobre o passo a passo de todos os serviços. Ela não entra na conta porque a spec avalia a aplicação rodando.

## 7. Decisões

**Fechadas**

| Decisão | Resultado |
|---|---|
| Prazo | Adiado para 12/10 |
| Autenticação | Completa, com senha e token |
| `perfil.html` | Removida |
| Criar artigo | Chips de autores e tags, PDF, área e resumo; campo `conteudo` removido |
| Detalhe do artigo | Página completa com download |
| Lista e status | Cards com busca por envio; badge de status sem polling |
| Erros no front | Alerta Bootstrap com a mensagem da API |

**Abertas**

1. **Tradução:** Amazon Translate (sem chave externa) ou Gemini (já no código, depende de chave na EC2).
2. **Log de leitura (READ) e de erros no DynamoDB:** manter ou cortar.
3. **Onde fica o front na AWS:** S3 estático ou nginx na EC2 da API.
4. **O que fica fora:** paginação.

## 8. Ordem sugerida até o prazo (12/10)

1. Commitar o trabalho local. Mesclar `backend-AWS` limpa (3.2) e apagar as branches mortas.
2. Mover o S3 para `services/s3.py` e corrigir 3.1 itens 2 a 11. Testes verdes.
3. Criar RDS, bucket e tabela. Subir a API numa EC2 com `gunicorn` e `/health/`. Testar o fluxo no front.
4. `cache.py` e `messaging.py`. Criar Redis, tópico, fila e DLQ.
5. Worker. Teste ponta a ponta.
6. Parte 2: launch template, ALB, ASG, políticas. Teste de carga e vídeo.
7. Limpar os READMEs (seção 9) e entregar.

## 9. O que remover dos READMEs

Regra: README é conhecimento público (o que é, como rodar, como usar). Conhecimento da equipe (status, pendências, decisões, branches, custos, "como implementar") sai. **`docs/aws/` fica inteira**, por ser o passo a passo das etapas ainda por fazer.

**Já feito:** `frontend/README.md` sem a seção Pendente; `frontend/js/README.md` reescrito; `backend/README.md` com rotas novas e exemplo `curl` atualizado; "48 testes" removido do README da raiz; seção "Como rodar localmente" adicionada; comentários de boilerplate do `django-admin`, `# Falta:` e referências a branches removidos do código.

**Ainda por fazer**

| Arquivo | Remover | Manter |
|---|---|---|
| `README.md` (raiz) | Linha vazia `**Equipe:**` (preencher ou apagar). Parágrafo sobre "Parte 1 / Parte 2 da spec". Seção **Status** (está desatualizada: diz que o JS do front e a autenticação estão pendentes). Seção **Pontos em aberto** (idem). Seção **Regras do time**. Seção **Decisões técnicas** (custos, Learner Lab, LabRole). Tabela de decisões do modelo de dados (a nota "simplifica o laboratório"). Coluna "Exigência da spec" da tabela de serviços. Seção **Índice da documentação** (duplica a estrutura). Diagramas de sequência e de estados | O que é, como funciona (resumido), tabela de serviços, diagrama de componentes, modelo de dados (ER), estrutura do repositório, como rodar. Atualizar a "Estrutura do repositório" (falta `accounts/`) |
| `backend/README.md` | Tabela de **Migrations**. Parágrafo "Crescimento previsto" (a autenticação já virou o app `accounts`). Parágrafo "Ao implementar um serviço, escreva primeiro o teste…". Texto "ainda não lidas pelo código". Descrição dos arquivos de teste um a um | Estrutura, rotas, erros, modelo de dados, como rodar testes, variáveis de ambiente (acrescentar `CORS_ALLOWED_ORIGINS`) |
| `backend/articles/services/README.md` | **Apagar o arquivo.** Só tem branches, estado de esqueleto e regras para quem implementa | |
| `worker/README.md` | "**Só o esqueleto existe**". Tabela de arquivos. Regras de robustez escritas como tarefa | O que faz, decisão de ser independente do Django (uma linha), como rodar |
| `infra/README.md` | **Apagar o arquivo** (lista de tarefas "a pesquisar"). Recriar quando a Parte 2 existir | |
| `backend/articles/tests/integration/README.md` | Seção **Estado**. Regra 4 (custos). Regra 6 e a observação sobre o POST "ainda não existe". Nota "dependem de services implementado" | Como rodar, variáveis por arquivo |
| `backend/articles/tests/fixtures/README.md` | "depois que o POST aceitar PDF", "ainda será definido", e o exemplo `curl` sem token | Tabela de PDFs e como regerar |
| `docs/aws/*` | **Nada.** | Tudo |

Fora dos READMEs:

- **Docstrings "Como fazer:"** em `services/*.py` e `worker.py`: viram código normal quando os stubs forem implementados.
- **Branches remotas** `backend`, `backend-S3`, `django_init`, `telas` (seção 1).
- **`backend/articles/guia_p_testar.txt`**, só na branch `django_init`.
