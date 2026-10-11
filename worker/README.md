# Worker

Processa os artigos fora da API. Roda numa EC2 própria, fora do Auto Scaling Group, e não importa o Django: tem o próprio `requirements.txt` e atualiza o RDS com SQL direto.

## O que faz

1. Lê a fila SQS com long polling (20 s), uma mensagem por vez.
2. Marca o artigo como `PROCESSANDO`, baixa o PDF do S3 e extrai o texto com `pypdf`.
3. Traduz para o inglês com o Gemini o resumo digitado no cadastro. Se o resumo estiver vazio, traduz o texto extraído do PDF. PDF escaneado sem resumo não tem o que traduzir e termina em `ERRO`.
4. Grava `translated_abstract` no RDS, marca o artigo como `PROCESSADO` e apaga `artigo:{id}` do Redis.
5. Só então apaga a mensagem da fila.

Se algo falhar, o artigo vira `ERRO` e a mensagem volta à fila. Depois de 3 tentativas ela vai para a DLQ. A mesma mensagem pode chegar duas vezes, e o resultado é o mesmo. O worker aceita a entrega bruta do SNS ou o envelope do SNS.

Mensagem esperada: `{"article_id": 1, "s3_key": "artigos/1.pdf", "bucket": "nome-do-bucket"}`.

## Variáveis de ambiente

| Variável | Uso |
|---|---|
| `AWS_REGION` | Região (padrão `us-east-1`) |
| `SQS_QUEUE_URL` | URL da fila principal |
| `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`, `DB_SSLMODE` | RDS (`DB_SSLMODE` padrão `require`) |
| `REDIS_URL` | Cache a invalidar. Se falhar, só registra no log (o cache expira em 5 minutos) |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Tradução. A chave é segredo: fica só no ambiente do worker |

As credenciais da AWS vêm da IAM Role da instância. O worker precisa de acesso de saída à internet (HTTPS) para falar com o Gemini.

## Rodar

```
cd worker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a; source ../backend/.env; set +a      # mais GEMINI_API_KEY e GEMINI_MODEL
python worker.py
```

## Testes

```
python -m unittest discover -s tests -v                                          # sem AWS e sem Gemini
RUN_GEMINI=1 python -m unittest discover -s tests -p 'test_gemini_real.py' -v    # Gemini de verdade
```

`tests/test_worker.py` cobre a extração (5 e 30 páginas, escaneado, misto, corrompido, acentos) e o resultado do `process()` em cada cenário. `tests/test_gemini_real.py` confere o que a tradução não pode estragar: termos técnicos, números e idioma. Os PDFs vêm de `backend/articles/tests/fixtures/pdfs`.
