// Funções de acesso à API. Todas as telas usam estas funções, nenhuma chama fetch direto.
// Precisa vir depois de config.js e antes do script da tela:
//   <script src="js/config.js"></script>
//   <script src="js/api.js"></script>
//   <script src="js/artigos.js"></script>
//
// Rotas (ver backend/README.md): GET/POST /articles/, GET/PUT/DELETE /articles/<id>/,
// GET /articles/search/?q=..., GET /articles/<id>/download/

async function apiRequest(path, options = {}) {
    const response = await fetch(API_BASE_URL + path, options);
    if (!response.ok) {
        // TODO: mostrar a mensagem de erro da API na tela.
        throw new Error('Erro ' + response.status + ' em ' + path);
    }
    return response.json();
}

function listarArtigos() {
    return apiRequest('/articles/');
}

function buscarArtigos(termo) {
    return apiRequest('/articles/search/?q=' + encodeURIComponent(termo));
}

function obterArtigo(id) {
    return apiRequest('/articles/' + id + '/');
}

// formData é um FormData com os campos do formulário e o arquivo PDF.
// Não defina Content-Type: o navegador coloca o boundary do multipart sozinho.
function criarArtigo(formData) {
    return apiRequest('/articles/', { method: 'POST', body: formData });
}

function atualizarArtigo(id, dados) {
    return apiRequest('/articles/' + id + '/', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados),
    });
}

function excluirArtigo(id) {
    return apiRequest('/articles/' + id + '/', { method: 'DELETE' });
}

// Devolve a URL pré-assinada do S3. Abra com window.location = url.
function urlDownload(id) {
    return apiRequest('/articles/' + id + '/download/');
}
