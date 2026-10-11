# 9. Estudo geral para a arguição

[← 8. Teste de ponta a ponta e conferência de custos](08-ponta-a-ponta-e-custos.md) | [Índice](README.md)

As decisões de cada serviço estão no fim do arquivo de cada etapa, na seção "Por que configuramos assim". Esta página reúne o que é comum a todos.

## Ideia central: um papel para cada serviço

| Dado | Onde fica | Por quê |
|---|---|---|
| Metadados (título, autores, status) | RDS | Dados estruturados com relações (N:N) e busca. Exigem consistência |
| PDF | S3 | Arquivo binário grande. O S3 é barato e feito para objetos |
| Cópia temporária das consultas | Redis | Leitura em memória, muito mais rápida que o banco |
| Log de ações | DynamoDB | Só recebe escritas, sem relações. Escala sem administrar servidor |
| Aviso de "novo artigo" | SNS + SQS | A API responde sem esperar o trabalho pesado |

Pergunta provável: "Por que não guardar o PDF no RDS?" Resposta: o banco ficaria pesado e caro, os backups cresceriam e cada download passaria pela API. No S3, o download vai direto ao S3 por URL pré-assinada.

## boto3 no código

O `backend/articles/services/aws.py` é a fábrica de clientes. Ele foi revisado com estas práticas:

| Prática | Motivo |
|---|---|
| Cliente criado uma vez por serviço (`lru_cache`) | Criar a cada chamada é lento e refaz a busca de credenciais |
| Clientes compartilhados, resources por thread | O cliente boto3 é thread-safe. O resource, não. O Django atende em várias threads |
| `connect_timeout=3`, `read_timeout=10` | Sem timeout, um serviço lento trava a requisição inteira |
| Retries no modo `standard` (3 retries) | Absorve falhas passageiras com espera crescente |
| Região vem de `AWS_REGION` | O mesmo código serve para qualquer região |
| S3 com Signature v4 | Necessária para URLs pré-assinadas |
| Sem chaves no código | O boto3 acha a LabRole sozinho na EC2 |
| Import dentro da função | O projeto importa e testa sem `boto3` instalado |

Pontos para cada serviço quando implementar:
- **S3:** `upload_fileobj` envia em partes e não carrega o arquivo todo na memória. Capture `botocore.exceptions.ClientError`.
- **DynamoDB:** use `Decimal`. Capture `ClientError` e registre com `logging`.
- **SNS:** a publicação pode falhar. O artigo fica em `ERRO` e o dono reenvia por `POST /articles/<id>/reprocess/`.
- **SQS (worker):** use `WaitTimeSeconds=20` e chame `delete_message` só no fim.
- **Gemini:** a tradução usa a API do Google (`google-genai`), não um serviço da AWS. Precisa de `GEMINI_API_KEY`, `GEMINI_MODEL` e saída para a internet. Traduza só o resumo. Pergunta provável: "Por que não Amazon Translate?" Resposta: o Gemini traduz com melhor qualidade e já estava integrado; o custo é uma chave externa e uma dependência fora da AWS.
- **Redis:** o cliente é criado uma vez, com `socket_connect_timeout` e `socket_timeout` de 2 s. O código captura qualquer exceção e segue sem cache.
- **Testes:** os unitários (`tests/unit/`) usam `unittest.mock` e não dependem da rede. Os de integração (`tests/integration/`) usam a AWS real e só rodam com `RUN_AWS_INTEGRATION=1`.

O arquivo `articles/tests/unit/test_aws_clients.py` cobre a fábrica: cache do cliente, região, timeouts, retries e Signature v4.

## Perguntas gerais para treinar

1. Por que cada serviço tem um papel único?
2. O que acontece se o Redis cair? E o SQS? E o S3?
3. Onde ficam as credenciais da aplicação e por quê?
4. Por que a API responde antes de a tradução terminar?
5. O que a DLQ resolve?
6. Por que o worker precisa ser idempotente?
7. Qual a ordem das gravações no cadastro e o que acontece se o upload ao S3 falhar?
8. Como o PDF chega ao usuário sem passar pela API?
9. Quais serviços cobram por hora e como evitamos gasto?
10. O que mudaria em produção (Multi-AZ, Secrets Manager, HTTPS, autenticação)?

---
[← 8. Teste de ponta a ponta e conferência de custos](08-ponta-a-ponta-e-custos.md) | [Índice](README.md)
