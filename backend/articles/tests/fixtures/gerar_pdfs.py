"""Gera os PDFs de exemplo da pasta pdfs/ sem dependências externas.

Uso: python gerar_pdfs.py

Os PDFs servem para testar o upload no S3, a extração de texto do worker e as
validações da API. O texto fica em fonte padrão (Helvetica), então pypdf extrai.
"""
from pathlib import Path

PASTA = Path(__file__).parent / 'pdfs'

ARTIGOS = {
    'artigo_nuvem.pdf': (
        'Computação em Nuvem para Repositórios Acadêmicos',
        [
            'Resumo',
            'Este trabalho descreve uma arquitetura em nuvem para armazenar e consultar',
            'artigos acadêmicos. Os metadados ficam em banco relacional, o arquivo em',
            'armazenamento de objetos e as consultas frequentes em cache.',
            '',
            'Palavras-chave: nuvem, AWS, armazenamento, cache.',
        ],
    ),
    'artigo_mensageria.pdf': (
        'Processamento Assíncrono com Filas',
        [
            'Resumo',
            'A API publica um evento a cada novo artigo e responde ao usuário sem esperar.',
            'Um worker consome a fila, extrai o texto do PDF e traduz o resumo.',
            'Mensagens que falham três vezes seguem para uma fila de descarte.',
            '',
            'Palavras-chave: SNS, SQS, worker, idempotência.',
        ],
    ),
    'artigo_banco_de_dados.pdf': (
        'Modelagem de Dados para Artigos e Autores',
        [
            'Resumo',
            'O modelo relaciona artigos, autores e palavras-chave por tabelas de ligação.',
            'O título é único para evitar cadastros duplicados do mesmo trabalho.',
            '',
            'Palavras-chave: PostgreSQL, modelagem, relação N:N.',
        ],
    ),
}


def escapar(texto):
    return texto.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def montar_pdf(conteudo_pagina):
    """Monta um PDF de uma página. `conteudo_pagina` é o fluxo de operadores da página."""
    stream = conteudo_pagina.encode('cp1252')
    objetos = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R '
        b'/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>',
        b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>',
    ]
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


def pagina_com_texto(titulo, linhas):
    partes = ['BT /F2 18 Tf 60 780 Td (%s) Tj ET' % escapar(titulo)]
    y = 740
    for linha in linhas:
        if linha:
            partes.append('BT /F1 12 Tf 60 %d Td (%s) Tj ET' % (y, escapar(linha)))
        y -= 20
    return '\n'.join(partes)


def main():
    PASTA.mkdir(exist_ok=True)
    for nome, (titulo, linhas) in ARTIGOS.items():
        (PASTA / nome).write_bytes(montar_pdf(pagina_com_texto(titulo, linhas)))

    # Simula PDF escaneado: só desenho, sem texto. O worker deve usar o resumo digitado.
    (PASTA / 'escaneado_sem_texto.pdf').write_bytes(
        montar_pdf('0.8 g 60 600 475 150 re f\n0 g 60 600 475 150 re S')
    )
    # Arquivo que não é PDF, para testar a validação da API (deve ser recusado).
    (PASTA / 'invalido_nao_e_pdf.pdf').write_text('Isto não é um PDF.\n', encoding='utf-8')


if __name__ == '__main__':
    main()
