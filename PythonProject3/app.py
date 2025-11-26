from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file
import google.generativeai as genai
import os
from datetime import datetime, timedelta
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import time
from dotenv import load_dotenv
import random
import json
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import threading
import re
import bleach
from functools import lru_cache
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

# ============================================
# IMPORTAR SCRAPER E CACHE
# ============================================
try:
    from scraper_ava import sincronizar_dados_ava, verificar_cache_recente
except ImportError:
    print("⚠️ AVISO: 'scraper_ava.py' não encontrado. Sincronização automática desativada.")


    def sincronizar_dados_ava(*args, **kwargs):
        pass


    def verificar_cache_recente(*args):
        return False

# ============================================
# CARREGAR VARIÁVEIS DE AMBIENTE
# ============================================
load_dotenv()
app = Flask(__name__)

# ============================================
# CONTROLE DE STATUS DA SINCRONIZAÇÃO (GLOBAL)
# ============================================
status_sincronizacao = {}

# ============================================
# CONFIGURAÇÕES DE SEGURANÇA
# ============================================
app.secret_key = os.getenv('SECRET_KEY', 'chave_desenvolvimento_segura')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DATABASE = os.getenv('DATABASE', 'unievangelica.db')

# Configurações do Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)
s = URLSafeTimedSerializer(app.secret_key)

if not GEMINI_API_KEY:
    print("⚠️ AVISO: GEMINI_API_KEY não configurada no arquivo .env")

# ============================================
# CONFIGURAR GEMINI API
# ============================================
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    generation_config = {
        'temperature': 0.7,
        'top_p': 0.95,
        'top_k': 40,
        'max_output_tokens': 4000,
    }

# ============================================
# CONTROLE DE RATE LIMITING
# ============================================
last_request_time = {}
request_count = {}


def can_make_request(user_id, min_seconds=4, max_requests_per_minute=15):
    current_time = time.time()
    if user_id not in last_request_time:
        last_request_time[user_id] = current_time
        request_count[user_id] = {'count': 1, 'window_start': current_time}
        return True

    time_diff = current_time - last_request_time[user_id]
    if time_diff < min_seconds:
        return False

    if user_id in request_count:
        window_elapsed = current_time - request_count[user_id]['window_start']
        if window_elapsed > 60:
            request_count[user_id] = {'count': 1, 'window_start': current_time}
        else:
            if request_count[user_id]['count'] >= max_requests_per_minute:
                return False
            request_count[user_id]['count'] += 1

    last_request_time[user_id] = current_time
    return True


def get_wait_time(user_id):
    if user_id not in last_request_time:
        return 0
    current_time = time.time()
    time_diff = current_time - last_request_time[user_id]
    wait_time = max(0, 4 - time_diff)
    return int(wait_time)


# ============================================
# SANITIZAÇÃO DE HTML
# ============================================
def sanitizar_html(texto):
    """Remove tags HTML perigosas mantendo formatação segura"""
    tags_permitidas = ['b', 'i', 'u', 'p', 'br', 'strong', 'em', 'code', 'pre']
    return bleach.clean(texto, tags=tags_permitidas, strip=True)


# ============================================
# BANCO DE DADOS
# ============================================
def get_db_connection():
    """Retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()

        # Tabela de usuários
        c.execute(''' 
            CREATE TABLE IF NOT EXISTS usuarios ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                nome TEXT NOT NULL, 
                matricula TEXT UNIQUE NOT NULL, 
                cpf TEXT,  
                email TEXT UNIQUE NOT NULL, 
                curso TEXT NOT NULL, 
                senha TEXT NOT NULL, 
                dark_mode INTEGER DEFAULT 0,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
            ) 
        ''')

        # Tabela CONTEUDOS_AVA
        c.execute(''' 
            CREATE TABLE IF NOT EXISTS conteudos_ava ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT,  
                usuario_id INTEGER,  
                disciplina TEXT,  
                conteudo_texto TEXT,  
                data_extracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
            ) 
        ''')

        # Tabela de posts (com tags)
        c.execute(''' 
            CREATE TABLE IF NOT EXISTS posts ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                post_id TEXT UNIQUE NOT NULL, 
                curso TEXT NOT NULL, 
                tipo TEXT NOT NULL, 
                titulo TEXT NOT NULL, 
                conteudo TEXT NOT NULL,
                tags TEXT,
                usuario_id INTEGER NOT NULL, 
                nome_usuario TEXT NOT NULL, 
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id) 
            ) 
        ''')

        # Tabela de curtidas
        c.execute(''' 
            CREATE TABLE IF NOT EXISTS curtidas ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                post_id TEXT NOT NULL, 
                usuario_id INTEGER NOT NULL, 
                data_curtida TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id), 
                UNIQUE(post_id, usuario_id) 
            ) 
        ''')

        # Tabela de comentários
        c.execute(''' 
            CREATE TABLE IF NOT EXISTS comentarios ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                post_id TEXT NOT NULL, 
                usuario_id INTEGER NOT NULL, 
                nome_usuario TEXT NOT NULL, 
                comentario TEXT NOT NULL, 
                data_comentario TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id) 
            ) 
        ''')

        # Tabela de histórico de chat
        c.execute(''' 
            CREATE TABLE IF NOT EXISTS historico_chat ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                usuario_id INTEGER NOT NULL, 
                mensagem TEXT NOT NULL, 
                resposta TEXT NOT NULL, 
                data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id) 
            ) 
        ''')

        # Tabela de eventos do calendário
        c.execute(''' 
            CREATE TABLE IF NOT EXISTS eventos_calendario ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                usuario_id INTEGER NOT NULL, 
                titulo TEXT NOT NULL, 
                descricao TEXT, 
                data_evento DATE NOT NULL, 
                hora_evento TIME, 
                tipo TEXT NOT NULL, 
                cor TEXT DEFAULT '#4a90e2', 
                alerta INTEGER DEFAULT 0, 
                minutos_antes_alerta INTEGER DEFAULT 30, 
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id) 
            ) 
        ''')

        # Tabela de notas do aluno
        c.execute(''' 
            CREATE TABLE IF NOT EXISTS notas_aluno ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                usuario_id INTEGER NOT NULL, 
                disciplina TEXT NOT NULL, 
                va1 REAL DEFAULT 0, 
                va2 REAL DEFAULT 0, 
                va3 REAL DEFAULT 0, 
                media REAL DEFAULT 0, 
                situacao TEXT DEFAULT 'Cursando', 
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id) 
            ) 
        ''')

        # Tabela de faltas do aluno
        c.execute(''' 
            CREATE TABLE IF NOT EXISTS faltas_aluno ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                usuario_id INTEGER NOT NULL, 
                disciplina TEXT NOT NULL, 
                total_faltas INTEGER DEFAULT 0, 
                total_aulas INTEGER DEFAULT 60, 
                percentual_presenca REAL DEFAULT 100, 
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id) 
            ) 
        ''')

        # Tabela de notificações (NOVA)
        c.execute(''' 
            CREATE TABLE IF NOT EXISTS notificacoes ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                usuario_id INTEGER NOT NULL, 
                tipo TEXT NOT NULL, 
                mensagem TEXT NOT NULL, 
                link TEXT, 
                lida INTEGER DEFAULT 0, 
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id) 
            ) 
        ''')

        # Verificar se coluna tags existe, senão adicionar
        try:
            c.execute("SELECT tags FROM posts LIMIT 1")
        except sqlite3.OperationalError:
            c.execute("ALTER TABLE posts ADD COLUMN tags TEXT")

        # Verificar se coluna dark_mode existe
        try:
            c.execute("SELECT dark_mode FROM usuarios LIMIT 1")
        except sqlite3.OperationalError:
            c.execute("ALTER TABLE usuarios ADD COLUMN dark_mode INTEGER DEFAULT 0")

        conn.commit()
    print("✅ Banco de dados inicializado/verificado com sucesso!")


# ============================================
# SISTEMA DE NOTIFICAÇÕES
# ============================================
def criar_notificacao(usuario_id, tipo, mensagem, link=None):
    """Cria uma notificação para o usuário"""
    try:
        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO notificacoes (usuario_id, tipo, mensagem, link, lida)
                VALUES (?, ?, ?, ?, 0)
            ''', (usuario_id, tipo, mensagem, link))
            conn.commit()
    except Exception as e:
        print(f"[ERROR] Erro ao criar notificacao: {e}")


@app.route('/api/notificacoes')
def buscar_notificacoes():
    """Busca notificações do usuário"""
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    user_id = session['user_id']

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT id, tipo, mensagem, link, lida, 
                       strftime('%d/%m/%Y %H:%M', data_criacao) as data_formatada
                FROM notificacoes
                WHERE usuario_id = ?
                ORDER BY data_criacao DESC
                LIMIT 20
            ''', (user_id,))

            notificacoes = []
            for row in c.fetchall():
                notificacoes.append({
                    'id': row['id'],
                    'tipo': row['tipo'],
                    'mensagem': row['mensagem'],
                    'link': row['link'],
                    'lida': row['lida'],
                    'data': row['data_formatada']
                })

            # Contar não lidas
            c.execute('SELECT COUNT(*) as total FROM notificacoes WHERE usuario_id = ? AND lida = 0', (user_id,))
            nao_lidas = c.fetchone()['total']

        return jsonify({
            'success': True,
            'notificacoes': notificacoes,
            'nao_lidas': nao_lidas
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notificacoes/marcar_lida', methods=['POST'])
def marcar_notificacao_lida():
    """Marca notificação como lida"""
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    data = request.json
    notif_id = data.get('notificacao_id')

    try:
        with get_db_connection() as conn:
            conn.execute('UPDATE notificacoes SET lida = 1 WHERE id = ? AND usuario_id = ?',
                         (notif_id, session['user_id']))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notificacoes/marcar_todas_lidas', methods=['POST'])
def marcar_todas_lidas():
    """Marca todas as notificações como lidas"""
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    try:
        with get_db_connection() as conn:
            conn.execute('UPDATE notificacoes SET lida = 1 WHERE usuario_id = ?', (session['user_id'],))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# CACHE DE DADOS
# ============================================
@lru_cache(maxsize=128)
def get_eventos_cache_key(user_id, timestamp):
    """Cache de eventos com invalidação por timestamp"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT id, titulo, descricao, data_evento, hora_evento, tipo, cor, alerta, minutos_antes_alerta
            FROM eventos_calendario
            WHERE usuario_id = ?
            ORDER BY data_evento ASC
        ''', (user_id,))
        return c.fetchall()


def limpar_cache_eventos():
    """Limpa o cache de eventos"""
    get_eventos_cache_key.cache_clear()


# ============================================
# DADOS ACADÊMICOS
# ============================================
DADOS_ACADEMICOS = """ 
INFORMAÇÕES DA UNIEVANGELICA - CURSO DE INTELIGÊNCIA ARTIFICIAL 
Data de Atualização: 2025 

HORÁRIOS DAS AULAS - SEMESTRE 2025.2 
SEGUNDA-FEIRA: 
• 19:00 - 20:40: Cidadania ética e espiritualidade 
• 21:00 - 22:40: Fundamentos matemáticos para computação 

TERÇA-FEIRA: 
• 19:00 - 22:40: Introdução a engenharia de soluções 

QUARTA-FEIRA: 
• 19:00 - 22:40: Fundamentos matemáticos para computação 

QUINTA-FEIRA: 
• 19:00 - 22:40: Fundamentos de computação e infraestrutura 

SEXTA-FEIRA: 
• 19:00 - 22:40: Fundamento de engenharia de dados 

EAD: 
• Introdução a língua portuguesa (modalidade online) 

DISCIPLINAS DO CURSO: 
1. Cidadania ética e espiritualidade 
2. Introdução a engenharia de soluções 
3. Fundamentos matemáticos para computação 
4. Fundamentos de computação e infraestrutura 
5. Fundamentos de engenharia de dados 
6. Leitura e interpretação de texto 

CORPO DOCENTE: 
• Coordenadora: Natasha Sophie Campos 
• Prof. Holehon Santos Campos - Cidadania ética 
• Prof. Eder José Almeida da Silva - Eng. de soluções 
• Prof. Henrique Valle de Lima - Fundamentos matemáticos 
• Prof. Jeferson Silva Araújo - Computação e infraestrutura 
• Prof. Fábio Pereira Botelho - Engenharia de dados 
• Prof. Leonardo Rodrigues de Souza - Leitura e interpretação 

CALENDÁRIO DE PROVAS 2025.2: 
• 1ª VA: 15 a 20 de Setembro 
• 2ª VA: 27 de Outubro a 01 de Novembro 
• 3ª VA: 08 a 13 de Dezembro 
• Substitutivas 1ª e 2ª VA: 11 e 12 de Novembro 
• Substitutivas 3ª VA: 16 e 17 de Dezembro 
"""

# ============================================
# HORÁRIOS DAS AULAS
# ============================================
HORARIOS_AULAS = {
    'Segunda-feira': [
        {'horario': '19:00 - 20:40', 'disciplina': 'Cidadania ética e espiritualidade',
         'professor': 'Holehon Santos Campos'},
        {'horario': '21:00 - 22:40', 'disciplina': 'Fundamentos matemáticos para computação',
         'professor': 'Henrique Valle de Lima'}
    ],
    'Terça-feira': [
        {'horario': '19:00 - 22:40', 'disciplina': 'Introdução a engenharia de soluções',
         'professor': 'Eder José Almeida da Silva'}
    ],
    'Quarta-feira': [
        {'horario': '19:00 - 22:40', 'disciplina': 'Fundamentos matemáticos para computação',
         'professor': 'Henrique Valle de Lima'}
    ],
    'Quinta-feira': [
        {'horario': '19:00 - 22:40', 'disciplina': 'Fundamentos de computação e infraestrutura',
         'professor': 'Jeferson Silva Araújo'}
    ],
    'Sexta-feira': [
        {'horario': '19:00 - 22:40', 'disciplina': 'Fundamento de engenharia de dados',
         'professor': 'Fábio Pereira Botelho'}
    ],
    'EAD': [
        {'horario': 'Online', 'disciplina': 'Leitura e interpretação de texto',
         'professor': 'Leonardo Rodrigues de Souza'}
    ]
}

# ============================================
# EVENTOS ACADÊMICOS FIXOS
# ============================================
EVENTOS_ACADEMICOS = [
    {'title': '🎉 Feriado Municipal', 'start': '2025-07-26', 'color': '#e63946', 'tipo': 'feriado', 'allDay': True},
    {'title': '🎓 Colação de Grau Unificada', 'start': '2025-07-30', 'color': '#4a90e2', 'tipo': 'evento',
     'allDay': True},
    {'title': '🎂 Aniversário de Anápolis', 'start': '2025-07-31', 'color': '#e63946', 'tipo': 'feriado',
     'allDay': True},
    {'title': '📚 INÍCIO DAS AULAS', 'start': '2025-08-04', 'color': '#28a745', 'tipo': 'importante', 'allDay': True},
    {'title': '🎓 Dia do Estudante', 'start': '2025-08-11', 'color': '#ffc107', 'tipo': 'comemorativo', 'allDay': True},
    {'title': '🏆 Prêmio Mérito Científico', 'start': '2025-08-19', 'color': '#4a90e2', 'tipo': 'evento',
     'allDay': True},
    {'title': '⚠️ Inclusão/Exclusão Disciplinas', 'start': '2025-08-29', 'color': '#ff6b6b', 'tipo': 'prazo',
     'allDay': True},
    {'title': '🇧🇷 Independência do Brasil', 'start': '2025-09-07', 'color': '#e63946', 'tipo': 'feriado',
     'allDay': True},
    {'title': '📝 INÍCIO 1ª VA', 'start': '2025-09-15', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '📝 1ª VA', 'start': '2025-09-16', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '📝 1ª VA', 'start': '2025-09-17', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '📝 1ª VA', 'start': '2025-09-18', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '📝 1ª VA', 'start': '2025-09-19', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '📝 FIM 1ª VA', 'start': '2025-09-20', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '⏰ Lançamento notas 1ª VA', 'start': '2025-10-03', 'color': '#ff6b6b', 'tipo': 'prazo', 'allDay': True},
    {'title': '🇧🇷 Nossa Senhora Aparecida', 'start': '2025-10-12', 'color': '#e63946', 'tipo': 'feriado',
     'allDay': True},
    {'title': '👨‍🏫 Dia do Professor', 'start': '2025-10-15', 'color': '#ffc107', 'tipo': 'comemorativo',
     'allDay': True},
    {'title': '📝 INÍCIO 2ª VA', 'start': '2025-10-27', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '📝 2ª VA', 'start': '2025-10-28', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '📝 2ª VA', 'start': '2025-10-29', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '📝 2ª VA', 'start': '2025-10-30', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '⚠️ Trancamento de Matrícula', 'start': '2025-10-31', 'color': '#ff6b6b', 'tipo': 'prazo',
     'allDay': True},
    {'title': '📝 FIM 2ª VA', 'start': '2025-11-01', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '🕯️ Finados', 'start': '2025-11-02', 'color': '#e63946', 'tipo': 'feriado', 'allDay': True},
    {'title': '🔄 Substitutivas 1ª e 2ª VA', 'start': '2025-11-11', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '🔄 Substitutivas 1ª e 2ª VA', 'start': '2025-11-12', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '🇧🇷 Proclamação da República', 'start': '2025-11-15', 'color': '#e63946', 'tipo': 'feriado',
     'allDay': True},
    {'title': '✊ Consciência Negra', 'start': '2025-11-20', 'color': '#e63946', 'tipo': 'feriado', 'allDay': True},
    {'title': '📝 INÍCIO 3ª VA', 'start': '2025-12-08', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '📝 3ª VA', 'start': '2025-12-09', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '📝 3ª VA', 'start': '2025-12-10', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '📝 3ª VA', 'start': '2025-12-11', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '📝 3ª VA', 'start': '2025-12-12', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '📝 FIM 3ª VA', 'start': '2025-12-13', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '🔄 Substitutivas 3ª VA', 'start': '2025-12-16', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '🔄 Substitutivas 3ª VA', 'start': '2025-12-17', 'color': '#dc3545', 'tipo': 'prova', 'allDay': True},
    {'title': '🎄 Natal', 'start': '2025-12-25', 'color': '#e63946', 'tipo': 'feriado', 'allDay': True},
    {'title': '🎆 Ano Novo', 'start': '2026-01-01', 'color': '#e63946', 'tipo': 'feriado', 'allDay': True},
]


# ============================================
# FUNÇÕES AUXILIARES
# ============================================
def executar_sincronizacao_monitorada(user_id, matricula, cpf, forcar=False):
    """Sincronização em thread"""
    try:
        print(f"[SYNC] Iniciando sync para ID {user_id}")
        status_sincronizacao[user_id] = 'em_andamento'
        sincronizar_dados_ava(user_id, matricula, cpf, forcar_atualizacao=forcar)
        print(f"[SYNC] Sync finalizado para ID {user_id}")
        status_sincronizacao[user_id] = 'concluido'
    except Exception as e:
        print(f"[ERROR] Erro no sync: {e}")
        status_sincronizacao[user_id] = 'erro'


def gerar_notas_ficticias(usuario_id):
    """Gera notas fictícias para o aluno"""
    disciplinas = [
        'Cidadania ética e espiritualidade',
        'Introdução a engenharia de soluções',
        'Fundamentos matemáticos para computação',
        'Fundamentos de computação e infraestrutura',
        'Fundamentos de engenharia de dados',
        'Leitura e interpretação de texto'
    ]
    with get_db_connection() as conn:
        c = conn.cursor()
        for disciplina in disciplinas:
            c.execute('SELECT * FROM notas_aluno WHERE usuario_id = ? AND disciplina = ?', (usuario_id, disciplina))
            if not c.fetchone():
                va1 = round(random.uniform(5.0, 10.0), 1)
                va2 = round(random.uniform(5.0, 10.0), 1)
                va3 = round(random.uniform(5.0, 10.0), 1)
                media = round((va1 + va2 + va3) / 3, 1)
                situacao = 'Aprovado' if media >= 6.0 else 'Reprovado' if media > 0 else 'Cursando'
                c.execute(''' 
                    INSERT INTO notas_aluno (usuario_id, disciplina, va1, va2, va3, media, situacao) 
                    VALUES (?, ?, ?, ?, ?, ?, ?) 
                ''', (usuario_id, disciplina, va1, va2, va3, media, situacao))
        conn.commit()


def gerar_faltas_ficticias(usuario_id):
    """Gera faltas fictícias para o aluno"""
    disciplinas = [
        'Cidadania ética e espiritualidade',
        'Introdução a engenharia de soluções',
        'Fundamentos matemáticos para computação',
        'Fundamentos de computação e infraestrutura',
        'Fundamentos de engenharia de dados',
        'Leitura e interpretação de texto'
    ]
    with get_db_connection() as conn:
        c = conn.cursor()
        for disciplina in disciplinas:
            c.execute('SELECT * FROM faltas_aluno WHERE usuario_id = ? AND disciplina = ?', (usuario_id, disciplina))
            if not c.fetchone():
                total_faltas = random.randint(0, 10)
                total_aulas = 60
                percentual_presenca = round(((total_aulas - total_faltas) / total_aulas) * 100, 1)
                c.execute(''' 
                    INSERT INTO faltas_aluno (usuario_id, disciplina, total_faltas, total_aulas, percentual_presenca) 
                    VALUES (?, ?, ?, ?, ?) 
                ''', (usuario_id, disciplina, total_faltas, total_aulas, percentual_presenca))
        conn.commit()


def salvar_historico_chat(usuario_id, mensagem, resposta):
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute(''' 
                INSERT INTO historico_chat (usuario_id, mensagem, resposta) 
                VALUES (?, ?, ?) 
            ''', (usuario_id, mensagem, resposta))
            conn.commit()
    except Exception as e:
        print(f"[ERROR] Erro ao salvar historico: {e}")


def montar_contexto_comunidade(limite_posts=6):
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute(''' 
                SELECT post_id, curso, titulo, conteudo, nome_usuario, 
                       strftime('%d/%m/%Y %H:%M', data_criacao) as data_formatada 
                FROM posts 
                WHERE tipo = 'duvida' 
                ORDER BY data_criacao DESC 
                LIMIT ? 
            ''', (limite_posts,))
            posts = c.fetchall()

            if not posts:
                return "Nenhuma dúvida registrada na comunidade."

            bloco = []
            for post in posts:
                post_id = post['post_id']
                curso = post['curso']
                curso_label = {
                    'ia': 'Inteligência Artificial',
                    'ads': 'Análise e Desenvolvimento de Sistemas',
                    'es': 'Engenharia de Software'
                }.get(curso, curso)

                bloco.append(f"[DÚVIDA - {curso_label}] {post['titulo']}")
                bloco.append(f"Pergunta: {post['conteudo']}")

                c.execute(''' 
                    SELECT nome_usuario, comentario 
                    FROM comentarios 
                    WHERE post_id = ? 
                    ORDER BY data_comentario ASC 
                    LIMIT 5 
                ''', (post_id,))
                comentarios = c.fetchall()
                if comentarios:
                    bloco.append("Respostas:")
                    for com in comentarios:
                        bloco.append(f"- {com['nome_usuario']}: {com['comentario']}")
                bloco.append("")

            return "\n".join(bloco)
    except Exception as e:
        print(f"[ERROR] Erro ao montar contexto: {e}")
        return "Não foi possível carregar dúvidas."


def criar_evento_rapido_via_chat(usuario_id, mensagem):
    texto = mensagem.strip()
    gatilho = "criar evento:"

    if not texto.lower().startswith(gatilho):
        return None

    try:
        conteudo = texto[len(gatilho):].strip()
        partes = [p.strip() for p in conteudo.split('|')]

        if len(partes) < 2:
            return "Para criar evento: criar evento: Título | AAAA-MM-DD | HH:MM (opcional)."

        titulo = partes[0]
        data_evento = partes[1]
        hora_evento = partes[2] if len(partes) >= 3 else ''

        try:
            datetime.strptime(data_evento, "%Y-%m-%d")
        except ValueError:
            return "Data inválida. Use: AAAA-MM-DD."

        with get_db_connection() as conn:
            conn.execute(''' 
                INSERT INTO eventos_calendario ( 
                    usuario_id, titulo, descricao, data_evento, hora_evento, 
                    tipo, cor, alerta, minutos_antes_alerta 
                ) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) 
            ''', (usuario_id, titulo, 'Criado via chat', data_evento, hora_evento, 'pessoal', '#4a90e2', 0, 30))
            conn.commit()

        limpar_cache_eventos()

        if hora_evento:
            return f"[OK] Evento criado: **{titulo}** em **{data_evento} as {hora_evento}**."
        else:
            return f"[OK] Evento criado: **{titulo}** em **{data_evento}**."
    except Exception as e:
        print(f"[ERROR] Erro ao criar evento: {e}")
        return "[ERROR] Erro ao criar evento."


# ============================================
# ROTAS
# ============================================
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    erro = session.pop('login_erro', None)
    sucesso = session.pop('login_sucesso', None)
    return render_template('index.html', erro=erro, sucesso=sucesso)


@app.route('/cadastro')
def cadastro():
    return render_template('cadastro.html')


@app.route('/cadastro', methods=['POST'])
def cadastrar():
    nome = request.form['nome']
    matricula = request.form['matricula']
    cpf = request.form['cpf']
    email = request.form['email']
    curso = request.form['curso']
    senha = request.form['password']
    confirm_senha = request.form['confirm_password']

    if senha != confirm_senha:
        return render_template('cadastro.html', erro='As senhas não coincidem!')

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute(''' 
                INSERT INTO usuarios (nome, matricula, cpf, email, curso, senha) 
                VALUES (?, ?, ?, ?, ?, ?) 
            ''', (nome, matricula, cpf, email, curso, generate_password_hash(senha)))
            conn.commit()
            usuario_id = c.lastrowid

        gerar_notas_ficticias(usuario_id)
        gerar_faltas_ficticias(usuario_id)

        session['login_sucesso'] = 'Cadastro realizado! Faça login.'
        return redirect(url_for('index'))
    except sqlite3.IntegrityError:
        return render_template('cadastro.html', erro='Matrícula ou e-mail já cadastrados!')


@app.route('/login', methods=['POST'])
def login():
    """Login com sincronização"""
    login_input = request.form.get('login') or request.form.get('matricula') or request.form.get('email')
    senha = request.form.get('password')

    if not login_input or not senha:
        session['login_erro'] = 'Preencha todos os campos!'
        return redirect(url_for('index'))

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(''' 
            SELECT id, nome, matricula, email, curso, senha, cpf, dark_mode  
            FROM usuarios  
            WHERE email = ? OR matricula = ? 
        ''', (login_input, login_input))
        usuario = c.fetchone()

    if usuario and check_password_hash(usuario['senha'], senha):
        session['user_id'] = usuario['id']
        session['user_nome'] = usuario['nome']
        session['user_curso'] = usuario['curso']
        session['dark_mode'] = usuario['dark_mode']

        if usuario['cpf']:
            tem_cache = verificar_cache_recente(usuario['id'])

            if tem_cache:
                print(f"[LOGIN] Login rapido: {usuario['nome']}")
                status_sincronizacao[usuario['id']] = 'concluido'
                return redirect(url_for('dashboard'))
            else:
                print(f"[LOGIN] Login completo: {usuario['nome']}")
                status_sincronizacao[usuario['id']] = 'iniciando'

                thread_ava = threading.Thread(
                    target=executar_sincronizacao_monitorada,
                    args=(usuario['id'], usuario['matricula'], usuario['cpf'], True)
                )
                thread_ava.daemon = True
                thread_ava.start()

                return redirect(url_for('tela_carregamento'))

        gerar_notas_ficticias(usuario['id'])
        gerar_faltas_ficticias(usuario['id'])
        return redirect(url_for('dashboard'))
    else:
        session['login_erro'] = 'E-mail/matrícula ou senha incorretos!'
        return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = request.form.get('email')

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT email FROM usuarios WHERE email = ?', (email,))
            usuario = c.fetchone()

        if usuario:
            token = s.dumps(email, salt='email-recuperacao')
            link = url_for('redefinir_senha', token=token, _external=True)

            try:
                msg = Message('Recuperação de Senha - IAUniev', recipients=[email])
                msg.body = f'Clique no link: {link}\n\nExpira em 1 hora.'
                msg.html = f"""<p>Clique no botão:</p><a href="{link}" style="background:#0056b3; color:white; padding:10px 20px; text-decoration:none; border-radius:5px;">Redefinir Senha</a>"""
                mail.send(msg)
                flash('E-mail enviado!', 'success')
            except Exception as e:
                print(f"Erro: {e}")
                print(f"🔗 LINK (DEV): {link}")
                flash('Erro ao enviar. (Veja console)', 'warning')
        else:
            flash('E-mail não encontrado.', 'error')

    return render_template('esqueci_senha.html')


@app.route('/redefinir-senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    try:
        email = s.loads(token, salt='email-recuperacao', max_age=3600)
    except SignatureExpired:
        return render_template('redefinir_senha.html', erro='Link expirou!', token=None)
    except BadSignature:
        return render_template('redefinir_senha.html', erro='Link inválido!', token=None)

    if request.method == 'POST':
        nova_senha = request.form.get('password')
        confirm_senha = request.form.get('confirm_password')

        if nova_senha != confirm_senha:
            return render_template('redefinir_senha.html', erro='Senhas não coincidem!', token=token)

        senha_hash = generate_password_hash(nova_senha)

        with get_db_connection() as conn:
            conn.execute('UPDATE usuarios SET senha = ? WHERE email = ?', (senha_hash, email))
            conn.commit()

        session['login_sucesso'] = 'Senha redefinida!'
        return redirect(url_for('index'))

    return render_template('redefinir_senha.html', token=token)


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    nome = session.get('user_nome', 'Usuário')
    curso = session.get('user_curso', 'Não especificado')
    user_id = session['user_id']
    dark_mode = session.get('dark_mode', 0)

    with get_db_connection() as conn:
        c = conn.cursor()
        posts_por_curso = {}
        cursos = ['ia', 'ads', 'es']
        for curso_id in cursos:
            c.execute(''' 
                SELECT post_id, tipo, titulo, conteudo, tags, nome_usuario,  
                       strftime('%d/%m/%Y %H:%M', data_criacao) as data_formatada, 
                       usuario_id 
                FROM posts 
                WHERE curso = ? 
                ORDER BY data_criacao DESC 
            ''', (curso_id,))
            posts = []
            for row in c.fetchall():
                posts.append({
                    'post_id': row['post_id'],
                    'tipo': row['tipo'],
                    'titulo': row['titulo'],
                    'conteudo': row['conteudo'],
                    'tags': row['tags'] or '',
                    'nome_usuario': row['nome_usuario'],
                    'data': row['data_formatada'],
                    'e_meu': row['usuario_id'] == user_id
                })
            posts_por_curso[curso_id] = posts

        c.execute(''' 
            SELECT disciplina, va1, va2, va3, media, situacao 
            FROM notas_aluno 
            WHERE usuario_id = ? 
            ORDER BY disciplina 
        ''', (user_id,))
        notas = []
        for row in c.fetchall():
            notas.append({
                'disciplina': row['disciplina'],
                'va1': row['va1'],
                'va2': row['va2'],
                'va3': row['va3'],
                'media': row['media'],
                'situacao': row['situacao']
            })

        c.execute(''' 
            SELECT disciplina, total_faltas, total_aulas, percentual_presenca 
            FROM faltas_aluno 
            WHERE usuario_id = ? 
            ORDER BY disciplina 
        ''', (user_id,))
        faltas = []
        for row in c.fetchall():
            faltas.append({
                'disciplina': row['disciplina'],
                'total_faltas': row['total_faltas'],
                'total_aulas': row['total_aulas'],
                'percentual_presenca': row['percentual_presenca']
            })

    return render_template(
        'dashboard.html',
        nome=nome,
        curso=curso,
        dark_mode=dark_mode,
        posts_ia=posts_por_curso.get('ia', []),
        posts_ads=posts_por_curso.get('ads', []),
        posts_es=posts_por_curso.get('es', []),
        horarios_aulas=HORARIOS_AULAS,
        eventos_academicos=json.dumps(EVENTOS_ACADEMICOS),
        notas=notas,
        faltas=faltas
    )


@app.route('/carregando')
def tela_carregamento():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('loading.html')


# ============================================
# ROTA DO CHAT (ATUALIZADA)
# ============================================
@app.route('/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    user_id = session['user_id']

    if not can_make_request(user_id):
        wait_time = get_wait_time(user_id)
        return jsonify({
            'response': f'⏳ Aguarde {wait_time}s.',
            'wait_time': wait_time,
            'rate_limited': True
        })

    data = request.json
    mensagem_usuario = sanitizar_html(data.get('message', '').strip())

    resposta_evento = criar_evento_rapido_via_chat(user_id, mensagem_usuario)
    if resposta_evento is not None:
        salvar_historico_chat(user_id, mensagem_usuario, resposta_evento)
        return jsonify({'response': resposta_evento})

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT nome, matricula, email, curso FROM usuarios WHERE id = ?', (user_id,))
        usuario_dados = c.fetchone()

        c.execute(''' 
            SELECT mensagem, resposta  
            FROM historico_chat  
            WHERE usuario_id = ?  
            ORDER BY data_hora DESC  
            LIMIT 6 
        ''', (user_id,))
        historico_recente = c.fetchall()

        c.execute('SELECT disciplina, conteudo_texto FROM conteudos_ava WHERE usuario_id=?', (user_id,))
        conteudos_ava = c.fetchall()

    termo_lower = mensagem_usuario.lower()
    ava_texto = ""

    termos_cal = ['quando', 'data', 'dia', 'feriado', 'provas', 'calendário', 'calendario', 'va1', 'va2']
    quer_calendario = any(t in termo_lower for t in termos_cal)

    contexto_cal = ""
    if quer_calendario:
        contexto_cal = f"CALENDÁRIO:\n{DADOS_ACADEMICOS}\n"

    match_semana = re.search(r'semana\s*(\d+)', termo_lower)
    semana_foco = match_semana.group(1) if match_semana else None

    materiais_encontrados = False

    if conteudos_ava:
        ava_texto = "--- CONTEÚDOS DO AVA ---\n"

        for item in conteudos_ava:
            disc_texto = item['conteudo_texto']
            disc_nome = item['disciplina']

            if semana_foco:
                if f"Semana {semana_foco}" in disc_texto or f"Semana {semana_foco.zfill(2)}" in disc_texto:
                    blocos = disc_texto.split("=================================")
                    blocos_uteis = [b for b in blocos if
                                    f"Semana {semana_foco}" in b or f"Semana {semana_foco.zfill(2)}" in b]

                    if blocos_uteis:
                        resumo = "\n".join(blocos_uteis)
                        ava_texto += f"\n>>> [{disc_nome}] - SEMANA {semana_foco} <<<\n{resumo}\n"
                        materiais_encontrados = True
            elif any(t in disc_nome.lower() for t in termo_lower.split() if len(t) > 3):
                ava_texto += f"\n>>> {disc_nome} <<<\n{disc_texto[:15000]}\n"
                materiais_encontrados = True

        if not materiais_encontrados:
            if semana_foco:
                ava_texto += f"\nAVISO: Semana {semana_foco} não encontrada.\n"
            for item in conteudos_ava:
                ava_texto += f"## {item['disciplina']}:\n{item['conteudo_texto'][:800]}\n...\n"
    else:
        ava_texto = "AVA não sincronizado."

    historico_texto = ""
    if historico_recente:
        for h in reversed(historico_recente):
            historico_texto += f"Aluno: {h['mensagem']}\nAssistente: {h['resposta']}\n"
    else:
        historico_texto = "Nenhuma conversa anterior."

    if usuario_dados:
        nome_usuario = usuario_dados['nome']
        matricula_usuario = usuario_dados['matricula']
        email_usuario = usuario_dados['email']
        curso_usuario = usuario_dados['curso']
    else:
        nome_usuario = session.get('user_nome', 'Usuário')
        matricula_usuario = 'N/A'
        email_usuario = 'N/A'
        curso_usuario = 'N/A'

    try:
        contexto_usuario = f""" 
Usuário: 
- Nome: {nome_usuario} 
- Matrícula: {matricula_usuario} 
- E-mail: {email_usuario} 
- Curso: {curso_usuario} 
"""
        contexto_comunidade = montar_contexto_comunidade(limite_posts=6)

        prompt = f"""
Você é o **IAUniev Professor**, assistente acadêmico da UniEvangélica.

{contexto_usuario}

{contexto_cal}

CONTEÚDO DO AVA:
{ava_texto}

HISTÓRICO:
{historico_texto}

PERGUNTA:
\"\"\"{mensagem_usuario}\"\"\"

### DIRETRIZES ###
1. Explique o conteúdo
2. PRIORIZE LINKS: Se houver vídeos/arquivos, liste-os
3. Use Markdown
4. Se Semana X solicitada, mostre materiais
"""

        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]

        if model:
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            if response.parts:
                resposta_final = response.text
                salvar_historico_chat(user_id, mensagem_usuario, resposta_final)
                return jsonify({'response': resposta_final})
            else:
                resposta = "Não consegui gerar resposta."
                salvar_historico_chat(user_id, mensagem_usuario, resposta)
                return jsonify({'response': resposta})
        else:
            return jsonify({'response': "Erro de configuração."})

    except Exception as e:
        print(f"Erro Gemini: {str(e)}")
        resposta = "Erro de conexão."
        salvar_historico_chat(user_id, mensagem_usuario, resposta)
        return jsonify({'response': resposta})


# ============================================
# ROTAS API - COMUNIDADE
# ============================================
@app.route('/api/historico_chat')
def buscar_historico_chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    user_id = session['user_id']
    limite = request.args.get('limite', 20, type=int)
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute(''' 
                SELECT mensagem, resposta, strftime('%d/%m/%Y %H:%M', data_hora) as data_formatada 
                FROM historico_chat 
                WHERE usuario_id = ? 
                ORDER BY data_hora DESC 
                LIMIT ? 
            ''', (user_id, limite))
            historico = []
            for row in c.fetchall():
                historico.append({
                    'mensagem': row['mensagem'],
                    'resposta': row['resposta'],
                    'data': row['data_formatada']
                })
        return jsonify({'success': True, 'historico': historico})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/limpar_historico', methods=['POST'])
def limpar_historico():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    user_id = session['user_id']
    try:
        with get_db_connection() as conn:
            conn.execute('DELETE FROM historico_chat WHERE usuario_id = ?', (user_id,))
            conn.commit()
        return jsonify({'success': True, 'message': 'Histórico limpo!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/posts')
def buscar_posts():
    """Lazy loading de posts"""
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    curso = request.args.get('curso', 'ia')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    offset = (page - 1) * limit

    user_id = session['user_id']

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT post_id, tipo, titulo, conteudo, tags, nome_usuario,
                       strftime('%d/%m/%Y %H:%M', data_criacao) as data_formatada,
                       usuario_id
                FROM posts
                WHERE curso = ?
                ORDER BY data_criacao DESC
                LIMIT ? OFFSET ?
            ''', (curso, limit, offset))

            posts = []
            for row in c.fetchall():
                posts.append({
                    'post_id': row['post_id'],
                    'tipo': row['tipo'],
                    'titulo': row['titulo'],
                    'conteudo': row['conteudo'],
                    'tags': row['tags'] or '',
                    'nome_usuario': row['nome_usuario'],
                    'data': row['data_formatada'],
                    'e_meu': row['usuario_id'] == user_id
                })

        return jsonify({'success': True, 'posts': posts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/criar_post', methods=['POST'])
def criar_post():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    data = request.json
    curso = data.get('curso')
    tipo = data.get('tipo')
    titulo = sanitizar_html(data.get('titulo'))
    conteudo = sanitizar_html(data.get('conteudo'))
    tags = sanitizar_html(data.get('tags', ''))
    user_id = session['user_id']
    nome_usuario = session['user_nome']
    post_id = f"post-{curso}-{int(datetime.now().timestamp())}"

    try:
        with get_db_connection() as conn:
            conn.execute(''' 
                INSERT INTO posts (post_id, curso, tipo, titulo, conteudo, tags, usuario_id, nome_usuario) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?) 
            ''', (post_id, curso, tipo, titulo, conteudo, tags, user_id, nome_usuario))
            conn.commit()
        return jsonify({
            'success': True,
            'post_id': post_id,
            'nome_usuario': nome_usuario,
            'data': datetime.now().strftime('%d/%m/%Y %H:%M')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/curtir', methods=['POST'])
def curtir_post():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    data = request.json
    post_id = data.get('post_id')
    user_id = session['user_id']

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM curtidas WHERE post_id = ? AND usuario_id = ?', (post_id, user_id))
            curtida_existe = c.fetchone()

            # Buscar dono do post para notificação
            c.execute('SELECT usuario_id, titulo FROM posts WHERE post_id = ?', (post_id,))
            post = c.fetchone()

            if curtida_existe:
                c.execute('DELETE FROM curtidas WHERE post_id = ? AND usuario_id = ?', (post_id, user_id))
                acao = 'descurtiu'
            else:
                c.execute('INSERT INTO curtidas (post_id, usuario_id) VALUES (?, ?)', (post_id, user_id))
                acao = 'curtiu'

                # Criar notificação para o dono do post
                if post and post['usuario_id'] != user_id:
                    criar_notificacao(
                        post['usuario_id'],
                        'curtida',
                        f"{session['user_nome']} curtiu seu post: {post['titulo']}",
                        f"/dashboard#post-{post_id}"
                    )

            c.execute('SELECT COUNT(*) AS total FROM curtidas WHERE post_id = ?', (post_id,))
            total_curtidas = c.fetchone()['total']
            conn.commit()
        return jsonify({'success': True, 'acao': acao, 'total_curtidas': total_curtidas})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/comentar', methods=['POST'])
def comentar_post():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    data = request.json
    post_id = data.get('post_id')
    comentario = sanitizar_html(data.get('comentario'))
    user_id = session['user_id']
    nome_usuario = session['user_nome']

    try:
        with get_db_connection() as conn:
            c = conn.cursor()

            # Buscar dono do post
            c.execute('SELECT usuario_id, titulo FROM posts WHERE post_id = ?', (post_id,))
            post = c.fetchone()

            c.execute(''' 
                INSERT INTO comentarios (post_id, usuario_id, nome_usuario, comentario) 
                VALUES (?, ?, ?, ?) 
            ''', (post_id, user_id, nome_usuario, comentario))
            comentario_id = c.lastrowid
            conn.commit()

            # Criar notificação
            if post and post['usuario_id'] != user_id:
                criar_notificacao(
                    post['usuario_id'],
                    'comentario',
                    f"{nome_usuario} comentou no seu post: {post['titulo']}",
                    f"/dashboard#post-{post_id}"
                )

        return jsonify({
            'success': True,
            'comentario_id': comentario_id,
            'nome_usuario': nome_usuario,
            'comentario': comentario,
            'data': datetime.now().strftime('%d/%m/%Y %H:%M')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/excluir_post', methods=['POST'])
def excluir_post():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    data = request.json
    post_id = data.get('post_id')
    user_id = session['user_id']

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT usuario_id FROM posts WHERE post_id = ?', (post_id,))
            post = c.fetchone()
            if not post:
                return jsonify({'error': 'Post não encontrado'}), 404
            if post['usuario_id'] != user_id:
                return jsonify({'error': 'Sem permissão'}), 403
            c.execute('DELETE FROM comentarios WHERE post_id = ?', (post_id,))
            c.execute('DELETE FROM curtidas WHERE post_id = ?', (post_id,))
            c.execute('DELETE FROM posts WHERE post_id = ?', (post_id,))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/excluir_comentario', methods=['POST'])
def excluir_comentario():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    data = request.json
    comentario_id = data.get('comentario_id')
    user_id = session['user_id']

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT usuario_id FROM comentarios WHERE id = ?', (comentario_id,))
            comentario = c.fetchone()
            if not comentario:
                return jsonify({'error': 'Comentário não encontrado'}), 404
            if comentario['usuario_id'] != user_id:
                return jsonify({'error': 'Sem permissão'}), 403
            c.execute('DELETE FROM comentarios WHERE id = ?', (comentario_id,))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/interacoes/<post_id>')
def buscar_interacoes(post_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    user_id = session['user_id']

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) AS total FROM curtidas WHERE post_id = ?', (post_id,))
            total_curtidas = c.fetchone()['total']
            c.execute('SELECT * FROM curtidas WHERE post_id = ? AND usuario_id = ?', (post_id, user_id))
            usuario_curtiu = c.fetchone() is not None
            c.execute(''' 
                SELECT id, nome_usuario, comentario, strftime('%d/%m/%Y %H:%M', data_comentario) as data_formatada, usuario_id 
                FROM comentarios 
                WHERE post_id = ? 
                ORDER BY data_comentario ASC 
            ''', (post_id,))
            comentarios = []
            for row in c.fetchall():
                comentarios.append({
                    'id': row['id'],
                    'nome_usuario': row['nome_usuario'],
                    'comentario': row['comentario'],
                    'data': row['data_formatada'],
                    'e_meu': row['usuario_id'] == user_id
                })
        return jsonify({
            'success': True,
            'total_curtidas': total_curtidas,
            'usuario_curtiu': usuario_curtiu,
            'total_comentarios': len(comentarios),
            'comentarios': comentarios
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# ROTAS DO CALENDÁRIO
# ============================================
@app.route('/api/eventos_calendario')
def buscar_eventos_calendario():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    user_id = session['user_id']

    try:
        # Usar cache
        timestamp = int(time.time() // 300)  # Cache por 5 minutos
        eventos_db = get_eventos_cache_key(user_id, timestamp)

        eventos_pessoais = []
        for row in eventos_db:
            start_datetime = row['data_evento']
            if row['hora_evento']:
                start_datetime += 'T' + row['hora_evento']

            eventos_pessoais.append({
                'id': row['id'],
                'title': row['titulo'],
                'start': start_datetime,
                'color': row['cor'],
                'extendedProps': {
                    'descricao': row['descricao'],
                    'tipo': row['tipo'],
                    'pessoal': True,
                    'alerta': row['alerta'],
                    'minutos_antes_alerta': row['minutos_antes_alerta']
                },
                'allDay': False if row['hora_evento'] else True
            })

        todos_eventos = EVENTOS_ACADEMICOS + eventos_pessoais
        return jsonify({'success': True, 'eventos': todos_eventos})
    except Exception as e:
        print(f"[ERROR] Erro: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/criar_evento', methods=['POST'])
def criar_evento():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    user_id = session['user_id']
    data = request.json

    titulo = sanitizar_html(data.get('titulo'))
    descricao = sanitizar_html(data.get('descricao', ''))
    data_evento = data.get('data')
    hora_evento = data.get('hora', '')
    tipo = data.get('tipo', 'pessoal')
    cor = data.get('cor', '#4a90e2')
    alerta = data.get('alerta', 0)
    minutos_antes_alerta = data.get('minutos_antes_alerta', 30)

    if not titulo or not data_evento:
        return jsonify({'error': 'Título e data obrigatórios!'}), 400

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute(''' 
                INSERT INTO eventos_calendario (usuario_id, titulo, descricao, data_evento, hora_evento, tipo, cor, alerta, minutos_antes_alerta) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) 
            ''', (user_id, titulo, descricao, data_evento, hora_evento, tipo, cor, alerta, minutos_antes_alerta))
            evento_id = c.lastrowid
            conn.commit()

        limpar_cache_eventos()

        return jsonify({
            'success': True,
            'evento_id': evento_id,
            'mensagem': 'Evento criado!'
        })
    except Exception as e:
        print(f"[ERROR] Erro: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/excluir_evento', methods=['POST'])
def excluir_evento():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    user_id = session['user_id']
    data = request.json
    evento_id = data.get('evento_id')

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT usuario_id FROM eventos_calendario WHERE id = ?', (evento_id,))
            evento = c.fetchone()
            if not evento:
                return jsonify({'error': 'Evento não encontrado'}), 404
            if evento['usuario_id'] != user_id:
                return jsonify({'error': 'Sem permissão'}), 403
            c.execute('DELETE FROM eventos_calendario WHERE id = ?', (evento_id,))
            conn.commit()

        limpar_cache_eventos()

        return jsonify({'success': True, 'mensagem': 'Evento excluído!'})
    except Exception as e:
        print(f"[ERROR] Erro: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# ROTAS DE STATUS
# ============================================
@app.route('/api/checar_status_sync')
def checar_status_sync():
    if 'user_id' not in session:
        return jsonify({'status': 'erro', 'redirect': url_for('index')})

    user_id = session['user_id']
    estado = status_sincronizacao.get(user_id, 'concluido')

    return jsonify({'status': estado})


@app.route('/api/status_sincronizacao')
def status_sincronizacao_dashboard():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    user_id = session['user_id']
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM conteudos_ava WHERE usuario_id = ?', (user_id,))
        count_conteudos = c.fetchone()[0]

    sincronizado = count_conteudos > 0
    detalhes = f"{count_conteudos} materiais baixados."

    return jsonify({
        'sincronizado': sincronizado,
        'detalhes': detalhes
    })


# ============================================
# MODO ESCURO
# ============================================
@app.route('/api/toggle_dark_mode', methods=['POST'])
def toggle_dark_mode():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    user_id = session['user_id']

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT dark_mode FROM usuarios WHERE id = ?', (user_id,))
            current = c.fetchone()['dark_mode']
            new_mode = 0 if current == 1 else 1

            c.execute('UPDATE usuarios SET dark_mode = ? WHERE id = ?', (new_mode, user_id))
            conn.commit()

            session['dark_mode'] = new_mode

        return jsonify({'success': True, 'dark_mode': new_mode})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# EXPORT DE DADOS (PDF/EXCEL)
# ============================================
@app.route('/api/exportar_notas/<formato>')
def exportar_notas(formato):
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    user_id = session['user_id']

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''SELECT disciplina, va1, va2, va3, media, situacao 
                     FROM notas_aluno WHERE usuario_id = ?''', (user_id,))
        notas = c.fetchall()

        c.execute('SELECT nome FROM usuarios WHERE id = ?', (user_id,))
        nome = c.fetchone()['nome']

    if formato == 'pdf':
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        y = 800
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, y, "RELATÓRIO DE NOTAS - IAUniev")

        y -= 30
        p.setFont("Helvetica", 12)
        p.drawString(100, y, f"Aluno: {nome}")

        y -= 30
        p.drawString(100, y, f"Data: {datetime.now().strftime('%d/%m/%Y')}")

        y -= 50

        # Criar tabela
        data_table = [['Disciplina', 'VA1', 'VA2', 'VA3', 'Média', 'Situação']]
        for nota in notas:
            data_table.append([
                nota['disciplina'][:30],
                str(nota['va1']),
                str(nota['va2']),
                str(nota['va3']),
                str(nota['media']),
                nota['situacao']
            ])

        table = Table(data_table, colWidths=[200, 50, 50, 50, 50, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        table.wrapOn(p, 100, y)
        table.drawOn(p, 50, y - len(data_table) * 25)

        p.save()
        buffer.seek(0)

        return send_file(buffer,
                         mimetype='application/pdf',
                         as_attachment=True,
                         download_name=f'notas_{nome}.pdf')

    elif formato == 'excel':
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Notas"

            # Cabeçalho
            ws['A1'] = f"Relatório de Notas - {nome}"
            ws['A1'].font = Font(size=14, bold=True)
            ws['A2'] = f"Data: {datetime.now().strftime('%d/%m/%Y')}"

            # Títulos das colunas
            headers = ['Disciplina', 'VA1', 'VA2', 'VA3', 'Média', 'Situação']
            for col, header in enumerate(headers, start=1):
                cell = ws.cell(row=4, column=col, value=header)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
                cell.alignment = Alignment(horizontal="center")

            # Dados
            for row_idx, nota in enumerate(notas, start=5):
                ws.cell(row=row_idx, column=1, value=nota['disciplina'])
                ws.cell(row=row_idx, column=2, value=nota['va1'])
                ws.cell(row=row_idx, column=3, value=nota['va2'])
                ws.cell(row=row_idx, column=4, value=nota['va3'])
                ws.cell(row=row_idx, column=5, value=nota['media'])
                ws.cell(row=row_idx, column=6, value=nota['situacao'])

            # Ajustar largura das colunas
            ws.column_dimensions['A'].width = 40
            for col in ['B', 'C', 'D', 'E']:
                ws.column_dimensions[col].width = 10
            ws.column_dimensions['F'].width = 15

            buffer = io.BytesIO()
            wb.save(buffer)
            buffer.seek(0)

            return send_file(buffer,
                             mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                             as_attachment=True,
                             download_name=f'notas_{nome}.xlsx')
        except ImportError:
            return jsonify({'error': 'openpyxl não instalado'}), 500

    return jsonify({'error': 'Formato inválido'}), 400


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)