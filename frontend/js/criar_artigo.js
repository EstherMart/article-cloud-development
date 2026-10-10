// Tela criar_artigo.html: envia o formulário e o PDF em multipart.
exigirLogin();

const TAMANHO_MAXIMO_MB = 20;
const autores = criarChips('autor', 'lista-autores');
const tags = criarChips('tag', 'lista-tags');

// Validação só para ajudar o usuário. A que vale é a do back.
function validarArquivo(arquivo) {
    if (arquivo.type !== 'application/pdf') {
        return 'O arquivo deve ser um PDF.';
    }
    if (arquivo.size > TAMANHO_MAXIMO_MB * 1024 * 1024) {
        return 'O PDF deve ter no máximo ' + TAMANHO_MAXIMO_MB + ' MB.';
    }
    return null;
}

document.getElementById('form-artigo').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    limparAlerta();

    const arquivo = document.getElementById('arquivo').files[0];
    const problema = validarArquivo(arquivo);
    if (problema) {
        mostrarAlerta(problema);
        return;
    }
    if (autores.valores().length === 0) {
        mostrarAlerta('Informe pelo menos um autor.');
        return;
    }

    const dados = new FormData();
    dados.append('title', document.getElementById('titulo').value.trim());
    dados.append('area', document.getElementById('area').value.trim());
    dados.append('abstract', document.getElementById('resumo').value.trim());
    dados.append('authors', JSON.stringify(autores.valores()));
    dados.append('tags', JSON.stringify(tags.valores()));
    dados.append('file', arquivo);

    const botao = document.getElementById('botao-enviar');
    botao.disabled = true;
    try {
        await criarArtigo(dados);
        window.location = 'meus_artigos.html';
    } catch (erro) {
        mostrarAlerta(erro.message);
        botao.disabled = false;
    }
});
