"""Gera os PDFs de teste de pdfs/ (todos com mais de uma página, sem dependências externas).

Uso: python gerar_pdfs.py. A tabela de cenários está em README.md.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BACKEND))

from articles.demo.artigos import ARTIGOS, PARAGRAFOS, PARAGRAFOS_EN, secoes_demo  # noqa: E402
from articles.demo.pdf import documento, documento_misto, documento_sem_texto  # noqa: E402

PASTA = Path(__file__).parent / 'pdfs'


def demo(indice):
    artigo = ARTIGOS[indice]
    return documento(artigo['title'], secoes_demo(artigo))


def artigo_longo(paginas_alvo, titulo):
    """Texto corrido em português, repetindo seções numeradas até passar de `paginas_alvo`."""
    secoes = []
    for numero in range(1, 200):
        corpo = [PARAGRAFOS[(numero + i) % len(PARAGRAFOS)] for i in range(3)]
        secoes.append(('Seção %d' % numero, corpo))
        pdf = documento(titulo, secoes)
        if pdf.count(b'/Type /Page ') >= paginas_alvo:
            return pdf
    raise RuntimeError('não chegou ao número de páginas pedido')


def com_paginas(titulo, secoes, pool, minimo):
    """Acrescenta seções do `pool` até o PDF ter pelo menos `minimo` páginas."""
    secoes = list(secoes)
    for numero in range(1, 100):
        pdf = documento(titulo, secoes)
        if pdf.count(b'/Type /Page ') >= minimo:
            return pdf
        secoes.append(('Seção %d' % numero, [pool[(numero + i) % len(pool)] for i in range(2)]))
    raise RuntimeError('não chegou ao número de páginas pedido')


ACENTOS = [
    ('Resumo', [
        'Este trabalho analisa a distribuição de conteúdo em redes de alta disponibilidade. A coleção '
        'tem ação, emissão, inovação, órgão, ônibus, pingüim e coração, para testar acentos e cedilha.',
        'Citação: “o desempenho não é um acaso” – afirmam os autores. Valores: R$ 10,00 (dez reais), '
        '50% de desconto e 3,14159 como constante. Anotações entre parênteses (como esta) e barra \\ também.',
    ]),
    ('Termos técnicos que não devem ser traduzidos', [
        'PostgreSQL, Redis, DynamoDB, Auto Scaling, Application Load Balancer, SQS, SNS, S3, EC2 e RDS.',
        'Siglas: API REST, CRUD, TTL, DLQ, CPU. Identificadores: artigo_nuvem.pdf, artigos/42.pdf, us-east-1.',
    ]),
    ('Conclusão', [
        'A tradução deve manter os termos acima, os números e a pontuação, e trocar apenas o idioma do texto '
        'em volta. Qualquer alteração de “70%” ou de “R$ 10,00” é um erro de tradução.',
    ]),
]

INGLES = [
    ('Abstract', [
        'This paper describes a cloud architecture for an academic repository. Metadata is stored in a '
        'relational database, the files in object storage and frequent queries in an in-memory cache.',
        'The text of this document is already in English. Translating it to English should not change its '
        'meaning, and the system must not fail when the source and the target language are the same.',
    ]),
    ('Conclusion', [
        'Asynchronous processing keeps the API fast, because the heavy work happens in a separate worker.',
    ]),
]

TECNICO = [
    ('Resumo', [
        'Medimos o tempo de resposta de 1.000 requisições com e sem cache. A média caiu de 182 ms para '
        '37 ms (redução de 79,7%), e o p95 de 410 ms para 88 ms. O banco recebeu 12 consultas em vez de 1.000.',
    ]),
    ('Tabela 1 - Resultados', [
        'Cenário | Média (ms) | p95 (ms) | Consultas ao banco',
        'Sem cache | 182 | 410 | 1000',
        'Com cache | 37 | 88 | 12',
        'Com cache e invalidação | 41 | 95 | 37',
    ]),
    ('Configuração', [
        'CPU alvo: 70% para subir e 25% para descer. Instâncias: mínimo 1, máximo 3. TTL do cache: 300 s. '
        'Fila: visibilidade 120 s, long polling 20 s, 3 tentativas antes da DLQ.',
    ]),
]


def main():
    PASTA.mkdir(exist_ok=True)
    arquivos = {
        # Caminho feliz: 2 a 3 páginas, texto em português.
        'artigo_nuvem.pdf': demo(0),
        'artigo_mensageria.pdf': demo(2),
        'artigo_banco_de_dados.pdf': demo(3),
        # Muitas páginas: o worker junta o texto de todas (quando não há resumo digitado).
        'artigo_longo_5_paginas.pdf': artigo_longo(5, 'Repositórios de Artigos na Nuvem: Estudo Completo'),
        'artigo_muito_longo_30_paginas.pdf': artigo_longo(30, 'Anais Completos: Computação em Nuvem'),
        # Conteúdo que a tradução pode estragar.
        'artigo_acentos_e_simbolos.pdf': com_paginas('Acentuação, Símbolos e Termos Técnicos', ACENTOS, PARAGRAFOS, 3),
        'artigo_tecnico_numeros_e_tabela.pdf': com_paginas('Desempenho do Cache em Números', TECNICO, PARAGRAFOS, 2),
        'artigo_em_ingles.pdf': com_paginas('Cloud Architecture for an Academic Repository', INGLES, PARAGRAFOS_EN, 2),
        # PDF com texto em algumas páginas e imagem em outra.
        'artigo_misto_texto_e_imagem.pdf': documento_misto(
            'Artigo com Página Escaneada',
            'A primeira página tem texto: este trecho deve aparecer na extração.',
            'A terceira página também tem texto: este trecho também deve aparecer na extração.',
        ),
        # Sem camada de texto: pypdf devolve vazio. Sem resumo digitado, o worker marca ERRO.
        'escaneado_sem_texto.pdf': documento_sem_texto(3),
    }
    for nome, conteudo in arquivos.items():
        (PASTA / nome).write_bytes(conteudo)

    # Cortado no meio: tem cabeçalho de PDF, mas o arquivo está incompleto.
    inteiro = arquivos['artigo_nuvem.pdf']
    (PASTA / 'corrompido_truncado.pdf').write_bytes(inteiro[: len(inteiro) // 3])
    # Extensão .pdf, mas não é PDF: a API recusa (415).
    (PASTA / 'invalido_nao_e_pdf.pdf').write_text('Isto não é um PDF.\n', encoding='utf-8')


if __name__ == '__main__':
    main()
