# Setup dos recursos AWS

Checklist para criar os recursos no AWS Academy / Learner Lab (região us-east-1). Marque conforme avançar e registre aqui os nomes usados (sem senhas).

- [ ] **RDS PostgreSQL** (db.t3.micro). Criar o banco `academichub` com `CREATE DATABASE`. Security Group aceitando 5432 só da aplicação.
- [ ] **S3**. Bucket privado para os PDFs. Chave sugerida: `artigos/{id}.pdf`.
- [ ] **DynamoDB**. Tabela `logs_crud`. Definir a chave de partição e a de ordenação.
- [ ] **ElastiCache Redis** (cache.t3.micro). Security Group aceitando a porta 6379 só da aplicação.
- [ ] **SNS**. Tópico de artigos.
- [ ] **SQS**. Fila com DLQ (3 tentativas), long polling e Visibility Timeout maior que o processamento. Assinar a fila no tópico com raw message delivery.
- [ ] **EC2 da API**. Role LabRole. Python e dependências instalados, `.env` no servidor.
- [ ] **EC2 do worker**. Role LabRole.

## Conexão com o RDS

```
export RDSHOST="<endpoint-do-rds>"
psql "host=$RDSHOST port=5432 dbname=postgres user=postgres sslmode=verify-full sslrootcert=./global-bundle.pem"
```

Use o endpoint do RDS no lugar de `<endpoint-do-rds>`. O banco do projeto é criado depois de conectar. O `global-bundle.pem` é o certificado raiz da AWS e não deve ir para o git. Senhas ficam só no `.env`.
