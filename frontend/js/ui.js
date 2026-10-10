// Componentes de tela compartilhados: alerta de erro, badge de status, card de artigo e chips.

const COR_STATUS = {
    PENDENTE: 'secondary',
    PROCESSANDO: 'warning',
    PROCESSADO: 'success',
    ERRO: 'danger',
};

function escapeHtml(texto) {
    const div = document.createElement('div');
    div.textContent = texto;
    return div.innerHTML;
}

// Mostra a mensagem no elemento #alerta da tela.
function mostrarAlerta(mensagem, tipo = 'danger') {
    document.getElementById('alerta').innerHTML =
        '<div class="alert alert-' + tipo + '" role="alert">' + escapeHtml(mensagem) + '</div>';
}

function limparAlerta() {
    document.getElementById('alerta').innerHTML = '';
}

function badgeStatus(status) {
    return '<span class="badge text-bg-' + (COR_STATUS[status] || 'secondary') + '">' + escapeHtml(status) + '</span>';
}

function badgesTags(tags) {
    return tags.map((tag) => '<span class="badge text-bg-light border me-1">' + escapeHtml(tag) + '</span>').join('');
}

// `acoes` é um HTML opcional exibido no rodapé do card (botões de editar e excluir).
function cardArtigo(artigo, acoes = '') {
    return (
        '<div class="card mb-3"><div class="card-body">' +
        '<div class="d-flex justify-content-between align-items-start gap-2">' +
        '<h5 class="card-title"><a href="artigo.html?id=' + artigo.id + '">' + escapeHtml(artigo.title) + '</a></h5>' +
        badgeStatus(artigo.processing_status) +
        '</div>' +
        '<p class="text-muted mb-2">' + escapeHtml(artigo.authors.join(', ')) + ' · ' + escapeHtml(artigo.area) + '</p>' +
        '<div>' + badgesTags(artigo.tags) + '</div>' +
        (acoes ? '<div class="mt-3 d-flex gap-2">' + acoes + '</div>' : '') +
        '</div></div>'
    );
}

function listaDeCards(artigos, vazio, acoesPorArtigo) {
    if (artigos.length === 0) {
        return '<p class="text-muted">' + vazio + '</p>';
    }
    return artigos.map((artigo) => cardArtigo(artigo, acoesPorArtigo ? acoesPorArtigo(artigo) : '')).join('');
}

// Campo de lista em chips (autores, tags). Enter ou vírgula adiciona, o × remove.
// HTML esperado: <input id="{inputId}"> e <div id="{listaId}"></div>.
function criarChips(inputId, listaId) {
    const input = document.getElementById(inputId);
    const lista = document.getElementById(listaId);
    let valores = [];

    function desenhar() {
        lista.innerHTML = valores
            .map((valor, i) =>
                '<span class="badge text-bg-primary me-1 mb-1 fs-6 fw-normal">' + escapeHtml(valor) +
                ' <button type="button" class="btn-close btn-close-white ms-1" data-remover="' + i + '" aria-label="Remover"></button></span>')
            .join('');
    }

    function adicionar() {
        const valor = input.value.replace(/,/g, '').trim();
        if (valor && !valores.includes(valor)) {
            valores.push(valor);
            desenhar();
        }
        input.value = '';
    }

    input.addEventListener('keydown', (evento) => {
        if (evento.key === 'Enter' || evento.key === ',') {
            evento.preventDefault();
            adicionar();
        }
    });
    input.addEventListener('blur', adicionar);
    lista.addEventListener('click', (evento) => {
        const indice = evento.target.dataset.remover;
        if (indice !== undefined) {
            valores.splice(Number(indice), 1);
            desenhar();
        }
    });

    return {
        valores() {
            adicionar();
            return valores;
        },
        definir(novos) {
            valores = [...novos];
            desenhar();
        },
    };
}
