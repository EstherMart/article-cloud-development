// Tela artigo.html?id=N: detalhe, tradução e download do PDF.
const idArtigo = new URLSearchParams(location.search).get('id');

function textoTraducao(artigo) {
    if (artigo.processing_status === 'PROCESSADO' && artigo.translated_abstract) {
        return artigo.translated_abstract;
    }
    if (artigo.processing_status === 'ERRO') {
        return 'Não foi possível traduzir este resumo.';
    }
    return 'Tradução em processamento. Recarregue a página em instantes.';
}

async function carregarArtigo() {
    try {
        const artigo = await obterArtigo(idArtigo);
        document.title = artigo.title;
        document.getElementById('titulo').textContent = artigo.title;
        document.getElementById('status').innerHTML = badgeStatus(artigo.processing_status);
        document.getElementById('autores').textContent = artigo.authors.join(', ');
        document.getElementById('area').textContent = artigo.area + ' · enviado por ' + artigo.user;
        document.getElementById('tags').innerHTML = badgesTags(artigo.tags);
        document.getElementById('resumo').textContent = artigo.abstract || 'Sem resumo.';
        document.getElementById('traducao').textContent = textoTraducao(artigo);
        document.getElementById('artigo').hidden = false;
    } catch (erro) {
        mostrarAlerta(erro.message);
    }
}

document.getElementById('botao-download').addEventListener('click', async () => {
    try {
        window.location = await urlDownload(idArtigo);
    } catch (erro) {
        mostrarAlerta(erro.message);
    }
});

carregarArtigo();
