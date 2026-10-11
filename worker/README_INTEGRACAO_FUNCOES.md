# Integração e validação do worker

## Artigo salvo, mas evento SNS não publicado

Se a API respondeu `503` por falha no SNS, o artigo já foi salvo. Tentar
cadastrá-lo novamente com o mesmo título pode resultar em conflito, porque o
título é único. A recuperação precisa reenviar o evento do artigo existente ou
usar algum mecanismo de nova tentativa; isso ainda não está implementado.

## 1. Fazer a tradução funcionar com Gemini

A função `translate` em [`worker.py`](./worker.py) já usa o SDK `google-genai`.
Para ela conseguir traduzir, o processo do worker precisa receber:

- `GEMINI_API_KEY`: uma chave válida para o serviço Gemini;
- `GEMINI_MODEL`: o nome de um modelo disponível para essa chave;
- acesso de saída à internet por HTTPS — normalmente, pela porta `443`.

Essas variáveis não estão no `.env.example` do backend. O worker também não
carrega o arquivo `.env` sozinho: elas precisam estar no ambiente antes de
iniciar o processo ou ser carregadas pelo shell, como explica o
[`README.md`](./README.md).

Para confirmar a tradução, primeiro teste `translate` isoladamente com um texto
curto. Confira tanto o caso de tradução bem-sucedida quanto os erros por chave
ausente, modelo incorreto, falta de rede ou resposta sem texto. Não coloque a
chave diretamente no código nem em um arquivo versionado.

## 2. Garantir que a API realmente dispare o processamento

O cadastro em `ArticleView.post` já chama `publish_article_created` depois de
gravar os metadados e enviar o PDF ao S3. Essa função, em
[`messaging.py`](../backend/articles/services/messaging.py), publica o evento no
SNS.

Para isso funcionar na AWS, ainda é necessário:

- configurar `SNS_TOPIC_ARN` no ambiente da API;
- conceder à role da EC2 da API permissão para publicar no tópico SNS;
- criar a fila SQS e assiná-la ao tópico SNS;
- configurar a política da fila para permitir que aquele tópico envie mensagens;
- garantir que a mensagem entregue tenha `article_id`, `s3_key` e `bucket`, no
  formato que o worker valida.

O worker aceita tanto JSON direto quanto o envelope SNS, mas as configurações de
SNS/SQS precisam estar corretas. O roteiro de criação está em
[`06-sns-sqs.md`](../docs/aws/06-sns-sqs.md).

## 3. Configurar o ambiente e as permissões do worker

O processo do worker precisa, no mínimo, das variáveis:

- `SQS_QUEUE_URL`: URL da fila principal;
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` e, conforme o ambiente,
  `DB_PORT` e `DB_SSLMODE`;
- `GEMINI_API_KEY` e `GEMINI_MODEL`;
- `AWS_REGION`.

Também precisa de permissões para:

- receber, consultar e apagar mensagens da SQS;
- baixar objetos do bucket S3.

O worker conecta diretamente a um PostgreSQL usando `psycopg2`; não usa o
SQLite local do Django. Portanto, para o fluxo completo, `DB_HOST` precisa
apontar para um PostgreSQL acessível, normalmente o RDS.

Na rede, a EC2 do worker precisa conseguir chegar ao RDS pela porta `5432` e ao
Redis pela `6379`. O guia [`07-ec2-worker.md`](../docs/aws/07-ec2-worker.md)
descreve a EC2 e o Security Group do worker. Para Gemini, também é necessária
saída de rede HTTPS.

## 4. Conferir se as falhas e novas tentativas estão bem tratadas

O fluxo em `process` tenta marcar o artigo como `PROCESSANDO`; se uma etapa
falhar, tenta marcá-lo como `ERRO` e deixa a exceção subir. Em `main`, a
mensagem só é apagada depois do processamento. Se houver falha, ela não é
apagada e poderá reaparecer na fila.

Ainda é preciso testar a configuração da SQS para garantir que:

- o *visibility timeout* seja maior que o tempo de processamento;
- a fila esteja configurada para encaminhar à DLQ após o número desejado de
  tentativas;
- alguém consiga inspecionar e, se necessário, redespachar mensagens que
  chegaram à DLQ.

Uma chamada ao Gemini pode demorar. Se o processamento durar mais do que o
*visibility timeout*, a mensagem pode voltar a ficar visível enquanto o
primeiro worker ainda trabalha. Isso pode provocar processamento duplicado e
chamadas extras ao Gemini. Para evitar isso, configure um timeout adequado ou
implemente a renovação do *visibility timeout* durante o processamento.

## 5. Rever dois pontos do processamento do conteúdo

A implementação atual tem estas escolhas:

- O resumo digitado no formulário é a fonte preferida para tradução. O worker
  usa o texto extraído do PDF apenas quando o resumo está vazio.
- `extract_text` usa `pypdf`; ela extrai texto selecionável, mas não faz OCR em
  PDFs que são imagens escaneadas.

Além disso, quando o resumo está vazio, o worker pode enviar todo o texto
extraído do artigo ao Gemini, não apenas o resumo. Convém definir um limite ou
extrair uma seção de resumo, para evitar textos grandes demais, erros por limite
do modelo ou consumo desnecessário.

## 6. Completar os testes

Vale testar com serviços simulados:

- mensagens válidas, envelope SNS e mensagem malformada;
- PDF com texto, PDF escaneado e PDF inválido;
- Gemini com resposta, sem resposta e falha;
- atualização correta dos status e da tradução no banco;
- cache indisponível;
- confirmação de que `delete_message` só ocorre após o processamento
  bem-sucedido.

O teste de integração ponta a ponta em
[`test_pipeline_e2e.py`](../backend/articles/tests/integration/test_pipeline_e2e.py)
ainda contém comentários e um exemplo de cadastro antigos: ele precisa ser
atualizado para o cadastro autenticado e o formato atual do multipart antes de
ser usado para validar tudo junto.

## Ordem prática recomendada

1. Testar a função Gemini com chave, modelo e texto curto.
2. Configurar e testar o worker conectando ao PostgreSQL.
3. Testar acesso do worker ao S3 e ao Redis.
4. Publicar manualmente no SNS uma mensagem de um artigo existente e confirmar
   que a SQS a recebe.
5. Deixar o worker ativo e verificar se o artigo chega a `PROCESSADO` e recebe
   tradução.
6. Testar uma falha controlada e verificar a nova tentativa e a DLQ.
7. Só então testar o fluxo completo:
   **formulário → API → S3 → SNS → SQS → worker → RDS**.

A existência dessas funções no código não comprova que a AWS, a rede, as
permissões e o Gemini estejam configurados. Isso ainda precisa ser confirmado
na execução.
