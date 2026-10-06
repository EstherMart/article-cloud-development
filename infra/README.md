# Infraestrutura (Parte 2)

ALB e Auto Scaling Group para tornar a API elástica. **A pesquisar na documentação da AWS e preencher aqui.**

## Regras da spec

- Estratégia horizontal. Começa com uma instância (micro ou small).
- Um balanceador de carga à frente das instâncias.
- CPU média acima de 70% por mais de 1 minuto: sobe uma instância, até no máximo 3.
- CPU média do grupo abaixo de 25% por mais de 1 minuto: termina uma instância.
- O worker fica fora do ASG.

## Pré-requisito

A API precisa ser stateless e subir sozinha numa instância nova (user data ou AMI). Nenhum estado em disco ou memória da EC2.

## A registrar aqui

Launch template, target group e health check, política de scaling, IDs e nomes dos recursos, e o roteiro do vídeo da demonstração.
