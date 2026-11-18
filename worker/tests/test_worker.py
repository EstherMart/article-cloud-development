"""Testes do worker sem AWS, sem banco e sem Gemini (tudo simulado).

Rodar:  cd worker && python -m unittest discover -s tests -v
Os PDFs vêm de backend/articles/tests/fixtures/pdfs (regerar: python gerar_pdfs.py).
"""
import json
import unittest
from io import BytesIO
from unittest import mock

import pypdf

from base import pdf
import worker


class ExtracaoDeTextoTests(unittest.TestCase):

    def test_junta_o_texto_de_todas_as_paginas(self):
        texto = worker.extract_text(pdf('artigo_longo_5_paginas.pdf'))
        self.assertIn('Página 1 de 5', texto)
        self.assertIn('Página 5 de 5', texto)

    def test_pdf_escaneado_devolve_texto_vazio(self):
        self.assertEqual(worker.extract_text(pdf('escaneado_sem_texto.pdf')), '')

    def test_pdf_misto_aproveita_as_paginas_que_tem_texto(self):
        texto = worker.extract_text(pdf('artigo_misto_texto_e_imagem.pdf'))
        self.assertIn('primeira página tem texto', texto)
        self.assertIn('terceira página também tem texto', texto)

    def test_acentos_numeros_e_termos_tecnicos_chegam_intactos(self):
        texto = worker.extract_text(pdf('artigo_acentos_e_simbolos.pdf'))
        for esperado in ('ação', 'coração', 'R$ 10,00', '50%', 'PostgreSQL', 'artigos/42.pdf'):
            self.assertIn(esperado, texto)

    def test_pdf_cortado_no_meio_levanta_erro(self):
        with self.assertRaises(pypdf.errors.PyPdfError):
            worker.extract_text(pdf('corrompido_truncado.pdf'))

    def test_arquivo_que_nao_e_pdf_levanta_erro(self):
        with self.assertRaises(pypdf.errors.PyPdfError):
            worker.extract_text(pdf('invalido_nao_e_pdf.pdf'))


class ProcessarMensagemTests(unittest.TestCase):
    """process(): o que o worker traduz em cada cenário e o status em que o artigo termina."""

    def processar(self, pdf_nome, resumo, traducao='Translated text'):
        mensagem = {'Body': json.dumps({'article_id': 7, 's3_key': 'artigos/7.pdf', 'bucket': 'bucket-teste'})}
        s3 = mock.Mock()
        s3.get_object.return_value = {'Body': BytesIO(pdf(pdf_nome))}
        patches = {
            '_set_status': mock.DEFAULT, '_get_abstract': mock.DEFAULT,
            'translate': mock.DEFAULT, 'save_result': mock.DEFAULT, '_invalidate_cache': mock.DEFAULT,
        }
        with mock.patch.multiple(worker, **patches) as mocks, mock.patch.object(worker, '_minio_client', return_value=s3):
            mocks['_get_abstract'].return_value = resumo
            if isinstance(traducao, Exception):
                mocks['translate'].side_effect = traducao
            else:
                mocks['translate'].return_value = traducao
            erro = None
            try:
                worker.process(mensagem)
            except Exception as exc:
                erro = exc
        return mocks, erro

    def test_resumo_digitado_e_traduzido_e_o_pdf_nao_e_usado(self):
        mocks, erro = self.processar('artigo_nuvem.pdf', 'Resumo digitado pelo autor.')
        self.assertIsNone(erro)
        mocks['translate'].assert_called_once_with('Resumo digitado pelo autor.')
        mocks['save_result'].assert_called_once_with(7, 'Translated text', 'PROCESSADO')
        mocks['_invalidate_cache'].assert_called_once_with(7)

    def test_sem_resumo_traduz_o_texto_extraido_do_pdf(self):
        mocks, erro = self.processar('artigo_nuvem.pdf', '')
        self.assertIsNone(erro)
        enviado = mocks['translate'].call_args.args[0]
        self.assertIn('Arquitetura em Nuvem', enviado)
        mocks['save_result'].assert_called_once_with(7, 'Translated text', 'PROCESSADO')

    def test_pdf_longo_vai_inteiro_para_a_traducao_quando_nao_ha_resumo(self):
        # Cenário de carga: 30 páginas, mais de 80 mil caracteres numa única chamada ao Gemini.
        mocks, erro = self.processar('artigo_muito_longo_30_paginas.pdf', '')
        self.assertIsNone(erro)
        self.assertGreater(len(mocks['translate'].call_args.args[0]), 80_000)

    def test_sem_resumo_e_pdf_escaneado_termina_em_erro(self):
        mocks, erro = self.processar('escaneado_sem_texto.pdf', '')
        self.assertIsInstance(erro, ValueError)
        mocks['translate'].assert_not_called()
        mocks['save_result'].assert_not_called()
        mocks['_set_status'].assert_any_call(7, 'ERRO')

    def test_com_resumo_o_pdf_escaneado_nao_atrapalha(self):
        mocks, erro = self.processar('escaneado_sem_texto.pdf', 'Resumo digitado.')
        self.assertIsNone(erro)
        mocks['save_result'].assert_called_once_with(7, 'Translated text', 'PROCESSADO')

    def test_pdf_corrompido_termina_em_erro_e_a_mensagem_volta_para_a_fila(self):
        mocks, erro = self.processar('corrompido_truncado.pdf', 'Resumo digitado.')
        self.assertIsNotNone(erro)  # a exceção sobe: handle_delivery não faz ack
        mocks['_set_status'].assert_any_call(7, 'ERRO')
        mocks['save_result'].assert_not_called()

    def test_falha_do_gemini_termina_em_erro_e_a_mensagem_volta_para_a_fila(self):
        mocks, erro = self.processar('artigo_nuvem.pdf', 'Resumo.', traducao=RuntimeError('cota esgotada'))
        self.assertIsInstance(erro, RuntimeError)
        mocks['_set_status'].assert_any_call(7, 'ERRO')
        mocks['save_result'].assert_not_called()


class MensagemETraducaoTests(unittest.TestCase):

    def test_aceita_o_json_do_evento_em_texto_ou_bytes(self):
        evento = {'article_id': 3, 's3_key': 'artigos/3.pdf', 'bucket': 'b', 'event': 'ARTICLE_CREATED'}
        self.assertEqual(worker._decode_body(json.dumps(evento))['article_id'], 3)
        self.assertEqual(worker._decode_body(json.dumps(evento).encode())['article_id'], 3)  # o pika entrega bytes

    def test_json_invalido_e_recusado(self):
        for corpo in ('isto não é json', b'\xff\xfe', '[1, 2]', '"texto"'):
            with self.subTest(corpo=corpo), self.assertRaises(ValueError):
                worker._decode_body(corpo)

    def test_mensagem_sem_campo_obrigatorio_e_recusada(self):
        for corpo in ({'article_id': 0, 's3_key': 'k', 'bucket': 'b'},
                      {'article_id': 'x', 's3_key': 'k', 'bucket': 'b'},
                      {'article_id': 1, 's3_key': '', 'bucket': 'b'},
                      {'article_id': 1, 's3_key': 'k'}):
            with self.subTest(corpo=corpo), self.assertRaises(ValueError):
                worker._decode_body(json.dumps(corpo))

    def test_texto_vazio_nao_chama_o_gemini(self):
        with mock.patch.object(worker.genai, 'Client') as cliente:
            self.assertEqual(worker.translate('   '), '')
        cliente.assert_not_called()


EVENTO = json.dumps({'article_id': 7, 's3_key': 'artigos/7.pdf', 'bucket': 'artigos', 'event': 'ARTICLE_CREATED'}).encode()


class EntregaDoRabbitMQTests(unittest.TestCase):
    """handle_delivery(): como o worker responde ao broker (ack, nack para reentrega ou nack para a DLQ)."""

    def entregar(self, corpo=EVENTO, erro=None):
        canal = mock.Mock()
        metodo = mock.Mock(delivery_tag=42)
        with mock.patch.object(worker, 'process', side_effect=erro) as process:
            worker.handle_delivery(canal, metodo, corpo)
        return canal, process

    def test_sucesso_confirma_com_ack(self):
        canal, process = self.entregar()
        process.assert_called_once_with({'Body': EVENTO})
        canal.basic_ack.assert_called_once_with(delivery_tag=42)
        canal.basic_nack.assert_not_called()

    def test_falha_ao_processar_devolve_para_a_fila(self):
        canal, _ = self.entregar(erro=RuntimeError('Gemini fora do ar'))
        canal.basic_nack.assert_called_once_with(delivery_tag=42, requeue=True)
        canal.basic_ack.assert_not_called()

    def test_mensagem_invalida_vai_para_a_dlq_sem_tentar_processar(self):
        for corpo in (b'nao e json', json.dumps({'article_id': 0, 's3_key': 'k', 'bucket': 'b'}).encode()):
            with self.subTest(corpo=corpo):
                canal, process = self.entregar(corpo=corpo)
                canal.basic_nack.assert_called_once_with(delivery_tag=42, requeue=False)
                canal.basic_ack.assert_not_called()
                process.assert_not_called()


class ConsumoTests(unittest.TestCase):

    ENV = {'RABBITMQ_HOST': 'rabbitmq', 'RABBITMQ_DEFAULT_USER': 'u', 'RABBITMQ_DEFAULT_PASS': 'p',
           'RABBITMQ_QUEUE': 'fila.teste'}

    def test_consume_declara_a_fila_limita_a_uma_mensagem_e_so_confirma_manualmente(self):
        conexao = mock.Mock()
        canal = conexao.channel.return_value
        with mock.patch.dict('os.environ', self.ENV), \
                mock.patch.object(worker.pika, 'BlockingConnection', return_value=conexao):
            worker.consume()

        canal.queue_declare.assert_any_call(
            queue='fila.teste', durable=True,
            arguments={'x-queue-type': 'quorum', 'x-delivery-limit': 3,
                       'x-dead-letter-exchange': 'fila.teste.dlx', 'x-dead-letter-routing-key': 'fila.teste'})
        canal.basic_qos.assert_called_once_with(prefetch_count=1)
        self.assertEqual(canal.basic_consume.call_args.kwargs['queue'], 'fila.teste')
        self.assertNotIn('auto_ack', canal.basic_consume.call_args.kwargs)  # ack manual
        canal.start_consuming.assert_called_once_with()

    def test_heartbeat_alto_para_nao_cair_durante_o_processamento(self):
        with mock.patch.dict('os.environ', self.ENV):
            self.assertGreaterEqual(worker._connection_parameters().heartbeat, 600)

    def test_main_reconecta_quando_o_broker_cai(self):
        tentativas = [worker.pika.exceptions.AMQPConnectionError('caiu'), OSError('rede'), KeyboardInterrupt()]
        with mock.patch.object(worker, 'consume', side_effect=tentativas) as consume, \
                mock.patch.object(worker.time, 'sleep') as dormir:
            with self.assertRaises(KeyboardInterrupt):
                worker.main()
        self.assertEqual(consume.call_count, 3)
        self.assertEqual(dormir.call_count, 2)


if __name__ == '__main__':
    unittest.main()
