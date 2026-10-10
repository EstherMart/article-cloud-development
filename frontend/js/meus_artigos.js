// Tela meus_artigos.html: artigos do usuário logado, com editar e excluir.
exigirLogin();

const lista = document.getElementById('lista_artigos');

function acoesDoArtigo(artigo) {
    return (
        '<a href="editar_artigo.html?id=' + artigo.id + '" class="btn btn-sm btn-outline-primary">Editar</a>' +
        '<button type="button" class="btn btn-sm btn-outline-danger" data-excluir="' + artigo.id + '">Excluir</button>'
    );
}

async function carregarMeusArtigos() {
    try {
        const todos = await listarArtigos();
        const meus = todos.filter((artigo) => artigo.user === usuarioLogado());
        lista.innerHTML = listaDeCards(meus, 'Você ainda não cadastrou artigos.', acoesDoArtigo);
    } catch (erro) {
        mostrarAlerta(erro.message);
    }
}

lista.addEventListener('click', async (evento) => {
    const id = evento.target.dataset.excluir;
    if (!id || !confirm('Excluir este artigo? O PDF também será apagado.')) {
        return;
    }
    limparAlerta();
    try {
        await excluirArtigo(id);
        carregarMeusArtigos();
    } catch (erro) {
        mostrarAlerta(erro.message);
    }
});

carregarMeusArtigos();
