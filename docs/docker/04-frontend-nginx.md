# 4. Frontend e Nginx

[← 3. Dockerfiles](03-dockerfiles.md) | [Índice](README.md) | [5. DynamoDB e credenciais →](05-dynamodb-e-credenciais.md)

No trabalho 1 as telas ficavam num bucket S3 de site estático e chamavam a API no ALB. Agora um container Nginx serve as telas **e** encaminha as chamadas da API.

## `frontend/nginx.conf`

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;
    client_max_body_size 25M;

    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ { expires 7d; ... }

    location /api/ {
        resolver 127.0.0.11 valid=10s;
        set $backend_upstream http://backend:8000;
        rewrite ^/api/(.*)$ /$1 break;
        proxy_pass $backend_upstream;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / { try_files $uri $uri/ =404; }
}
```

| Trecho | O que faz | Por quê |
|---|---|---|
| `root` + `location /` | Serve os `.html`, `css/` e `js/` copiados no Dockerfile | Telas estáticas |
| `location /api/` | Proxy reverso para o backend | O navegador só fala com a porta 8080 |
| `rewrite ^/api/(.*)$ /$1 break` | Tira o prefixo `/api` | O Django expõe `/articles/`, não `/api/articles/` |
| `client_max_body_size 25M` | Limite de upload | O padrão do Nginx é 1 MB e rejeitaria PDFs (a API aceita até 10 MB) |
| `expires 7d` em estáticos | Cache no navegador por 7 dias | Menos requisições; depois de alterar CSS/JS pode ser preciso forçar a atualização (Ctrl+Shift+R) |
| `proxy_set_header ...` | Repassa host, IP e protocolo originais | O backend enxerga o cliente real, não o Nginx |

### Por que `resolver 127.0.0.11` e a variável `$backend_upstream`

Com `proxy_pass http://backend:8000;` direto, o Nginx resolve o nome `backend` **uma vez, ao iniciar**. Se o backend ainda não existe nesse momento (ou é recriado e muda de IP), o Nginx falha ao subir ou fica apontando para um IP velho. Guardando o endereço numa **variável**, o Nginx passa a resolver o nome **a cada requisição** (cache de 10 s, `valid=10s`), e o `resolver 127.0.0.11` aponta para o DNS embutido do Docker, que conhece os nomes dos serviços. Efeito prático: o frontend sobe mesmo se o backend ainda não estiver pronto.

Detalhe: com variável no `proxy_pass`, o Nginx **não** reescreve a URI sozinho, por isso o `rewrite ... break` é necessário.

### Por que não precisa de CORS no compose

`frontend/js/config.js` define `const API_BASE_URL = '/api';` (caminho relativo). O navegador chama `http://localhost:8080/api/...`, a **mesma origem** da tela, e o Nginx faz o salto até o backend. CORS só existe quando o navegador chama outra origem (outra porta ou domínio). Por isso, no compose, o `CORS_ALLOWED_ORIGINS` do backend quase não importa. Ele era necessário no trabalho 1, em que a tela ficava no S3 e a API no ALB.

Isso também afeta o `DJANGO_ALLOWED_HOSTS`: o Nginx repassa `Host: $host` (`localhost` no caso local). Numa VM, o IP ou DNS público precisa estar nessa lista, senão o Django responde 400.

### Fluxo de uma requisição

```
navegador  GET http://localhost:8080/api/articles/
   └─> nginx (frontend:80)  location /api/ -> rewrite para /articles/
         └─> backend:8000   (nome resolvido pelo DNS do Docker)
```

### O que NÃO passa pelo Nginx

O **download do PDF**: a API só devolve a URL pré-assinada, e o navegador a abre direto em `localhost:9000` (MinIO). Ver [02](02-postgres-minio-redis.md#dois-endereços-interno-e-público).

## Perguntas prováveis

1. **Para que serve um proxy reverso?** Ponto de entrada único: serve o estático, encaminha a API e esconde o backend.
2. **Por que o front usa `/api` e não `http://localhost:8000`?** Mesma origem: sem CORS, e o endereço do backend não aparece no código do navegador. Funciona igual em qualquer máquina.
3. **Por que `resolver` com variável?** Para o Nginx resolver o nome do backend em cada requisição, e não só ao iniciar.
4. **De onde vem `127.0.0.11`?** É o servidor DNS embutido que o Docker coloca em cada container de uma rede definida pelo usuário.
5. **O que o front mudou em relação ao trabalho 1?** O hospedeiro (S3 estático → Nginx em container) e o `API_BASE_URL` (endereço do ALB → `/api`). O código das telas é o mesmo.
6. **Por que o front não usa `ports` para falar com o backend?** Quem fala com o backend é o Nginx, dentro da rede do Docker, pela porta interna 8000.

[← 3. Dockerfiles](03-dockerfiles.md) | [Índice](README.md) | [5. DynamoDB e credenciais →](05-dynamodb-e-credenciais.md)
