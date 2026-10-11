# Infraestrutura

Scripts de apoio. O passo a passo para criar cada serviço na AWS está em [docs/aws](../docs/aws/README.md).

## publicar_front.sh

Publica as telas (`frontend/`) no bucket S3 de site estático, trocando o endereço da API na cópia enviada (o arquivo do repositório não muda).

```
infra/publicar_front.sh <bucket-do-site> <url-da-api>
infra/publicar_front.sh artigos-site-2026 http://meu-alb-123.us-east-1.elb.amazonaws.com
```

Precisa do `aws` configurado. Se o endereço da API mudar (por exemplo, o ALB foi recriado), rode de novo com o endereço novo.
