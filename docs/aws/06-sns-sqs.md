# 6. SNS e SQS

[← 5. ElastiCache Redis](05-elasticache.md) | [Índice](README.md) | [7. EC2 do worker →](07-ec2-worker.md)

## O que são o SNS e o SQS
- **SQS** é uma fila de mensagens. A API coloca um aviso ("novo artigo") e o worker o retira depois. Se o worker estiver fora do ar, o aviso espera na fila.
- **SNS** é um mensageiro: a API publica num tópico, e o SNS entrega uma cópia na fila.
- **DLQ** (fila de mensagens não entregues) recebe as mensagens que falharam 3 vezes. Assim uma mensagem com problema não trava o resto.

Crie nesta ordem: DLQ, fila principal, tópico e assinatura. Depois volte à fila principal para colar o ARN do tópico na política.

Os nomes abaixo seguem o console em português. Entre parênteses vai o nome em inglês, caso o seu console esteja em outro idioma. Campo que não aparece aqui fica no valor padrão.

**1. DLQ.** SQS > **Filas** > **Criar fila**.

| Campo (inglês) | Valor | O que é e por quê |
|---|---|---|
| Tipo (Type) | **Padrão** (Standard) | Entrega "pelo menos uma vez" e alta vazão |
| Nome (Name) | `artigos-dlq` | Rótulo |
| Tempo limite de visibilidade (Visibility timeout) | 30 segundos (padrão) | Sem ajustes |
| Período de retenção de mensagens (Message retention) | **14 dias** | Mensagens com erro ficam disponíveis para você analisar |
| Atraso na entrega (Delivery delay) | 0 | Sem atraso |
| Tamanho máximo da mensagem | 256 KB | Padrão |
| Tempo de espera para recebimento (Receive wait time) | 0 | Padrão |
| Criptografia (Encryption) | **SSE-SQS** (padrão) | Criptografa, sem custo |
| Fila de mensagens não entregues (Dead-letter queue) | desabilitada | Esta já é a DLQ |

**2. Fila principal.** SQS > **Criar fila**.

| Campo (inglês) | Valor | O que é e por quê |
|---|---|---|
| Tipo | **Padrão** | Igual à DLQ |
| Nome | `artigos-fila` | Rótulo |
| Tempo limite de visibilidade (Visibility timeout) | **120 segundos** | Quando o worker pega uma mensagem, ela fica "invisível" por esse tempo. Precisa ser maior que o tempo de processar um PDF. Senão outro worker pega a mesma |
| Período de retenção de mensagens | 4 dias (padrão) | Quanto tempo a mensagem espera |
| Atraso na entrega | 0 | Sem atraso |
| Tamanho máximo da mensagem | 256 KB | Padrão |
| Tempo de espera para recebimento (Receive message wait time) | **20 segundos** | Ativa o "long polling": o worker espera até 20 s por mensagem, em vez de perguntar sem parar. Reduz custo e chamadas vazias |
| Criptografia | **SSE-SQS** (padrão) | Não use chave KMS própria: o SNS precisaria de permissão extra |
| Política de acesso (Access policy) | **Avançado**, com o JSON abaixo | Sem essa política, o SNS não consegue escrever na fila |
| Fila de mensagens não entregues | **Habilitada**, fila `artigos-dlq`, **Máximo de recebimentos = 3** | Depois de 3 tentativas sem sucesso, a mensagem vai para a DLQ |

Política de acesso da `artigos-fila` (troque os dois ARNs pelos seus). Ela diz: "o SNS pode enviar mensagens para esta fila, mas só se vier deste tópico".

```
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PermiteSNS",
    "Effect": "Allow",
    "Principal": {"Service": "sns.amazonaws.com"},
    "Action": "sqs:SendMessage",
    "Resource": "<ARN da artigos-fila>",
    "Condition": {"ArnEquals": {"aws:SourceArn": "<ARN do tópico artigos-eventos>"}}
  }]
}
```

Se você ainda não tem o ARN do tópico, crie o tópico primeiro e volte aqui para editar a política.

**3. Tópico.** SNS > **Tópicos** > **Criar tópico**.

| Campo (inglês) | Valor | O que é e por quê |
|---|---|---|
| Tipo (Type) | **Padrão** (Standard) | Igual à fila |
| Nome (Name) | `artigos-eventos` | Rótulo |
| Nome de exibição (Display name) | vazio | Só para SMS e e-mail |
| Criptografia (Encryption) | desligada | Opcional |
| Política de acesso (Access policy) | **Básico** (padrão) | Só a sua conta publica |
| Política de repetição de entrega | padrão | Sem ajustes |

Copie o **ARN** do tópico.

**4. Assinatura.** No tópico, **Criar assinatura**.

| Campo (inglês) | Valor | O que é e por quê |
|---|---|---|
| ARN do tópico (Topic ARN) | o do `artigos-eventos` | De onde vêm as mensagens |
| Protocolo (Protocol) | **Amazon SQS** | Entrega numa fila |
| Endpoint | ARN da `artigos-fila` | Para onde vão |
| Habilitar entrega de mensagens brutas (Enable raw message delivery) | **marcado** | A fila recebe o JSON puro, sem o envelope do SNS. O worker lê direto |
| Política de filtro (Subscription filter policy) | desligada | Entrega tudo |
| Política de redirecionamento (Redrive policy) | desligada | A DLQ já está na fila |

Copie a **URL** da `artigos-fila` (para `SQS_QUEUE_URL`) e o **ARN** do tópico (para `SNS_TOPIC_ARN`).

## Configurar o código
```
SNS_TOPIC_ARN=<arn do tópico>
SQS_QUEUE_URL=<url da fila>
```

## Formato da mensagem
```
{"article_id": 1, "s3_key": "artigos/1.pdf", "bucket": "<bucket>"}
```
Feche esse formato com o time antes de implementar a API e o worker.

## Implementar
- API (`messaging.py`): `publish_article_created(article_id, s3_key, bucket)` usa `client('sns').publish(TopicArn=..., Message=json.dumps(...))`.
- Worker (`worker/worker.py`): `receive_message(WaitTimeSeconds=20)`, processa, grava no RDS e só então chama `delete_message`.

## Testar no console
1. SNS > tópico > **Publicar mensagem**. Corpo: o JSON acima. Clique em **Publicar mensagem**.
2. SQS > `artigos-fila` > **Enviar e receber mensagens** > **Pesquisar mensagens**. A mensagem deve aparecer.
3. Clique na mensagem. Com raw delivery ligado, o corpo é o JSON puro, sem envelope do SNS.
4. Teste a DLQ: receba a mesma mensagem 3 vezes sem apagá-la (aguarde o visibility timeout entre as leituras). Depois, em `artigos-dlq`, clique em **Pesquisar mensagens**. A mensagem deve estar lá.

## Apagar
SNS: apague a assinatura e depois o tópico. SQS: apague `artigos-fila` e `artigos-dlq`.

## Por que configuramos assim (estudo para a arguição)

| Configuração | Motivo |
|---|---|
| SNS + SQS em vez de chamar o worker direto | Desacopla a API do worker. O usuário recebe resposta sem esperar a tradução |
| Fila SQS entre os dois | Guarda a mensagem se o worker estiver fora do ar. Nada se perde |
| Long polling (20 s) | Menos chamadas vazias, menor custo e menor latência |
| Visibility timeout (120 s) | Maior que o tempo de processar. Impede que dois workers peguem a mesma mensagem |
| DLQ com 3 tentativas | Mensagem "envenenada" não trava a fila para sempre. Vai para análise |
| Raw message delivery | A mensagem chega como o JSON original, sem o envelope do SNS |
| Apagar a mensagem só no final | Se o worker falhar, a mensagem volta e é reprocessada |
| Fila Standard | Entrega "pelo menos uma vez": a mesma mensagem pode chegar duas vezes |

Consequência da fila Standard: o worker precisa ser **idempotente**. Processar o mesmo artigo duas vezes deve dar o mesmo resultado. Basta gravar `translated_abstract` e `PROCESSADO` sobrescrevendo.

Pergunta provável: "Por que SNS e SQS juntos?" O SNS publica para vários assinantes (fan-out). O SQS dá a fila durável e a DLQ. Hoje há um assinante, mas o desenho permite adicionar outros (por exemplo, e-mail) sem mudar a API.

---
[← 5. ElastiCache Redis](05-elasticache.md) | [Índice](README.md) | [7. EC2 do worker →](07-ec2-worker.md)
