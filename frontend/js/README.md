# frontend/js

Scripts das telas. Sem build e sem framework: JavaScript puro.

| Arquivo | Função |
|---|---|
| `config.js` | URL base da API (`API_BASE_URL`). Único lugar onde ela aparece |
| `api.js` | Funções de acesso à API (`listarArtigos`, `criarArtigo`, ...) |
| `artigos.js` | Tela `artigos.html` |
| `criar_artigo.js` | Tela `criar_artigo.html` |
| `editar_artigo.js` | Tela `editar_artigo.html` |
| `meus_artigos.js` | Tela `meus_artigos.html` |

Os scripts das telas só têm comentários com o que fazer. Implemente seguindo os TODOs.

## Como ligar uma tela

Os HTMLs já incluem o script da tela. Falta incluir `config.js` e `api.js` antes dele:

```html
<script src="js/config.js"></script>
<script src="js/api.js"></script>
<script src="js/artigos.js"></script>
```

## Regras

- Nenhuma tela chama `fetch` direto. Todas usam `api.js`.
- No envio do PDF use `FormData` e não defina `Content-Type`.
- O download do PDF vem de uma URL pré-assinada do S3, obtida em `/articles/<id>/download/`.
- Quando a API estiver em outra origem, o back precisa de CORS (`django-cors-headers`). Sem isso o navegador bloqueia as chamadas.
- `artigo.html` (detalhe) ainda não tem script. Crie `artigo.js` quando for a vez dela.
