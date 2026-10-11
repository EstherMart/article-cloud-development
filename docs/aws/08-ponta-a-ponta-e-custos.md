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
