# 1. RDS PostgreSQL

[← 0. Preparação: Security Groups e variáveis](00-preparacao.md) | [Índice](README.md) | [2. EC2 da API →](02-ec2-api.md)

## O que é o RDS
É o banco de dados gerenciado da AWS. A AWS cuida da instalação, dos patches e da máquina. Nós só usamos o PostgreSQL. Aqui ficam os metadados dos artigos (título, autores, status).

Caminho: RDS > **Bancos de dados** > **Criar banco de dados**.

Os nomes abaixo seguem o console em português. Entre parênteses vai o nome em inglês, caso o seu console esteja em outro idioma. Campo que não aparece aqui fica no valor padrão.

| Campo (inglês) | Valor | O que é e por quê |
|---|---|---|
| Método de criação (Creation method) | **Criação padrão** (Standard create) | Mostra todas as opções. A "Criação fácil" escolhe por você e traz problemas (ver aviso abaixo) |
| Tipo de mecanismo (Engine type) | **PostgreSQL** | Não use "Aurora": é outro produto, mais caro, fora do que a spec descreve |
| Versão do mecanismo (Engine version) | a padrão sugerida | A versão 17 funciona com o nosso `psycopg2` |
| Modelos (Templates) | **Desenvolvimento/Teste** (Dev/Test) | Opções de laboratório, sem os recursos caros de produção |
| Disponibilidade e durabilidade (Availability) | **Instância de banco de dados única** (Single-AZ) | Uma só zona. Multi-AZ dobra o custo e não precisamos disso aqui |
| Identificador da instância (DB instance identifier) | `artigos-rds` | Só o nome do recurso na AWS |
| Nome de usuário principal (Master username) | `postgres` | O usuário administrador. Vai para `DB_USER` |
| Gerenciamento de credenciais (Credentials management) | **Autogerenciada** (Self managed) | Você define a senha. Evita o Secrets Manager, que cobra |
| Senha principal (Master password) | uma senha nova, só sua | Vai para `DB_PASSWORD`. Guarde fora do git. A AWS não a mostra de novo |
| Configuração da instância (Instance configuration) | **Classes com capacidade de intermitência** (Burstable), `db.t3.micro` | A menor e mais barata. Basta para o laboratório |
| Tipo de armazenamento (Storage type) | **SSD de uso geral** (gp2 ou gp3) | Disco comum |
| Armazenamento alocado (Allocated storage) | `20` GiB | O mínimo. Mais disco custa mais |
| Ativar escalabilidade automática do armazenamento (Storage autoscaling) | **desligado** | Evita o disco crescer e cobrar sem você perceber |
| Recurso de computação (Compute resource) | **Não se conectar a um recurso de computação do EC2** | Nós configuramos a rede à mão pelo Security Group |
| Tipo de rede (Network type) | IPv4 | Padrão |
| Nuvem privada virtual, VPC | a padrão (default) | A mesma rede da EC2 |
| Grupo de sub-redes de banco de dados (DB subnet group) | o padrão (default) | Define em quais sub-redes o banco pode ficar |
| Acesso público (Public access) | **Não** se você testar só pela EC2. **Sim** só se testar da sua máquina | "Sim" dá um endereço alcançável de fora, mas o Security Group ainda bloqueia quem não é o seu IP |
| Grupo de segurança da VPC (VPC security group) | **Escolher existente** > `sg-rds`. Remova o `default` | É o firewall do banco ([seção 0](00-preparacao.md)) |
| Zona de disponibilidade (Availability Zone) | Sem preferência | A AWS escolhe |
| Autenticação de banco de dados (Database authentication) | **Autenticação de senha** (Password authentication) | O Django entra com usuário e senha. **Não use "somente IAM"**: não existe senha e o código não funciona |
| Insights de performance (Performance Insights) | **desligado** | Recurso extra que pode cobrar |
| Monitoramento avançado (Enhanced Monitoring) | **desligado** | Recurso extra que pode cobrar |
| Configuração adicional > Nome do banco de dados inicial (Initial database name) | `metadata` | Cria o banco `metadata` junto. Sem isso, o RDS só cria o `postgres`. Vai para `DB_NAME` |
| Configuração adicional > Grupo de parâmetros (Parameter group) | o padrão | Sem ajustes |
| Configuração adicional > Backup automatizado (Automated backups) | **desligado** | Backup ocupa disco e cobra. Não precisamos |
| Configuração adicional > Criptografia (Encryption) | padrão | Já vem ligada, sem custo |
| Configuração adicional > Atualização automática de versão secundária (Auto minor version upgrade) | pode desligar | Evita reinício inesperado |
| Configuração adicional > Proteção contra exclusão (Deletion protection) | **desligada** | Se ficar ligada, você não consegue apagar no fim do dia e continua pagando |

Clique em **Criar banco de dados**. Espere o status **Disponível** (5 a 10 minutos). Abra a instância e copie o **Endpoint** (aba **Conectividade e segurança**). Ele vai para `DB_HOST`.

**Aviso sobre a "Criação fácil/expressa" (Aurora Serverless):** ela escolhe "somente IAM", sem VPC e com capacidade até 16 ACU. Isso quebra o nosso projeto e pode custar caro. Se o console oferecer só esse modelo, me avise.

## Configurar o código
```
DB_HOST=<endpoint>
DB_NAME=metadata
DB_USER=postgres
DB_PASSWORD=<sua senha>
DB_PORT=5432
DB_SSLMODE=require
```

O `settings.py` já lê essas variáveis. Nenhuma mudança de código é necessária.

## Testar
1. No terminal: `cd backend && source .venv/bin/activate && set -a; source .env; set +a`.
2. Teste a rede: `nc -zv "$DB_HOST" 5432`. Deve dizer "succeeded".
3. Rode `python manage.py migrate`. Deve listar as migrations `articles.0001` a `0004` como `OK`.
4. Suba a API (`python manage.py runserver`) e crie o usuário pela própria API: `curl -X POST localhost:8000/auth/register/ -H 'Content-Type: application/json' -d '{"username":"teste","password":"senha-forte-123"}'`.
5. Faça login em `/auth/login/`, pegue o token e cadastre um artigo com o `curl` do `backend/README.md`.
6. Pare e suba a API de novo. `GET /articles/` deve devolver o artigo. Isso prova que ele foi para o RDS.

### Artigos de demonstração (migration 0005)
O `migrate` também cria **12 artigos de demonstração**, dono `demo`, para a busca da arguição (migration `0005_artigos_de_demonstracao`). Eles nascem sem PDF. Para enviar os PDFs ao S3 (de várias páginas), depois do bucket criado:

```
python manage.py carregar_demo_pdfs
```

- `SEED_DEMO_DATA=0` no `.env` desliga a criação. Sem a variável, ela fica ligada.
- `DEMO_USER_PASSWORD` no `.env` (opcional) permite entrar como `demo` para editar, apagar e reprocessar. Sem ela, ninguém entra como `demo`.
- Todos nascem `PROCESSADO`, com a tradução em inglês pronta: o site já abre com lista, busca e detalhe funcionando. O worker e o reprocessamento se mostram cadastrando um artigo novo pelo front.
- Os artigos entram direto no banco, sem passar pela API: não geram log no DynamoDB, mensagem no SNS nem chave no Redis. O `carregar_demo_pdfs` também apaga o cache de lista e busca, para o site não mostrar uma lista antiga.
- Desfazer: `python manage.py migrate articles 0004` apaga só os artigos de demonstração.
- Antes do `carregar_demo_pdfs`, o download desses artigos devolve 404 (`Arquivo inexistente`). Isso é esperado.

Opcional: conectar com o `psql` para olhar o banco por dentro. O `global-bundle.pem` é o certificado raiz da AWS e não vai para o git (o `.gitignore` já ignora `*.pem`).

```
export RDSHOST="<endpoint-do-rds>"
psql "host=$RDSHOST port=5432 dbname=metadata user=postgres sslmode=require"
```

No console: RDS > sua instância > aba **Monitoring**. O gráfico **DatabaseConnections** sobe quando a API conecta.

## Erros comuns
| Erro | Causa |
|---|---|
| Timeout | Security Group ou Public access |
| `password authentication failed` | Usuário ou senha errados |
| `database "..." does not exist` | Falta criar o banco (passo 10) |
| Tabelas criadas no SQLite | `DB_HOST` vazio ou `.env` não carregado |
| Senha cortada ou `FATAL: password authentication failed` mesmo certa | A senha tem caractere especial e o `source .env` a leu errado. Use só letras e números |

## Apagar
RDS > **Bancos de dados** > selecione > **Ações > Excluir**. Desmarque "Criar snapshot final" e "Reter backups automatizados". Confirme digitando `delete me`.

## Por que configuramos assim (estudo para a arguição)

| Configuração | Motivo |
|---|---|
| PostgreSQL | Modelo relacional: artigo, autor e tag têm relação N:N. A busca usa JOIN |
| Single-AZ, `db.t3.micro` | É um laboratório. Multi-AZ dobra o custo. Em produção, usaríamos Multi-AZ para tolerar falha de zona |
| `sg-rds` aceita 5432 só do `sg-api` | Princípio do menor privilégio: o banco não fica exposto à internet |
| Public access desligado | Reduz a superfície de ataque. Só a aplicação acessa |
| `DB_SSLMODE=require` | Criptografa a senha e os dados em trânsito |
| Senha no `.env`, fora do git | Segredo nunca vai para o repositório. Em produção, usaríamos o Secrets Manager |
| Variáveis de ambiente | O mesmo código roda local (SQLite) e na nuvem (RDS), sem alterar o `settings.py` |
| Migrations versionadas | O esquema do banco é reproduzível: `migrate` recria tudo em um RDS novo |
| `title` único e `CASCADE` | Evitam duplicata e registro órfão |

Perguntas prováveis:
- "O que acontece se o RDS cair?" A API devolve erro 500 nas rotas que usam o banco. Com Multi-AZ, a AWS faz failover para a réplica.
- "Por que o RDS não é público?" Para que só a EC2 acesse. Qualquer pessoa na internet tentaria força bruta.

---
[← 0. Preparação: Security Groups e variáveis](00-preparacao.md) | [Índice](README.md) | [2. EC2 da API →](02-ec2-api.md)
