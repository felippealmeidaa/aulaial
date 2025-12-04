import sqlite3
import os
from dotenv import load_dotenv

# ============================================
# MIGRAÇÃO: ADICIONAR TABELAS LYCEUM V7.0
# ============================================

load_dotenv()
DATABASE = os.getenv('DATABASE', 'unievangelica.db')

print("=" * 80)
print("🔄 MIGRAÇÃO DO BANCO DE DADOS - LYCEUM V7.0")
print("=" * 80)
print(f"Database: {DATABASE}\n")

try:
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # ==============================================
    # TABELA 1: horarios_aluno (com coluna professor e local)
    # ==============================================
    print("📌 Verificando tabela: horarios_aluno")
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS horarios_aluno (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            dia_semana INTEGER NOT NULL,
            dia_nome TEXT,
            disciplina TEXT NOT NULL,
            horario_inicio TEXT,
            horario_fim TEXT,
            local TEXT,
            professor TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Verificar se coluna professor existe
    c.execute("PRAGMA table_info(horarios_aluno)")
    colunas = [col[1] for col in c.fetchall()]
    
    if 'professor' not in colunas:
        print("   Adicionando coluna: professor")
        c.execute('ALTER TABLE horarios_aluno ADD COLUMN professor TEXT')
    
    if 'local' not in colunas:
        print("   Adicionando coluna: local")
        c.execute('ALTER TABLE horarios_aluno ADD COLUMN local TEXT')
    
    print("   ✅ Tabela horarios_aluno OK")

    # ==============================================
    # TABELA 2: disciplinas_aluno
    # ==============================================
    print("\n📌 Verificando tabela: disciplinas_aluno")
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS disciplinas_aluno (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            disciplina TEXT NOT NULL,
            situacao TEXT,
            periodo TEXT,
            docente TEXT,
            data_inicial TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    print("   ✅ Tabela disciplinas_aluno OK")

    # ==============================================
    # TABELA 3: calendario_lyceum (NOVA V7.0)
    # ==============================================
    print("\n📌 Verificando tabela: calendario_lyceum")
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS calendario_lyceum (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            data_evento DATE NOT NULL,
            tipo TEXT,
            cor TEXT,
            descricao TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    print("   ✅ Tabela calendario_lyceum OK")

    # ==============================================
    # VERIFICAR COLUNAS NA TABELA usuarios
    # ==============================================
    print("\n📌 Verificando tabela: usuarios")
    
    c.execute("PRAGMA table_info(usuarios)")
    colunas_usuarios = [col[1] for col in c.fetchall()]
    
    if 'ultima_atualizacao_lyceum' not in colunas_usuarios:
        print("   Adicionando coluna: ultima_atualizacao_lyceum")
        c.execute('ALTER TABLE usuarios ADD COLUMN ultima_atualizacao_lyceum TEXT')
    
    if 'senha_lyceum' not in colunas_usuarios:
        print("   Adicionando coluna: senha_lyceum")
        c.execute('ALTER TABLE usuarios ADD COLUMN senha_lyceum TEXT')
    
    print("   ✅ Tabela usuarios OK")

    conn.commit()

    # ==============================================
    # RESUMO
    # ==============================================
    print("\n" + "=" * 80)
    print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 80)
    print()
    print("📊 Tabelas verificadas/criadas:")
    print("   • horarios_aluno (horários das aulas com local)")
    print("   • disciplinas_aluno (disciplinas matriculadas)")
    print("   • calendario_lyceum (eventos do calendário)")
    print("   • usuarios (colunas de sincronização)")
    print()
    print("🎯 Próximos passos:")
    print("   1. Reinicie o servidor Flask")
    print("   2. Clique em 'Sincronizar Lyceum' no dashboard")
    print("   3. Os dados serão baixados automaticamente")
    print()
    print("=" * 80)

    conn.close()

except sqlite3.OperationalError as e:
    print(f"❌ Erro de operação no banco: {e}")
    print()
    print("Possível solução:")
    print("   • Verifique se o arquivo .db existe")
    print("   • Verifique permissões do arquivo")
    print("   • Certifique-se que o banco não está aberto em outro programa")

except Exception as e:
    print(f"❌ Erro na migração: {e}")
    import traceback
    traceback.print_exc()

print()

