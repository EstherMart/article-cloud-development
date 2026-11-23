# 6. CI e deploy com GitHub Actions

[← 5. DynamoDB e credenciais](05-dynamodb-e-credenciais.md) | [Índice](README.md) | [7. Estudo para a arguição →](07-estudo-arguicao.md)

Arquivo: `.github/workflows/deploy.yml`. Não é exigido pela spec (que só pede subir os serviços por Compose, opcionalmente numa VM da AWS), mas é o que faz a "correção online" funcionar sem entrar na máquina.

## O que faz

Dispara a cada `push` na branch `main` e roda num **runner self-hosted**, ou seja, num agente instalado na própria máquina/VM onde a aplicação vai rodar (não nos servidores do GitHub). Por isso os comandos `docker compose` atuam direto nos containers dessa máquina.

| Passo | Comando | Para quê |
|---|---|---|
| Checkout | `actions/checkout@v4` | Baixa o código na máquina do runner |
| Configurar `.env` | `printf "%s\n" "${{ secrets.ENV_FILE }}" > .env` | O `.env` inteiro mora num *secret* do repositório (`ENV_FILE`), não no Git |
| Derrubar | `docker compose down` | Remove os containers antigos (os volumes ficam, então os dados persistem) |
| Build | `docker compose build` | Gera as imagens com o código novo |
| Subir | `docker compose up -d` | Inicia tudo em segundo plano |
| Migrations | `sleep 5` + `docker compose exec -T backend python manage.py migrate` | Cria/atualiza as tabelas |

`-T` desliga o pseudo-terminal, necessário em CI (não há terminal interativo).

## Segredos

Todo valor sensível (senhas do Postgres, MinIO e RabbitMQ, `GEMINI_API_KEY`, `DJANGO_SECRET_KEY`, credenciais AWS) vai no secret `ENV_FILE` do GitHub, que o pipeline grava como `.env` na máquina. O arquivo não é versionado (está no `.gitignore`).

## Observações

- O `sleep 5` antes do `migrate` é uma espera fixa: se o backend ou o Postgres demorarem mais que isso, o `migrate` falha. O `depends_on` com healthcheck do Postgres reduz o risco, mas o backend não tem healthcheck próprio.
- Esse passo de migrations existe **só no pipeline**. Quem roda `docker compose up` na mão precisa executar o `migrate` também (ver [limitações](07-estudo-arguicao.md#limitações-conhecidas)).
- Não há etapa de testes no pipeline: ele só faz build e deploy.
- O `docker compose down` antes do build causa uma pequena indisponibilidade a cada deploy.

## Perguntas prováveis

1. **O que é um runner self-hosted?** Um agente do GitHub Actions rodando numa máquina sua, em vez de nas do GitHub. Permite acessar o Docker local.
2. **Onde ficam as senhas?** No secret `ENV_FILE` do repositório; o pipeline as grava no `.env` da máquina.
3. **O deploy apaga os dados?** Não: `down` sem `-v` preserva os volumes.
4. **Por que `up -d`?** `-d` (detached) devolve o terminal; sem ele o passo ficaria preso exibindo logs.

[← 5. DynamoDB e credenciais](05-dynamodb-e-credenciais.md) | [Índice](README.md) | [7. Estudo para a arguição →](07-estudo-arguicao.md)
