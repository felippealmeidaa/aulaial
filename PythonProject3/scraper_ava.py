import sqlite3
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
import os
import time
import re
from dotenv import load_dotenv
import io
from datetime import datetime

# ============================================
# BIBLIOTECAS DE PDF
# ============================================
try:
    import PyPDF2

    PDF_LIBRARY = 'pypdf2'
except ImportError:
    try:
        import pdfplumber

        PDF_LIBRARY = 'pdfplumber'
    except ImportError:
        PDF_LIBRARY = None

# ============================================
# CONFIGURAÇÕES
# ============================================
load_dotenv()
DATABASE = os.getenv('DATABASE', 'unievangelica.db')


def get_db_connection_scraper():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================
# GARANTIR ESQUEMA (MIGRAÇÃO LEVE)
# ============================================
def garantir_esquema_conteudos_ava():
    try:
        with get_db_connection_scraper() as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS conteudos_ava (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    disciplina TEXT NOT NULL,
                    conteudo_texto TEXT,
                    ultima_atualizacao TEXT,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
                )
            ''')

            c.execute("PRAGMA table_info(conteudos_ava)")
            cols = {row[1] for row in c.fetchall()}
            if 'ultima_atualizacao' not in cols:
                c.execute("ALTER TABLE conteudos_ava ADD COLUMN ultima_atualizacao TEXT")
            conn.commit()
    except Exception as e:
        print(f"❌ Erro ao garantir esquema conteudos_ava: {e}")


# ============================================
# 🆕 VERIFICAR SE USUÁRIO TEM CACHE
# ============================================
def usuario_tem_cache(user_id):
    """
    Verifica se usuário já tem dados salvos.
    NOTA: Não verifica expiração - cache é infinito!
    Usuário decide quando atualizar clicando no botão.
    """
    try:
        with get_db_connection_scraper() as conn:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM conteudos_ava WHERE usuario_id = ?', (user_id,))
            count = c.fetchone()[0]

            return count > 0

    except Exception as e:
        print(f"❌ Erro ao verificar cache: {e}")
        return False


# ============================================
# 🆕 OBTER ÚLTIMA SINCRONIZAÇÃO
# ============================================
def obter_ultima_sincronizacao(user_id):
    """
    Retorna data e hora da última sincronização do usuário.
    Retorna None se nunca sincronizou.
    """
    try:
        with get_db_connection_scraper() as conn:
            c = conn.cursor()
            c.execute("PRAGMA table_info(conteudos_ava)")
            cols = {row[1] for row in c.fetchall()}
            if 'ultima_atualizacao' not in cols:
                return None
            c.execute('''
                SELECT MAX(ultima_atualizacao) as ultima_sync
                FROM conteudos_ava 
                WHERE usuario_id = ?
            ''', (user_id,))
            row = c.fetchone()
            if row and row['ultima_sync']:
                return datetime.fromisoformat(row['ultima_sync'])
            return None
    except Exception as e:
        print(f"❌ Erro ao obter última sync: {e}")
        return None


# ============================================
# FUNÇÕES DE LIMPEZA
# ============================================
def limpar_texto(texto):
    if not texto: return ""
    texto = re.sub(r'[ \t]+', ' ', texto)
    return re.sub(r'\n\s*\n', '\n', texto.strip())


# ============================================
# EXTRAÇÃO DE PDF
# ============================================
def extrair_texto_pdf(pdf_url, session):
    if not PDF_LIBRARY:
        return "[PDF] PyPDF2 não instalado"

    try:
        response = session.get(pdf_url, timeout=30)
        if response.status_code != 200:
            return "[PDF] Erro ao baixar"

        pdf_bytes = io.BytesIO(response.content)
        texto = ""

        if PDF_LIBRARY == 'pypdf2':
            reader = PyPDF2.PdfReader(pdf_bytes)
            num_pages = min(len(reader.pages), 30)

            for i in range(num_pages):
                page_text = reader.pages[i].extract_text()
                if page_text:
                    texto += page_text + "\n"

        if texto:
            return limpar_texto(texto)[:3000]
        return "[PDF] Texto não extraído"

    except Exception as e:
        return f"[PDF] Erro: {str(e)[:100]}"


# ============================================
# EXTRAÇÃO ULTRA PROFUNDA DE ATIVIDADE
# ============================================
def extrair_atividade_ultra_profunda(link, nome, session):
    """Entra na atividade e extrai ABSOLUTAMENTE TUDO"""
    resultado = {
        'nome': nome,
        'tipo': 'Desconhecido',
        'texto': '',
        'videos': [],
        'pdfs': [],
        'links': []
    }

    try:
        if "page/view" in link:
            resultado['tipo'] = 'Página'
        elif "url/view" in link:
            resultado['tipo'] = 'Link Externo'
        elif "resource/view" in link:
            resultado['tipo'] = 'Arquivo'
        elif "assign/view" in link:
            resultado['tipo'] = 'Tarefa'
        elif "folder/view" in link:
            resultado['tipo'] = 'Pasta'

        r = session.get(link, timeout=20)
        soup = BeautifulSoup(r.content, 'html.parser')

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.extract()

        area_conteudo = soup.find("div", role="main")
        if not area_conteudo:
            area_conteudo = soup.find("div", class_=re.compile(r"(content|activity|generalbox)"))

        if area_conteudo:
            texto = limpar_texto(area_conteudo.get_text())
            if len(texto) > 30:
                resultado['texto'] = texto[:2000]

        iframes = soup.find_all("iframe")
        for iframe in iframes:
            src = iframe.get("src", "")
            if any(p in src for p in ["youtube", "youtu.be", "vimeo"]):
                resultado['videos'].append(src)

        if area_conteudo:
            links = area_conteudo.find_all("a", href=True)

            for link_elem in links:
                href = link_elem['href']
                texto_link = link_elem.get_text(strip=True)

                if any(p in href for p in ["youtube.com/watch", "youtu.be/"]):
                    resultado['videos'].append({'titulo': texto_link, 'url': href})

                elif ".pdf" in href.lower() or "pluginfile.php" in href:
                    pdf_info = {'titulo': texto_link, 'url': href}

                    if PDF_LIBRARY:
                        texto_pdf = extrair_texto_pdf(href, session)
                        pdf_info['texto'] = texto_pdf

                    resultado['pdfs'].append(pdf_info)

                elif href.startswith("http") and "unievangelica" not in href:
                    resultado['links'].append({'titulo': texto_link, 'url': href})

        return resultado

    except Exception as e:
        resultado['texto'] = f"[Erro: {str(e)[:50]}]"
        return resultado


# ============================================
# EXPANDIR E EXTRAIR SEÇÃO COMPLETA
# ============================================
def expandir_e_extrair_secao(secao_soup, nome_semana, session):
    """Expande seção e extrai TODO o conteúdo"""

    titulo_secao = secao_soup.find("h3", class_="sectionname")
    if not titulo_secao:
        titulo_secao = secao_soup.find("span", class_="sectionname")

    nome_secao = titulo_secao.get_text(strip=True) if titulo_secao else "Seção"

    print(f"\n      📂 {nome_secao}")

    resultado_secao = {
        'semana': nome_semana,
        'nome': nome_secao,
        'atividades': []
    }

    classes = secao_soup.get('class', [])
    esta_colapsada = 'section-summary' in classes

    if esta_colapsada:
        print(f"         🔐 Colapsada - expandindo...")
        section_id = secao_soup.get('data-id')

        if section_id:
            try:
                url_secao = f"https://avagrad.unievangelica.edu.br/course/section.php?id={section_id}"
                r = session.get(url_secao, timeout=10)
                soup_expandido = BeautifulSoup(r.content, 'html.parser')

                secao_soup = soup_expandido.find("div", role="main")
                if not secao_soup:
                    secao_soup = soup_expandido

                print(f"         ✅ Expandida")
            except Exception as e:
                print(f"         ❌ Erro: {str(e)[:30]}")
                return resultado_secao

    atividades = secao_soup.find_all("li", class_=re.compile(r"activity"))

    if not atividades:
        links_mod = secao_soup.find_all("a", href=re.compile(r"/mod/"))
        atividades = [l.parent for l in links_mod if l.parent]

    if not atividades:
        print(f"         ⚠️ Nenhuma atividade")
        return resultado_secao

    print(f"         ✅ {len(atividades)} atividades")

    links_vistos = set()

    for atividade in atividades[:30]:
        try:
            link_tag = atividade.find("a", href=True)
            if not link_tag:
                continue

            href = link_tag['href']

            if href in links_vistos:
                continue

            if any(x in href for x in ["section.php", "delete", "calendar"]):
                continue

            links_vistos.add(href)

            nome_ativ = link_tag.get_text(strip=True) or "Atividade"

            print(f"         [{len(links_vistos)}] {nome_ativ[:40]}...")

            dados_atividade = extrair_atividade_ultra_profunda(href, nome_ativ, session)
            resultado_secao['atividades'].append(dados_atividade)

            time.sleep(0.3)

        except Exception as e:
            continue

    return resultado_secao


# ============================================
# FORMATAR CONTEÚDO COM HIERARQUIA
# ============================================
def formatar_conteudo_estruturado(dados_disciplina):
    """Formata dados em texto legível com hierarquia"""

    texto = f"\n{'=' * 80}\n"
    texto += f"📚 {dados_disciplina['nome']}\n"
    texto += f"{'=' * 80}\n\n"

    semanas = {}
    for secao in dados_disciplina['secoes']:
        semana = secao['semana']
        if semana not in semanas:
            semanas[semana] = []
        semanas[semana].append(secao)

    for semana in sorted(semanas.keys()):
        texto += f"\n{'─' * 80}\n"
        texto += f"📅 {semana.upper()}\n"
        texto += f"{'─' * 80}\n"

        secoes_semana = semanas[semana]

        for secao in secoes_semana:
            texto += f"\n📂 {secao['nome']}\n"

            if not secao['atividades']:
                texto += "   ⚠️ Sem atividades\n"
                continue

            for idx, ativ in enumerate(secao['atividades'], 1):
                texto += f"\n   [{idx}] {ativ['tipo'].upper()}: {ativ['nome']}\n"

                if ativ['texto']:
                    texto += f"   📝 {ativ['texto'][:500]}\n"

                for video in ativ['videos']:
                    if isinstance(video, dict):
                        texto += f"   🎬 {video.get('titulo', 'Vídeo')}: {video.get('url', '')}\n"
                    else:
                        texto += f"   🎬 Vídeo: {video}\n"

                for pdf in ativ['pdfs']:
                    texto += f"   📄 PDF: {pdf.get('titulo', 'Documento')}\n"
                    if 'texto' in pdf and pdf['texto']:
                        texto += f"      {pdf['texto'][:300]}...\n"

                for link in ativ['links']:
                    texto += f"   🔗 {link.get('titulo', 'Link')}: {link.get('url', '')}\n"

    return texto


# ============================================
# COLETAR DISCIPLINAS (ANTI-STALE)
# ============================================
def coletar_disciplinas_selenium(driver):
    print("📋 Coletando disciplinas...")
    cursos = []

    try:
        time.sleep(3)
        elems = driver.find_elements(By.XPATH, "//a[contains(@href, 'course/view.php?id=')]")

        for idx, elem in enumerate(elems):
            try:
                url = elem.get_attribute('href')
                nome = elem.text or elem.get_attribute('aria-label') or ""
                nome = nome.split("\n")[0].strip()

                if url and "id=" in url and len(nome) > 4:
                    if "Biblioteca" not in nome and "Apoio" not in nome:
                        cursos.append({'nome': nome, 'url': url})

            except StaleElementReferenceException:
                continue
            except:
                continue

        urls_vistas = set()
        cursos_unicos = []
        for curso in cursos:
            if curso['url'] not in urls_vistas:
                urls_vistas.add(curso['url'])
                cursos_unicos.append(curso)

        print(f"✅ {len(cursos_unicos)} disciplinas coletadas")
        return cursos_unicos

    except Exception as e:
        print(f"❌ Erro: {e}")
        return []


# ============================================
# 🆕 SINCRONIZAÇÃO V5.1 - CACHE INFINITO
# ============================================
def sincronizar_dados_ava(user_id, matricula, cpf, forcar_atualizacao=False):
    """
    Sincroniza dados do AVA.

    CACHE INFINITO: Só faz scraping se:
    - Usuário não tem dados OU
    - forcar_atualizacao=True (botão clicado)
    """

    print(f"\n{'=' * 80}")
    print(f"🚀 SCRAPER V5.1 - CACHE INFINITO")
    print(f"{'=' * 80}")
    print(f"User ID: {user_id}")
    print(f"PDF: {PDF_LIBRARY or 'Não instalado'}")
    print(f"Forçar: {forcar_atualizacao}")
    print(f"{'=' * 80}\n")

    # 🆕 GARANTIR ESQUEMA
    garantir_esquema_conteudos_ava()

    # 🆕 VERIFICAR CACHE (SEM EXPIRAÇÃO)
    if not forcar_atualizacao:
        if usuario_tem_cache(user_id):
            ultima = obter_ultima_sincronizacao(user_id)
            if ultima:
                print(f"✅ CACHE ENCONTRADO")
                print(f"   Última sync: {ultima.strftime('%d/%m/%Y às %H:%M')}")
                print(f"   Usando dados salvos (cache infinito)")
                print(f"   Para atualizar: clique no botão 'Sincronizar'\n")
                return
            else:
                print("⚠️ Dados existem mas sem timestamp")
                print("   Fazendo novo scraping...\n")

    print("⚡ Iniciando scraping completo...\n")

    # CHROME CONFIG
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--log-level=3")
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    driver = None
    cursos = []

    # FASE 1: SELENIUM
    try:
        print("🔐 [FASE 1] Autenticando...")
        from typing import Any
        selenium_service: Any = Service(ChromeDriverManager().install())
        chrome_opts: Any = chrome_options
        driver = webdriver.Chrome(service=selenium_service, options=chrome_opts)
        driver.set_page_load_timeout(90)
        driver.implicitly_wait(15)
        wait = WebDriverWait(driver, 40)

        driver.get("https://avagrad.unievangelica.edu.br/login/index.php")
        digits = ''.join(filter(str.isdigit, str(cpf or '')))
        cpf_nove = digits[:9]

        def tentar_login(passwd: str) -> bool:
            try:
                wait.until(EC.presence_of_element_located((By.NAME, "username")))
                user_elem = driver.find_element(By.NAME, "username")
                pass_elem = driver.find_element(By.NAME, "password")
                login_btn = driver.find_element(By.ID, "loginbtn")
                user_elem.clear(); pass_elem.clear()
                user_elem.send_keys(matricula)
                pass_elem.send_keys(passwd)
                try:
                    login_btn.click()
                except Exception:
                    pass_elem.send_keys(Keys.ENTER)
                time.sleep(3)
                # Ir direto à página de cursos e validar
                try:
                    driver.get("https://avagrad.unievangelica.edu.br/my/courses.php")
                    time.sleep(8)
                except Exception:
                    pass
                links = driver.find_elements(By.XPATH, "//a[contains(@href, 'course/view.php?id=')]")
                if links and len(links) > 0:
                    return True
                # Detectar mensagens de erro de login
                try:
                    err = driver.find_elements(By.CSS_SELECTOR, "#loginerrormessage, .alert-danger, .loginerrors")
                    if err:
                        return False
                except Exception:
                    pass
                # Se não há links mas também sem erro claro, considerar falha
                return False
            except Exception:
                return False

        ok = tentar_login(cpf_nove)
        if not ok:
            raise Exception("Falha ao autenticar no AVA com CPF (9 dígitos)")

        # Ir para página de cursos
        if "my" not in driver.current_url:
            driver.get("https://avagrad.unievangelica.edu.br/my/courses.php")
            time.sleep(8)

        cursos = coletar_disciplinas_selenium(driver)
        if not cursos:
            # Como fallback, tenta página principal do usuário
            try:
                driver.get("https://avagrad.unievangelica.edu.br/my")
                time.sleep(8)
                cursos = coletar_disciplinas_selenium(driver)
            except Exception:
                pass
        cookies = driver.get_cookies()
        driver.quit()

    except Exception as e:
        print(f"❌ Erro Selenium: {e}")
        if driver: driver.quit()
        return

    if not cursos:
        print("⚠️ Nenhuma disciplina")
        return

    # FASE 2: EXTRAÇÃO ULTRA PROFUNDA
    print(f"\n{'=' * 80}")
    print("⚡ [FASE 2] Extração Ultra Profunda...")
    print(f"{'=' * 80}\n")

    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})
    for c in cookies:
        session.cookies.set(c['name'], c['value'])

    todas_disciplinas = []

    for i, curso in enumerate(cursos):
        print(f"\n📚 [{i + 1}/{len(cursos)}] {curso['nome']}")

        try:
            r = session.get(curso['url'], timeout=30)
            soup = BeautifulSoup(r.content, 'html.parser')

            dados_disciplina = {
                'nome': curso['nome'],
                'secoes': []
            }

            secoes = soup.find_all("li", class_=re.compile(r"section.*course-section"))

            if not secoes:
                print("   ⚠️ Sem seções")
                continue

            print(f"   ✅ {len(secoes)} seções encontradas")

            for secao in secoes:
                if "hidden" in secao.get("class", []):
                    continue

                titulo = secao.find("h3", class_="sectionname") or secao.find("span", class_="sectionname")
                nome_completo = titulo.get_text(strip=True) if titulo else "Seção"

                semana_match = re.search(r'(Fase \d+\s*-\s*)?Semana \d+', nome_completo, re.IGNORECASE)
                nome_semana = semana_match.group(0) if semana_match else nome_completo

                dados_secao = expandir_e_extrair_secao(secao, nome_semana, session)
                dados_disciplina['secoes'].append(dados_secao)

            todas_disciplinas.append(dados_disciplina)

        except Exception as e:
            print(f"   ❌ Erro: {str(e)[:100]}")

    # FASE 3: SALVAR COM TIMESTAMP
    print(f"\n{'=' * 80}")
    print("💾 [FASE 3] Salvando com timestamp...")
    print(f"{'=' * 80}\n")

    if todas_disciplinas:
        try:
            with get_db_connection_scraper() as conn:
                conn.execute('DELETE FROM conteudos_ava WHERE usuario_id = ?', (user_id,))

                timestamp = datetime.now().isoformat()

                for disc in todas_disciplinas:
                    texto_formatado = formatar_conteudo_estruturado(disc)
                    tamanho_kb = len(texto_formatado) / 1024

                    print(f"   💾 {disc['nome']}: {tamanho_kb:.1f} KB")

                    conn.execute('''
                        INSERT INTO conteudos_ava 
                        (usuario_id, disciplina, conteudo_texto, ultima_atualizacao) 
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, disc['nome'], texto_formatado, timestamp))

                conn.commit()

            print(f"\n{'=' * 80}")
            print(f"✅ SUCESSO!")
            print(f"   • {len(todas_disciplinas)} disciplinas")
            print(f"   • Sincronizado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}")
            print(f"   • Cache: INFINITO (até próximo clique)")
            print(f"{'=' * 80}\n")

        except Exception as e:
            print(f"❌ Erro ao salvar: {e}")


if __name__ == "__main__":
    print("Scraper V5.1 - Cache Infinito com Sincronização Manual")
