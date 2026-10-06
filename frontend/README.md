# Frontend

Telas estáticas em HTML com Bootstrap e CSS próprio. Não há build: abra os arquivos no navegador ou sirva a pasta (`python -m http.server` dentro de `frontend/`).

## Telas

| Arquivo | Tela |
|---|---|
| `index.html` | Home |
| `cadastro.html` | Cadastro de usuário |
| `login.html` | Login |
| `perfil.html` | Perfil |
| `artigos.html` | Lista e busca de artigos |
| `artigo.html` | Detalhe do artigo (só o layout inicial) |
| `criar_artigo.html` | Formulário de novo artigo com PDF |
| `editar_artigo.html` | Edição de artigo |
| `meus_artigos.html` | Artigos do usuário |
| `css/style.css` | Estilos |

## Pendente

- Os HTMLs referenciam scripts que ainda não existem: `js/artigos.js`, `js/criar_artigo.js`, `js/editar_artigo.js` e `js/meus_artigos.js`. Falta criar a pasta `js/` e ligar os formulários à API (`fetch`).
- A tela de detalhe (`artigo.html`) não tem formulário nem script.
- Definir a URL base da API em um único lugar (por exemplo `js/config.js`), para trocar entre local e o ALB.
- O back não tem login ainda. Decidir como a autenticação funciona antes de ligar `login.html` e `cadastro.html`.
- Se o front for aberto de outra origem que a API, o back precisará de CORS.
