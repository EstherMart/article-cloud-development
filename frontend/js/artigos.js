// Tela artigos.html: lista todos os artigos ou o resultado da busca (?busca=termo).
async function carregarArtigos() {
    const termo = (new URLSearchParams(location.search).get('busca') || '').trim();
    document.getElementById('campo-busca').value = termo;
    document.getElementById('texto-pesquisa').textContent = termo ? 'Resultados para "' + termo + '"' : '';

    try {
        const artigos = termo ? await buscarArtigos(termo) : await listarArtigos();
        document.getElementById('lista_artigos').innerHTML = listaDeCards(artigos, 'Nenhum artigo encontrado.');
    } catch (erro) {
        mostrarAlerta(erro.message);
    }
}

carregarArtigos();
