# Arquitetura

Cada serviço tem um papel único. O PDF vai para o S3, os metadados para o RDS, o cache para o Redis, os logs para o DynamoDB, e o processamento pesado roda fora da API via SNS/SQS.

## Fluxo de cadastro (síncrono, na API)

1. O front envia formulário e PDF para `POST /articles/`.
2. O back valida os dados e o arquivo.
3. Grava os metadados no RDS com status PENDENTE.
4. Envia o PDF ao S3.
5. Registra o CREATE no DynamoDB.
6. Publica a mensagem no SNS e responde ao usuário.

A API não espera a tradução.

## Fluxo de processamento (assíncrono, no worker)

1. O SNS entrega a mensagem na fila SQS.
2. O worker baixa o PDF do S3, extrai o texto e traduz o resumo.
3. Salva a tradução no RDS, muda o status para PROCESSADO e invalida o cache do artigo.
4. Só então apaga a mensagem da fila.

## Consulta com cache (cache-aside)

1. A API procura a chave no Redis.
2. Hit: retorna direto.
3. Miss: consulta o RDS, grava no Redis com TTL e retorna.

Chaves: `artigo:{id}`, `artigos:recentes`, `busca:*`.

## Decisões técnicas

- **Redis não guarda PDF.** Um PDF tem vários MB e o ElastiCache é memória cara. Cacheie metadados, listas e buscas. O PDF sai do S3 por URL pré-assinada.
- **Ordem das gravações.** RDS primeiro para obter o id, depois S3 com o id na chave, depois `s3_key`, log e SNS. Se o upload falhar, apague o registro ou marque ERRO.
- **Invalidação.** Todo CREATE, UPDATE e DELETE apaga as chaves afetadas. O worker também invalida `artigo:{id}`. O TTL de 5 a 10 minutos é a rede de segurança.
- **Segurança.** Sem chaves no código, IAM Role na EC2 (LabRole), RDS e Redis em Security Groups que só aceitam as instâncias da aplicação, bucket S3 privado.
- **Stateless.** Sessão, uploads e cache vão para S3 e Redis, nunca para disco ou memória da EC2. Isso evita retrabalho na Parte 2.
- **Custos.** RDS e ElastiCache cobram por hora mesmo parados. Use t3.micro e cache.t3.micro, desligue ao fim do dia e apague tudo após a entrega.

## Pontos em aberto

- Autores: lista ou M2M com `Author`.
- Chave e atributos da tabela `logs_crud`.
- Formato final da mensagem SNS/SQS.
- Autenticação de usuários (o front tem login e cadastro, o back ainda não).
