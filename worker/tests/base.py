"""Caminhos e helpers comuns aos testes do worker."""
import sys
from pathlib import Path

WORKER = Path(__file__).resolve().parents[1]
PDFS = WORKER.parent / 'backend' / 'articles' / 'tests' / 'fixtures' / 'pdfs'
sys.path.insert(0, str(WORKER))


def pdf(nome):
    return (PDFS / nome).read_bytes()
