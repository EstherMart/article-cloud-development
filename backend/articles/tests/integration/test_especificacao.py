"""A configuração na AWS cumpre o que a aplicação precisa? Um grupo de testes por requisito da especificação.

Só lê (describe, get): não cria nem altera nada. Cada classe se pula sozinha se faltar variável do .env.
Os nomes dos recursos vêm do ambiente (ver README desta pasta). Rode depois de criar cada serviço.
"""
import json
import os
import urllib.request

from .base import AwsIntegrationTestCase

TIPOS_PEQUENOS = ('t2.micro', 't3.micro', 't2.small', 't3.small')


def cliente(servico):
    from articles.services.aws import client

    return client(servico)


def http(url, headers=None, metodo='GET'):
    req = urllib.request.Request(url, headers=headers or {}, method=metodo)
    with urllib.request.urlopen(req, timeout=15) as resposta:
        return resposta.status, dict(resposta.headers), resposta.read()


def instancia_por_nome(nome):
    resposta = cliente('ec2').describe_instances(Filters=[
        {'Name': 'tag:Name', 'Values': [nome]},
        {'Name': 'instance-state-name', 'Values': ['running']},
    ])
    instancias = [i for r in resposta['Reservations'] for i in r['Instances']]
    return instancias[0] if instancias else None


class Req1_Ec2_Api(AwsIntegrationTestCase):
    """Requisito 1: a aplicação roda em instância EC2 (API e worker em máquinas separadas)."""
    REQUIRED_ENV = ('API_BASE_URL',)

    def setUp(self):
        self.api = instancia_por_nome(os.environ.get('API_INSTANCE_NAME', 'api'))
        self.worker = instancia_por_nome(os.environ.get('WORKER_INSTANCE_NAME', 'worker'))

    def test_api_responde_no_health_check(self):
        status, _, corpo = http(os.environ['API_BASE_URL'].rstrip('/') + '/health/')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(corpo)['status'], 'ok')

    def test_instancia_da_api_esta_rodando_em_tipo_micro_ou_small(self):
        self.assertIsNotNone(self.api, 'nenhuma EC2 com a tag Name=api em execução')
        self.assertIn(self.api['InstanceType'], TIPOS_PEQUENOS)

    def test_instancia_usa_a_role_do_laboratorio_e_nao_chaves(self):
        self.assertIsNotNone(self.api)
        self.assertIn('IamInstanceProfile', self.api, 'sem instance profile: o boto3 não acha credenciais')

    def test_worker_roda_em_outra_instancia(self):
        self.assertIsNotNone(self.worker, 'nenhuma EC2 com a tag Name=worker em execução')
        self.assertIsNotNone(self.api)
        self.assertNotEqual(self.worker['InstanceId'], self.api['InstanceId'])

    def test_banco_e_cache_nao_estao_abertos_para_a_internet(self):
        for grupo in cliente('ec2').describe_security_groups()['SecurityGroups']:
            for regra in grupo['IpPermissions']:
                if not any(r['CidrIp'] == '0.0.0.0/0' for r in regra.get('IpRanges', [])):
                    continue
                portas = range(regra.get('FromPort', 0), regra.get('ToPort', 65535) + 1)
                for porta in (5432, 6379):
                    self.assertNotIn(porta, portas, f'{grupo["GroupName"]}: porta {porta} aberta para o mundo')


class Req2_Rds(AwsIntegrationTestCase):
    """Requisito 2: dados da aplicação em banco relacional criado pelo Amazon RDS."""
    REQUIRED_ENV = ('RDS_INSTANCE_ID', 'DB_HOST')

    def setUp(self):
        self.rds = cliente('rds').describe_db_instances(DBInstanceIdentifier=os.environ['RDS_INSTANCE_ID'])['DBInstances'][0]

    def test_instancia_esta_disponivel_e_e_postgresql(self):
        self.assertEqual(self.rds['DBInstanceStatus'], 'available')
        self.assertEqual(self.rds['Engine'], 'postgres')

    def test_o_django_aponta_para_esta_instancia(self):
        self.assertEqual(self.rds['Endpoint']['Address'], os.environ['DB_HOST'])

    def test_banco_do_projeto_foi_criado(self):
        self.assertEqual(self.rds['DBName'], os.environ.get('DB_NAME', 'metadata'))

    def test_instancia_e_de_laboratorio_sem_multi_az(self):
        self.assertTrue(self.rds['DBInstanceClass'].startswith('db.t'))
        self.assertFalse(self.rds['MultiAZ'])


class Req3_S3(AwsIntegrationTestCase):
    """Requisito 3: arquivos binários (PDF) no Amazon S3, em bucket privado."""
    REQUIRED_ENV = ('S3_BUCKET',)

    def setUp(self):
        self.s3 = cliente('s3')
        self.bucket = os.environ['S3_BUCKET']

    def test_bucket_existe_na_regiao_da_aplicacao(self):
        regiao = self.s3.get_bucket_location(Bucket=self.bucket)['LocationConstraint'] or 'us-east-1'
        self.assertEqual(regiao, os.environ.get('AWS_REGION', 'us-east-1'))

    def test_bucket_bloqueia_todo_acesso_publico(self):
        bloqueio = self.s3.get_public_access_block(Bucket=self.bucket)['PublicAccessBlockConfiguration']
        self.assertTrue(all(bloqueio.values()), bloqueio)

    def test_objetos_sao_criptografados_em_repouso(self):
        regras = self.s3.get_bucket_encryption(Bucket=self.bucket)['ServerSideEncryptionConfiguration']['Rules']
        self.assertTrue(regras)


class Req4_ElastiCache(AwsIntegrationTestCase):
    """Requisito 4: ElastiCache (Redis) como camada de cache."""
    REQUIRED_ENV = ('ELASTICACHE_ID', 'REDIS_URL')

    def setUp(self):
        elasticache = cliente('elasticache')
        nome = os.environ['ELASTICACHE_ID']
        try:
            cluster = elasticache.describe_cache_clusters(CacheClusterId=nome, ShowCacheNodeInfo=True)['CacheClusters'][0]
            self.cluster = {
                'status': cluster['CacheClusterStatus'], 'engine': cluster['Engine'],
                'endereco': cluster['CacheNodes'][0]['Endpoint']['Address'],
                'transito': cluster.get('TransitEncryptionEnabled', False),
            }
        except elasticache.exceptions.CacheClusterNotFoundFault:
            # Cluster sem modo cluster criado pelo console é um replication group (nó: <nome>-001).
            grupo = elasticache.describe_replication_groups(ReplicationGroupId=nome)['ReplicationGroups'][0]
            self.cluster = {
                'status': grupo['Status'], 'engine': 'redis',
                'endereco': grupo['NodeGroups'][0]['PrimaryEndpoint']['Address'],
                'transito': grupo.get('TransitEncryptionEnabled', False),
            }

    def test_cluster_esta_disponivel_e_e_redis(self):
        self.assertEqual(self.cluster['status'], 'available')
        self.assertEqual(self.cluster['engine'], 'redis')

    def test_redis_url_aponta_para_o_cluster(self):
        self.assertIn(self.cluster['endereco'], os.environ['REDIS_URL'])

    def test_sem_criptografia_em_transito_porque_o_codigo_usa_redis_simples(self):
        self.assertTrue(os.environ['REDIS_URL'].startswith('redis://'))
        self.assertFalse(self.cluster['transito'])

    def test_o_cache_funciona_pela_api(self):
        from articles.services import cache

        self.assertTrue(cache.get_client().ping())


class Req5_DynamoDb(AwsIntegrationTestCase):
    """Requisito 5: ações do CRUD logadas em banco NoSQL (DynamoDB), com ação, dados e hora."""
    REQUIRED_ENV = ('DYNAMODB_TABLE',)

    def setUp(self):
        self.tabela = cliente('dynamodb').describe_table(TableName=os.environ['DYNAMODB_TABLE'])['Table']

    def test_tabela_esta_ativa_e_sob_demanda(self):
        self.assertEqual(self.tabela['TableStatus'], 'ACTIVE')
        self.assertEqual(self.tabela['BillingModeSummary']['BillingMode'], 'PAY_PER_REQUEST')

    def test_chave_e_a_que_o_codigo_grava(self):
        chaves = {k['KeyType']: k['AttributeName'] for k in self.tabela['KeySchema']}
        tipos = {a['AttributeName']: a['AttributeType'] for a in self.tabela['AttributeDefinitions']}
        self.assertEqual(chaves, {'HASH': 'article_id', 'RANGE': 'timestamp'})
        self.assertEqual(tipos, {'article_id': 'S', 'timestamp': 'S'})


class Req6_SnsSqs(AwsIntegrationTestCase):
    """Requisito 6: processamento desacoplado da API por SNS e SQS (com DLQ)."""
    REQUIRED_ENV = ('SNS_TOPIC_ARN', 'SQS_QUEUE_URL', 'SQS_DLQ_URL')

    def setUp(self):
        self.sqs = cliente('sqs')
        self.sns = cliente('sns')
        self.fila = self.sqs.get_queue_attributes(QueueUrl=os.environ['SQS_QUEUE_URL'], AttributeNames=['All'])['Attributes']
        self.dlq = self.sqs.get_queue_attributes(QueueUrl=os.environ['SQS_DLQ_URL'], AttributeNames=['All'])['Attributes']

    def test_fila_recebe_do_topico_com_entrega_bruta(self):
        assinaturas = self.sns.list_subscriptions_by_topic(TopicArn=os.environ['SNS_TOPIC_ARN'])['Subscriptions']
        da_fila = [a for a in assinaturas if a['Endpoint'] == self.fila['QueueArn']]
        self.assertTrue(da_fila, 'a fila não está assinada no tópico')
        atributos = self.sns.get_subscription_attributes(SubscriptionArn=da_fila[0]['SubscriptionArn'])['Attributes']
        self.assertEqual(atributos.get('RawMessageDelivery'), 'true')

    def test_fila_permite_que_o_topico_envie(self):
        politica = json.loads(self.fila['Policy'])
        origem = json.dumps(politica)
        self.assertIn(os.environ['SNS_TOPIC_ARN'], origem)
        self.assertIn('sqs:SendMessage', origem)

    def test_long_polling_e_visibilidade_maior_que_o_processamento(self):
        self.assertEqual(self.fila['ReceiveMessageWaitTimeSeconds'], '20')
        self.assertGreaterEqual(int(self.fila['VisibilityTimeout']), 60)

    def test_dlq_recebe_depois_de_3_tentativas(self):
        redrive = json.loads(self.fila['RedrivePolicy'])
        self.assertEqual(redrive['deadLetterTargetArn'], self.dlq['QueueArn'])
        self.assertEqual(int(redrive['maxReceiveCount']), 3)

    def test_dlq_guarda_as_mensagens_por_14_dias(self):
        self.assertEqual(int(self.dlq['MessageRetentionPeriod']), 14 * 24 * 3600)


class Req7_InterfaceGrafica(AwsIntegrationTestCase):
    """Requisito 7: interface gráfica (telas no bucket S3 de site estático, falando com a API por CORS)."""
    REQUIRED_ENV = ('FRONT_URL', 'API_BASE_URL')

    def test_site_abre_e_e_html(self):
        status, _, corpo = http(os.environ['FRONT_URL'])
        self.assertEqual(status, 200)
        self.assertIn(b'<html', corpo.lower())

    def test_todas_as_telas_estao_publicadas(self):
        base = os.environ['FRONT_URL'].rstrip('/')
        for tela in ('index', 'login', 'cadastro', 'artigos', 'artigo', 'meus_artigos', 'criar_artigo', 'editar_artigo'):
            with self.subTest(tela=tela):
                self.assertEqual(http(f'{base}/{tela}.html')[0], 200)

    def test_front_aponta_para_a_api_da_nuvem_e_nao_para_localhost(self):
        _, _, config = http(os.environ['FRONT_URL'].rstrip('/') + '/js/config.js')
        self.assertNotIn(b'127.0.0.1', config)
        self.assertIn(os.environ['API_BASE_URL'].rstrip('/').encode(), config)

    def test_api_autoriza_a_origem_do_site_por_cors(self):
        origem = os.environ['FRONT_URL'].rstrip('/')
        _, cabecalhos, _ = http(
            os.environ['API_BASE_URL'].rstrip('/') + '/articles/',
            headers={'Origin': origem, 'Access-Control-Request-Method': 'GET'}, metodo='OPTIONS')
        permitida = {k.lower(): v for k, v in cabecalhos.items()}.get('access-control-allow-origin')
        self.assertEqual(permitida, origem, 'ajuste CORS_ALLOWED_ORIGINS na API')


class Parte2_LoadBalancerEAutoScaling(AwsIntegrationTestCase):
    """Parte 2: ALB na frente da aplicação e Auto Scaling de 1 a 3 instâncias (sobe com CPU > 70%, desce com < 25%)."""
    REQUIRED_ENV = ('ASG_NAME', 'ALB_NAME')

    def setUp(self):
        self.asg = cliente('autoscaling').describe_auto_scaling_groups(
            AutoScalingGroupNames=[os.environ['ASG_NAME']])['AutoScalingGroups'][0]
        self.elb = cliente('elbv2')
        self.alb = self.elb.describe_load_balancers(Names=[os.environ['ALB_NAME']])['LoadBalancers'][0]

    def _politicas(self):
        return cliente('autoscaling').describe_policies(AutoScalingGroupName=os.environ['ASG_NAME'])['ScalingPolicies']

    def _alarmes(self):
        paginas = cliente('cloudwatch').get_paginator('describe_alarms').paginate()
        alarmes = [a for pagina in paginas for a in pagina['MetricAlarms']]
        return [a for a in alarmes if {'Name': 'AutoScalingGroupName', 'Value': os.environ['ASG_NAME']} in a['Dimensions']]

    def test_grupo_tem_minimo_1_e_maximo_3(self):
        self.assertEqual(self.asg['MinSize'], 1)
        self.assertEqual(self.asg['MaxSize'], 3)
        self.assertGreaterEqual(self.asg['DesiredCapacity'], 1)

    def test_instancias_do_grupo_sao_micro_ou_small(self):
        ids = [i['InstanceId'] for i in self.asg['Instances']]
        self.assertTrue(ids, 'o grupo está sem instâncias')
        tipos = {i['InstanceType'] for r in cliente('ec2').describe_instances(InstanceIds=ids)['Reservations']
                 for i in r['Instances']}
        self.assertTrue(tipos <= set(TIPOS_PEQUENOS), tipos)

    def test_alb_e_publico_e_escuta_na_porta_80(self):
        self.assertEqual(self.alb['Scheme'], 'internet-facing')
        portas = [l['Port'] for l in self.elb.describe_listeners(LoadBalancerArn=self.alb['LoadBalancerArn'])['Listeners']]
        self.assertIn(80, portas)

    def test_health_check_do_alb_usa_a_rota_sem_banco(self):
        alvos = self.elb.describe_target_groups(LoadBalancerArn=self.alb['LoadBalancerArn'])['TargetGroups']
        self.assertTrue(alvos)
        self.assertEqual(alvos[0]['HealthCheckPath'], '/health/')

    def test_ha_instancia_saudavel_atras_do_alb(self):
        alvos = self.elb.describe_target_groups(LoadBalancerArn=self.alb['LoadBalancerArn'])['TargetGroups']
        saude = self.elb.describe_target_health(TargetGroupArn=alvos[0]['TargetGroupArn'])['TargetHealthDescriptions']
        self.assertIn('healthy', [s['TargetHealth']['State'] for s in saude])

    def test_alarme_de_cpu_acima_de_70_por_1_minuto_adiciona_instancia(self):
        arns_que_sobem = {p['PolicyARN'] for p in self._politicas() if self._ajuste(p) > 0}
        alarmes = [a for a in self._alarmes() if a['MetricName'] == 'CPUUtilization'
                   and a['Threshold'] == 70 and 'Greater' in a['ComparisonOperator']]
        self.assertTrue(alarmes, 'falta o alarme de CPU > 70%')
        self.assertTrue(any(set(a['AlarmActions']) & arns_que_sobem for a in alarmes))
        self.assertTrue(all(a['Period'] * a['EvaluationPeriods'] >= 60 for a in alarmes))

    def test_alarme_de_cpu_abaixo_de_25_por_1_minuto_remove_instancia(self):
        arns_que_descem = {p['PolicyARN'] for p in self._politicas() if self._ajuste(p) < 0}
        alarmes = [a for a in self._alarmes() if a['MetricName'] == 'CPUUtilization'
                   and a['Threshold'] == 25 and 'Less' in a['ComparisonOperator']]
        self.assertTrue(alarmes, 'falta o alarme de CPU < 25%')
        self.assertTrue(any(set(a['AlarmActions']) & arns_que_descem for a in alarmes))
        self.assertTrue(all(a['Period'] * a['EvaluationPeriods'] >= 60 for a in alarmes))

    @staticmethod
    def _ajuste(politica):
        if 'StepAdjustments' in politica and politica['StepAdjustments']:
            return politica['StepAdjustments'][0]['ScalingAdjustment']
        return politica.get('ScalingAdjustment', 0)
