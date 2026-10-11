# 3b. Front no S3 (site estático)

[← 3. S3](03-s3.md) | [Índice](README.md) | [4. DynamoDB →](04-dynamodb.md)

## O que é
As telas (`frontend/`) são só arquivos HTML, CSS e JavaScript. O navegador os baixa e roda. Por isso podem ficar num **segundo bucket**, separado do bucket dos PDFs, usando o recurso de "site estático" do S3. A API continua na EC2 (e, na Parte 2, atrás do ALB).

```
Navegador --> bucket do site (telas)          [fora do Auto Scaling]
          \-> API (EC2 ou ALB)                [escala de 1 a 3]
```

Este bucket é **público de propósito**: o conteúdo é só o código das telas, sem dado de ninguém. O bucket dos PDFs continua privado.

Caminho: S3 > **Buckets** > **Criar bucket**. Campo que não aparece aqui fica no valor padrão.

| Campo (inglês) | Valor | O que é e por quê |
|---|---|---|
| Nome do bucket | único, por exemplo `artigos-site-<seu-nome>-2026` | Faz parte do endereço do site |
| Região | us-east-1 | A mesma dos outros serviços |
| Propriedade de objeto | ACLs desabilitadas | Só a política manda |
| Bloquear todo o acesso público | **desmarque** as 4 caixas e confirme o aviso | Sem isso, ninguém abre o site |
| Versionamento | desabilitado | Sem custo extra |

## Hospedagem de site estático
Bucket > aba **Propriedades** > no fim, **Hospedagem de site estático** > **Editar**:

| Campo | Valor |
|---|---|
| Hospedagem de site estático | **Habilitar** |
| Tipo de hospedagem | **Hospedar um site estático** |
| Documento de índice | `index.html` |
| Documento de erro | `index.html` |

Salve. O **endereço do site** aparece no fim da mesma tela: `http://<bucket>.s3-website-us-east-1.amazonaws.com`. Ele é **HTTP**, não HTTPS. Anote: é o valor de `CORS_ALLOWED_ORIGINS` da API.

## Política de bucket
Aba **Permissões** > **Política do bucket** > **Editar** (troque o nome do bucket):

```
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "LeituraPublicaDoSite",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::<bucket-do-site>/*"
  }]
}
```

Se o console recusar a política com "Block public access", volte e confirme que as 4 caixas estão desmarcadas.

## Publicar as telas
O endereço da API fica em `frontend/js/config.js` (`API_BASE_URL`). O script envia os arquivos ao bucket e grava o `config.js` já com o endereço da API trocado, sem alterar o arquivo do repositório:

```
infra/publicar_front.sh <bucket-do-site> http://<IP público da EC2>:8000
```

Na Parte 2, repita com o endereço do ALB: `infra/publicar_front.sh <bucket-do-site> http://<DNS do ALB>`. Precisa do `aws` configurado (na sua máquina, com as credenciais do Learner Lab).

## Configurar a API para aceitar o site
No `.env` da API (e no do launch template na Parte 2):

```
CORS_ALLOWED_ORIGINS=http://<bucket-do-site>.s3-website-us-east-1.amazonaws.com
```

Sem barra no final e com `http://`, igual ao endereço do site. Reinicie a API (`sudo systemctl restart api`).

## Testar
1. Abra o endereço do site. A página inicial deve carregar com o visual.
2. Abra o console do navegador (F12 > Console). Não pode haver erro de **CORS**.
3. Crie uma conta, entre, cadastre um artigo com PDF e baixe o PDF.
4. Se a lista não carregar, abra F12 > Rede e veja para qual endereço o front está chamando.

## O que pode dar errado
| Sintoma | Causa provável |
|---|---|
| `403 Forbidden` ao abrir o site | Política do bucket ausente ou Block Public Access ainda ligado |
| `404` no endereço do site | Hospedagem de site estático não habilitada, ou o `index.html` não foi enviado |
| Telas abrem, mas a lista fica vazia e o console mostra **CORS** | `CORS_ALLOWED_ORIGINS` diferente do endereço do site (barra no final, `https`, nome do bucket) ou API não reiniciada |
| Telas abrem e as chamadas vão para `127.0.0.1:8000` | Você enviou o `frontend/` direto, sem o script. Use `infra/publicar_front.sh` |
| `ERR_CONNECTION_REFUSED` ou tempo esgotado na API | Porta 8000 do `sg-api` não aceita o seu IP (ou, na Parte 2, o ALB mudou) |
| O ALB foi recriado e o front quebrou | O DNS do ALB muda quando ele é recriado. Rode o script de novo com o DNS novo |
| Navegador bloqueia chamadas ("conteúdo misto") | O site é HTTP e a API está em HTTPS (ou o contrário). Mantenha os dois em HTTP |
| O Learner Lab não deixa desmarcar o Block Public Access | Plano B: nginx na EC2 da API ou front local. Avise o grupo |

## Apagar
Bucket do site > **Esvaziar** (digite `permanently delete`) e **Excluir**. Pode ficar criado: sem tráfego, custa centavos.

## Por que configuramos assim (estudo para a arguição)

| Configuração | Motivo |
|---|---|
| Bucket separado do dos PDFs | O bucket de PDFs é privado e o do site é público. Misturar exporia os PDFs |
| Site público | É só código de tela. Nenhum dado de usuário fica nele |
| Front fora do Auto Scaling | Entregar arquivo estático não gasta CPU da API. O ASG escala só o que pesa |
| CORS na API | O navegador bloqueia chamadas entre origens diferentes, a menos que a API autorize a do site |
| HTTP em tudo | O Learner Lab não traz certificado HTTPS. Com tudo em HTTP, não há bloqueio de conteúdo misto |
| Script de publicação | Evita guardar o endereço do ALB no git e esquecer de trocá-lo |

Pergunta provável: "Onde roda a interface gráfica?" Resposta: as telas são estáticas, entregues pelo S3 direto ao navegador. A lógica e os dados passam pela API na EC2, atrás do ALB.

---
[← 3. S3](03-s3.md) | [Índice](README.md) | [4. DynamoDB →](04-dynamodb.md)
