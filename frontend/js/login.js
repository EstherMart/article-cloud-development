// Tela login.html: autentica e guarda o token.
document.getElementById('form-login').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    limparAlerta();
    try {
        const dados = await entrar(
            document.getElementById('usuario').value.trim(),
            document.getElementById('senha').value
        );
        salvarSessao(dados.token, dados.username);
        window.location = 'meus_artigos.html';
    } catch (erro) {
        mostrarAlerta(erro.message);
    }
});
