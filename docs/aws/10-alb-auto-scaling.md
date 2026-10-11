# 10. ALB e Auto Scaling (Parte 2)

[← 9. Estudo geral](09-estudo-geral.md) | [Índice](README.md)

Faça esta etapa só depois de a API funcionar sozinha numa EC2 ([etapa 2](02-ec2-api.md)) com o front no S3 ([etapa 3b](03b-front-s3.md)).

## O que é
- **ALB** (Application Load Balancer) recebe os pedidos num só endereço e os distribui entre as instâncias saudáveis da API. Ele chama `GET /health/` em cada uma; a que não responde 200 sai do rodízio.
- **Auto Scaling Group (ASG)** mantém de 1 a 3 instâncias iguais. Um alarme de CPU acima de 70% cria uma; um alarme abaixo de 25% encerra uma.

```
Navegador --> ALB (porta 80) --> instância 1 (gunicorn :8000)
                             --> instância 2     (de 1 a 3, criadas pelo ASG)
                             --> instância 3
```

O worker fica fora do ASG. As instâncias nascem de uma **imagem (AMI)** da sua EC2 da API, então já vêm com o código, o `.env` e o `systemd` configurados.

## 1. Preparar a EC2 da API antes de tirar a imagem
1. Na EC2 `api`, confirme: `systemctl is-enabled api` devolve `enabled` (a API sobe sozinha quando a máquina liga).
2. No `.env`, `DJANGO_ALLOWED_HOSTS=*`. O health check do ALB chega com o **IP privado** da instância no cabeçalho `Host`, e esse IP muda a cada instância. É aceitável no laboratório; em produção, use o DNS do ALB e a faixa de IPs da VPC.
3. A mesma `DJANGO_SECRET_KEY` vale para todas as cópias (a imagem leva o `.env`). Sem isso, o token de login de uma instância é recusado por outra.
4. `CORS_ALLOWED_ORIGINS` com o endereço do site do front ([etapa 3b](03b-front-s3.md)).
5. Teste: `curl localhost:8000/health/` devolve `{"status": "ok"}`.

## 2. Security Groups
Crie o `sg-alb` e ajuste o `sg-api` (EC2 > Grupos de segurança):

| Grupo | Regra de entrada | Origem | Para quê |
|---|---|---|---|
| `sg-alb` (novo) | HTTP, TCP 80 | `0.0.0.0/0` | O mundo chama o ALB |
| `sg-api` | TCP 8000 | `sg-alb` | Só o ALB chama a API (mantenha a regra do SSH) |

## 3. Imagem e modelo de execução
**Imagem:** EC2 > Instâncias > `api` > **Ações > Imagem e modelos > Criar imagem**. Nome `api-imagem`. Espere ficar **Disponível**.

**Modelo:** EC2 > **Modelos de execução** > **Criar modelo de execução**.

| Campo | Valor | Por quê |
|---|---|---|
| Nome | `api-modelo` | |
| Imagem (AMI) | **Minhas AMIs** > `api-imagem` | Já traz a API pronta |
| Tipo de instância | `t3.micro` | A spec pede micro ou small |
| Par de chaves | `vockey` | SSH |
| Grupos de segurança | `sg-api` | |
| Detalhes avançados > Perfil de instância do IAM | `LabInstanceProfile` | A LabRole, sem chaves |
| Detalhes avançados > **Monitoramento detalhado do CloudWatch** | **Habilitar** | Sem isso a métrica de CPU chega de 5 em 5 minutos e o alarme de 1 minuto não funciona |

## 4. Target group e ALB
**Grupo de destino:** EC2 > **Grupos de destino** > **Criar**.

| Campo | Valor |
|---|---|
| Tipo | Instâncias |
| Nome | `api-destino` |
| Protocolo e porta | HTTP, **8000** |
| Caminho do health check | **`/health/`** |
| Intervalo / limite de saudável | 15 s / 2 (deixa o teste mais rápido) |

Não registre instâncias: o ASG faz isso.

**Balanceador:** EC2 > **Load Balancers** > **Criar** > **Application Load Balancer**.

| Campo | Valor |
|---|---|
| Nome | `api-alb` |
| Esquema | **Voltado para a Internet** |
| VPC e sub-redes | A padrão, com **pelo menos 2 zonas** marcadas |
| Grupo de segurança | `sg-alb` (remova o `default`) |
| Listener | HTTP, porta 80, encaminhar para `api-destino` |

Anote o **nome DNS** do ALB (`api-alb-123.us-east-1.elb.amazonaws.com`). É o endereço da API.

## 5. Auto Scaling Group
EC2 > **Grupos do Auto Scaling** > **Criar**.

| Campo | Valor | Por quê |
|---|---|---|
| Nome | `api-asg` | |
| Modelo de execução | `api-modelo` | |
| Rede | VPC padrão e as mesmas sub-redes (2 zonas) do ALB | |
| Balanceamento de carga | **Anexar a um balanceador existente** > `api-destino` | Registra as instâncias no destino |
| Verificações de integridade | Ligar **ELB** | Troca a instância que falha no `/health/` |
| Período de carência | 120 s | Tempo para o gunicorn subir |
| Capacidade desejada / mínima / máxima | **1 / 1 / 3** | Spec: começa com 1, vai até 3 |
| Políticas de escalabilidade | **Nenhuma** (criamos à mão, abaixo) | A regra é 70% e 25%, e a política de "rastreamento de destino" usa outros limites |

Em 2 a 3 minutos, o destino mostra 1 instância **healthy**.

## 6. Políticas e alarmes (a regra 70% e 25%)
No ASG > aba **Escalabilidade automática** > **Criar política de escalabilidade dinâmica**. Crie duas, tipo **Escalabilidade simples** (Simple scaling):

| | Sobe | Desce |
|---|---|---|
| Nome | `sobe-cpu` | `desce-cpu` |
| Alarme (criar novo) | CPUUtilization do grupo, **Média**, período **1 minuto**, **maior que 70**, **2 períodos consecutivos** | CPUUtilization do grupo, **Média**, período **1 minuto**, **menor que 25**, **2 períodos consecutivos** |
| Ação | **Adicionar 1** unidade de capacidade | **Remover 1** unidade de capacidade |
| Espera (cooldown) | 120 s | 120 s |

Dois períodos de 1 minuto atendem "mais de um minuto" da spec. A métrica fica em CloudWatch > EC2 > **Por grupo do Auto Scaling**.

## 7. Apontar o front para o ALB
```
infra/publicar_front.sh <bucket-do-site> http://<DNS do ALB>
```
E, se o endereço do site mudou, atualize `CORS_ALLOWED_ORIGINS` (já está na imagem; reinicie com uma nova imagem se precisar mudar).

## 8. Testar
**Configuração:** `RDS_INSTANCE_ID` e os outros nomes no `.env`, mais `ASG_NAME=api-asg` e `ALB_NAME=api-alb`, e rode:

```
RUN_AWS_INTEGRATION=1 python manage.py test articles.tests.integration.test_especificacao.Parte2_LoadBalancerEAutoScaling
```

**Balanceamento:** `curl http://<DNS do ALB>/health/` várias vezes devolve 200. No destino, as instâncias aparecem **healthy**.

**Elasticidade (para o vídeo):**
1. Mostre o ASG com 1 instância (EC2 > Instâncias e a aba **Atividade** do ASG).
2. Gere CPU na instância (SSH): `sudo dnf install -y stress-ng && stress-ng --cpu 2 --timeout 600`. Também serve carga pelo ALB, de outra máquina: `ab -n 100000 -c 50 "http://<DNS do ALB>/articles/search/?q=nuvem"`.
3. Em 2 a 3 minutos o alarme `sobe-cpu` entra em estado de **alarme** e o ASG cria uma instância; com a carga mantida, chega a 3. Mostre o CloudWatch, a aba Atividade e a lista de instâncias.
4. Pare a carga. A CPU cai abaixo de 25%, o alarme `desce-cpu` dispara e uma instância é encerrada (leva alguns minutos, por causa dos períodos e do cooldown).
5. Abra o front pelo site do S3 durante o teste: a aplicação continua respondendo.

## O que pode dar errado
| Sintoma | Causa provável |
|---|---|
| Destino com instância `unhealthy` | `DJANGO_ALLOWED_HOSTS` sem o IP privado (use `*`), `sg-api` sem a regra do `sg-alb` na 8000, ou o `systemd` não sobe a API na imagem |
| 502 ou 503 do ALB | Nenhuma instância saudável ainda (espere o período de carência) |
| O alarme nunca dispara | Monitoramento detalhado desligado no modelo, ou a CPU não passou de 70% |
| O login funciona numa chamada e falha na outra | `DJANGO_SECRET_KEY` diferente entre as instâncias |
| O front mostra erro de CORS | `CORS_ALLOWED_ORIGINS` não tem o endereço do site |
| Instância nova nasce sem o último código | A imagem é antiga. Crie outra imagem e um modelo novo |
| O ASG não cria o grupo | Sub-redes de uma só zona, ou o modelo sem `LabInstanceProfile` |

## Custo
O ALB cobra por hora enquanto existir (centavos por hora). As instâncias extras só existem durante a carga. Apague tudo no fim do dia.

## Apagar
Nesta ordem: ASG (encerra as instâncias), ALB, grupo de destino, modelo de execução, **imagem (AMI)** e o **snapshot** dela (EC2 > Snapshots), `sg-alb`.

## Por que configuramos assim (estudo para a arguição)

| Configuração | Motivo |
|---|---|
| Health check em `/health/` sem banco | Se dependesse do RDS, uma queda do banco marcaria todas as instâncias como doentes e o ASG as recriaria em loop |
| API stateless, token assinado | Qualquer instância atende qualquer pedido, desde que a `DJANGO_SECRET_KEY` seja a mesma |
| Front no S3, fora do ASG | Entregar arquivo estático não gasta CPU; o ASG escala só o que pesa |
| Política simples com alarmes | É a que expressa literalmente "acima de 70% por mais de um minuto" e "abaixo de 25%" |
| Monitoramento detalhado | A métrica de CPU de 1 minuto só existe com ele |
| Mínimo 1, máximo 3 | Regra da spec |
| Worker fora do ASG | O processamento pesado não deve competir nem escalar junto com a API |

---
[← 9. Estudo geral](09-estudo-geral.md) | [Índice](README.md)
