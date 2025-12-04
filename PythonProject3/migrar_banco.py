"""
MIGRAÇÃO DO BANCO DE DADOS - V5.1 (CORRIGIDA)

Este script:
1. Cria a tabela conteudos_ava SE não existir
2. Adiciona a coluna ultima_atualizacao SE não existir
3. Trata todos os casos possíveis

Execute: python migrar_banco_v5_corrigido.py
"""

import sqlite3
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Caminho do banco
DATABASE = os.getenv('DATABASE', 'unievangelica.db')


def migrar_banco():
    """
    Migração inteligente que:
    1. Cria a tabela se não existir
    2. Adiciona a coluna se necessário
    """
    print("=" * 70)
    print("🔄 MIGRAÇÃO DO BANCO DE DADOS - V5.1 (CORRIGIDA)")
    print("=" * 70)

    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # ============================================
        # PASSO 1: VERIFICAR SE A TABELA EXISTE
        # ============================================
        print("\n📋 PASSO 1: Verificando se tabela 'conteudos_ava' existe...")

        c.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='conteudos_ava'
        """)

        tabela_existe = c.fetchone() is not None

        if not tabela_existe:
            print("⚠️  Tabela 'conteudos_ava' NÃO existe!")
            print("➕ Criando tabela 'conteudos_ava'...")

            # Cria a tabela COM a coluna ultima_atualizacao
            c.execute('''
                CREATE TABLE conteudos_ava (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    disciplina TEXT NOT NULL,
                    conteudo_texto TEXT NOT NULL,
                    data_extracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ultima_atualizacao TEXT,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
                )
            ''')
            conn.commit()
            print("✅ Tabela 'conteudos_ava' criada com sucesso!")
            print("✅ Coluna 'ultima_atualizacao' já incluída!")

        else:
            print("✅ Tabela 'conteudos_ava' já existe!")

            # ============================================
            # PASSO 2: VERIFICAR SE A COLUNA EXISTE
            # ============================================
            print("\n📋 PASSO 2: Verificando se coluna 'ultima_atualizacao' existe...")

            c.execute("PRAGMA table_info(conteudos_ava)")
            colunas = [col[1] for col in c.fetchall()]

            if 'ultima_atualizacao' in colunas:
                print("✅ Coluna 'ultima_atualizacao' já existe!")
                print("ℹ️  Nenhuma migração necessária.")
            else:
                print("⚠️  Coluna 'ultima_atualizacao' NÃO existe!")
                print("➕ Adicionando coluna 'ultima_atualizacao'...")

                c.execute('''
                    ALTER TABLE conteudos_ava 
                    ADD COLUMN ultima_atualizacao TEXT
                ''')
                conn.commit()
                print("✅ Coluna 'ultima_atualizacao' adicionada com sucesso!")

        # ============================================
        # PASSO 3: VERIFICAR ESTRUTURA FINAL
        # ============================================
        print("\n📋 PASSO 3: Verificando estrutura final...")

        c.execute("PRAGMA table_info(conteudos_ava)")
        colunas_finais = c.fetchall()

        print("\n📊 Estrutura da tabela 'conteudos_ava':")
        print("-" * 70)
        for col in colunas_finais:
            col_id, nome, tipo, notnull, default, pk = col
            print(f"   • {nome:25} {tipo:15} {'NOT NULL' if notnull else ''}")
        print("-" * 70)

        # ============================================
        # PASSO 4: VERIFICAR DADOS EXISTENTES
        # ============================================
        print("\n📋 PASSO 4: Verificando dados existentes...")

        c.execute("SELECT COUNT(*) as total FROM conteudos_ava")
        total_registros = c.fetchone()[0]

        if total_registros > 0:
            print(f"📂 Encontrados {total_registros} registro(s) na tabela.")

            # Verificar quantos têm ultima_atualizacao preenchida
            c.execute("SELECT COUNT(*) as total FROM conteudos_ava WHERE ultima_atualizacao IS NOT NULL")
            com_data = c.fetchone()[0]

            print(f"   • {com_data} com data de atualização")
            print(f"   • {total_registros - com_data} sem data de atualização")

            if com_data < total_registros:
                print("\nℹ️  NOTA: Registros sem data serão considerados 'antigos'")
                print("   O scraper atualizará a data na próxima sincronização.")
        else:
            print("📂 Tabela vazia (nenhum registro encontrado).")

        conn.close()

        # ============================================
        # CONCLUSÃO
        # ============================================
        print("\n" + "=" * 70)
        print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 70)
        print("\n📌 PRÓXIMOS PASSOS:")
        print("   1. Execute: python app.py")
        print("   2. Faça login no sistema")
        print("   3. Clique no botão 'Sincronizar com AVA'")
        print("   4. Aguarde 5-8 minutos")
        print("   5. ✅ Pronto!")
        print("\n" + "=" * 70 + "\n")

        return True

    except sqlite3.Error as e:
        print(f"\n❌ ERRO na migração: {e}")
        print("\n🔍 DIAGNÓSTICO:")
        print(f"   • Banco de dados: {DATABASE}")
        print(f"   • Arquivo existe? {os.path.exists(DATABASE)}")

        if not os.path.exists(DATABASE):
            print("\n💡 SOLUÇÃO:")
            print("   O banco de dados não existe!")
            print("   Execute: python app.py")
            print("   Isso criará o banco automaticamente.")

        return False

    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    sucesso = migrar_banco()

    if sucesso:
        print("✅ Migração bem-sucedida! Banco pronto para V5.1!")
        exit(0)
    else:
        print("❌ Migração falhou. Verifique os erros acima.")
        exit(1)