# Fixtures de teste

PDFs de exemplo, gerados por `gerar_pdfs.py` (sem dependências). Para recriar: `python gerar_pdfs.py`.

| Arquivo | Para que serve |
|---|---|
| `pdfs/artigo_nuvem.pdf` | Upload no S3 e extração de texto (caminho feliz) |
| `pdfs/artigo_mensageria.pdf` | Segundo artigo, para testar lista, busca e vários uploads |
| `pdfs/artigo_banco_de_dados.pdf` | Terceiro artigo |
| `pdfs/escaneado_sem_texto.pdf` | Simula PDF escaneado: `pypdf` devolve texto vazio e o worker usa o resumo digitado |
| `pdfs/invalido_nao_e_pdf.pdf` | Tem extensão `.pdf`, mas não é PDF. A API deve recusar (validação do tipo) |

Todos têm cerca de 1 KB. Para testar o limite de tamanho do upload, crie um arquivo maior na hora (por exemplo `head -c 25M /dev/zero > /tmp/grande.pdf`) e não o coloque no repositório.

## Uso rápido (depois que o POST aceitar PDF)

```
curl -X POST http://127.0.0.1:8000/articles/ \
  -F title="Computação em Nuvem" -F authors="Ana" -F area="Computação" -F user=teste \
  -F file=@backend/articles/tests/fixtures/pdfs/artigo_nuvem.pdf
```

(o formato multipart do POST ainda será definido junto com o upload no S3.)

Pelo console da AWS: S3 > bucket > **Upload** e escolha um destes arquivos para a pasta `artigos/`.
