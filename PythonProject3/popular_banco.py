import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

DATABASE = 'unievangelica.db'


def popular_dados_ficticios():
    """Popular banco com usuários, curtidas e comentários fictícios"""

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    print("🚀 Iniciando população de dados fictícios...\n")

    # 1. CRIAR USUÁRIOS FICTÍCIOS
    print("👥 Criando usuários fictícios...")
    usuarios_ficticios = [
        ('Maria Santos', '2521001', 'maria.santos@aluno.unievangelica.edu.br', 'Inteligência Artificial'),
        ('Carlos Mendes', '2521002', 'carlos.mendes@aluno.unievangelica.edu.br', 'Inteligência Artificial'),
        ('Ana Costa', '2521003', 'ana.costa@aluno.unievangelica.edu.br', 'Inteligência Artificial'),
        ('Pedro Alves', '2521004', 'pedro.alves@aluno.unievangelica.edu.br', 'Análise e Desenvolvimento de Sistemas'),
        ('Julia Fernandes', '2521005', 'julia.fernandes@aluno.unievangelica.edu.br', 'Engenharia de Software'),
        ('Lucas Ferreira', '2521006', 'lucas.ferreira@aluno.unievangelica.edu.br', 'Análise e Desenvolvimento de Sistemas'),
        ('Beatriz Lima', '2521007', 'beatriz.lima@aluno.unievangelica.edu.br', 'Análise e Desenvolvimento de Sistemas'),
        ('Rafael Souza', '2521008', 'rafael.souza@aluno.unievangelica.edu.br', 'Engenharia de Software'),
        ('Gabriel Martins', '2521009', 'gabriel.martins@aluno.unievangelica.edu.br', 'Engenharia de Software'),
        ('Fernanda Costa', '2521010', 'fernanda.costa@aluno.unievangelica.edu.br', 'Análise e Desenvolvimento de Sistemas'),
        ('Rafael Costa', '2521011', 'rafael.costa@aluno.unievangelica.edu.br', 'Análise e Desenvolvimento de Sistemas'),
        ('Ricardo Silva', '2521012', 'ricardo.silva@aluno.unievangelica.edu.br', 'Análise e Desenvolvimento de Sistemas'),
        ('Thiago Ribeiro', '2521013', 'thiago.ribeiro@aluno.unievangelica.edu.br', 'Inteligência Artificial'),
        ('Larissa Santos', '2521014', 'larissa.santos@aluno.unievangelica.edu.br', 'Inteligência Artificial'),
        ('Prof. Fábio Botelho', '1001', 'fabio.botelho@unievangelica.edu.br', 'Inteligência Artificial'),
        ('Prof. Henrique Valle', '1002', 'henrique.valle@unievangelica.edu.br', 'Inteligência Artificial'),
        ('Prof. Eder José', '1003', 'eder.jose@unievangelica.edu.br', 'Inteligência Artificial'),
    ]

    senha_padrao = generate_password_hash('senha123')

    for nome, matricula, email, curso in usuarios_ficticios:
        try:
            c.execute('''
                INSERT INTO usuarios (nome, matricula, email, curso, senha)
                VALUES (?, ?, ?, ?, ?)
            ''', (nome, matricula, email, curso, senha_padrao))
        except sqlite3.IntegrityError:
            pass  # Usuário já existe

    conn.commit()
    print(f"✅ {len(usuarios_ficticios)} usuários fictícios criados!\n")

    # 1.5. CRIAR POSTS INICIAIS
    print("📝 Criando posts iniciais...")

    posts_iniciais = [
        # ================================
        # INTELIGÊNCIA ARTIFICIAL (6 posts)
        # ================================
        ('post-ia-1', 'ia', 'projeto', '🎯 Projeto de Visão Computacional',
         'Galera, terminei meu projeto de reconhecimento facial usando OpenCV e Deep Learning! Consegui 95% de acurácia. Alguém quer testar? 🚀',
         'João Pedro Silva'),
        ('post-ia-2', 'ia', 'duvida', 'Ajuda com Redes Neurais',
         'Pessoal, estou com dificuldade pra entender backpropagation. Alguém tem algum material bom pra indicar? 📚',
         'Maria Santos'),
        ('post-ia-3', 'ia', 'discussao', 'IA Generativa x IA Discriminativa',
         'Qual vocês acham mais promissor pro futuro? Vamos debater sobre GANs, Transformers e o futuro da IA! 🤖✨',
         'Carlos Mendes'),
        ('post-ia-4', 'ia', 'projeto', '🤖 Chatbot Acadêmico com LLM',
         'Estou desenvolvendo um chatbot treinado com os dados das disciplinas pra responder dúvidas dos alunos. Usei embeddings + LLM. Alguém quer ajudar a evoluir? 💬',
         'Thiago Ribeiro'),
        ('post-ia-5', 'ia', 'duvida', 'NLP: Fine-tuning vs Prompt Engineering',
         'Quando vale a pena fazer fine-tuning em vez de só melhorar o prompt? Casos reais na área acadêmica seriam top! 🧠',
         'Larissa Santos'),
        ('post-ia-6', 'ia', 'projeto', '📊 MLOps para Monitorar Modelos em Produção',
         'Monteiro um pipeline com monitoramento de drift dos dados e das métricas do modelo. Estou usando Python + MLflow. Alguém mais mexe com MLOps aqui? 🔧',
         'Ana Costa'),

        # ================================
        # ADS (6 posts — já estavam 6)
        # ================================
        ('post-cc-1', 'ads', 'projeto', '🔐 Sistema de Criptografia RSA',
         'Implementei RSA do zero em Python! Alguém quer ver o código? Ficou bem didático pra aprender. 🔑',
         'Rafael Costa'),
        ('post-cc-2', 'ads', 'duvida', 'Árvores Balanceadas - AVL vs Red-Black',
         'Galera, quando usar AVL vs Red-Black Tree? Alguém consegue explicar de forma simples as diferenças? 🌳',
         'Beatriz Lima'),
        ('post-cc-3', 'ads', 'discussao', '🖥️ Algoritmos de Escalonamento de CPU',
         'Qual algoritmo vocês acham mais eficiente? Round-Robin, SJF ou Prioridade? Vamos debater! ⚙️',
         'Lucas Ferreira'),
        ('post-si-1', 'ads', 'projeto', '📊 Dashboard de Analytics com Power BI',
         'Criei um dashboard em Power BI integrado com SQL Server. Visualização de dados em tempo real! 📈',
         'Pedro Alves'),
        ('post-si-2', 'ads', 'duvida', '💾 Normalização de Banco de Dados',
         'Pessoal, quando vale a pena desnormalizar um BD? Qual a diferença prática entre 3FN e BCNF? 🤔',
         'Fernanda Costa'),
        ('post-si-3', 'ads', 'projeto', '🔄 Pipeline de ETL com Python',
         'Construí um pipeline ETL automatizado usando Pandas e Airflow. Processa 1M+ registros por dia! 🚀',
         'Ricardo Silva'),

        # ================================
        # ENGENHARIA DE SOFTWARE (6 posts)
        # ================================
        ('post-es-1', 'es', 'projeto', '🚀 App Mobile com React Native',
         'Lancei meu app de delivery na Play Store! 10k downloads na primeira semana! 🎉📱',
         'Gabriel Martins'),
        ('post-es-2', 'es', 'discussao', '🏗️ Arquitetura de Microsserviços',
         'Microserviços ou Monolito? Quando vale a pena fazer a migração? Vamos debater! ⚙️',
         'Julia Fernandes'),
        ('post-es-3', 'es', 'projeto', '🔧 CI/CD com GitHub Actions',
         'Automatizei deploy completo: testes, build e deploy pro AWS. Pipeline rodando liso! 🚀',
         'Rafael Souza'),
        ('post-es-4', 'es', 'duvida', '🧪 Testes Automatizados: Unitário x Integração',
         'Galera, vocês priorizam mais testes unitários ou de integração nos projetos web? Como equilibram isso no dia a dia? ✅',
         'Lucas Ferreira'),
        ('post-es-5', 'es', 'projeto', '🏛️ Clean Architecture em API REST',
         'Refatorei uma API monolítica aplicando Clean Architecture. Separação de camadas ficou bem mais clara. Alguém quer ver o diagrama? 🧱',
         'Beatriz Lima'),
        ('post-es-6', 'es', 'discussao', '♻️ Refatoração de Código Legacy',
         'Como vocês abordam refatoração de código legado sem quebrar tudo? Estratégias, ferramentas e boas práticas são bem-vindas. 🔍',
         'Pedro Alves'),
    ]

    posts_criados = 0
    for post_id, curso, tipo, titulo, conteudo, nome_usuario in posts_iniciais:
        # Buscar ID do usuário
        c.execute('SELECT id FROM usuarios WHERE nome = ?', (nome_usuario,))
        result = c.fetchone()

        if result:
            usuario_id = result[0]
            try:
                c.execute('''
                    INSERT INTO posts (post_id, curso, tipo, titulo, conteudo, usuario_id, nome_usuario)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (post_id, curso, tipo, titulo, conteudo, usuario_id, nome_usuario))
                posts_criados += 1
            except sqlite3.IntegrityError:
                pass  # Post já existe

    conn.commit()
    print(f"✅ {posts_criados} posts criados!\n")

    # 2. ADICIONAR CURTIDAS
    print("❤️ Adicionando curtidas...")

    # Pegar IDs dos usuários
    c.execute('SELECT id FROM usuarios')
    usuario_ids = [row[0] for row in c.fetchall()]

    posts_ids = [
        'post-ia-1', 'post-ia-2', 'post-ia-3', 'post-ia-4', 'post-ia-5', 'post-ia-6',
        'post-cc-1', 'post-cc-2', 'post-cc-3',
        'post-si-1', 'post-si-2', 'post-si-3',
        'post-es-1', 'post-es-2', 'post-es-3', 'post-es-4', 'post-es-5', 'post-es-6'
    ]

    curtidas_adicionadas = 0
    for post_id in posts_ids:
        # Cada post recebe curtidas de 5 a 12 usuários aleatórios
        num_curtidas = random.randint(5, 12)
        usuarios_curtiram = random.sample(usuario_ids, min(num_curtidas, len(usuario_ids)))

        for usuario_id in usuarios_curtiram:
            try:
                c.execute('''
                    INSERT INTO curtidas (post_id, usuario_id)
                    VALUES (?, ?)
                ''', (post_id, usuario_id))
                curtidas_adicionadas += 1
            except sqlite3.IntegrityError:
                pass  # Curtida já existe

    conn.commit()
    print(f"✅ {curtidas_adicionadas} curtidas adicionadas!")
    print(f"   📊 Média de {curtidas_adicionadas // len(posts_ids)} curtidas por post\n")

    # 3. ADICIONAR COMENTÁRIOS
    print("💬 Adicionando comentários...\n")

    comentarios_por_post = {
        # ---------- IA ----------
        'post-ia-1': [
            ('Maria Santos', 'Incrível! Qual dataset você usou para treinar o modelo?'),
            ('Carlos Mendes', 'Parabéns! Você usou transfer learning ou treinou do zero?'),
            ('Ana Costa', '95% é excelente! Me passa o código no GitHub? 🚀'),
            ('Pedro Alves', 'Esse projeto vai ficar show no portfólio!'),
            ('Prof. Fábio Botelho', 'Excelente trabalho! Apresente na próxima aula, por favor.'),
            ('Lucas Ferreira', 'Consegue rodar em tempo real? Estou fazendo um similar.'),
            ('Julia Fernandes', 'Testou com fotos de diferentes ângulos e iluminação?'),
            ('Rafael Souza', 'Que bibliotecas você usou além do OpenCV?'),
        ],
        'post-ia-2': [
            ('Prof. Henrique Valle', 'Recomendo o vídeo do 3Blue1Brown sobre redes neurais!'),
            ('Carlos Mendes', 'Tem um livro gratuito do Michael Nielsen que é ótimo!'),
            ('Ana Costa', 'Vou te mandar uns slides que salvaram minha vida! 📚'),
            ('Lucas Ferreira', 'O canal Statquest no YouTube explica muito bem!'),
            ('Beatriz Lima', 'O curso do Andrew Ng no Coursera é perfeito pra isso!'),
            ('Pedro Alves', 'Faz um desenho do fluxo de gradientes, ajuda demais!'),
            ('Julia Fernandes', 'Se quiser, posso te explicar no Discord depois da aula!'),
            ('Rafael Souza', 'Comece pelo perceptron simples, depois vai evoluindo!'),
            ('Gabriel Martins', 'Implementa no NumPy do zero, vai clarear tudo!'),
            ('Fernanda Costa', 'Me ajudou muito desenhar o grafo computacional!'),
        ],
        'post-ia-3': [
            ('Lucas Ferreira', 'IA Generativa tá dominando! Olha o ChatGPT e DALL-E!'),
            ('Ana Costa', 'Mas discriminativa ainda é essencial pra classificação!'),
            ('Pedro Alves', 'Acho que os dois vão convergir no futuro! 🤖'),
            ('Maria Santos', 'GANs são incríveis pra síntese de imagens realistas!'),
            ('Rafael Souza', 'Diffusion models tão superando GANs em qualidade!'),
            ('Beatriz Lima', 'O futuro é multimodal: texto + imagem + áudio!'),
            ('Julia Fernandes', 'LLMs vão mudar tudo nos próximos anos!'),
            ('Prof. Eder José', 'Ótima discussão! Ambas têm seus casos de uso específicos.'),
            ('Gabriel Martins', 'Reinforcement Learning vai ser o próximo boom!'),
            ('Fernanda Costa', 'IA Generativa + discriminativa = futuro híbrido! ✨'),
        ],
        'post-ia-4': [
            ('Maria Santos', 'Esse chatbot vai salvar muitos alunos na madrugada 😂'),
            ('Lucas Ferreira', 'Você usou embeddings locais ou API externa?'),
            ('Pedro Alves', 'Integra com o Moodle/AVA então fica perfeito!'),
            ('Fernanda Costa', 'Daria pra usar pra tirar dúvidas de bibliografia também.'),
            ('Prof. Eder José', 'Excelente ideia, podemos transformar em projeto de extensão.'),
        ],
        'post-ia-5': [
            ('Ana Costa', 'Se for algo muito específico, fine-tuning ajuda bastante.'),
            ('Rafael Costa', 'Pra casos genéricos, só prompt já resolve e é mais barato.'),
            ('Beatriz Lima', 'Também depende do volume de dados que você tem.'),
            ('Lucas Ferreira', 'Fine-tuning é bom pra tom de voz fixo e domínio fechado.'),
        ],
        'post-ia-6': [
            ('Rafael Souza', 'MLOps é o que mais falta nas empresas hoje. Parabéns!'),
            ('Gabriel Martins', 'Você monitora latência e consumo de recurso também?'),
            ('Julia Fernandes', 'MLflow é top, já tentou Kubeflow também?'),
            ('Pedro Alves', 'Depois posta um print do dashboard!'),
        ],

        # ---------- ADS ----------
        'post-cc-1': [
            ('Lucas Ferreira', 'Cara, passa o GitHub! Quero estudar a implementação!'),
            ('Ana Costa', 'Você implementou os testes de primalidade também?'),
            ('Pedro Alves', 'Testou o desempenho com chaves de diferentes tamanhos?'),
            ('Maria Santos', 'Ficou muito bom! Vou usar como referência pro meu projeto.'),
            ('Beatriz Lima', 'Como você lidou com números grandes no Python?'),
            ('Gabriel Martins', 'RSA é muito elegante! Já tentou implementar outros algoritmos?'),
        ],
        'post-cc-2': [
            ('Rafael Costa', 'AVL tem rotações mais simples, mas Red-Black é mais eficiente!'),
            ('Ana Costa', 'AVL mantém balanceamento mais rígido, melhor pra busca intensiva.'),
            ('Pedro Alves', 'Red-Black é usado na STL do C++ e TreeMap do Java!'),
            ('Lucas Ferreira', 'Depende do caso: mais buscas = AVL, mais inserções = Red-Black'),
            ('Maria Santos', 'Implementei os dois no trabalho, AVL foi mais fácil de debugar!'),
            ('Thiago Ribeiro', 'A diferença de performance só aparece com muitos dados!'),
            ('Prof. Henrique Valle', 'Ótima pergunta! Testem na prática pra sentir a diferença.'),
        ],
        'post-cc-3': [
            ('Beatriz Lima', 'Round-Robin é justo, mas pode ter muito overhead de troca!'),
            ('Rafael Costa', 'SJF minimiza tempo médio, mas difícil prever tempo de execução.'),
            ('Ana Costa', 'Prioridade pode causar starvation se não tiver aging!'),
            ('Pedro Alves', 'Na prática, SO modernos usam Multi-Level Feedback Queue!'),
            ('Maria Santos', 'Linux usa CFS (Completely Fair Scheduler), é genial! 🐧'),
            ('Gabriel Martins', 'Round-Robin com quantum ajustável funciona bem!'),
        ],
        'post-si-1': [
            ('Ana Costa', 'Ficou lindo! Como você fez a integração em tempo real?'),
            ('Fernanda Costa', 'Usa algum sistema de cache pra otimizar as queries?'),
            ('Lucas Ferreira', 'Power BI é muito bom! Testou com datasets grandes?'),
            ('Maria Santos', 'Que tipo de métricas você tá visualizando?'),
            ('Ricardo Silva', 'DAX é complicado no início, mas vale a pena aprender!'),
            ('Gabriel Martins', 'Integrou com algum sistema de alertas?'),
        ],
        'post-si-2': [
            ('Pedro Alves', 'Desnormalização vale quando tem muitas JOINs caras!'),
            ('Ricardo Silva', '3FN elimina dependências transitivas, BCNF é mais rigoroso.'),
            ('Ana Costa', 'Data warehouses costumam desnormalizar pra performance.'),
            ('Lucas Ferreira', 'Na prática, normalize até 3FN e desnormalize se necessário!'),
            ('Maria Santos', 'BCNF resolve alguns edge cases que 3FN não pega.'),
            ('Fernanda Costa', 'Já tentaram modelar dimensional? Star schema é massa!'),
            ('Prof. Eder José', 'Ótima discussão! Normalização não é dogma, é ferramenta.'),
        ],
        'post-si-3': [
            ('Fernanda Costa', '1M+ registros é impressionante! Quanto tempo leva?'),
            ('Pedro Alves', 'Airflow é ótimo! Usa algum sistema de monitoramento?'),
            ('Ana Costa', 'Como você lida com falhas no meio do pipeline?'),
            ('Lucas Ferreira', 'Pandas com chunks é a sacada pra processar grandes volumes!'),
            ('Maria Santos', 'Já testou Spark pra processamento distribuído?'),
            ('Ricardo Silva', 'ETL incremental ou full load? Como gerencia histórico?'),
        ],

        # ---------- ES ----------
        'post-es-1': [
            ('Ana Costa', '10k downloads é incrível! Parabéns! 🎉'),
            ('Julia Fernandes', 'Qual foi o maior desafio no desenvolvimento?'),
            ('Lucas Ferreira', 'Usou TypeScript ou JavaScript puro?'),
            ('Maria Santos', 'Vai lançar pra iOS também?'),
            ('Rafael Souza', 'Como tá sendo a experiência com React Native?'),
            ('Pedro Alves', 'Teve problema com performance em algum momento?'),
        ],
        'post-es-2': [
            ('Rafael Souza', 'Microserviços trazem complexidade! Só vale se escalar muito.'),
            ('Julia Fernandes', 'Monolito bem feito escala muito antes de precisar migrar!'),
            ('Gabriel Martins', 'Netflix, Uber usam microserviços, mas são gigantes!'),
            ('Ana Costa', 'Comunicação entre serviços é o maior desafio!'),
            ('Lucas Ferreira', 'Se o time é pequeno, monolito é mais produtivo.'),
            ('Pedro Alves', 'Kubernetes ajuda muito no deploy de microserviços!'),
            ('Maria Santos', 'Event-driven architecture funciona bem com microserviços!'),
        ],
        'post-es-3': [
            ('Julia Fernandes', 'GitHub Actions é muito bom! Mais simples que Jenkins.'),
            ('Gabriel Martins', 'Como você configurou os testes automatizados?'),
            ('Ana Costa', 'Quanto tempo leva o pipeline completo?'),
            ('Rafael Souza', 'Usa Docker pra garantir ambiente consistente?'),
            ('Lucas Ferreira', 'Deploy blue-green ou canary?'),
            ('Pedro Alves', 'Integrou com alguma ferramenta de monitoramento?'),
        ],
        'post-es-4': [
            ('Beatriz Lima', 'Eu começo pelos unitários e depois adiciono integração.'),
            ('Rafael Costa', 'Testes de integração pegam muita coisa que passa batido.'),
            ('Fernanda Costa', 'Cobertura é importante, mas qualidade dos testes é mais.'),
            ('Prof. Eder José', 'Excelente tópico, vamos discutir em sala!'),
        ],
        'post-es-5': [
            ('Gabriel Martins', 'Clean Architecture ajuda muito a manter o código organizado.'),
            ('Julia Fernandes', 'Você usou casos de uso bem separados?'),
            ('Lucas Ferreira', 'Posta o diagrama no Git pra gente ver!'),
            ('Maria Santos', 'Quero aplicar isso num projeto da disciplina.'),
        ],
        'post-es-6': [
            ('Pedro Alves', 'Eu costumo começar por testes de caracterização.'),
            ('Ana Costa', 'Feature flags ajudam a refatorar sem impactar usuário final.'),
            ('Rafael Souza', 'Refatorar em pequenos passos é o segredo.'),
            ('Thiago Ribeiro', 'Ferramentas de code coverage ajudam a saber onde tocar.'),
        ],
    }

    comentarios_adicionados = 0

    for post_id, comentarios in comentarios_por_post.items():
        for nome_usuario, texto_comentario in comentarios:
            # Buscar ID do usuário pelo nome
            c.execute('SELECT id FROM usuarios WHERE nome = ?', (nome_usuario,))
            result = c.fetchone()

            if result:
                usuario_id = result[0]

                # Calcular data do comentário (últimas 24 horas)
                horas_atras = random.randint(1, 24)
                data_comentario = datetime.now() - timedelta(hours=horas_atras)

                c.execute('''
                    INSERT INTO comentarios (post_id, usuario_id, nome_usuario, comentario, data_comentario)
                    VALUES (?, ?, ?, ?, ?)
                ''', (post_id, usuario_id, nome_usuario, texto_comentario, data_comentario))

                comentarios_adicionados += 1

    conn.commit()
    print(f"✅ {comentarios_adicionados} comentários adicionados!\n")

    # 4. ESTATÍSTICAS
    print("📊 ESTATÍSTICAS FINAIS:")
    print("=" * 50)

    c.execute('SELECT COUNT(*) FROM usuarios')
    total_usuarios = c.fetchone()[0]
    print(f"👥 Total de usuários: {total_usuarios}")

    c.execute('SELECT COUNT(*) FROM curtidas')
    total_curtidas = c.fetchone()[0]
    print(f"❤️ Total de curtidas: {total_curtidas}")

    c.execute('SELECT COUNT(*) FROM comentarios')
    total_comentarios = c.fetchone()[0]
    print(f"💬 Total de comentários: {total_comentarios}")

    print("=" * 50)

    # Curtidas por post
    print("\n📈 Curtidas por post:")
    for post_id in posts_ids:
        c.execute('SELECT COUNT(*) FROM curtidas WHERE post_id = ?', (post_id,))
        qtd = c.fetchone()[0]
        print(f"  • {post_id}: {qtd} curtidas")

    # Comentários por post
    print("\n💭 Comentários por post:")
    for post_id in posts_ids:
        c.execute('SELECT COUNT(*) FROM comentarios WHERE post_id = ?', (post_id,))
        qtd = c.fetchone()[0]
        print(f"  • {post_id}: {qtd} comentários")

    conn.close()

    print("\n✅ População de dados concluída com sucesso!")
    print("🎉 Agora você pode acessar o sistema e ver a comunidade ativa!\n")


if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║       🤖 IAUniev - Popular Dados Fictícios                 ║
    ║       Sistema de Comunidade Acadêmica                      ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    try:
        popular_dados_ficticios()
    except Exception as e:
        print(f"\n❌ Erro ao popular dados: {e}")
        print("Certifique-se de que o app.py foi executado pelo menos uma vez")
        print("para criar as tabelas do banco de dados.\n")
