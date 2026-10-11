"""Artigos de demonstração para a arguição (autores e pessoas fictícios).

Usados pela migration `0005_artigos_de_demonstracao` e pelo comando `carregar_demo_pdfs`.
Não altere os títulos depois de aplicar a migration: o comando encontra os artigos por título.

Os resumos em inglês (`translated`) simulam o que o worker grava. Todos nascem PROCESSADO: a lista,
a busca e o detalhe mostram o site já com dados. Para mostrar o worker e o reprocessamento ao vivo,
cadastre um artigo novo pelo front.
"""

USUARIO_DEMO = 'demo'

ARTIGOS = [
    {
        'title': 'Arquitetura em Nuvem para Repositórios de Artigos Científicos',
        'area': 'Computação em Nuvem',
        'authors': ['Ana Souza', 'Bruno Lima'],
        'tags': ['nuvem', 'AWS', 'armazenamento', 'cache'],
        'abstract': (
            'Este trabalho descreve uma arquitetura em nuvem para armazenar e consultar artigos '
            'acadêmicos. Os metadados ficam em banco relacional, os PDFs em armazenamento de objetos '
            'e as consultas frequentes em cache. A solução reduz o tempo de resposta das buscas.'
        ),
        'translated': (
            'This work describes a cloud architecture to store and query academic articles. Metadata '
            'is kept in a relational database, PDFs in object storage, and frequent queries in a cache. '
            'The solution reduces search response time.'
        ),
        'status': 'PROCESSADO',
    },
    {
        'title': 'Cache com Redis para Acelerar Consultas em Bases Acadêmicas',
        'area': 'Banco de Dados',
        'authors': ['Carla Mendes', 'Ana Souza'],
        'tags': ['Redis', 'cache', 'desempenho', 'ElastiCache'],
        'abstract': (
            'Avaliamos o padrão cache-aside com Redis em consultas de listagem e busca. Mostramos como '
            'a invalidação a cada escrita e um tempo de vida curto evitam dados desatualizados, '
            'sem sobrecarregar o banco relacional nos momentos de pico.'
        ),
        'translated': (
            'We evaluate the cache-aside pattern with Redis for listing and search queries. We show how '
            'invalidation on every write and a short time to live avoid stale data without overloading '
            'the relational database at peak times.'
        ),
        'status': 'PROCESSADO',
    },
    {
        'title': 'Processamento Assíncrono com SNS e SQS em Sistemas de Publicação',
        'area': 'Sistemas Distribuídos',
        'authors': ['Diego Alves', 'Bruno Lima'],
        'tags': ['SNS', 'SQS', 'mensageria', 'desacoplamento'],
        'abstract': (
            'A API publica um evento a cada novo artigo e responde ao usuário sem esperar. Um worker '
            'consome a fila, extrai o texto do PDF e traduz o resumo. Mensagens que falham três vezes '
            'seguem para uma fila de descarte, o que evita bloquear o restante do processamento.'
        ),
        'translated': (
            'The API publishes an event for each new article and answers the user without waiting. A worker '
            'consumes the queue, extracts the PDF text and translates the abstract. Messages that fail three '
            'times go to a dead-letter queue, which avoids blocking the rest of the processing.'
        ),
        'status': 'PROCESSADO',
    },
    {
        'title': 'Modelagem Relacional de Artigos, Autores e Palavras-chave',
        'area': 'Banco de Dados',
        'authors': ['Elisa Ferreira'],
        'tags': ['PostgreSQL', 'modelagem', 'RDS', 'relação N:N'],
        'abstract': (
            'O modelo relaciona artigos, autores e palavras-chave por tabelas de ligação. O título é '
            'único para evitar cadastros duplicados do mesmo trabalho, e a exclusão de um usuário '
            'remove os seus artigos em cascata.'
        ),
        'translated': (
            'The model relates articles, authors and keywords through join tables. The title is unique to '
            'avoid duplicate records of the same work, and deleting a user removes their articles in cascade.'
        ),
        'status': 'PROCESSADO',
    },
    {
        'title': 'Elasticidade Horizontal com Auto Scaling Groups',
        'area': 'Computação em Nuvem',
        'authors': ['Felipe Costa', 'Diego Alves'],
        'tags': ['Auto Scaling', 'ALB', 'elasticidade', 'CPU'],
        'abstract': (
            'Uma instância inicial atende a aplicação. Quando a média de CPU passa de 70% por mais de um '
            'minuto, o grupo cria novas instâncias, até o máximo de três. Quando cai abaixo de 25%, '
            'uma instância é encerrada. Descrevemos o comportamento observado em um teste de carga.'
        ),
        'translated': (
            'A single initial instance serves the application. When average CPU stays above 70% for more '
            'than one minute, the group creates new instances, up to a maximum of three. When it drops '
            'below 25%, one instance is terminated. We describe the behavior observed in a load test.'
        ),
        'status': 'PROCESSADO',
    },
    {
        'title': 'Tradução Automática de Resumos Científicos com Modelos de Linguagem',
        'area': 'Inteligência Artificial',
        'authors': ['Gabriela Rocha', 'Ana Souza'],
        'tags': ['tradução', 'PLN', 'Gemini', 'resumo'],
        'abstract': (
            'Comparamos a tradução de resumos científicos do português para o inglês feita por um modelo '
            'de linguagem. Termos técnicos como PostgreSQL e Auto Scaling devem permanecer intactos, e '
            'números e porcentagens precisam ser preservados.'
        ),
        'translated': (
            'We compare the translation of scientific abstracts from Portuguese to English performed by a '
            'language model. Technical terms such as PostgreSQL and Auto Scaling must remain intact, and '
            'numbers and percentages must be preserved.'
        ),
        'status': 'PROCESSADO',
    },
    {
        'title': 'Segurança de Objetos no S3: URLs Pré-assinadas e Buckets Privados',
        'area': 'Segurança da Informação',
        'authors': ['Henrique Dias', 'Carla Mendes'],
        'tags': ['S3', 'segurança', 'URL pré-assinada', 'privacidade'],
        'abstract': (
            'Discutimos como manter os PDFs em um bucket privado e liberar o download por URLs '
            'pré-assinadas de curta duração. O arquivo vai direto do S3 ao navegador, sem passar pela '
            'API, e o link deixa de funcionar depois de alguns minutos.'
        ),
        'translated': (
            'We discuss how to keep PDFs in a private bucket and allow downloads through short-lived '
            'presigned URLs. The file goes straight from S3 to the browser, without passing through the '
            'API, and the link stops working after a few minutes.'
        ),
        'status': 'PROCESSADO',
    },
    {
        'title': 'Registro de Auditoria em Bancos NoSQL com DynamoDB',
        'area': 'Banco de Dados',
        'authors': ['Elisa Ferreira', 'Felipe Costa'],
        'tags': ['DynamoDB', 'NoSQL', 'auditoria', 'log'],
        'abstract': (
            'Cada criação, atualização e exclusão de artigo gera um registro com a ação, os dados e a '
            'hora. A tabela usa o identificador do artigo como chave de partição e o horário como '
            'chave de ordenação, o que mantém o histórico de cada artigo em ordem.'
        ),
        'translated': (
            'Every creation, update and deletion of an article generates a record with the action, the data '
            'and the time. The table uses the article identifier as partition key and the timestamp as sort '
            'key, which keeps the history of each article in order.'
        ),
        'status': 'PROCESSADO',
    },
    {
        'title': 'Autenticação por Token em APIs REST para Aplicações Web',
        'area': 'Engenharia de Software',
        'authors': ['Henrique Dias', 'Bruno Lima'],
        'tags': ['API REST', 'autenticação', 'token', 'Django'],
        'abstract': (
            'Apresentamos uma autenticação com token assinado para uma API REST em Django. Somente o dono '
            'de um artigo pode alterá-lo ou excluí-lo, e um token adulterado é recusado. Discutimos os '
            'limites da abordagem, como a ausência de revogação antes da expiração.'
        ),
        'translated': (
            'We present signed-token authentication for a REST API in Django. Only the owner of an article '
            'can change or delete it, and a tampered token is rejected. We discuss the limits of the '
            'approach, such as the lack of revocation before expiration.'
        ),
        'status': 'PROCESSADO',
    },
    {
        'title': 'Extração de Texto de PDFs: Desafios com Documentos Escaneados',
        'area': 'Inteligência Artificial',
        'authors': ['Gabriela Rocha', 'Diego Alves'],
        'tags': ['PDF', 'extração de texto', 'OCR', 'pypdf'],
        'abstract': (
            'PDFs escaneados não têm camada de texto, e bibliotecas de extração devolvem texto vazio. '
            'Quando o resumo digitado também está vazio, o processamento não tem o que traduzir e o '
            'artigo termina em erro. O reprocessamento só ajuda depois de corrigir a causa.'
        ),
        'translated': (
            'Scanned PDFs have no text layer, and extraction libraries return empty text. When the typed '
            'abstract is also empty, processing has nothing to translate and the article ends in error. '
            'Reprocessing only helps after the cause is fixed.'
        ),
        'status': 'PROCESSADO',
    },
    {
        'title': 'Testes de Integração em Serviços de Nuvem: Estratégias e Custos',
        'area': 'Engenharia de Software',
        'authors': ['Carla Mendes', 'Felipe Costa'],
        'tags': ['testes', 'integração', 'AWS', 'custos'],
        'abstract': (
            'Testes que usam a nuvem de verdade encontram erros que simulações não encontram, como senha '
            'errada, firewall fechado e permissão ausente. Sugerimos desligá-los por padrão, criar os '
            'próprios dados e apagar tudo ao final para não gerar custo.'
        ),
        'translated': (
            'Tests that use the real cloud find errors that simulations do not, such as a wrong password, a '
            'closed firewall and a missing permission. We suggest turning them off by default, creating '
            'their own data and deleting everything at the end to avoid costs.'
        ),
        'status': 'PROCESSADO',
    },
    {
        'title': 'Balanceamento de Carga e Alta Disponibilidade em Aplicações Web',
        'area': 'Redes de Computadores',
        'authors': ['Ana Souza', 'Felipe Costa'],
        'tags': ['balanceamento de carga', 'ALB', 'disponibilidade', 'health check'],
        'abstract': (
            'O balanceador distribui as requisições entre as instâncias e remove do rodízio as que falham '
            'no health check. Mostramos por que o health check não deve depender do banco de dados: uma '
            'queda do banco derrubaria todas as instâncias ao mesmo tempo.'
        ),
        'translated': (
            'The load balancer distributes requests among instances and removes from rotation those that fail '
            'the health check. We show why the health check should not depend on the database: a database '
            'outage would take down all instances at once.'
        ),
        'status': 'PROCESSADO',
    },
]

# Parágrafos de apoio, usados para dar corpo (várias páginas) aos PDFs de demonstração e de teste.
PARAGRAFOS = [
    'Repositórios de artigos científicos concentram dados de natureza diferente. Os metadados, como título, '
    'autores e palavras-chave, são pequenos e relacionais. O arquivo em PDF é grande e binário. Tratar os dois '
    'do mesmo jeito torna o banco pesado e caro, por isso cada tipo de dado fica no serviço mais adequado.',
    'O armazenamento de objetos é barato e feito para arquivos. O banco guarda apenas o caminho do arquivo. '
    'Quando o usuário pede o download, a aplicação gera um endereço temporário e o navegador baixa o PDF '
    'diretamente do armazenamento, sem que o arquivo passe pelo servidor da aplicação.',
    'Consultas frequentes, como a lista dos artigos mais recentes, repetem o mesmo resultado muitas vezes. '
    'Um cache em memória guarda a resposta por alguns minutos. A cada criação, alteração ou exclusão, as '
    'chaves afetadas são apagadas, de modo que o usuário nunca vê um dado muito antigo.',
    'O processamento de cada arquivo recebido pode demorar. Para não deixar o usuário esperando, a aplicação '
    'publica um aviso em um tópico e responde na hora. Uma fila recebe o aviso e um serviço separado, o '
    'worker, faz o trabalho pesado e grava o resultado quando termina.',
    'Se o worker falhar, a mensagem volta para a fila e é tentada de novo. Depois de três tentativas sem '
    'sucesso, ela vai para uma fila de descarte, onde pode ser analisada. Como a mesma mensagem pode chegar '
    'duas vezes, o processamento precisa produzir o mesmo resultado nas duas.',
    'A tradução do resumo usa um modelo de linguagem. Termos técnicos, nomes de serviços e números devem '
    'ser preservados. Quando o autor não digita o resumo, o worker usa o texto extraído do PDF. Se o PDF '
    'for uma imagem escaneada, não há texto e o artigo é marcado com erro.',
    'Todas as ações de criação, atualização e exclusão são registradas em um banco não relacional, com o '
    'tipo da ação, os dados manipulados e a hora. O registro continua existindo depois que o artigo é '
    'apagado, o que permite auditar o que aconteceu com cada trabalho.',
    'Para tornar a aplicação elástica, um balanceador distribui as requisições entre as instâncias. Quando '
    'a média de uso de CPU passa de 70% por mais de um minuto, uma nova instância é criada, até o máximo '
    'de três. Abaixo de 25%, uma instância é encerrada. Todas precisam usar a mesma chave de assinatura.',
]

PARAGRAFOS_EN = [
    'Academic repositories hold data of different natures. Metadata such as title, authors and keywords is '
    'small and relational. The PDF file is large and binary. Treating both the same way makes the database '
    'heavy and expensive, so each kind of data lives in the service that suits it best.',
    'Object storage is cheap and built for files. The database keeps only the path of the file. When the user '
    'asks for a download, the application generates a temporary address and the browser downloads the PDF '
    'directly from storage, without the file passing through the application server.',
    'Frequent queries, such as the list of the most recent articles, repeat the same result many times. An '
    'in-memory cache keeps the answer for a few minutes. On every creation, change or deletion, the affected '
    'keys are erased, so the user never sees data that is too old.',
    'Processing each received file can take a while. To avoid keeping the user waiting, the application '
    'publishes a notice to a topic and answers right away. A queue receives the notice and a separate '
    'service, the worker, does the heavy work and stores the result when it finishes.',
]


def secoes_demo(artigo):
    """Seções de um PDF de demonstração com mais de uma página para o artigo dado."""
    titulos = ['Introdução', 'Fundamentação', 'Arquitetura proposta', 'Discussão', 'Conclusão']
    secoes = [
        ('Resumo', [artigo['abstract']]),
        ('Palavras-chave', [', '.join(artigo['tags']) + '.']),
    ]
    for posicao, titulo in enumerate(titulos):
        corpo = [PARAGRAFOS[(posicao + deslocamento) % len(PARAGRAFOS)] for deslocamento in range(3)]
        secoes.append((titulo, corpo))
    return secoes
