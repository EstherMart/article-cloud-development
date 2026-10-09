"""RDS PostgreSQL (requisito 2). Variáveis: DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT.

O que vai aqui (descomentar e implementar depois que o RDS existir):

# class RdsConnectionTests(AwsIntegrationTestCase):
#     @require_env('DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD')
#     def test_conecta_e_responde_select_1(self):
#         # connection.cursor().execute('SELECT 1') sem erro de rede ou senha.
#
#     def test_usa_postgresql_e_nao_sqlite(self):
#         # connection.vendor == 'postgresql'. Pega o caso de DB_HOST vazio caindo no SQLite.
#
#     def test_conexao_usa_ssl(self):
#         # SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid() devolve true.
#
#     def test_migrations_aplicadas(self):
#         # MigrationExecutor mostra articles 0001 a 0004 como aplicadas.
#
#     def test_crud_basico_persiste(self):
#         # cria Article, relê pelo id, apaga. Limpa no addCleanup.
#
# Pega: senha errada, Security Group fechado, banco inexistente, SSL.
"""
