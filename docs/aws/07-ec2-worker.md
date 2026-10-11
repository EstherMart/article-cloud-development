# 7. EC2 do worker

[← 6. SNS e SQS](06-sns-sqs.md) | [Índice](README.md) | [8. Teste de ponta a ponta e conferência de custos →](08-ponta-a-ponta-e-custos.md)

Crie esta instância só depois de S3, RDS, Redis e SNS/SQS funcionarem, porque o worker usa todos eles. A spec pede o worker em instância própria. Nos testes iniciais, você pode rodá-lo na EC2 da API.

## O que é o worker
É um programa que roda sozinho em uma EC2 separada. Ele fica lendo a fila SQS. Para cada mensagem, baixa o PDF, extrai o texto, traduz o resumo com o **Gemini** (API do Google, fora da AWS) e grava o resultado no RDS. Assim a API responde ao usuário sem esperar esse trabalho pesado.

Caminho: EC2 > **Instâncias** > **Executar instâncias**.

Os nomes abaixo seguem o console em português. Entre parênteses vai o nome em inglês, caso o seu console esteja em outro idioma. Campo que não aparece aqui fica no valor padrão.

| Campo (inglês) | Valor | O que é e por quê |
|---|---|---|
| Nome (Name) | `worker` | Rótulo |
| Imagens de aplicações e de sistemas operacionais (AMI) | **Amazon Linux 2023 AMI** (64 bits, x86) | Igual à API |
| Tipo de instância | `t3.micro` | Basta para o laboratório |
| Par de chaves | `vockey` | Para entrar por SSH |
| Configurações de rede > VPC | a padrão | A mesma rede do RDS e do Redis |
| Configurações de rede > Atribuir IP público automaticamente | **Habilitar** | Precisa de internet para o `pip` e para falar com a AWS |
| Firewall (grupos de segurança) | **Selecionar grupo de segurança existente** > `sg-worker` | Sem porta 8000: o worker não recebe conexões |
| Configurar armazenamento | `8` GiB gp3 (padrão) | Disco comum |
| Detalhes avançados > Perfil da instância do IAM | **LabInstanceProfile** | Permissão para SQS e S3 (a tradução usa o Gemini, não a AWS) |
| Número de instâncias | `1` | Só uma |

Antes de criar, crie o `sg-worker` ([seção 0](00-preparacao.md)) e adicione-o como origem permitida em `sg-rds` (5432) e `sg-redis` (6379).

## Configurar e subir
```
sudo dnf install -y python3.12 python3.12-pip git
git clone <url-do-repo>
cd article-cloud-development-/worker
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
nano ../backend/.env        # DB_*, SQS_QUEUE_URL, REDIS_URL, AWS_REGION, GEMINI_API_KEY e GEMINI_MODEL
set -a; source ../backend/.env; set +a
python worker.py
```

O worker precisa de acesso à internet (HTTPS, porta 443) para falar com o Gemini. A regra de saída padrão do `sg-worker` já permite. Ele **não** lê `S3_BUCKET`: o bucket vem na mensagem.

### Deixar o worker rodando (systemd)
Crie `/etc/systemd/system/worker.service` com o mesmo modelo da API ([etapa 2](02-ec2-api.md)), trocando o `WorkingDirectory` para a pasta `worker`, o `ExecStart` para `<caminho>/worker/.venv/bin/python worker.py` e mantendo `Restart=always`. Ative com `sudo systemctl enable --now worker` e veja os logs com `journalctl -u worker -f`.

### O que pode dar errado
| Sintoma | Causa provável |
|---|---|
| Todo artigo termina em `ERRO` | `GEMINI_API_KEY` ou `GEMINI_MODEL` ausentes, modelo inexistente, chave sem cota ou sem saída para a internet. O log do worker mostra o motivo |
| Artigo fica `PENDENTE` | O worker não está rodando, ou `SQS_QUEUE_URL` aponta para outra fila |
| `psycopg2.OperationalError` | `sg-rds` sem a regra do `sg-worker`, ou senha com caractere especial lida errado pelo `source` |
| O artigo vira `PROCESSADO`, mas a tela mostra o texto antigo | O worker não alcançou o Redis (falta `REDIS_URL` ou regra no `sg-redis`). O cache expira sozinho em 5 minutos |
| PDF escaneado (sem texto) e sem resumo | Não há o que traduzir. O artigo vai para `ERRO`. O worker prefere o resumo digitado; o texto do PDF é só o plano B |
| Mensagem processada duas vezes | Esperado na fila Standard. O resultado é o mesmo |

A chave do Gemini é segredo: fica só no `.env` do worker, fora do git. Se a chave vazar, gere outra.

## Testar
1. Deixe o worker rodando. No SNS, **Publicar mensagem** com `{"article_id": <id de um artigo>, "s3_key": "artigos/<id>.pdf", "bucket": "<bucket>"}`.
2. O log do worker deve mostrar o processamento. No RDS (pela API), o artigo vira `PROCESSADO`.
3. Em SQS > `artigos-fila`, **Messages available** volta a 0 e **Messages in flight** também.
4. Derrube o worker (Ctrl+C) no meio de uma mensagem. Ela deve reaparecer depois do visibility timeout.

## Apagar
EC2 > **Instâncias** > `worker` > **Estado da instância > Encerrar instância**.

---
[← 6. SNS e SQS](06-sns-sqs.md) | [Índice](README.md) | [8. Teste de ponta a ponta e conferência de custos →](08-ponta-a-ponta-e-custos.md)
