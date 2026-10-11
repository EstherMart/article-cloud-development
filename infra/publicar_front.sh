#!/usr/bin/env bash
# Publica o frontend/ no bucket do site, com o endereço da API já trocado.
# Uso: infra/publicar_front.sh <bucket-do-site> <url-da-api>
# Ex.:  infra/publicar_front.sh artigos-site-ana-2026 http://meu-alb-123.us-east-1.elb.amazonaws.com
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Uso: $0 <bucket-do-site> <url-da-api>" >&2
    exit 1
fi

bucket="$1"
api_url="${2%/}"
origem="$(cd "$(dirname "$0")/../frontend" && pwd)"

# Tudo, menos o config.js e os READMEs.
aws s3 sync "$origem" "s3://${bucket}/" --delete --exclude "*.md" --exclude "js/config.js"

# O config.js sai com o endereço da API trocado; o arquivo do repositório não muda.
config="$(sed "s|^const API_BASE_URL = .*|const API_BASE_URL = '${api_url}';|" "$origem/js/config.js")"
case "$config" in
    *"API_BASE_URL = '${api_url}'"*) ;;
    *) echo "Não consegui trocar API_BASE_URL no config.js" >&2; exit 1 ;;
esac
printf '%s\n' "$config" | aws s3 cp - "s3://${bucket}/js/config.js" --content-type "application/javascript"

echo "Publicado: http://${bucket}.s3-website-us-east-1.amazonaws.com"
