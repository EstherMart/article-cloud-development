// Tela cadastro.html: cria a conta e já entra.
document.getElementById('form-cadastro').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    limparAlerta();

    const usuario = document.getElementById('usuario').value.trim();
    const senha = document.getElementById('senha').value;
    if (senha !== document.getElementById('confirmarSenha').value) {
        mostrarAlerta('As senhas não conferem.');
        return;
    }

    try {
        await cadastrarUsuario(usuario, document.getElementById('email').value.trim(), senha);
        const dados = await entrar(usuario, senha);
        salvarSessao(dados.token, dados.username);
        window.location = 'meus_artigos.html';
    } catch (erro) {
        mostrarAlerta(erro.message);
    }
});
