// Tela editar_artigo.html?id=N: carrega o artigo e salva as alterações (PUT).
exigirLogin();

const idArtigo = new URLSearchParams(location.search).get('id');
const autores = criarChips('autor', 'lista-autores');
const tags = criarChips('tag', 'lista-tags');

async function carregarArtigo() {
    try {
        const artigo = await obterArtigo(idArtigo);
        document.getElementById('titulo').value = artigo.title;
        document.getElementById('area').value = artigo.area;
        document.getElementById('resumo').value = artigo.abstract;
        autores.definir(artigo.authors);
        tags.definir(artigo.tags);
    } catch (erro) {
        mostrarAlerta(erro.message);
    }
}

document.getElementById('form-editar').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    limparAlerta();

    const botao = document.getElementById('botao-enviar');
    botao.disabled = true;
    try {
        await atualizarArtigo(idArtigo, {
            title: document.getElementById('titulo').value.trim(),
            area: document.getElementById('area').value.trim(),
            abstract: document.getElementById('resumo').value.trim(),
            authors: autores.valores(),
            tags: tags.valores(),
        });
        window.location = 'meus_artigos.html';
    } catch (erro) {
        mostrarAlerta(erro.message);
        botao.disabled = false;
    }
});

carregarArtigo();
