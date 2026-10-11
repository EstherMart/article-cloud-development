# PDFs de teste

Todos têm mais de uma página (exceto o inválido), são gerados por `gerar_pdfs.py` (sem dependências) e
servem para o upload no S3, para a extração de texto do worker e para os testes de tradução.
Para recriar: `python backend/articles/tests/fixtures/gerar_pdfs.py`.

| Arquivo | Págs | Cenário que cobre |
|---|---|---|
| `artigo_nuvem.pdf`, `artigo_mensageria.pdf`, `artigo_banco_de_dados.pdf` | 2 | Caminho feliz: texto em português, com resumo, palavras-chave e seções |
| `artigo_longo_5_paginas.pdf` | 5 | O worker junta o texto de todas as páginas; tradução de texto médio (~12 mil caracteres) |
| `artigo_muito_longo_30_paginas.pdf` | 30 | Carga: ~83 mil caracteres numa única chamada ao Gemini (sem resumo digitado) |
| `artigo_acentos_e_simbolos.pdf` | 3 | Acentos, cedilha, aspas curvas, `R$ 10,00`, `50%`, barra invertida, siglas e nomes de serviços que não podem ser traduzidos |
| `artigo_tecnico_numeros_e_tabela.pdf` | 2 | Números, porcentagens e tabela em texto: a tradução não pode alterá-los |
| `artigo_em_ingles.pdf` | 2 | Texto já em inglês: traduzir para inglês não pode falhar nem mudar o sentido |
| `artigo_misto_texto_e_imagem.pdf` | 3 | Páginas 1 e 3 com texto, página 2 só desenho: o worker aproveita o que tem texto |
| `escaneado_sem_texto.pdf` | 3 | Sem camada de texto: `pypdf` devolve vazio. Sem resumo digitado, o artigo termina em `ERRO` |
| `corrompido_truncado.pdf` | - | Cabeçalho de PDF, mas cortado no meio: a extração levanta erro e o artigo termina em `ERRO` |
| `invalido_nao_e_pdf.pdf` | - | Extensão `.pdf`, conteúdo de texto: a API recusa com 415 |

## Qual cenário vale o quê (resumo e tradução)

O worker traduz o **resumo digitado**; se estiver vazio, traduz o **texto extraído do PDF**.

| Resumo digitado | PDF | Resultado esperado |
|---|---|---|
| preenchido | qualquer PDF válido | Traduz o resumo, `PROCESSADO` |
| preenchido | escaneado | Traduz o resumo, `PROCESSADO` (o PDF não atrapalha) |
| vazio | com texto | Traduz o texto do PDF, `PROCESSADO` |
| vazio | escaneado | Nada para traduzir: `ERRO` |
| qualquer | corrompido | `ERRO` e a mensagem volta para a fila (até 3 vezes, depois DLQ) |
| qualquer | Gemini sem chave, sem cota ou fora do ar | `ERRO` e a mensagem volta para a fila |

Esses cenários estão automatizados em `worker/tests/test_worker.py` (sem AWS e sem Gemini) e, com o Gemini
de verdade, em `worker/tests/test_gemini_real.py`.

## Uso rápido

Pela API (token do login):

```
curl -X POST http://127.0.0.1:8000/articles/ -H "Authorization: Token $TOKEN" \
  -F title="Computação em Nuvem" -F 'authors=["Ana"]' -F 'tags=["AWS"]' -F area="Computação" \
  -F abstract="Resumo digitado" -F file=@backend/articles/tests/fixtures/pdfs/artigo_longo_5_paginas.pdf
```

Para testar só o worker sem resumo, envie `-F abstract=""`. Pelo console da AWS: S3 > bucket > **Upload** na pasta `artigos/`.
