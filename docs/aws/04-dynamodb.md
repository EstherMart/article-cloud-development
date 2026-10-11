# 4. DynamoDB

[← 3b. Front no S3](03b-front-s3.md) | [Índice](README.md) | [5. ElastiCache Redis →](05-elasticache.md)

## O que é o DynamoDB
É um banco NoSQL (sem tabelas relacionadas) totalmente gerenciado. Aqui ele guarda o **log de ações** de escrita (criar, atualizar, apagar). Leituras (GET) não são logadas, para o cache valer. Esse log só recebe escritas, e a leitura é por chave.

Caminho: DynamoDB > **Tabelas** > **Criar tabela**.

Os nomes abaixo seguem o console em português. Entre parênteses vai o nome em inglês, caso o seu console esteja em outro idioma. Campo que não aparece aqui fica no valor padrão.

| Campo (inglês) | Valor | O que é e por quê |
|---|---|---|
| Nome da tabela (Table name) | `logs_crud` | Vai para `DYNAMODB_TABLE` |
| Chave de partição (Partition key) | `article_id`, tipo **String** | Agrupa todo o histórico de um artigo. **Tem de ser String:** o código grava `str(article_id)`. Com tipo Número, toda gravação falha e o erro some no log |
| Chave de classificação (Sort key) | `timestamp`, tipo **String** | Ordena as ações no tempo. O formato ISO 8601 ordena certo como texto |
| Configurações da tabela (Table settings) | **Personalizar configurações** (Customize settings) | Permite escolher a capacidade |
| Classe da tabela (Table class) | **DynamoDB Standard** | A classe comum |
| Modo de capacidade (Capacity mode) | **Sob demanda** (On-demand) | Paga só por uso. Parada, custa zero. O modo "provisionado" cobra por hora mesmo sem uso |
| Índices secundários (Secondary indexes) | nenhum | Não precisamos |
| Criptografia em repouso (Encryption at rest) | **De propriedade do Amazon DynamoDB** | Padrão e sem custo |
| Proteção contra exclusão (Deletion protection) | **desligada** | Permite apagar no fim |
| Tags | nenhuma | Opcional |

Clique em **Criar tabela**. No `.env`: `DYNAMODB_TABLE=logs_crud`.

A chave (`article_id` String + `timestamp` String) é a que o código `services/dynamo_log.py` usa. Não mude os tipos.

## Como o código grava (`backend/articles/services/dynamo_log.py`)
- `log_action(action, article_id, data)`: `put_item` com `article_id` (texto), `timestamp` (UTC, ISO 8601), `action` (CREATE, UPDATE ou DELETE) e `data` (o artigo em dict).
- Os dados do artigo só têm texto, inteiros e listas, então não há problema com `float`.
- **Falha de log não derruba o CRUD e não aparece para o usuário.** Se a tabela não existir, tiver outro nome ou outra chave, a API continua funcionando e **nenhum log é gravado**. O erro só aparece em `journalctl -u api` (`Não foi possível gravar o log`). Depois de criar a tabela, sempre cadastre um artigo e confira o item.

## Testar no console
1. Tabela > **Explorar itens da tabela** > **Criar item**.
2. Preencha `article_id` = `1` (texto), `timestamp` = `2026-10-09T12:00:00`, e um atributo `action` = `CREATE`.
3. Clique em **Executar** (Scan). O item deve aparecer.
4. Depois de implementar, cadastre um artigo pela API e confira que surge um item novo.

## Apagar
Tabela > **Excluir**. Desmarque a criação de backup.

## Por que configuramos assim (estudo para a arguição)

| Configuração | Motivo |
|---|---|
| NoSQL | O log só recebe escritas e leituras por chave. Não precisa de JOIN |
| Partição `article_id` | Reúne todo o histórico de um artigo. Consulta rápida por artigo |
| Ordenação `timestamp` (ISO 8601) | Ordena as ações no tempo. O formato ISO ordena corretamente como texto |
| On-demand | Sem capacidade para dimensionar nem custo fixo. Combina com tráfego imprevisível |
| Tabela separada do RDS | O log sobrevive ao DELETE do artigo. Serve de auditoria |
| Falha do log não derruba o CRUD | O log é secundário. O usuário não deve ver erro por causa dele |
| `Decimal` em vez de `float` | O DynamoDB rejeita `float` |

Pergunta provável: "Por que o log não fica no RDS?" Porque cada leitura e escrita já pesa no RDS. O log cresce sem parar e não precisa de relações. O DynamoDB isola essa carga.

---
[← 3b. Front no S3](03b-front-s3.md) | [Índice](README.md) | [5. ElastiCache Redis →](05-elasticache.md)
