import sqlite3
import os
import re
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

# ============================================
# CONFIGURAÇÕES
# ============================================
load_dotenv()
DATABASE = os.getenv('DATABASE', 'unievangelica.db')


def get_db_connection_lyceum():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================
# VERIFICAR SE USUÁRIO TEM CACHE (LYCEUM)
# ============================================
def usuario_tem_cache_lyceum(user_id):
    try:
        with get_db_connection_lyceum() as conn:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM notas_aluno WHERE usuario_id = ?', (user_id,))
            count_notas = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM faltas_aluno WHERE usuario_id = ?', (user_id,))
            count_faltas = c.fetchone()[0]
            return count_notas > 0 or count_faltas > 0
    except Exception as e:
        print(f"❌ [LYCEUM] Erro ao verificar cache: {e}")
        return False


# ============================================
# OBTER ÚLTIMA SINCRONIZAÇÃO (LYCEUM)
# ============================================
def obter_ultima_sincronizacao_lyceum(user_id):
    try:
        with get_db_connection_lyceum() as conn:
            c = conn.cursor()
            c.execute('SELECT ultima_atualizacao_lyceum FROM usuarios WHERE id = ?', (user_id,))
            row = c.fetchone()
            if row and row['ultima_atualizacao_lyceum']:
                return datetime.fromisoformat(row['ultima_atualizacao_lyceum'])
            return None
    except Exception as e:
        print(f"❌ [LYCEUM] Erro ao obter última sync: {e}")
        return None


# ============================================
# FUNÇÃO DE LIMPEZA
# ============================================
def limpar_texto(texto):
    if not texto:
        return ""
    return re.sub(r'\s+', ' ', texto).strip()


def normalizar_disciplina(nome):
    if not nome:
        return ""
    nome = limpar_texto(nome).upper()
    nome = re.sub(r'[.,;:]+$', '', nome)
    return nome


# ============================================
# LOGIN NO LYCEUM (SELENIUM)
# ============================================
def login_lyceum(driver, matricula, cpf):
    print("🔐 [LYCEUM] Iniciando login...")

    try:
        driver.get("https://portal.unievangelica.edu.br/aluno/#/login")
        time.sleep(8)

        wait = WebDriverWait(driver, 40)

        # Senha = 9 primeiros dígitos do CPF
        senha = ''.join(filter(str.isdigit, cpf))[:9]

        print(f"   Matrícula: {matricula}")
        print(f"   Senha (9 dígitos CPF): {senha}")

        try:
            user_field = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[type='text'], input[formcontrolname='usuario'], input[placeholder*='Aluno']")
            ))
            pass_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            print("   ✓ Campos de login encontrados")
        except Exception as e:
            print(f"   ❌ Erro ao encontrar campos: {e}")
            return False

        user_field.clear()
        user_field.send_keys(matricula)
        time.sleep(0.5)

        pass_field.clear()
        pass_field.send_keys(senha)
        time.sleep(0.5)

        print("   ✓ Credenciais preenchidas")

        try:
            btn_login = driver.find_element(By.CSS_SELECTOR,
                                            "button[type='submit'], button.btn-login, button[color='primary']")
            btn_login.click()
            print("   ✓ Botão de login clicado")
        except:
            btn_login = driver.find_element(By.XPATH, "//button[contains(text(), 'Entrar')]")
            btn_login.click()
            print("   ✓ Botão de login clicado (por texto)")

        time.sleep(8)

        if "login" not in driver.current_url.lower() or "home" in driver.current_url.lower():
            print("✅ [LYCEUM] Login realizado com sucesso!")
            print(f"   URL atual: {driver.current_url}")
            return True
        else:
            print("❌ [LYCEUM] Falha no login")
            return False

    except Exception as e:
        print(f"❌ [LYCEUM] Erro no login: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================
# EXTRAIR NOTAS - V12.0 COM SCROLL JAVASCRIPT
# ============================================
def extrair_notas(driver):
    """
    Extrai notas da página: Avaliação > Notas
    URL: https://portal.unievangelica.edu.br/aluno/#/home/boletim/notas

    IMPORTANTE:
    - Usa JavaScript para scroll agressivo
    - Média SEMPRE divide por 3
    """
    print("\n📊 [LYCEUM] Extraindo NOTAS (V12.0)...")
    dados_notas = {}

    try:
        driver.get("https://portal.unievangelica.edu.br/aluno/#/home/boletim/notas")
        time.sleep(6)

        print(f"   URL: {driver.current_url}")

        # SCROLL AGRESSIVO com JavaScript
        for scroll_attempt in range(25):
            driver.execute_script("""
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
            """)
            time.sleep(0.8)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)

        # Aguardar carregamento
        time.sleep(5)

        # Voltar ao topo e fazer scroll novamente
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        for _ in range(8):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.2)

        body_text = driver.find_element(By.TAG_NAME, "body").text

        print(f"   Tamanho do texto: {len(body_text)} caracteres")

        # Debug
        print("   === CONTEÚDO DA PÁGINA DE NOTAS ===")
        print(body_text[:4000])
        print("   === FIM ===")

        linhas = body_text.split('\n')
        linhas = [l.strip() for l in linhas if l.strip()]

        # Processar linha por linha - melhorar detecção de notas
        i = 0
        disciplina_atual = None

        while i < len(linhas):
            linha = linhas[i]

            # Pular headers conhecidos
            if linha in ['Notas', 'Notas e Faltas', 'Gráfico de notas', 'Boletim', 'Nota',
                         'Situação do aluno', 'Em andamento', 'Aprovado', 'Reprovado']:
                i += 1
                continue

            # Verificar se parece uma disciplina (mais flexível)
            # Disciplinas geralmente começam com maiúscula e têm mais de 10 caracteres
            if (len(linha) > 10 and
                re.match(r'^[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑa-záàâãéèêíïóôõöúçñ\s,\.\-À-ú]+$', linha)):

                disciplina = limpar_texto(linha)

                # Pular menus e termos conhecidos
                termos_ignorar = ['AVALIAÇÃO', 'DISCIPLINA', 'CALENDÁRIO', 'NOTAS',
                                 'FREQUÊNCIA', 'CADASTRO', 'SECRETARIA VIRTUAL',
                                 'FINANCEIRO', 'AVALIAÇÃO INSTITUCIONAL', 'BIBLIOTECA',
                                 'IDIOMA', 'SAIR', 'AVISO', 'FELIPPE', 'ALMEIDA', 'RODRIGUES',
                                 'INTELIGÊNCIA ARTIFICIAL', 'RA:', 'SÉRIE', 'PERÍODO', 'TURMA', 'STATUS']

                if any(termo in disciplina.upper() for termo in termos_ignorar):
                    i += 1
                    continue

                # Verificar se contém palavras-chave de disciplinas
                palavras_chave = ['FUNDAMENTOS', 'COMPUTAÇÃO', 'ENGENHARIA', 'INTRODUÇÃO',
                                'ALGORITMOS', 'PROGRAMAÇÃO', 'MATEMÁTIC', 'CIDADANIA',
                                'ÉTICA', 'ESPIRITUALIDADE', 'LEITURA', 'INTERPRETAÇÃO',
                                'TEXTO', 'DADOS', 'INFRAESTRUTURA', 'SOLUÇÕES']

                if any(palavra in disciplina.upper() for palavra in palavras_chave):
                    disciplina_atual = disciplina
                    disc_key = normalizar_disciplina(disciplina)

                    if disc_key not in dados_notas:
                        dados_notas[disc_key] = {
                            'disciplina': disciplina,
                            'va1': 0.0,
                            'va2': 0.0,
                            'va3': 0.0,
                            'media': 0.0,
                            'situacao': 'Cursando'
                        }

            # Procurar por padrão de verificação de aprendizagem
            # Formato: "DD/MM/YYYY - Xª Verificação De Aprendizagem"
            match_verificacao = re.search(r'(\d{1,2}/\d{1,2}/\d{4})\s*-\s*(\d)[ªa]\s*Verificação', linha, re.IGNORECASE)

            if match_verificacao:
                num_va = match_verificacao.group(2)
                tipo_va = f"VA{num_va}"

                # IMPORTANTE: Procurar a disciplina PARA TRÁS a partir desta linha
                # No Lyceum, cada entrada de nota tem a disciplina logo acima da linha de VA
                disciplina_encontrada = None
                for k in range(i - 1, max(0, i - 5), -1):
                    linha_anterior = linhas[k].strip()
                    if any(p in linha_anterior.upper() for p in ['FUNDAMENTOS', 'COMPUTAÇÃO', 'ENGENHARIA', 'INTRODUÇÃO', 'ALGORITMOS', 'CIDADANIA', 'LEITURA', 'MATEMÁTIC', 'ÉTICA', 'ESPIRITUALIDADE', 'INTERPRETAÇÃO', 'SOLUÇÕES', 'INFRAESTRUTURA', 'DADOS']):
                        # Verificar que não é uma linha de VA ou outros headers
                        if not re.search(r'\d{1,2}/\d{1,2}/\d{4}', linha_anterior) and 'verificação' not in linha_anterior.lower():
                            disciplina_encontrada = limpar_texto(linha_anterior)
                            break

                # Se encontrou disciplina para trás, usar ela; senão usar a atual
                if disciplina_encontrada:
                    disciplina_atual = disciplina_encontrada

                if not disciplina_atual:
                    i += 1
                    continue

                # IMPORTANTE: NÃO extrair nota da mesma linha (contém data que confunde o regex)
                # Procurar a nota nas PRÓXIMAS linhas apenas
                nota_valor = None

                # Procurar nas próximas linhas por um número standalone (a nota)
                for j in range(1, 10):
                    if i + j < len(linhas):
                        linha_nota = linhas[i + j].strip()

                        # Pular linhas que contêm texto irrelevante
                        if any(skip in linha_nota.lower() for skip in ['verificação', 'gráfico', 'aprendizagem']):
                            continue

                        # Pular a linha "Nota" (é um label, não um número)
                        if linha_nota.lower() == 'nota':
                            continue

                        # Se encontrar "/" significa que é uma data (nova entrada) - parar
                        if '/' in linha_nota:
                            break

                        # Pular se a linha for uma disciplina (nova entrada)
                        if any(p in linha_nota.upper() for p in ['FUNDAMENTOS', 'COMPUTAÇÃO', 'ENGENHARIA', 'INTRODUÇÃO', 'ALGORITMOS', 'CIDADANIA', 'LEITURA', 'MATEMÁTIC', 'ÉTICA']):
                            break

                        # Procurar número standalone (a nota é geralmente um número sozinho na linha)
                        # O número deve ser entre 0 e 100
                        match_nota = re.match(r'^(\d{1,3}(?:[.,]\d+)?)$', linha_nota)
                        if match_nota:
                            val = float(match_nota.group(1).replace(',', '.'))
                            # Validar que é um valor de nota plausível (0-100)
                            if 0 <= val <= 100:
                                nota_valor = val
                                break

                # Converter nota de escala 0-100 para 0-10
                if nota_valor is not None:
                    if nota_valor > 10:
                        nota_valor = round(nota_valor / 10, 1)

                if nota_valor is not None:
                    disc_key = normalizar_disciplina(disciplina_atual)

                    if disc_key not in dados_notas:
                        dados_notas[disc_key] = {
                            'disciplina': disciplina_atual,
                            'va1': 0.0,
                            'va2': 0.0,
                            'va3': 0.0,
                            'media': 0.0,
                            'situacao': 'Cursando'
                        }

                    # Atualizar a nota correspondente (não sobrescrever se já existe)
                    if tipo_va == 'VA1':
                        if dados_notas[disc_key]['va1'] == 0.0 or nota_valor > dados_notas[disc_key]['va1']:
                            dados_notas[disc_key]['va1'] = nota_valor
                    elif tipo_va == 'VA2':
                        if dados_notas[disc_key]['va2'] == 0.0 or nota_valor > dados_notas[disc_key]['va2']:
                            dados_notas[disc_key]['va2'] = nota_valor
                    elif tipo_va == 'VA3':
                        if dados_notas[disc_key]['va3'] == 0.0 or nota_valor > dados_notas[disc_key]['va3']:
                            dados_notas[disc_key]['va3'] = nota_valor

                    print(f"      ✓ {disciplina_atual} - {tipo_va}: {nota_valor}")

            # Detecção adicional de VA sem data completa (apenas "VA1", "VA2", etc.)
            # Este bloco é um fallback para formatos alternativos
            if disciplina_atual and not match_verificacao:
                va_match = re.search(r'\bVA\s*([123])\b', linha, re.IGNORECASE)
                if va_match:
                    num_va2 = va_match.group(1)
                    tipo_va2 = f"VA{num_va2}"
                    nota_valor2 = None

                    # Procurar nota nas próximas linhas (não na mesma linha)
                    for j in range(1, 10):
                        if i + j < len(linhas):
                            ln = linhas[i + j].strip()

                            # Pular linhas não-numéricas ou que contêm texto irrelevante
                            if any(skip in ln.lower() for skip in ['verificação', 'nota', 'gráfico', 'aprendizagem', '/']):
                                continue

                            # Pular se encontrar nova disciplina
                            if any(p in ln.upper() for p in ['FUNDAMENTOS', 'COMPUTAÇÃO', 'ENGENHARIA', 'INTRODUÇÃO', 'ALGORITMOS', 'CIDADANIA', 'LEITURA']):
                                break

                            # Procurar número standalone
                            m2 = re.match(r'^(\d{1,3}(?:[.,]\d+)?)$', ln)
                            if m2:
                                val = float(m2.group(1).replace(',', '.'))
                                if 0 <= val <= 100:
                                    nota_valor2 = val
                                    break

                    if nota_valor2 is not None and nota_valor2 > 10:
                        nota_valor2 = round(nota_valor2 / 10, 1)

                    if nota_valor2 is not None:
                        disc_key2 = normalizar_disciplina(disciplina_atual)
                        if disc_key2 not in dados_notas:
                            dados_notas[disc_key2] = {
                                'disciplina': disciplina_atual,
                                'va1': 0.0,
                                'va2': 0.0,
                                'va3': 0.0,
                                'media': 0.0,
                                'situacao': 'Cursando'
                            }
                        if tipo_va2 == 'VA1':
                            if dados_notas[disc_key2]['va1'] == 0.0 or nota_valor2 > dados_notas[disc_key2]['va1']:
                                dados_notas[disc_key2]['va1'] = nota_valor2
                        elif tipo_va2 == 'VA2':
                            if dados_notas[disc_key2]['va2'] == 0.0 or nota_valor2 > dados_notas[disc_key2]['va2']:
                                dados_notas[disc_key2]['va2'] = nota_valor2
                        elif tipo_va2 == 'VA3':
                            if dados_notas[disc_key2]['va3'] == 0.0 or nota_valor2 > dados_notas[disc_key2]['va3']:
                                dados_notas[disc_key2]['va3'] = nota_valor2

            i += 1

        # Calcular médias - SEMPRE dividir por 3
        for disc_key, dados in dados_notas.items():
            soma = dados['va1'] + dados['va2'] + dados['va3']
            dados['media'] = round(soma / 3, 1)

            notas_preenchidas = sum(1 for n in [dados['va1'], dados['va2'], dados['va3']] if n > 0)

            if notas_preenchidas >= 3:
                dados['situacao'] = 'Aprovado' if dados['media'] >= 6.0 else 'Reprovado'
            else:
                dados['situacao'] = 'Cursando'

        resultado = list(dados_notas.values())

        # VALIDAÇÃO: Verificar se os dados fazem sentido
        print(f"\n   📊 VALIDAÇÃO DOS DADOS EXTRAÍDOS:")
        for nota in resultado:
            # Notas devem estar entre 0 e 10
            for va in ['va1', 'va2', 'va3']:
                if nota[va] < 0 or nota[va] > 10:
                    print(f"      ⚠️ ALERTA: {nota['disciplina']} tem {va.upper()}={nota[va]} fora do range 0-10")
                    # Corrigir valores fora do range
                    nota[va] = max(0, min(10, nota[va]))

            # Média deve ser coerente
            soma_calc = nota['va1'] + nota['va2'] + nota['va3']
            media_calc = round(soma_calc / 3, 1)
            if nota['media'] != media_calc:
                print(f"      ⚠️ ALERTA: Média inconsistente para {nota['disciplina']}: {nota['media']} vs calculado {media_calc}")
                nota['media'] = media_calc

        print(f"\n   📊 Total de disciplinas com notas: {len(resultado)}")
        for nota in resultado:
            print(f"      • {nota['disciplina']}: VA1={nota['va1']}, VA2={nota['va2']}, VA3={nota['va3']}, Média={nota['media']}, {nota['situacao']}")

    except Exception as e:
        print(f"❌ [LYCEUM] Erro ao extrair notas: {e}")
        import traceback
        traceback.print_exc()

    return list(dados_notas.values()) if dados_notas else []


# ============================================
# EXTRAIR FREQUÊNCIA - V13.0 COM PARSING ROBUSTO
# ============================================
def extrair_frequencia(driver):
    """
    Extrai frequência da página: Avaliação > Frequência
    URL: https://portal.unievangelica.edu.br/aluno/#/home/frequencia

    Formato esperado do Lyceum:
    DISCIPLINA_NAME (header em azul)
    Faltas                    X
    Frequência (%)            Y.YY

    IMPORTANTE: Parsing line-by-line para evitar confusão de valores
    """
    print("\n📅 [LYCEUM] Extraindo FREQUÊNCIA (V13.0)...")
    dados_faltas = {}

    # Termos do menu/header que NÃO são disciplinas
    IGNORAR_TERMOS = [
        'AVALIAÇÃO', 'FREQUÊNCIA (%)', 'FALTAS', 'DISCIPLINA',
        'INTELIGÊNCIA ARTIFICIAL', 'RA:', 'SÉRIE', 'PERÍODO',
        'TURMA', 'STATUS', 'CALENDÁRIO', 'CADASTRO', 'SECRETARIA',
        'FINANCEIRO', 'BIBLIOTECA', 'IDIOMA', 'SAIR', 'AVISO',
        'NOTAS', 'AVALIAÇÃO INSTITUCIONAL', 'UNIEVANGELICA',
        'UNIVERSIDADE EVANGÉLICA', 'FELIPPE', 'ALMEIDA', 'RODRIGUES'
    ]

    # Palavras-chave que identificam disciplinas reais
    PALAVRAS_DISCIPLINA = [
        'FUNDAMENTOS', 'COMPUTAÇÃO', 'ENGENHARIA', 'INTRODUÇÃO',
        'ALGORITMOS', 'PROGRAMAÇÃO', 'MATEMÁTIC', 'CIDADANIA',
        'ÉTICA', 'ESPIRITUALIDADE', 'LEITURA', 'INTERPRETAÇÃO',
        'TEXTO', 'DADOS', 'INFRAESTRUTURA', 'SOLUÇÕES', 'ON-LINE',
        'ONLINE', 'MATEMÁTICA'
    ]

    try:
        driver.get("https://portal.unievangelica.edu.br/aluno/#/home/frequencia")
        time.sleep(6)

        print(f"   URL: {driver.current_url}")

        # SCROLL agressivo para carregar todo o conteúdo
        for scroll_attempt in range(15):
            driver.execute_script("""
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
            """)
            time.sleep(0.8)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)

        time.sleep(3)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        for _ in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

        body_text = driver.find_element(By.TAG_NAME, "body").text

        print(f"   Tamanho do texto: {len(body_text)} caracteres")

        # Debug - mostrar conteúdo
        print("   === CONTEÚDO DA PÁGINA DE FREQUÊNCIA ===")
        print(body_text[:5000])
        print("   === FIM ===")

        def is_disciplina_valida(texto):
            """Verifica se o texto é um nome de disciplina válido"""
            texto_upper = texto.upper().strip()

            # Muito curto não é disciplina
            if len(texto_upper) < 10:
                return False

            # Verificar se contém termos do menu/header
            for termo in IGNORAR_TERMOS:
                if termo in texto_upper and not any(p in texto_upper for p in PALAVRAS_DISCIPLINA):
                    return False

            # Linhas que começam com código numérico não são disciplinas
            if re.match(r'^\d{4}\s*-', texto_upper):
                return False

            # Deve conter pelo menos uma palavra-chave de disciplina
            return any(p in texto_upper for p in PALAVRAS_DISCIPLINA)

        linhas = body_text.split('\n')
        linhas = [l.strip() for l in linhas if l.strip()]

        # Estratégia: Procurar padrões "Faltas" seguido de número na próxima linha
        # e associar com a disciplina mais próxima acima
        i = 0
        disciplina_atual = None

        while i < len(linhas):
            linha = linhas[i]
            linha_upper = linha.upper().strip()

            # Detectar header de disciplina
            if is_disciplina_valida(linha) or linha_upper == 'TOTAL':
                disciplina_atual = limpar_texto(linha)
                i += 1
                continue

            # Detectar linha "Faltas"
            if linha_upper == 'FALTAS' and disciplina_atual:
                # A próxima linha deve ser o número de faltas
                faltas = 0
                freq = 100.0

                # Procurar número de faltas nas próximas linhas
                for j in range(1, 5):
                    if i + j < len(linhas):
                        prox = linhas[i + j].strip()

                        # Se encontrar um número standalone, é o número de faltas
                        if re.match(r'^\d+$', prox):
                            faltas = int(prox)
                            break

                        # Se encontrar "Frequência", próximo valor é a frequência
                        if prox.upper().startswith('FREQUÊNCIA'):
                            # Buscar o valor na próxima linha ou mesma linha
                            freq_match = re.search(r'(\d+(?:[.,]\d+)?)', prox)
                            if freq_match:
                                freq = float(freq_match.group(1).replace(',', '.'))
                            elif i + j + 1 < len(linhas):
                                freq_line = linhas[i + j + 1].strip()
                                freq_match2 = re.match(r'^(\d+(?:[.,]\d+)?)$', freq_line)
                                if freq_match2:
                                    freq = float(freq_match2.group(1).replace(',', '.'))
                            break

                # Buscar frequência se ainda não encontrou
                for j in range(1, 8):
                    if i + j < len(linhas):
                        prox = linhas[i + j].strip()
                        if 'FREQUÊNCIA' in prox.upper() or prox.upper().startswith('FREQUÊNCIA'):
                            # Procurar número na mesma linha ou próxima
                            freq_match = re.search(r'(\d+(?:[.,]\d+)?)', prox)
                            if freq_match:
                                freq = float(freq_match.group(1).replace(',', '.'))
                            elif i + j + 1 < len(linhas):
                                freq_line = linhas[i + j + 1].strip()
                                freq_match2 = re.match(r'^(\d+(?:[.,]\d+)?)$', freq_line)
                                if freq_match2:
                                    freq = float(freq_match2.group(1).replace(',', '.'))
                            break

                # Sanitização
                if freq > 100:
                    freq = 100.0
                if freq < 0:
                    freq = 0.0
                if faltas < 0:
                    faltas = 0

                # Validação: faltas muito altas (>60) são provavelmente erros de parsing
                if faltas > 60:
                    print(f"   ⚠️ Faltas suspeitas para {disciplina_atual}: {faltas} (ignorando)")
                    # Se faltas > 60 e frequência está perto de 100%, provavelmente foi erro de parse
                    if freq >= 90:
                        faltas = 0

                disc_key = normalizar_disciplina(disciplina_atual)

                # Evitar sobrescrever com valores piores
                prev = dados_faltas.get(disc_key)
                if not prev or faltas <= prev.get('total_faltas', 999):
                    dados_faltas[disc_key] = {
                        'disciplina': disciplina_atual,
                        'total_faltas': faltas,
                        'percentual': freq
                    }
                    print(f"   📚 {disciplina_atual}: {faltas} faltas, {freq}%")

            i += 1

        # Fallback: Se não encontrou dados, tentar parsing alternativo
        if not dados_faltas:
            print("   ⚠️ Parsing primário falhou, tentando método alternativo...")

            # Método 2: Procurar padrões "DISCIPLINA Faltas X Frequência Y%"
            for i, linha in enumerate(linhas):
                if is_disciplina_valida(linha):
                    disciplina = limpar_texto(linha)
                    disc_key = normalizar_disciplina(disciplina)

                    # Procurar Faltas e Frequência nas próximas linhas
                    bloco = "\n".join(linhas[i:i+10])

                    faltas = 0
                    freq = 100.0

                    # Extrair faltas - procurar "Faltas" seguido de número
                    m_faltas = re.search(r'Faltas\s*\n?\s*(\d+)', bloco, re.IGNORECASE)
                    if m_faltas:
                        val = int(m_faltas.group(1))
                        # Validar que não é porcentagem
                        if val <= 60:
                            faltas = val

                    # Extrair frequência
                    m_freq = re.search(r'Frequência.*?(\d+(?:[.,]\d+)?)', bloco, re.IGNORECASE)
                    if m_freq:
                        freq = float(m_freq.group(1).replace(',', '.'))
                        if freq > 100:
                            freq = 100.0

                    if disc_key not in dados_faltas:
                        dados_faltas[disc_key] = {
                            'disciplina': disciplina,
                            'total_faltas': faltas,
                            'percentual': freq
                        }
                        print(f"   📚 (alt) {disciplina}: {faltas} faltas, {freq}%")

        # Remover entrada TOTAL se existir (não é uma disciplina)
        total_key = normalizar_disciplina('TOTAL')
        if total_key in dados_faltas:
            total_info = dados_faltas.pop(total_key)
            # Usar TOTAL para validação
            soma_faltas = sum(v['total_faltas'] for v in dados_faltas.values())
            print(f"   📊 Validação TOTAL: extraído {total_info['total_faltas']} vs soma {soma_faltas}")

        resultado = list(dados_faltas.values())

        print(f"\n   📅 Total de disciplinas com frequência: {len(resultado)}")
        for f in resultado:
            print(f"      • {f['disciplina']}: {f['total_faltas']} faltas, {f['percentual']}%")

    except Exception as e:
        print(f"❌ [LYCEUM] Erro ao extrair frequência: {e}")
        import traceback
        traceback.print_exc()

    return list(dados_faltas.values()) if dados_faltas else []


# ============================================
# EXTRAIR HORÁRIOS - V9.0 COM NAVEGAÇÃO POR DIAS
# ============================================
def extrair_horarios(driver):
    """
    Extrai horários da página: Calendário > Horário de Aulas
    URL: https://portal.unievangelica.edu.br/aluno/#/home/aulas

    Estrutura do Lyceum (baseado no print):
    - Dropdown "Dia da Semana" para selecionar o dia
    - Lista por dia: Disciplina | Local (BLOCO X - Yº PISO - SALA Z) | Horário

    IMPORTANTE: Precisa navegar pelo dropdown para pegar TODOS os dias!
    """
    print("\n🕐 [LYCEUM] Extraindo HORÁRIOS (V9.0)...")
    dados_horarios = []

    # Mapear dias
    dias_map = {
        'segunda': {'num': 1, 'nome': 'Segunda-feira'},
        'terça': {'num': 2, 'nome': 'Terça-feira'},
        'terca': {'num': 2, 'nome': 'Terça-feira'},
        'quarta': {'num': 3, 'nome': 'Quarta-feira'},
        'quinta': {'num': 4, 'nome': 'Quinta-feira'},
        'sexta': {'num': 5, 'nome': 'Sexta-feira'},
        'sábado': {'num': 6, 'nome': 'Sábado'},
        'sabado': {'num': 6, 'nome': 'Sábado'},
    }

    # Termos que NÃO são disciplinas
    IGNORAR_TERMOS = [
        'DIA DA SEMANA', 'TODOS', 'HORÁRIO DE AULAS',
        'INTELIGÊNCIA ARTIFICIAL', 'RA:', 'SÉRIE', 'PERÍODO', 'TURMA',
        'CALENDÁRIO', 'AVALIAÇÃO', 'DISCIPLINA', 'CADASTRO',
        'SECRETARIA', 'FINANCEIRO', 'BIBLIOTECA', 'SAIR', 'AVISO'
    ]

    try:
        driver.get("https://portal.unievangelica.edu.br/aluno/#/home/aulas")
        time.sleep(5)

        print(f"   URL: {driver.current_url}")

        wait = WebDriverWait(driver, 10)

        # Tentar clicar no dropdown "Dia da Semana" e selecionar "Todos"
        try:
            # Procurar dropdown
            dropdown = None

            # Tentar encontrar por diferentes seletores
            selectors = [
                "mat-select",
                "[role='listbox']",
                "select",
                "div[class*='dropdown']",
                "button[class*='dropdown']"
            ]

            for sel in selectors:
                try:
                    dropdown = driver.find_element(By.CSS_SELECTOR, sel)
                    if dropdown:
                        break
                except:
                    continue

            if dropdown:
                print("   📋 Dropdown encontrado, tentando selecionar 'Todos'...")
                dropdown.click()
                time.sleep(1)

                # Tentar clicar em "Todos"
                try:
                    todos_option = driver.find_element(By.XPATH, "//*[contains(text(), 'Todos')]")
                    todos_option.click()
                    time.sleep(2)
                    print("   ✓ Selecionado 'Todos' no dropdown")
                except:
                    print("   ⚠️ Opção 'Todos' não encontrada")
        except Exception as e:
            print(f"   ⚠️ Dropdown não encontrado: {e}")

        time.sleep(3)

        # Fazer scroll para garantir que toda a página carregue
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        body_text = driver.find_element(By.TAG_NAME, "body").text

        print(f"   Tamanho do texto: {len(body_text)} caracteres")

        # Debug
        print("   === CONTEÚDO DA PÁGINA DE HORÁRIOS ===")
        print(body_text[:5000])
        print("   === FIM ===")

        # Função para verificar se é disciplina válida
        def is_disciplina_valida(texto):
            texto_upper = texto.upper().strip()

            if len(texto_upper) < 10:
                return False

            for termo in IGNORAR_TERMOS:
                if termo in texto_upper:
                    return False

            # Ignorar se começa com código numérico
            if re.match(r'^\d{4}\s*-', texto_upper):
                return False

            # Disciplinas válidas contêm palavras-chave
            palavras_disciplina = [
                'FUNDAMENTOS', 'COMPUTAÇÃO', 'ENGENHARIA', 'INTRODUÇÃO',
                'ALGORITMOS', 'PROGRAMAÇÃO', 'MATEMÁTIC', 'CIDADANIA',
                'ÉTICA', 'ESPIRITUALIDADE', 'LEITURA', 'INTERPRETAÇÃO',
                'TEXTO', 'DADOS', 'INFRAESTRUTURA', 'SOLUÇÕES'
            ]

            for palavra in palavras_disciplina:
                if palavra in texto_upper:
                    return True

            return False

        linhas = body_text.split('\n')

        dia_atual = None
        dia_num = 0

        i = 0
        while i < len(linhas):
            linha = linhas[i].strip()

            if not linha:
                i += 1
                continue

            linha_lower = linha.lower()

            # Detectar dia da semana
            dia_encontrado = False
            for dia_key, dia_info in dias_map.items():
                if dia_key in linha_lower and ('feira' in linha_lower or linha_lower.endswith(dia_key)):
                    dia_atual = dia_info['nome']
                    dia_num = dia_info['num']
                    print(f"   📆 {dia_atual}")
                    dia_encontrado = True
                    break

            if dia_encontrado:
                i += 1
                continue

            # Se temos um dia atual, procurar aulas
            if dia_atual and is_disciplina_valida(linha):
                disciplina = limpar_texto(linha)
                local = ""
                horario_inicio = ""
                horario_fim = ""

                # Próximas linhas: local e horário
                for j in range(1, 6):
                    if i + j < len(linhas):
                        prox = linhas[i + j].strip()

                        # Local (BLOCO...)
                        if 'BLOCO' in prox.upper() or ('PISO' in prox.upper() and 'SALA' in prox.upper()):
                            local = prox

                        # Horário (XX:XX - XX:XX)
                        match_hora = re.match(r'^(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})$', prox)
                        if match_hora:
                            horario_inicio = match_hora.group(1)
                            horario_fim = match_hora.group(2)
                            break

                if disciplina and horario_inicio:
                    # Verificar se já existe (evitar duplicados)
                    existe = False
                    for aula in dados_horarios:
                        if (aula['dia_semana'] == dia_num and
                            aula['horario_inicio'] == horario_inicio and
                            aula['disciplina'] == disciplina):
                            existe = True
                            break

                    if not existe:
                        aula = {
                            'dia_semana': dia_num,
                            'dia_nome': dia_atual,
                            'disciplina': disciplina,
                            'horario_inicio': horario_inicio,
                            'horario_fim': horario_fim,
                            'local': local,
                            'professor': ''
                        }

                        dados_horarios.append(aula)
                        print(f"      ✓ {disciplina}")
                        print(f"        📍 {local}")
                        print(f"        ⏰ {horario_inicio} - {horario_fim}")

            i += 1

        # Se não encontrou muito, tentar estratégia 2: navegar por cada dia
        if len(dados_horarios) < 5:
            print("\n   ⚠️ Poucos horários encontrados, tentando navegar por cada dia...")

            dias_para_navegar = [
                ('Segunda', 1, 'Segunda-feira'),
                ('Terça', 2, 'Terça-feira'),
                ('Quarta', 3, 'Quarta-feira'),
                ('Quinta', 4, 'Quinta-feira'),
                ('Sexta', 5, 'Sexta-feira'),
            ]

            for dia_texto, dia_num, dia_nome in dias_para_navegar:
                try:
                    # Tentar clicar no dropdown e selecionar o dia
                    dropdown = driver.find_element(By.CSS_SELECTOR, "mat-select, select, [role='listbox']")
                    dropdown.click()
                    time.sleep(1)

                    # Selecionar o dia
                    opcao = driver.find_element(By.XPATH, f"//*[contains(text(), '{dia_texto}')]")
                    opcao.click()
                    time.sleep(2)

                    # Pegar o texto da página
                    body_text = driver.find_element(By.TAG_NAME, "body").text
                    linhas = body_text.split('\n')

                    # Processar as aulas deste dia
                    for idx, linha in enumerate(linhas):
                        linha = linha.strip()
                        if is_disciplina_valida(linha):
                            disciplina = limpar_texto(linha)
                            local = ""
                            horario_inicio = ""
                            horario_fim = ""

                            for j in range(1, 6):
                                if idx + j < len(linhas):
                                    prox = linhas[idx + j].strip()

                                    if 'BLOCO' in prox.upper():
                                        local = prox

                                    match_hora = re.match(r'^(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})$', prox)
                                    if match_hora:
                                        horario_inicio = match_hora.group(1)
                                        horario_fim = match_hora.group(2)
                                        break

                            if disciplina and horario_inicio:
                                existe = any(
                                    a['dia_semana'] == dia_num and
                                    a['horario_inicio'] == horario_inicio and
                                    a['disciplina'] == disciplina
                                    for a in dados_horarios
                                )

                                if not existe:
                                    aula = {
                                        'dia_semana': dia_num,
                                        'dia_nome': dia_nome,
                                        'disciplina': disciplina,
                                        'horario_inicio': horario_inicio,
                                        'horario_fim': horario_fim,
                                        'local': local,
                                        'professor': ''
                                    }
                                    dados_horarios.append(aula)
                                    print(f"      ✓ [{dia_nome}] {disciplina} ({horario_inicio})")

                except Exception as e:
                    print(f"      ⚠️ Erro ao navegar para {dia_texto}: {e}")
                    continue

        # Ordenar por dia e horário
        dados_horarios.sort(key=lambda x: (x['dia_semana'], x['horario_inicio']))

        print(f"\n   🕐 Total de aulas: {len(dados_horarios)}")

        # Resumo por dia
        dias_resumo = {}
        for aula in dados_horarios:
            dia = aula['dia_nome']
            if dia not in dias_resumo:
                dias_resumo[dia] = 0
            dias_resumo[dia] += 1

        for dia, count in dias_resumo.items():
            print(f"      • {dia}: {count} aulas")

    except Exception as e:
        print(f"❌ [LYCEUM] Erro ao extrair horários: {e}")
        import traceback
        traceback.print_exc()

    return dados_horarios


# ============================================
# EXTRAIR CALENDÁRIO - V13.0 COM NAVEGAÇÃO COMPLETA
# ============================================
def extrair_calendario(driver, horarios=None):
    """
    Extrai calendário da página: Calendário > Calendário
    URL: https://portal.unievangelica.edu.br/aluno/#/home/agenda

    IMPORTANTE:
    - Navegar por TODOS os meses do ano
    - Capturar FERIADOS e AULAS corretamente
    - Usar seletores mais robustos para navegação
    """
    print("\n📆 [LYCEUM] Extraindo CALENDÁRIO (V13.0)...")
    eventos = []
    feriados_encontrados = set()
    aulas_encontradas = set()

    try:
        driver.get("https://portal.unievangelica.edu.br/aluno/#/home/agenda")
        time.sleep(6)

        print(f"   URL: {driver.current_url}")

        meses_num_map = {
            'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
            'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
            'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
        }

        wait = WebDriverWait(driver, 10)

        try:
            for _ in range(12):
                btn_prev = None
                selectors_prev = [
                    "button[aria-label*='prev']",
                    "button[aria-label*='anterior']",
                    "button[aria-label*='Previous']",
                    "button.mat-icon-button:first-of-type",
                    "button[class*='prev']",
                    ".mat-calendar-previous-button",
                    "[class*='calendar-prev']"
                ]
                for sel in selectors_prev:
                    try:
                        btn_prev = driver.find_element(By.CSS_SELECTOR, sel)
                        if btn_prev.is_displayed() and btn_prev.is_enabled():
                            btn_prev.click()
                            time.sleep(2)
                            break
                    except:
                        continue
                if not btn_prev:
                    try:
                        result = driver.execute_script("""
                            var buttons = document.querySelectorAll('button');
                            for (var btn of buttons) {
                                var text = btn.textContent || '';
                                var ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
                                var className = (btn.className || '').toLowerCase();
                                if (text.includes('<') || ariaLabel.includes('prev') || ariaLabel.includes('anterior') || className.includes('prev')) {
                                    if (btn.offsetParent !== null) { btn.click(); return true; }
                                }
                            }
                            return false;
                        """)
                        if not result:
                            break
                        time.sleep(2)
                    except:
                        break
        except:
            pass

        # Processar 12 meses (ano completo)
        for mes_idx in range(12):
            time.sleep(2)

            # Scroll agressivo para garantir carregamento
            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)

            # Aguardar carregamento do calendário
            time.sleep(2)

            # Tentar obter texto do calendário usando diferentes métodos
            body_text = ""
            try:
                # Método 1: Texto do body
                body_text = driver.find_element(By.TAG_NAME, "body").text
            except:
                try:
                    # Método 2: Texto de elementos específicos do calendário
                    calendario_elem = driver.find_element(By.CSS_SELECTOR, "mat-calendar, .mat-calendar, [class*='calendar']")
                    body_text = calendario_elem.text
                except:
                    body_text = driver.find_element(By.TAG_NAME, "body").text

            # Detectar mês e ano atual
            match_mes = re.search(r'(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+de?\s*(\d{4})', body_text.lower())

            if match_mes:
                mes_nome = match_mes.group(1)
                ano = int(match_mes.group(2))
                mes_num = meses_num_map.get(mes_nome, 12)
                print(f"\n   📅 Processando: {mes_nome.capitalize()} {ano}")
            else:
                # Tentar usar data atual
                hoje = datetime.now()
                mes_num = (hoje.month + mes_idx - 1) % 12 + 1
                if mes_num == 0:
                    mes_num = 12
                ano = hoje.year + ((hoje.month + mes_idx - 1) // 12)
                mes_nome = list(meses_num_map.keys())[mes_num - 1]
                print(f"\n   📅 Processando (estimado): {mes_nome.capitalize()} {ano}")

            linhas = body_text.split('\n')
            linhas = [l.strip() for l in linhas if l.strip()]

            # Mapear dias do calendário - criar um dicionário para rastrear dias
            dias_calendario = {}
            ultimo_dia = None
            dia_atual = None

            # Primeiro, identificar todos os dias no calendário
            for i, linha in enumerate(linhas):
                # Verificar se é um número de dia (1-31)
                if linha.isdigit() and 1 <= int(linha) <= 31:
                    dia_num = int(linha)
                    ultimo_dia = dia_num
                    dia_atual = dia_num
                    try:
                        data_obj = datetime(ano, mes_num, dia_num)
                        dias_calendario[dia_num] = data_obj
                    except:
                        pass

            # Preparar contexto de datas por texto (modo lista)
            ultima_data_textual = None
            tem_aula_no_mes = False
            has_aula_word = ('aula' in body_text.lower())

            # Agora processar eventos
            for i, linha in enumerate(linhas):
                linha_lower = linha.lower().strip()

                # Capturar data textual (dd/mm/aaaa)
                mdata = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', linha)
                if mdata:
                    try:
                        dt = datetime.strptime(mdata.group(1), '%d/%m/%Y')
                        ultima_data_textual = dt
                    except:
                        pass
                else:
                    mdata2 = re.search(r'(\d{1,2}/\d{1,2})', linha)
                    if mdata2:
                        try:
                            dt2 = datetime.strptime(f"{mdata2.group(1)}/{ano}", '%d/%m/%Y')
                            ultima_data_textual = dt2
                        except:
                            pass

                # Capturar FERIADOS - pode aparecer como "Feriado" ou em bloco vermelho
                if 'feriado' in linha_lower:
                    try:
                        data_obj = None
                        # 1) Tentar vincular ao número de dia mais próximo no grid
                        dia_feriado = None
                        for j in range(max(0, i-6), min(len(linhas), i+6)):
                            if linhas[j].isdigit() and 1 <= int(linhas[j]) <= 31:
                                dia_feriado = int(linhas[j])
                                break
                        if dia_feriado and dia_feriado in dias_calendario:
                            data_obj = dias_calendario[dia_feriado]

                        # 2) Tentar data textual completa próxima
                        if not data_obj:
                            for k in range(max(0, i-4), min(len(linhas), i+5)):
                                mm = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', linhas[k])
                                if mm:
                                    try:
                                        dt = datetime.strptime(mm.group(1), '%d/%m/%Y')
                                        data_obj = dt
                                        break
                                    except:
                                        pass

                        # 3) Tentar dd/mm assumindo ano corrente do cabeçalho
                        if not data_obj:
                            for k in range(max(0, i-4), min(len(linhas), i+5)):
                                mm2 = re.search(r'(\d{1,2}/\d{1,2})', linhas[k])
                                if mm2:
                                    try:
                                        data_obj = datetime.strptime(f"{mm2.group(1)}/{ano}", '%d/%m/%Y')
                                        break
                                    except:
                                        pass

                        # 4) Último recurso: usar última_data_textual
                        if not data_obj and ultima_data_textual:
                            data_obj = ultima_data_textual

                        if not data_obj:
                            continue

                        if data_obj.month == mes_num and data_obj.year == ano:
                            data_iso = data_obj.strftime('%Y-%m-%d')
                            if data_iso not in feriados_encontrados:
                                feriados_encontrados.add(data_iso)
                                eventos.append({
                                    'titulo': 'Feriado',
                                    'data': data_iso,
                                    'tipo': 'feriado',
                                    'cor': '#e74c3c',
                                    'descricao': 'Feriado'
                                })
                                print(f"      🎉 Feriado: {data_iso}")
                    except Exception:
                        pass

                # Capturar AULAS - formato "HH:MM-HH:MM" ou "Aula HH:MM-HH:MM"
                match_aula = re.search(r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})', linha)
                if match_aula:
                    hora_inicio = match_aula.group(1)
                    hora_fim = match_aula.group(2)

                    # Verificar se é uma aula (pode ter "aula" na linha ou próxima)
                    is_aula = 'aula' in linha_lower
                    if not is_aula and i + 1 < len(linhas):
                        is_aula = 'aula' in linhas[i + 1].lower()

                    if is_aula:
                        try:
                            data_obj = None
                            if ultima_data_textual:
                                data_obj = ultima_data_textual
                            else:
                                dia_aula = ultimo_dia
                                for j in range(max(0, i-5), min(len(linhas), i+5)):
                                    if linhas[j].isdigit() and 1 <= int(linhas[j]) <= 31:
                                        dia_aula = int(linhas[j])
                                        break
                                if dia_aula in dias_calendario:
                                    data_obj = dias_calendario[dia_aula]

                            if data_obj is not None and data_obj.month == mes_num and data_obj.year == ano:
                                data_iso = data_obj.strftime('%Y-%m-%d')

                                chave = f"aula|{data_iso}|{hora_inicio}"
                                if chave not in aulas_encontradas:
                                    aulas_encontradas.add(chave)
                                    eventos.append({
                                        'titulo': f"Aula {hora_inicio}-{hora_fim}",
                                        'data': data_iso,
                                        'tipo': 'aula',
                                        'cor': '#4a90e2',
                                        'descricao': f'{hora_inicio} - {hora_fim}'
                                    })
                                    print(f"      📚 Aula: {data_iso} às {hora_inicio}")
                                    tem_aula_no_mes = True
                        except Exception as e:
                            pass

            # Gerar aulas a partir da grade semanal, se disponível
            # Sempre gerar para evitar meses em branco e replicar a visão do Lyceum
            if horarios:
                try:
                    mapa = {}
                    for h in horarios:
                        ds = h.get('dia_semana')
                        if not ds:
                            continue
                        mapa.setdefault(ds, []).append((h.get('horario_inicio'), h.get('horario_fim')))
                    for dia in range(1, 32):
                        try:
                            d = datetime(ano, mes_num, dia)
                        except:
                            continue
                        dow = d.weekday() + 1
                        data_iso = d.strftime('%Y-%m-%d')
                        if data_iso in feriados_encontrados:
                            continue
                        if dow in mapa:
                            for inicio, fim in mapa[dow]:
                                if not inicio or not fim:
                                    continue
                                chave = f"aula|{data_iso}|{inicio}"
                                if chave in aulas_encontradas:
                                    continue
                                aulas_encontradas.add(chave)
                                eventos.append({
                                    'titulo': f"Aula {inicio}-{fim}",
                                    'data': data_iso,
                                    'tipo': 'aula',
                                    'cor': '#4a90e2',
                                    'descricao': f"{inicio} - {fim}"
                                })
                except Exception as e:
                    pass

            # Avançar para próximo mês
            if mes_idx < 11:
                try:
                    clicou = False

                    # Método 1: Procurar botão de próximo mês por vários seletores
                    selectors = [
                        "button[aria-label*='next']",
                        "button[aria-label*='próximo']",
                        "button[aria-label*='Next']",
                        "button.mat-icon-button:last-of-type",
                        "button[class*='next']",
                        "button[class*='forward']",
                        ".mat-calendar-next-button",
                        "[class*='calendar-next']"
                    ]

                    for selector in selectors:
                        try:
                            btn = driver.find_element(By.CSS_SELECTOR, selector)
                            if btn.is_displayed() and btn.is_enabled():
                                btn.click()
                                clicou = True
                                break
                        except:
                            continue

                    # Método 2: JavaScript para encontrar e clicar no botão
                    if not clicou:
                        try:
                            result = driver.execute_script("""
                                var buttons = document.querySelectorAll('button');
                                for (var btn of buttons) {
                                    var text = btn.textContent || '';
                                    var ariaLabel = btn.getAttribute('aria-label') || '';
                                    var className = btn.className || '';
                                    
                                    if ((text.includes('>') || text.includes('next') || text.includes('próximo')) ||
                                        (ariaLabel.toLowerCase().includes('next') || ariaLabel.toLowerCase().includes('próximo')) ||
                                        (className.toLowerCase().includes('next') || className.toLowerCase().includes('forward'))) {
                                        if (btn.offsetParent !== null) {
                                            btn.click();
                                            return true;
                                        }
                                    }
                                }
                                
                                // Tentar encontrar botão pela posição (direita)
                                var allButtons = Array.from(document.querySelectorAll('button'));
                                var rightButtons = allButtons.filter(b => {
                                    var rect = b.getBoundingClientRect();
                                    return rect.x > window.innerWidth / 2 && b.offsetParent !== null;
                                });
                                if (rightButtons.length > 0) {
                                    rightButtons[0].click();
                                    return true;
                                }
                                
                                return false;
                            """)
                            if result:
                                clicou = True
                        except:
                            pass

                    if clicou:
                        print(f"   ➡️ Avançando para próximo mês...")
                        time.sleep(3)  # Aguardar carregamento do próximo mês
                    else:
                        print(f"   ⚠️ Não foi possível avançar para próximo mês")

                except Exception as e:
                    print(f"   ⚠️ Erro ao navegar: {e}")

        # Remover duplicados e filtrar por ano do Lyceum quando disponível
        eventos_unicos = {}
        for ev in eventos:
            chave = (ev['titulo'], ev['data'])
            if chave not in eventos_unicos:
                eventos_unicos[chave] = ev
        eventos = list(eventos_unicos.values())

        print(f"\n   📆 Total de eventos: {len(eventos)}")
        print(f"   🎉 Feriados: {len(feriados_encontrados)}")
        print(f"   📚 Aulas: {len(aulas_encontradas)}")

    except Exception as e:
        print(f"❌ [LYCEUM] Erro ao extrair calendário: {e}")
        import traceback
        traceback.print_exc()

    return eventos


# ============================================
# EXTRAIR DISCIPLINAS MATRICULADAS
# ============================================
def extrair_disciplinas(driver):
    print("\n📚 [LYCEUM] Extraindo DISCIPLINAS...")
    dados_disciplinas = []

    try:
        driver.get("https://portal.unievangelica.edu.br/aluno/#/home/disciplinas")
        time.sleep(5)

        body_text = driver.find_element(By.TAG_NAME, "body").text

        print(f"   Tamanho do texto: {len(body_text)} caracteres")

        # Procurar disciplinas no texto
        linhas = body_text.split('\n')

        for linha in linhas:
            linha = linha.strip()

            # Disciplinas geralmente são em maiúsculas ou título
            if (re.match(r'^[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ]', linha) and
                len(linha) > 15 and
                linha not in ['Disciplina', 'Disciplinas', 'DISCIPLINAS']):

                # Verificar se não é um menu/header
                if any(x in linha.upper() for x in ['FUNDAMENTOS', 'INTRODUÇÃO', 'CIDADANIA', 'LEITURA', 'ALGORITMOS', 'ENGENHARIA']):
                    disciplina = limpar_texto(linha)

                    # Evitar duplicados
                    if disciplina not in [d['disciplina'] for d in dados_disciplinas]:
                        dados_disciplinas.append({
                            'disciplina': disciplina,
                            'situacao': 'Matriculado',
                            'periodo': '',
                            'docente': '',
                            'data_inicial': ''
                        })
                        print(f"      ✓ {disciplina}")

        print(f"\n   📚 Total de disciplinas: {len(dados_disciplinas)}")

    except Exception as e:
        print(f"❌ [LYCEUM] Erro ao extrair disciplinas: {e}")
        import traceback
        traceback.print_exc()

    return dados_disciplinas


# ============================================
# SALVAR DADOS NO BANCO
# ============================================
def salvar_dados_lyceum(user_id, notas, faltas, horarios, disciplinas, calendario=None):
    print(f"\n💾 [LYCEUM] Salvando dados no banco...")

    try:
        timestamp = datetime.now().isoformat()

        with get_db_connection_lyceum() as conn:
            c = conn.cursor()

            # NOTAS
            c.execute('DELETE FROM notas_aluno WHERE usuario_id = ?', (user_id,))
            for n in notas:
                c.execute('''
                    INSERT INTO notas_aluno (usuario_id, disciplina, va1, va2, va3, media, situacao)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, n['disciplina'], n['va1'], n['va2'], n['va3'], n['media'], n['situacao']))
            print(f"   ✓ {len(notas)} notas salvas")

            # FALTAS
            c.execute('DELETE FROM faltas_aluno WHERE usuario_id = ?', (user_id,))
            for f in faltas:
                c.execute('''
                    INSERT INTO faltas_aluno (usuario_id, disciplina, total_faltas, total_aulas, percentual_presenca)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, f['disciplina'], f['total_faltas'], f.get('total_aulas', 60), f['percentual']))
            print(f"   ✓ {len(faltas)} registros de frequência salvos")

            # HORÁRIOS
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

            c.execute('DELETE FROM horarios_aluno WHERE usuario_id = ?', (user_id,))
            for h in horarios:
                c.execute('''
                    INSERT INTO horarios_aluno (usuario_id, dia_semana, dia_nome, disciplina, horario_inicio, horario_fim, local, professor)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, h['dia_semana'], h['dia_nome'], h['disciplina'],
                      h['horario_inicio'], h['horario_fim'], h['local'], h.get('professor', '')))
            print(f"   ✓ {len(horarios)} horários salvos")

            # DISCIPLINAS
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

            c.execute('DELETE FROM disciplinas_aluno WHERE usuario_id = ?', (user_id,))
            for d in disciplinas:
                c.execute('''
                    INSERT INTO disciplinas_aluno (usuario_id, disciplina, situacao, periodo, docente, data_inicial)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, d['disciplina'], d['situacao'], d['periodo'],
                      d['docente'], d['data_inicial']))
            print(f"   ✓ {len(disciplinas)} disciplinas salvas")

            # CALENDÁRIO
            if calendario:
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

                c.execute('DELETE FROM calendario_lyceum WHERE usuario_id = ?', (user_id,))
                for evento in calendario:
                    c.execute('''
                        INSERT INTO calendario_lyceum (usuario_id, titulo, data_evento, tipo, cor, descricao)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (user_id, evento['titulo'], evento['data'], evento['tipo'],
                          evento['cor'], evento.get('descricao', '')))
                print(f"   ✓ {len(calendario)} eventos do calendário salvos")

            # TIMESTAMP
            c.execute('''
                UPDATE usuarios 
                SET ultima_atualizacao_lyceum = ? 
                WHERE id = ?
            ''', (timestamp, user_id))

            conn.commit()

            print(f"\n✅ [LYCEUM] Todos os dados salvos!")
            print(f"   Timestamp: {timestamp}")

    except Exception as e:
        print(f"❌ [LYCEUM] Erro ao salvar: {e}")
        import traceback
        traceback.print_exc()


# ============================================
# SINCRONIZAÇÃO PRINCIPAL
# ============================================
def sincronizar_dados_lyceum(user_id, matricula, cpf, forcar_atualizacao=False):
    print(f"\n{'=' * 80}")
    print(f"🚀 LYCEUM SCRAPER V8.0 - BASEADO NOS PRINTS REAIS")
    print(f"{'=' * 80}")
    print(f"User ID: {user_id}")
    print(f"Matrícula: {matricula}")
    print(f"Forçar: {forcar_atualizacao}")
    print(f"{'=' * 80}\n")

    # Verificar cache
    if not forcar_atualizacao:
        if usuario_tem_cache_lyceum(user_id):
            ultima = obter_ultima_sincronizacao_lyceum(user_id)
            if ultima:
                print(f"✅ CACHE ENCONTRADO")
                print(f"   Última sync: {ultima.strftime('%d/%m/%Y às %H:%M')}")
                return

    print("⚡ Iniciando scraping...\n")

    # Configurar Chrome
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = None

    try:
        from typing import Any
        selenium_service: Any = Service(ChromeDriverManager().install())
        chrome_opts: Any = chrome_options
        driver = webdriver.Chrome(
            service=selenium_service,
            options=chrome_opts
        )

        # Configurar timeouts maiores para evitar timeout
        driver.set_page_load_timeout(90)
        driver.implicitly_wait(20)

        # Login
        if not login_lyceum(driver, matricula, cpf):
            print("❌ [LYCEUM] Falha no login.")
            return

        # Extrair dados
        horarios = extrair_horarios(driver)
        notas = extrair_notas(driver)
        faltas = extrair_frequencia(driver)
        disciplinas = extrair_disciplinas(driver)
        # Garantir que todas disciplinas apareçam nas faltas
        try:
            faltas_keys = {normalizar_disciplina(f['disciplina']) for f in (faltas or [])}
            for d in disciplinas or []:
                dk = normalizar_disciplina(d['disciplina'])
                if dk not in faltas_keys:
                    (faltas or []).append({'disciplina': d['disciplina'], 'total_faltas': 0, 'percentual': 100.0, 'total_aulas': 60})
        except:
            pass
        calendario = extrair_calendario(driver, horarios)

        # Salvar
        if notas or faltas or horarios or disciplinas:
            salvar_dados_lyceum(user_id, notas, faltas, horarios, disciplinas, calendario)

            print(f"\n{'=' * 80}")
            print(f"✅ SINCRONIZAÇÃO CONCLUÍDA!")
            print(f"   • {len(notas)} disciplinas com notas")
            print(f"   • {len(faltas)} disciplinas com frequência")
            print(f"   • {len(horarios)} aulas no horário")
            print(f"   • {len(calendario)} eventos")
            print(f"   • {len(disciplinas)} disciplinas")
            print(f"{'=' * 80}\n")
        else:
            print("⚠️ Nenhum dado extraído.")

    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if driver:
            driver.quit()
            print("🏁 Driver encerrado.\n")


if __name__ == "__main__":
    print("=" * 80)
    print("LYCEUM SCRAPER V8.0")
    print("=" * 80)
    print("Execute via app.py!")
    print("=" * 80)
def auto_scroll(driver, vezes=12, pausa=1.2):
    try:
        for _ in range(vezes):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pausa)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(pausa)
    except Exception:
        pass

def extrair_disciplinas_v2(driver):
    print("\n📚 [LYCEUM] Extraindo DISCIPLINAS V2...")
    dados = []
    try:
        driver.get("https://portal.unievangelica.edu.br/aluno/#/home/disciplinas")
        time.sleep(3)
        auto_scroll(driver, 15, 1.0)
        body = driver.find_element(By.TAG_NAME, "body").text
        linhas = [l.strip() for l in body.split('\n') if l.strip()]
        def is_header(t):
            u = t.upper()
            return len(u) > 10 and any(p in u for p in ["FUNDAMENTOS", "INTRODUÇÃO", "ENGENHARIA", "ALGORITMOS", "CIDADANIA", "LEITURA", "TEXTO", "INFRAESTRUTURA"]) and "DISCIPLINA" not in u and "SITUAÇÃO" not in u
        i = 0
        while i < len(linhas):
            if not is_header(linhas[i]):
                i += 1
                continue
            titulo = linhas[i]
            j = i + 1
            while j < len(linhas) and not is_header(linhas[j]):
                j += 1
            bloco = "\n".join(linhas[i:j])
            sit = None
            per = None
            doc = None
            data = None
            m = re.search(r"Situação\s*\n\s*([A-Za-zÁ-ú\s]+)", bloco, re.IGNORECASE)
            if m:
                sit = limpar_texto(m.group(1))
            m = re.search(r"Período\s*\n\s*([\w\sºª\-\/]+)", bloco, re.IGNORECASE)
            if m:
                per = limpar_texto(m.group(1))
            m = re.search(r"Docente\s*\n\s*([A-Za-zÁ-ú\s\.]+)", bloco, re.IGNORECASE)
            if m:
                doc = limpar_texto(m.group(1))
            m = re.search(r"Data\s*Inicial\s*\n\s*(\d{2}/\d{2}/\d{4})", bloco, re.IGNORECASE)
            if m:
                data = m.group(1)
            registro = {
                'disciplina': limpar_texto(titulo),
                'situacao': sit or 'Matriculado',
                'periodo': per or '',
                'docente': doc or '',
                'data_inicial': data or ''
            }
            dados.append(registro)
            print(f"      ✓ {registro['disciplina']}")
            i = j
        print(f"\n   📚 Total de disciplinas: {len(dados)}")
    except Exception as e:
        print(f"❌ [LYCEUM] Erro ao extrair disciplinas v2: {e}")
        import traceback
        traceback.print_exc()
    return dados

def sincronizar_dados_lyceum_v2(user_id, matricula, cpf, forcar_atualizacao=False):
    print(f"\n{'=' * 80}")
    print("🚀 LYCEUM SCRAPER V2")
    print(f"{'=' * 80}")
    print(f"User ID: {user_id}")
    print(f"Forçar: {forcar_atualizacao}")
    print(f"{'=' * 80}\n")
    driver = None
    try:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920x1080")
        chrome_options.add_argument("--log-level=3")
        from typing import Any
        service: Any = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(120)
        driver.implicitly_wait(20)
        wait = WebDriverWait(driver, 30)
        tentativas = 3
        ok = False
        for t in range(tentativas):
            ok = login_lyceum(driver, matricula, cpf)
            if ok:
                break
            time.sleep(5)
            try:
                driver.get("https://portal.unievangelica.edu.br/aluno/#/login")
                time.sleep(3)
            except Exception:
                pass
        if not ok:
            print("❌ Login Lyceum falhou")
            return
        disciplinas = extrair_disciplinas_v2(driver)
        notas = extrair_notas(driver)
        faltas = extrair_frequencia(driver)
        horarios = extrair_horarios(driver)
        calendario = extrair_calendario(driver, horarios)
        salvar_dados_lyceum(user_id, notas, faltas, horarios, disciplinas, calendario)
        print("✅ LYCEUM V2 concluído")
    except Exception as e:
        print(f"❌ Erro V2: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()
