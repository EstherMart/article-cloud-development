# Mensageria com RabbitMQ (substitui SNS e SQS)

No trabalho 1 a API avisava o worker por **SNS + SQS** ([docs/aws/06](../aws/06-sns-sqs.md)). No trabalho 2 esse par foi trocado por um único **RabbitMQ** rodando em container. Este texto explica o que mudou, como funciona e por que o RabbitMQ foi a escolha.

## Por que RabbitMQ e não Kafka

**O motivo principal foi a familiaridade.** O grupo já conhecia o RabbitMQ (fila, ack, consumidor) e não conhecia o Kafka. Com o prazo curto do trabalho, usar o que já se conhece permitiu gastar o tempo no que a especificação pontua: o container subir, e a produção e o consumo funcionarem de ponta a ponta.

Tecnicamente a escolha também não atrapalha, porque o problema do projeto é de **fila de tarefas**: a API pede "processe este artigo" e *um* worker faz o trabalho, uma vez. Isso é o que o RabbitMQ faz de forma nativa (fila, confirmação por mensagem, reentrega, fila de mensagens mortas). O Kafka é um *log distribuído* feito para alto volume, vários leitores independentes e reprocessamento do histórico. Seus conceitos (tópicos, partições, offsets, grupos de consumidores) seriam complexidade sem benefício para um fluxo com um produtor, um consumidor e baixo volume. Se o projeto crescesse para vários serviços lendo os mesmos eventos, o Kafka passaria a fazer sentido.

## O que mudou

| Antes (AWS) | Agora (RabbitMQ) |
|---|---|
| Tópico SNS publicado pela API | A API publica direto na fila `artigos.criados` (exchange padrão) |
| Fila SQS assinada no tópico | Fila `artigos.criados`, do tipo *quorum*, durável |
| Long polling de 20 s | O broker empurra a mensagem ao consumidor (`basic_consume`) |
| `delete_message` depois de processar | `basic_ack` depois de processar |
| Visibility timeout (mensagem reaparece) | Mensagem sem ack volta sozinha à fila se a conexão cair; falha explícita usa `basic_nack` |
| DLQ com `maxReceiveCount = 3` | DLX + fila `artigos.criados.dlq`, com `x-delivery-limit = 3` |
| Credenciais da IAM Role | Usuário e senha do broker, em `RABBITMQ_DEFAULT_USER` / `RABBITMQ_DEFAULT_PASS` |
| Envelope do SNS (ou entrega bruta) | Só o JSON do evento (o worker não aceita mais o envelope) |

O SNS "espalhava" uma mensagem para várias filas. Aqui há um único consumidor, então a publicação vai direto para a fila e o tópico deixou de ser necessário.

## Como foi implementado

**Mensagem** (igual à de antes, em JSON, persistente):

```json
{"article_id": 1, "s3_key": "artigos/1.pdf", "bucket": "artigos", "event": "ARTICLE_CREATED"}
```

**Produtor: `backend/articles/services/messaging.py`.** `publish_article_created()` abre uma conexão, liga a confirmação do broker (`confirm_delivery`), declara a fila e publica com `delivery_mode=Persistent` e `mandatory=True`. Se o broker estiver fora do ar, recusar ou não houver fila para receber, levanta `MessagingError` (um `RuntimeError`). A view `start_processing` captura isso, marca o artigo como `ERRO` e a API responde 503, como já fazia com o SNS. A conexão é aberta a cada publicação porque o `BlockingConnection` do pika não é thread-safe e o volume é baixo; timeouts curtos evitam que a requisição fique presa.

**Consumidor: `worker/worker.py`.** `consume()` conecta, declara a fila, limita a **uma mensagem por vez** (`basic_qos(prefetch_count=1)`) e consome com **ack manual**. `handle_delivery()` decide a resposta ao broker:

| Situação | Resposta | Resultado |
|---|---|---|
| Processou com sucesso | `ack` | A mensagem sai da fila |
| Falha ao processar (Gemini, banco, MinIO...) | `nack` com reenfileirar | Volta à fila. Depois de 3 reentregas, o RabbitMQ a envia à DLQ |
| Mensagem inválida (JSON ruim, campo faltando) | `nack` sem reenfileirar | Vai direto à DLQ, pois repetir não adianta |

Se a conexão cair, `main()` espera 5 s e reconecta.

**Fila e DLQ.** Backend e worker declaram a mesma estrutura, com argumentos idênticos:

```
exchange  artigos.criados.dlx   (direct, durável)
fila      artigos.criados.dlq   (durável)              <- ligada ao exchange acima
fila      artigos.criados       (durável, quorum)
          x-delivery-limit = 3
          x-dead-letter-exchange = artigos.criados.dlx
```

O limite vale para *reentregas*: a mensagem é entregue 1 vez e reentregue até 3, ou seja, **4 tentativas no total**, e então vai para a DLQ (o SQS contava 3 recebimentos no total). O teste de integração confirma esse número.

## Variáveis de ambiente

| Variável | Uso |
|---|---|
| `RABBITMQ_HOST` | Host do broker. No compose é o nome do serviço: `rabbitmq` |
| `RABBITMQ_PORT` | Porta AMQP (padrão `5672`) |
| `RABBITMQ_DEFAULT_USER`, `RABBITMQ_DEFAULT_PASS` | Login. O compose usa os mesmos valores para criar o usuário no container |
| `RABBITMQ_QUEUE` | Nome da fila (padrão `artigos.criados`) |
| `DB_SSLMODE` | `disable` no compose: o Postgres do container não tem TLS e o worker usa `require` por padrão |

Saíram `SNS_TOPIC_ARN`, `SQS_QUEUE_URL` e `SQS_DLQ_URL`. No compose o serviço `rabbitmq` define `RABBITMQ_DEFAULT_USER/PASS` porque o usuário `guest` padrão só aceita conexões locais e o backend e o worker falam com ele pela rede do Docker. Os dados ficam no volume `rabbitmq_data`, para as filas duráveis sobreviverem a um `docker compose down`.

## Como verificar

1. `docker compose up -d rabbitmq` e abra o painel em `http://localhost:15672` (login do `.env`). Em **Queues** aparecem `artigos.criados` e `artigos.criados.dlq` depois que o backend ou o worker sobem.
2. Cadastre um artigo pela API. A coluna **Total** de `artigos.criados` sobe e desce quando o worker consome.
3. Pela linha de comando: `docker compose exec rabbitmq rabbitmqctl list_queues name messages`.
4. Para um artigo que falha (por exemplo, sem `GEMINI_API_KEY`), a mensagem passa por 4 tentativas e termina em `artigos.criados.dlq`.
5. Teste automatizado contra o broker real (usa fila temporária, pode rodar com o worker no ar):

```
cd backend
RUN_RABBITMQ_INTEGRATION=1 RABBITMQ_HOST=localhost python manage.py test articles.tests.integration.test_rabbitmq
```

## Diferenças e limitações

- **Sem espera entre tentativas.** O SQS segurava a mensagem por 60 s ou mais (visibility timeout). Aqui a reentrega é imediata, então as 4 tentativas de uma falha do Gemini acontecem em milissegundos. Para ter espera seria preciso uma fila de retry com TTL, que ficou fora do escopo.
- **Heartbeat de 600 s no worker.** O processamento (PDF + Gemini) roda dentro do callback e bloqueia a thread que responde aos heartbeats do `BlockingConnection`. Com o padrão de 60 s o broker derrubaria a conexão no meio de um artigo lento. O valor alto resolve, ao custo de detectar mais devagar uma conexão morta.
- **`BlockingConnection` está deprecado no Pika 2.0.** Por isso o `requirements.txt` fixa `pika<2`. Uma migração futura para a `Connection` thread-safe do Pika 2 resolveria também o heartbeat.
- **A topologia está duplicada** no backend e no worker (imagens separadas, sem código compartilhado). Se mudar em um lado, mude no outro, ou o broker responde `PRECONDITION_FAILED`.
- **Processamento pelo menos uma vez.** Como no SQS, a mesma mensagem pode chegar duas vezes; o resultado do worker é o mesmo.
