// Sessão do usuário no navegador: token e username ficam no localStorage.
// Endpoints esperados do back: POST /auth/register/ e POST /auth/login/ (ver README.md).

const CHAVE_SESSAO = 'sessao';

function lerSessao() {
    try {
        return JSON.parse(localStorage.getItem(CHAVE_SESSAO));
    } catch (erro) {
        return null;
    }
}

function salvarSessao(token, username) {
    localStorage.setItem(CHAVE_SESSAO, JSON.stringify({ token, username }));
}

function sair() {
    localStorage.removeItem(CHAVE_SESSAO);
    window.location = 'index.html';
}

function usuarioLogado() {
    const sessao = lerSessao();
    return sessao ? sessao.username : null;
}

// Telas que exigem login chamam esta função antes de qualquer outra coisa.
function exigirLogin() {
    if (!lerSessao()) {
        window.location = 'login.html';
    }
}
