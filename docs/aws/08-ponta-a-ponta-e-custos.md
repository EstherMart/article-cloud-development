# 8. Teste de ponta a ponta e conferência de custos

[← 7. EC2 do worker](07-ec2-worker.md) | [Índice](README.md) | [9. Estudo geral para a arguição →](09-estudo-geral.md)

## Teste de ponta a ponta (quando tudo estiver implementado)

1. `POST /articles/` com um PDF.
2. RDS: o artigo existe com status `PENDENTE`.
3. S3: o objeto `artigos/<id>.pdf` existe.
4. DynamoDB: há um item `CREATE` para o artigo (se não houver, veja `journalctl -u api`: falha de log não aparece para o usuário).
5. SQS: a mensagem chegou (ou o worker já a consumiu).
6. Worker: o artigo muda para `PROCESSADO` e `translated_abstract` fica preenchido.
7. `GET /articles/<id>/` duas vezes: a segunda vem do Redis (`redis-cli keys 'artigo:*'`).
8. `PUT /articles/<id>/`: o DynamoDB ganha um item `UPDATE` e a chave do Redis some.
9. `GET /articles/<id>/download/` e abra a `download_url`: o PDF abre.
10. Derrube o SNS de propósito (`SNS_TOPIC_ARN` errado) e cadastre outro artigo: deve vir **503** com `article_id`. Corrija a variável e chame `POST /articles/<id>/reprocess/`: o artigo volta para `PENDENTE` e depois `PROCESSADO`.
11. `DELETE /articles/<id>/`: o PDF some do S3 e o DynamoDB ganha um item `DELETE`.

## Conferir a configuração de cada serviço (requisito por requisito)

Depois de criar os recursos, rode o teste que só lê a configuração e compara com o que a aplicação espera (variáveis no `.env`, ver `backend/articles/tests/integration/README.md`):

```
cd backend && set -a; source .env; set +a
RUN_AWS_INTEGRATION=1 python manage.py test articles.tests.integration.test_especificacao -v 2
```

Cada classe é um requisito (EC2, RDS, S3, ElastiCache, DynamoDB, SNS e SQS, interface, Parte 2) e se pula sozinha se o recurso ainda não existe. O teste do Redis só funciona de dentro da EC2.

Para testar um serviço isolado, use o arquivo dele (`test_rds`, `test_s3`, `test_dynamodb`, `test_redis`, `test_sns_sqs`). Para o fluxo todo, `test_pipeline_e2e`, de dentro da EC2 da API.

## Roteiro de buscas na arguição

Com os 12 artigos de demonstração ([etapa 1](01-rds.md)) e os PDFs carregados (`carregar_demo_pdfs`):

| Busca | Resultado esperado | O que mostra |
|---|---|---|
| `nuvem` | 3 artigos (título, área e tag) | Busca em título, área, autores e tags ao mesmo tempo |
| `Ana Souza` | 4 artigos | Busca por autor (relação N:N) |
| `Redis` | 1 artigo | Busca por palavra-chave |
| `Banco de Dados` | 3 artigos | Busca por área |
| `tradução` | 1 artigo | Acentos na busca |
| `zzz` | lista vazia | Sem resultado |

Rode cada busca duas vezes: a segunda vem do Redis (`redis-cli keys 'busca:*'`). Abra um artigo para mostrar o resumo original e a tradução em inglês gravada pelo worker. Para mostrar o worker ao vivo, cadastre um artigo novo pelo front com um PDF de `backend/articles/tests/fixtures/pdfs` e acompanhe o status `PENDENTE` → `PROCESSANDO` → `PROCESSADO`. Sem resumo digitado, use `artigo_longo_5_paginas.pdf`; para mostrar o erro, `escaneado_sem_texto.pdf` sem resumo.

## Conferência final de custos

Depois de apagar tudo, confira que estas telas estão vazias:
- EC2: instâncias, volumes, Elastic IPs.
- RDS: bancos e snapshots.
- ElastiCache: clusters.
- S3: buckets.
- DynamoDB: tabelas.
- SNS e SQS: tópicos e filas.

No Learner Lab, o painel inicial mostra o valor gasto em dólares. Olhe esse número antes e depois de cada sessão.

---
[← 7. EC2 do worker](07-ec2-worker.md) | [Índice](README.md) | [9. Estudo geral para a arguição →](09-estudo-geral.md)
