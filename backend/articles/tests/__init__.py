"""Testes do app articles, em dois grupos com responsabilidades diferentes.

unit/         Rodam sem rede e sem custo (SQLite em memória, AWS simulada).
              Provam a lógica do nosso código. Rodam em todo commit.
integration/  Falam com a AWS de verdade. Provam que a configuração funciona
              (rede, permissões, nomes dos recursos). Cobram, precisam de
              credenciais e ficam desligados por padrão. Ver integration/README.md.
"""
