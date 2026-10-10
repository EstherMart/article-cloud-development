# frontend/js

JavaScript puro, sem build. Ordem de carregamento em cada tela:
`config.js`, `auth.js`, `api.js`, `ui.js`, `nav.js` e o script da tela.

| Arquivo | Função |
|---|---|
| `config.js` | URL base da API (`API_BASE_URL`) |
| `auth.js` | Sessão (token e usuário no `localStorage`) |
| `api.js` | Todas as chamadas à API. Nenhuma tela usa `fetch` direto |
| `ui.js` | Alerta de erro, badge de status, card de artigo e campo de chips |
| `nav.js` | Barra de navegação (muda com o login) |
| `artigos.js`, `artigo.js`, `meus_artigos.js` | Listagem, detalhe e área do usuário |
| `criar_artigo.js`, `editar_artigo.js` | Formulários de artigo |
| `login.js`, `cadastro.js` | Autenticação |

No envio do PDF o `FormData` não define `Content-Type`: o navegador coloca o boundary do multipart. O download vem de uma URL pré-assinada do S3, obtida em `/articles/<id>/download/`.
