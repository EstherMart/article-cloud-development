"""Tradução com o Gemini de verdade (usa a chave e gasta cota). Desligado por padrão.

Rodar:
    cd worker
    set -a; source ../backend/.env; set +a
    RUN_GEMINI=1 python -m unittest discover -s tests -p 'test_gemini_real.py' -v
    RUN_GEMINI=1 RUN_GEMINI_SLOW=1 ...     inclui o PDF de 30 páginas

Cada teste confere o que a tradução NÃO pode estragar: termos técnicos, números, e o idioma.
Texto de saída de um modelo varia, então os testes procuram palavras-chave e não frases exatas.
"""
import os
import unittest

from base import pdf
import worker

requer_gemini = unittest.skipUnless(
    os.environ.get('RUN_GEMINI') == '1' and os.environ.get('GEMINI_API_KEY') and os.environ.get('GEMINI_MODEL'),
    'desligado: defina RUN_GEMINI=1, GEMINI_API_KEY e GEMINI_MODEL',
)
lento = unittest.skipUnless(os.environ.get('RUN_GEMINI_SLOW') == '1', 'lento: defina RUN_GEMINI_SLOW=1')


@requer_gemini
class TraducaoRealTests(unittest.TestCase):

    def traduzir(self, texto):
        resultado = worker.translate(texto)
        self.assertTrue(resultado.strip(), 'o Gemini devolveu texto vazio')
        return resultado

    def test_resumo_em_portugues_sai_em_ingles(self):
        saida = self.traduzir(
            'Este trabalho descreve uma arquitetura em nuvem para armazenar e consultar artigos acadêmicos. '
            'Os metadados ficam em banco relacional e as consultas frequentes em cache.'
        ).lower()
        for palavra in ('cloud', 'cache', 'database'):
            self.assertIn(palavra, saida)
        self.assertNotIn('nuvem', saida)

    def test_termos_tecnicos_e_numeros_nao_mudam(self):
        saida = self.traduzir(
            'O PostgreSQL e o Redis atenderam 70% das requisições em 37 ms, usando o Auto Scaling e o SQS.'
        )
        for preservado in ('PostgreSQL', 'Redis', '70%', '37', 'SQS'):
            self.assertIn(preservado, saida)

    def test_texto_extraido_de_pdf_com_acentos_e_simbolos(self):
        saida = self.traduzir(worker.extract_text(pdf('artigo_acentos_e_simbolos.pdf')))
        for preservado in ('R$ 10,00', '50%', 'PostgreSQL', 'artigos/42.pdf', 'us-east-1'):
            self.assertIn(preservado, saida)

    def test_texto_que_ja_esta_em_ingles_continua_em_ingles(self):
        saida = self.traduzir(worker.extract_text(pdf('artigo_em_ingles.pdf'))).lower()
        self.assertIn('cloud', saida)
        self.assertIn('worker', saida)

    def test_pdf_de_5_paginas_gera_traducao_de_tamanho_parecido(self):
        texto = worker.extract_text(pdf('artigo_longo_5_paginas.pdf'))
        saida = self.traduzir(texto)
        self.assertGreater(len(saida), len(texto) * 0.5, 'a tradução parece ter cortado o texto')

    @lento
    def test_pdf_de_30_paginas_nao_estoura_o_limite(self):
        texto = worker.extract_text(pdf('artigo_muito_longo_30_paginas.pdf'))
        saida = self.traduzir(texto)
        self.assertGreater(len(saida), len(texto) * 0.5, 'a tradução parece ter cortado o texto')


if __name__ == '__main__':
    unittest.main()
