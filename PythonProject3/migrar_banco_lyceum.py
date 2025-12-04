import sqlite3
import os
from dotenv import load_dotenv

# ============================================
# MIGRAÇÃO: ADICIONAR COLUNAS LYCEUM V5.1
# ============================================

load_dotenv()
DATABASE = os.getenv('DATABASE', 'unievangelica.db')

print("=" * 80)
print("🔄 MIGRAÇÃO DO BANCO DE DADOS - LYCEUM V5.1")
print("=" * 80)
print(f"Database: {DATABASE}\n")

try:
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Verifica estrutura atual da tabela usuarios
    c.execute("PRAGMA table_info(usuarios)")
    colunas_existentes = [col[1] for col in c.fetchall()]

    print("📋 Colunas existentes na tabela 'usuarios':")
    for col in colunas_existentes:
        print(f"   • {col}")
    print()

    # ==============================================
    # COLUNA 1: ultima_atualizacao_lyceum
    # ==============================================
    if 'ultima_atualizacao_lyceum' not in colunas_existentes:
        print("📌 Adicionando coluna: ultima_atualizacao_lyceum")
        c.execute('''
            ALTER TABLE usuarios 
            ADD COLUMN ultima_atualizacao_lyceum TEXT
        ''')
        conn.commit()
        print("✅ Coluna 'ultima_atualizacao_lyceum' adicionada!")
        print("   Uso: Armazena timestamp da última sincronização Lyceum")
        print("   Formato: ISO 8601 (YYYY-MM-DDTHH:MM:SS)")
    else:
        print("✅ Coluna 'ultima_atualizacao_lyceum' já existe")

    print()

    # ==============================================
    # COLUNA 2: senha_lyceum (OPCIONAL)
    # ==============================================
    if 'senha_lyceum' not in colunas_existentes:
        print("📌 Adicionando coluna: senha_lyceum (opcional)")
        c.execute('''
            ALTER TABLE usuarios 
            ADD COLUMN senha_lyceum TEXT
        ''')
        conn.commit()
        print("✅ Coluna 'senha_lyceum' adicionada!")
        print("   Uso: Armazena senha do Lyceum se diferente do CPF")
        print("   Padrão: 9 primeiros dígitos do CPF")
        print("   Obs: Se NULL, usa CPF automaticamente")
    else:
        print("✅ Coluna 'senha_lyceum' já existe")

    print()

    # ==============================================
    # VERIFICAÇÃO FINAL
    # ==============================================
    c.execute("PRAGMA table_info(usuarios)")
    colunas_finais = [col[1] for col in c.fetchall()]

    print("=" * 80)
    print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 80)
    print()
    print("📊 Resumo:")
    print(f"   • Total de colunas: {len(colunas_finais)}")
    print(f"   • Colunas novas: 2")
    print()
    print("🔧 Estrutura atual da tabela 'usuarios':")

    # Mostra estrutura completa
    c.execute("PRAGMA table_info(usuarios)")
    for col in c.fetchall():
        col_id, col_name, col_type, not_null, default_value, pk = col
        tipo_str = f"{col_type}"
        if pk:
            tipo_str += " PRIMARY KEY"
        if not_null:
            tipo_str += " NOT NULL"
        if default_value:
            tipo_str += f" DEFAULT {default_value}"

        print(f"   [{col_id}] {col_name:30} {tipo_str}")

    print()
    print("=" * 80)
    print("📝 INSTRUÇÕES:")
    print("=" * 80)
    print()
    print("1. A coluna 'ultima_atualizacao_lyceum' será preenchida automaticamente")
    print("   quando o usuário sincronizar com o Lyceum pela primeira vez.")
    print()
    print("2. A coluna 'senha_lyceum' é OPCIONAL:")
    print("   • Se NULL → usa 9 primeiros dígitos do CPF")
    print("   • Se preenchida → usa a senha especificada")
    print()
    print("3. Para configurar senha_lyceum manualmente:")
    print()
    print("   UPDATE usuarios")
    print("   SET senha_lyceum = '123456789'")
    print("   WHERE id = 1;")
    print()
    print("=" * 80)
    print()
    print("🎯 Próximos passos:")
    print("   1. ✅ Migração concluída")
    print("   2. ⏳ Copie scraper_lyceum.py para o projeto")
    print("   3. ⏳ Adicione código ao app.py")
    print("   4. ⏳ Adicione botão ao dashboard.html")
    print("   5. ⏳ Adicione JavaScript ao script.js")
    print("   6. ⏳ Reinicie o Flask")
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