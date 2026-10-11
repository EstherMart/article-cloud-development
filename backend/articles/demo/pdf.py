"""Gerador de PDFs de demonstração, sem dependências externas.

Gera PDFs de várias páginas com texto em fonte padrão (Helvetica), que o `pypdf` do worker
consegue extrair. Usado pelo comando `carregar_demo_pdfs` e pelos PDFs de teste do worker.
"""
import textwrap

LARGURA_LINHA = 88
ALTURA_PAGINA = 842
TOPO = 790
BASE = 60
ENTRELINHA = 14


def escapar(texto):
    return texto.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _stream(texto):
    return texto.encode('cp1252', errors='replace')


def montar_pdf(paginas):
    """Monta um PDF. `paginas` é uma lista com o fluxo de operadores de cada página."""
    total = len(paginas)
    primeiro_conteudo = 3 + total
    objetos = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        ('<< /Type /Pages /Kids [%s] /Count %d >>' % (
            ' '.join('%d 0 R' % (3 + i) for i in range(total)), total)).encode(),
    ]
    for i in range(total):
        objetos.append((
            '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents %d 0 R '
            '/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> >>'
            % (primeiro_conteudo + i, primeiro_conteudo + total, primeiro_conteudo + total + 1)
        ).encode())
    for pagina in paginas:
        corpo = _stream(pagina)
        objetos.append(b'<< /Length %d >>\nstream\n' % len(corpo) + corpo + b'\nendstream')
    objetos.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
    objetos.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>')

    saida = bytearray(b'%PDF-1.4\n')
    offsets = []
    for numero, corpo in enumerate(objetos, start=1):
        offsets.append(len(saida))
        saida += b'%d 0 obj\n' % numero + corpo + b'\nendobj\n'
    inicio_xref = len(saida)
    saida += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objetos) + 1)
    for offset in offsets:
        saida += b'%010d 00000 n \n' % offset
    saida += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objetos) + 1, inicio_xref)
    return bytes(saida)


def _linha(fonte, tamanho, y, texto):
    return 'BT /%s %d Tf 60 %d Td (%s) Tj ET' % (fonte, tamanho, y, escapar(texto))


def documento(titulo, secoes, rodape=True):
    """PDF com título, seções e parágrafos quebrados em linhas, paginado automaticamente.

    `secoes` é uma lista de (titulo_da_secao ou None, [parágrafos]).
    """
    itens = [('t', titulo, 0)]
    for cabecalho, paragrafos in secoes:
        if cabecalho:
            itens.append(('h', cabecalho, 10))
        for paragrafo in paragrafos:
            linhas = textwrap.wrap(paragrafo, LARGURA_LINHA) or ['']
            for numero, linha in enumerate(linhas):
                itens.append(('p', linha, 8 if numero == len(linhas) - 1 else 0))

    paginas, atual, y = [], [], TOPO
    for tipo, texto, depois in itens:
        tamanho, fonte, passo = {'t': (18, 'F2', 30), 'h': (13, 'F2', 20), 'p': (11, 'F1', ENTRELINHA)}[tipo]
        if y - passo < BASE:
            paginas.append(atual)
            atual, y = [], TOPO
        atual.append(_linha(fonte, tamanho, y, texto))
        y -= passo + depois
    paginas.append(atual)

    total = len(paginas)
    if rodape:
        for numero, operadores in enumerate(paginas, start=1):
            operadores.append(_linha('F1', 9, 30, 'Página %d de %d' % (numero, total)))
    return montar_pdf(['\n'.join(operadores) for operadores in paginas])


def documento_sem_texto(paginas=3):
    """Simula PDF escaneado: só desenho, sem camada de texto."""
    desenho = '0.8 g 60 300 475 400 re f\n0 g 60 300 475 400 re S'
    return montar_pdf([desenho] * paginas)


def documento_misto(titulo, texto_inicial, texto_final):
    """Três páginas: texto, só desenho (escaneada) e texto de novo."""
    pagina_1 = '\n'.join([_linha('F2', 18, TOPO, titulo)] + [
        _linha('F1', 11, TOPO - 40 - i * ENTRELINHA, linha)
        for i, linha in enumerate(textwrap.wrap(texto_inicial, LARGURA_LINHA))
    ])
    pagina_2 = '0.8 g 60 300 475 400 re f\n0 g 60 300 475 400 re S'
    pagina_3 = '\n'.join(
        _linha('F1', 11, TOPO - i * ENTRELINHA, linha)
        for i, linha in enumerate(textwrap.wrap(texto_final, LARGURA_LINHA))
    )
    return montar_pdf([pagina_1, pagina_2, pagina_3])
