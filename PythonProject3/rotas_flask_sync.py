# ============================================
# ROTAS FLASK PARA SINCRONIZAÇÃO MANUAL
# Adicione estas rotas ao seu app.py
# ============================================

from flask import jsonify, request, session
from datetime import datetime
import threading

# Importar do scraper
from scraper_ava import sincronizar_dados_ava, obter_ultima_sincronizacao
from app import app, get_db_connection

# Variável global para controlar sincronização em andamento
sincronizacoes_em_andamento = {}


# ============================================
# 🆕 ROTA: STATUS DA SINCRONIZAÇÃO
# ============================================
@app.route('/api/status_sync', methods=['GET'])
def status_sync():
    """
    Retorna o status da sincronização do usuário atual:
    - última data/hora de sincronização
    - se tem dados
    - se está sincronizando agora
    """
    try:
        # Pega user_id da sessão
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'erro': 'Não autenticado'}), 401

        # Verifica se está sincronizando agora
        sincronizando = sincronizacoes_em_andamento.get(user_id, False)

        # Pega última sincronização
        ultima_sync = obter_ultima_sincronizacao(user_id)

        # Verifica se tem dados
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM conteudos_ava WHERE usuario_id = ?', (user_id,))
            tem_dados = c.fetchone()[0] > 0

        response = {
            'sincronizando': sincronizando,
            'tem_dados': tem_dados,
            'ultima_sync': None,
            'ultima_sync_formatada': None
        }

        if ultima_sync:
            response['ultima_sync'] = ultima_sync.isoformat()
            response['ultima_sync_formatada'] = ultima_sync.strftime('%d/%m/%Y às %H:%M')

        return jsonify(response), 200

    except Exception as e:
        print(f"Erro ao obter status: {e}")
        return jsonify({'erro': str(e)}), 500


# ============================================
# 🆕 ROTA: SINCRONIZAR COM AVA
# ============================================
@app.route('/api/sincronizar_ava', methods=['POST'])
def api_sincronizar_ava():
    """
    Inicia sincronização manual com o AVA.
    - Executa em thread separada para não bloquear
    - Retorna imediatamente
    - Frontend deve polling /api/status_sync
    """
    try:
        # Pega user_id da sessão
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'erro': 'Não autenticado'}), 401

        # Verifica se já está sincronizando
        if sincronizacoes_em_andamento.get(user_id, False):
            return jsonify({
                'status': 'em_andamento',
                'mensagem': 'Sincronização já está em andamento'
            }), 200

        # Pega dados do usuário do banco
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT matricula, cpf FROM usuarios WHERE id = ?', (user_id,))
            usuario = c.fetchone()

            if not usuario:
                return jsonify({'erro': 'Usuário não encontrado'}), 404

            matricula = usuario['matricula']
            cpf = usuario['cpf']

        # Função para executar scraping em thread
        def executar_scraping():
            try:
                sincronizacoes_em_andamento[user_id] = True
                print(f"\n[SYNC] Iniciando sincronização para user {user_id}...")

                # EXECUTA SCRAPING COM forcar_atualizacao=True
                sincronizar_dados_ava(user_id, matricula, cpf, forcar_atualizacao=True)

                print(f"[SYNC] Sincronização concluída para user {user_id}")

            except Exception as e:
                print(f"[SYNC] Erro na sincronização: {e}")
            finally:
                sincronizacoes_em_andamento[user_id] = False

        # Inicia thread
        thread = threading.Thread(target=executar_scraping)
        thread.daemon = True  # Thread morre com o app
        thread.start()

        return jsonify({
            'status': 'iniciado',
            'mensagem': 'Sincronização iniciada com sucesso',
            'estimativa': '5-8 minutos'
        }), 200

    except Exception as e:
        print(f"Erro ao iniciar sincronização: {e}")
        return jsonify({'erro': str(e)}), 500


# ============================================
# 🆕 ROTA: CANCELAR SINCRONIZAÇÃO (OPCIONAL)
# ============================================
@app.route('/api/cancelar_sync', methods=['POST'])
def cancelar_sync():
    """
    Marca sincronização como cancelada.
    NOTA: O scraping em andamento continuará, mas o status mudará.
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'erro': 'Não autenticado'}), 401

        sincronizacoes_em_andamento[user_id] = False

        return jsonify({
            'status': 'cancelado',
            'mensagem': 'Status atualizado. Scraping em andamento terminará em breve.'
        }), 200

    except Exception as e:
        return jsonify({'erro': str(e)}), 500


# ============================================
# EXEMPLO DE INTEGRAÇÃO NO LOGIN
# ============================================
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id') or session.get('user_id') or 0
    nome = data.get('nome') or ''

    session['user_id'] = user_id

    tem_dados = False
    ultima_sync = None

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM conteudos_ava WHERE usuario_id = ?', (user_id,))
            tem_dados = c.fetchone()[0] > 0

        if tem_dados:
            ultima_sync = obter_ultima_sincronizacao(user_id)
    except Exception:
        pass

    return jsonify({
        'sucesso': True,
        'user_id': user_id,
        'nome': nome,
        'tem_dados_ava': tem_dados,
        'ultima_sync': ultima_sync.isoformat() if ultima_sync else None
    }), 200


# ============================================
# NOTAS DE IMPLEMENTAÇÃO
# ============================================
"""
1. Adicione estas rotas ao seu app.py

2. Importe as funções do scraper:
   from scraper_ava import sincronizar_dados_ava, obter_ultima_sincronizacao

3. A rota /api/sincronizar_ava executa em thread para não bloquear

4. Frontend deve fazer polling de /api/status_sync para ver progresso

5. O botão fica desabilitado enquanto sincronizando=True

6. Após término, atualiza automaticamente mostrando nova data/hora
"""
