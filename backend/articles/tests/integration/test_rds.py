"""RDS PostgreSQL (requisito 2). Usa psycopg2 direto, sem o banco de teste do Django.

Só lê o banco real e escreve numa tabela TEMPORÁRIA (some ao fechar a conexão).
Não altera dados nem tabelas do projeto.
"""
import os

from .base import AwsIntegrationTestCase

MIGRATIONS = [
    '0001_initial',
    '0002_remove_article_author_article_authors',
    '0003_alter_article_id_alter_author_id_alter_tag_id',
    '0004_article_abstract_article_s3_key_and_more',
]


class RdsConnectionTests(AwsIntegrationTestCase):
    REQUIRED_ENV = ('DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD')

    def setUp(self):
        import psycopg2

        self.conn = psycopg2.connect(
            host=os.environ['DB_HOST'],
            port=os.environ.get('DB_PORT', '5432'),
            dbname=os.environ['DB_NAME'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            sslmode=os.environ.get('DB_SSLMODE', 'require'),
            connect_timeout=10,
        )
        self.addCleanup(self.conn.close)

    def query(self, sql, params=None):
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def test_conecta_e_responde_select_1(self):
        self.assertEqual(self.query('SELECT 1'), [(1,)])

    def test_esta_no_banco_configurado(self):
        self.assertEqual(self.query('SELECT current_database()')[0][0], os.environ['DB_NAME'])

    def test_conexao_usa_ssl(self):
        self.assertTrue(self.query('SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()')[0][0])

    def test_django_esta_configurado_para_postgresql(self):
        # Pega o caso de DB_HOST vazio: o Django cai no SQLite sem avisar.
        from django.db import connection

        self.assertEqual(connection.vendor, 'postgresql')

    def test_migrations_do_app_estao_aplicadas(self):
        rows = self.query("SELECT name FROM django_migrations WHERE app = 'articles'")
        aplicadas = {name for (name,) in rows}
        self.assertEqual(set(MIGRATIONS) - aplicadas, set(), 'rode `python manage.py migrate`')

    def test_tabelas_do_modelo_existem(self):
        rows = self.query("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tabelas = {name for (name,) in rows}
        for esperada in ('articles_article', 'articles_author', 'articles_tag'):
            self.assertIn(esperada, tabelas)

    def test_escrita_e_leitura_funcionam(self):
        with self.conn.cursor() as cur:
            cur.execute('CREATE TEMP TABLE teste_integracao (valor text)')
            cur.execute("INSERT INTO teste_integracao VALUES ('ok')")
            cur.execute('SELECT valor FROM teste_integracao')
            self.assertEqual(cur.fetchone(), ('ok',))
