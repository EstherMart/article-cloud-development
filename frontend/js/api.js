// Funções de acesso à API. Todas as telas usam estas funções, nenhuma chama fetch direto.
// Ordem dos scripts: config.js, auth.js, api.js, ui.js, nav.js e o script da tela.
//
// Rotas (ver backend/README.md): GET/POST /articles/, GET/PUT/DELETE /articles/<id>/,
// GET /articles/search/?q=..., GET /articles/<id>/download/, POST /auth/register/ e /auth/login/

async function apiRequest(path, options = {}) {
    const headers = { ...options.headers };
    const sessao = lerSessao();
    if (sessao) {
        headers.Authorization = 'Token ' + sessao.token;
    }

    let response;
    try {
        response = await fetch(API_BASE_URL + path, { ...options, headers });
    } catch (erro) {
        throw new Error('Não foi possível conectar à API.');
    }

    const corpo = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(corpo.erro || 'Erro ' + response.status + ' em ' + path);
    }
    return corpo;
}

function enviarJson(path, metodo, dados) {
    return apiRequest(path, {
        method: metodo,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados),
    });
}

function cadastrarUsuario(username, email, password) {
    return enviarJson('/auth/register/', 'POST', { username, email, password });
}

function entrar(username, password) {
    return enviarJson('/auth/login/', 'POST', { username, password });
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
    return enviarJson('/articles/' + id + '/', 'PUT', dados);
}

function excluirArtigo(id) {
    return apiRequest('/articles/' + id + '/', { method: 'DELETE' });
}

// Devolve a URL pré-assinada do S3. Abra com window.location = url.
async function urlDownload(id) {
    const dados = await apiRequest('/articles/' + id + '/download/');
    return dados.download_url;
}
