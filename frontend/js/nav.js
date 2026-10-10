// Barra de navegação única. Cada tela tem <header id="navbar"></header>.

function desenharNavbar() {
    const usuario = usuarioLogado();
    const links = usuario
        ? '<a href="artigos.html" class="btn btn-outline-primary">Artigos</a>' +
          '<a href="meus_artigos.html" class="btn btn-outline-primary">Meus artigos</a>' +
          '<span class="navbar-text align-self-center">' + escapeHtml(usuario) + '</span>' +
          '<button type="button" id="botao-sair" class="btn btn-outline-secondary">Sair</button>'
        : '<a href="artigos.html" class="btn btn-outline-primary">Artigos</a>' +
          '<a href="login.html" class="btn btn-outline-primary">Login</a>' +
          '<a href="cadastro.html" class="btn btn-primary">Cadastro</a>';

    document.getElementById('navbar').innerHTML =
        '<nav class="navbar"><div class="container">' +
        '<a href="index.html" class="navbar-brand">Repositório de Artigos</a>' +
        '<div class="d-flex gap-2 flex-wrap">' + links + '</div></div></nav>';

    const botaoSair = document.getElementById('botao-sair');
    if (botaoSair) {
        botaoSair.addEventListener('click', sair);
    }
}

desenharNavbar();
