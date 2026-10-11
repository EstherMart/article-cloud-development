# 2. EC2 da API

[← 1. RDS PostgreSQL](01-rds.md) | [Índice](README.md) | [3. S3 →](03-s3.md)

## O que é a EC2
É um servidor virtual (uma máquina Linux na nuvem). A API Django roda nele. O worker roda em outra, na [etapa 7](07-ec2-worker.md).

Caminho: EC2 > **Instâncias** > **Executar instâncias**.

Os nomes abaixo seguem o console em português. Entre parênteses vai o nome em inglês, caso o seu console esteja em outro idioma. Campo que não aparece aqui fica no valor padrão.

| Campo (inglês) | Valor | O que é e por quê |
|---|---|---|
| Nome (Name) | `api` | Só o rótulo da máquina |
| Imagens de aplicações e de sistemas operacionais (AMI) | **Amazon Linux 2023 AMI** (64 bits, x86) | O sistema operacional. É gratuito e já traz as ferramentas da AWS (`aws`) |
| Tipo de instância (Instance type) | `t3.micro` | A máquina pequena (2 vCPUs, 1 GB). Basta para o laboratório |
| Par de chaves (Key pair) | `vockey` | A chave do Learner Lab para entrar por SSH |
| Configurações de rede > VPC | a padrão (default) | A mesma rede do RDS |
| Configurações de rede > Sub-rede (Subnet) | Sem preferência | A AWS escolhe |
| Configurações de rede > Atribuir IP público automaticamente (Auto-assign public IP) | **Habilitar** | Sem isso a máquina não tem IP público e você não a acessa |
| Firewall (grupos de segurança) | **Selecionar grupo de segurança existente** > `sg-api` | Aplica as regras da [seção 0](00-preparacao.md) |
| Configurar armazenamento (Storage) | `8` GiB gp3 (padrão) | O disco da máquina |
| Detalhes avançados > Perfil da instância do IAM (IAM instance profile) | **LabInstanceProfile** | Dá à máquina a permissão da LabRole. É por isso que o código não precisa de chaves |
| Detalhes avançados > Proteção contra encerramento (Termination protection) | desabilitada | Permite encerrar quando quiser |
| Detalhes avançados > Dados do usuário (User data) | vazio | Script de inicialização. Não usamos |
| Número de instâncias (Number of instances) | `1` | Só uma |

Clique em **Executar instância**. Espere o estado **Em execução** e **2/2 verificações aprovadas**. Copie o **Endereço IPv4 público** para o `DJANGO_ALLOWED_HOSTS`.

Estado **Encerrada** (Terminated) é uma instância já apagada. Ela não cobra e some da lista em cerca de 1 hora.

## Configurar e subir a API
```
sudo dnf install -y python3.12 python3.12-pip git
git clone <url-do-repo>
cd article-cloud-development-/backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
nano .env
set -a; source .env; set +a
python manage.py migrate
gunicorn article_cloud.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 60
```

O Django exige Python 3.12 ou mais novo. Use `gunicorn`, não `runserver`: o `runserver` é só para desenvolvimento. Ele não aguenta carga e fica fora do desenho da Parte 2.

### Deixar a API rodando sem o terminal aberto (systemd)

Sem isso, a API morre quando você fecha o SSH, e uma instância criada pelo Auto Scaling (Parte 2) nasceria sem a API. Crie `/etc/systemd/system/api.service`:

```
[Unit]
Description=API Django
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/article-cloud-development-/backend
EnvironmentFile=/home/ec2-user/article-cloud-development-/backend/.env
ExecStart=/home/ec2-user/article-cloud-development-/backend/.venv/bin/gunicorn article_cloud.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 60
Restart=always

[Install]
WantedBy=multi-user.target
```

Depois: `sudo systemctl daemon-reload && sudo systemctl enable --now api`. Veja os logs com `journalctl -u api -f`.

O `EnvironmentFile` não aceita `export` nem aspas com `$`. Se a senha tiver caractere especial, troque a senha.

### Front
O front (`frontend/`) não roda na EC2 da API. Para a demonstração, sirva-o na sua máquina (`cd frontend && python3 -m http.server 8080`), troque `API_BASE_URL` em `frontend/js/config.js` pelo `http://<IP público da EC2>:8000` e deixe `CORS_ALLOWED_ORIGINS=http://localhost:8080` no `.env` da API. Sem isso o navegador bloqueia as chamadas (erro de CORS no console). Onde hospedar o front na AWS ainda é uma decisão em aberto.

## Testar no navegador e no terminal
1. Abra `http://<IP público>:8000/health/` (deve responder `{"status": "ok"}`) e depois `/articles/` (deve responder `[]` ou a lista).
2. Crie o usuário em `/auth/register/`, faça login, faça um cadastro com o `curl` do `backend/README.md` e confira que `GET /articles/` o devolve. Esta é a prova de que a API grava no RDS.
3. Se der erro 400 `DisallowedHost`, coloque o IP em `DJANGO_ALLOWED_HOSTS` e reinicie.
4. Se a página não abrir, confira a regra da porta 8000 no `sg-api` e se o `gunicorn` está de pé (`systemctl status api`).
5. Se o cadastro devolver **502** (`Falha ao acessar o armazenamento`), o bucket está errado, não existe ou a LabRole não tem acesso: veja o motivo real em `journalctl -u api`. O erro real nunca vai na resposta.
6. Confirme a LabRole: `aws sts get-caller-identity` deve mostrar `LabRole`, sem pedir chaves.

## Apagar
EC2 > **Instâncias** > selecione > **Estado da instância > Encerrar instância**. Confira em **Volumes** e **IPs elásticos** se não sobrou nada.

## Por que configuramos assim (estudo para a arguição)

| Configuração | Motivo |
|---|---|
| LabRole pelo instance profile | Credenciais temporárias e automáticas. Sem chaves no código |
| API e worker em instâncias separadas | O processamento pesado não rouba CPU da API. Escalam de forma independente |
| `sg-api` com 8000 e 22 só do seu IP | Abre só o necessário |
| Variáveis em `.env` | Configuração fora do código. Cada ambiente tem a sua |

O worker usa a mesma lógica de máquina, rede e permissão. Ver [etapa 7](07-ec2-worker.md).

---
[← 1. RDS PostgreSQL](01-rds.md) | [Índice](README.md) | [3. S3 →](03-s3.md)
