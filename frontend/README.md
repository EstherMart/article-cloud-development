# Frontend

Telas estáticas em HTML com Bootstrap e JavaScript puro. Não há build. Sirva a pasta por HTTP (abrir o arquivo direto no navegador não funciona com o login):

```
cd frontend
python3 -m http.server 8080
```

Com a API no ar (ver README da raiz), abra `http://127.0.0.1:8080`.

## Telas

| Arquivo | Tela | Exige login |
|---|---|---|
| `index.html` | Home com busca | não |
| `login.html`, `cadastro.html` | Entrar e criar conta | não |
| `artigos.html` | Lista e busca (`?busca=termo`) | não |
| `artigo.html?id=N` | Detalhe, status, tradução e download do PDF | não |
| `meus_artigos.html` | Artigos do usuário, com editar e excluir | sim |
| `criar_artigo.html` | Novo artigo com PDF, autores e palavras-chave | sim |
| `editar_artigo.html?id=N` | Edição dos metadados | sim |

## Configuração

A URL da API fica em `js/config.js` (`API_BASE_URL`). O front roda em outra origem que a API, então a origem do front precisa estar em `CORS_ALLOWED_ORIGINS` no backend. Se mudar a porta do front, ajuste essa variável.

## Contrato esperado da API

Além das rotas de `/articles/` (ver `backend/README.md`):

| Rota | Corpo | Resposta |
|---|---|---|
| `POST /auth/register/` | `{username, email, password}` | 201 |
| `POST /auth/login/` | `{username, password}` | `{token, username}` |

As demais chamadas enviam `Authorization: Token <token>`. Erros da API vêm como `{"erro": "..."}` e aparecem num alerta na tela.
