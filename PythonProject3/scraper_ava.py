import sqlite3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import os
import time
import re
from dotenv import load_dotenv
from datetime import datetime, timedelta

# ============================================
# CONFIGURAÇÕES
# ============================================
load_dotenv()
DATABASE = os.getenv('DATABASE', 'unievangelica.db')


def get_db_connection_scraper():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def verificar_cache_recente(user_id, horas_validade=4):
    # Para testes, vamos ignorar cache e forçar sempre a busca
    # (Em produção você pode descomentar a lógica de data)
    return False


# ============================================
# EXTRAÇÃO
# ============================================
def extrair_conteudo_pagina(driver, wait):
    """Lê tudo que tem texto, video ou arquivo na página atual"""
    conteudo = ""
    materiais = []

    try:
        # Pega o texto visível total
        texto_body = driver.find_element(By.TAG_NAME, "body").text
        # Remove linhas em branco excessivas
        conteudo += re.sub(r'\n\s*\n', '\n', texto_body)[:20000]

        # Busca IFrames (Vídeos)
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            src = iframe.get_attribute("src")
            if src and "youtube" in src:
                materiais.append(f"🎬 [VÍDEO]: {src}")

        # Busca Links de Arquivos/Vídeos no texto
        links = driver.find_elements(By.XPATH, "//a[@href]")
        for link in links:
            h = link.get_attribute("href")
            t = link.text.strip() or "Link"
            if any(x in h for x in ['.pdf', '.pptx', 'forcedownload']):
                materiais.append(f"📎 [ARQUIVO]: {t} -> {h}")
            elif "youtu" in h:
                materiais.append(f"🎬 [VÍDEO]: {t} -> {h}")

    except Exception:
        pass

    if materiais:
        conteudo += "\n\n>>> LINKS DETECTADOS:\n" + "\n".join(list(set(materiais)))

    return conteudo


# ============================================
# LOGIN
# ============================================
def realizar_login(driver, wait, matricula, senha):
    try:
        print(f"🔐 [SCRAPER] Acessando login...")
        driver.get("https://avagrad.unievangelica.edu.br/login/index.php")

        wait.until(EC.presence_of_element_located((By.NAME, "username")))
        driver.find_element(By.NAME, "username").send_keys(matricula)
        driver.find_element(By.NAME, "password").send_keys(senha)
        driver.find_element(By.ID, "loginbtn").click()

        # Espera generosa para carregar dashboard
        time.sleep(5)

        if "login" not in driver.current_url:
            return True

        # Check secundário
        if len(driver.find_elements(By.CLASS_NAME, "userpicture")) > 0:
            return True

        print("❌ Falha login.")
        return False
    except Exception as e:
        print(f"❌ Erro login: {e}")
        return False


# ============================================
# SCRAPER "TRATOR" (Pega tudo)
# ============================================
def sincronizar_dados_ava(user_id, matricula, cpf, forcar_atualizacao=False):
    print("🚀 [SCRAPER] Iniciando modo Varredura Total...")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    # User Agent real para evitar bloqueios
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

    driver = None
    dados_finais = []

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        wait = WebDriverWait(driver, 15)

        # 1. Login
        cpf_limpo = ''.join(filter(str.isdigit, cpf))[:9]
        if not realizar_login(driver, wait, matricula, cpf_limpo):
            return

        # 2. Busca Cursos
        driver.get("https://avagrad.unievangelica.edu.br/my/courses.php")
        time.sleep(3)  # Espera JS renderizar

        links_cursos = driver.find_elements(By.XPATH, "//a[contains(@href, 'course/view.php?id=')]")
        lista_cursos = []
        vistos = set()

        for l in links_cursos:
            u = l.get_attribute("href")
            n = l.text.strip() or l.get_attribute("aria-label")
            if u and u not in vistos and "Biblioteca" not in n:
                lista_cursos.append({'nome': n, 'url': u})
                vistos.add(u)

        print(f"📚 {len(lista_cursos)} disciplinas para ler.")

        # 3. Loop Disciplinas
        for curso in lista_cursos:
            print(f"   📘 Entrando em: {curso['nome']}...")
            driver.get(curso['url'])
            time.sleep(3)  # Espera carregar abas/conteúdo

            # BUFFER GIGANTE DA DISCIPLINA
            texto_completo = f"--- DISCIPLINA: {curso['nome']} ---\n"

            # A) SALVA O TEXTO DA PÁGINA PRINCIPAL (Para pegar avisos e descrições soltas)
            texto_principal = extrair_conteudo_pagina(driver, wait)
            texto_completo += f"\n[VISÃO GERAL DA PÁGINA]\n{texto_principal}\n"

            # B) VARREDURA DE LINKS DE ATIVIDADE (Estratégia BRUTA)
            # Procura qualquer link que pareça uma atividade interna do moodle
            # Ignora fóruns, chats, deletar, etc.
            links_brutos = driver.find_elements(By.XPATH,
                                                "//a[contains(@href, '/mod/') or contains(@href, 'view.php?id=')]")

            atividades_para_ler = []
            urls_ativ_vistas = set()

            for lb in links_brutos:
                href = lb.get_attribute("href")
                txt = lb.text.strip()

                # Filtros de lixo
                if not href or href in urls_ativ_vistas: continue
                if any(x in href for x in ['forum', 'chat', 'delete', 'assign',
                                           'quiz']): continue  # Pula quiz/tarefa por enquanto pra ser rápido
                if "course/view" in href: continue  # Link para o próprio curso

                # Tenta adivinhar a "Semana" olhando para cima no HTML
                # Procura um elemento pai que tenha texto indicando semana
                try:
                    # XPath sobe até achar um container com texto "Semana" ou "Fase"
                    semana_pai = lb.find_element(By.XPATH,
                                                 "./ancestor::*[contains(text(), 'Semana') or contains(text(), 'Fase')][1]")
                    semana_label = semana_pai.text.split('\n')[0][:30]
                except:
                    semana_label = "Tópico Geral"

                atividades_para_ler.append({'url': href, 'nome': txt, 'secao': semana_label})
                urls_ativ_vistas.add(href)

            print(f"      ↳ {len(atividades_para_ler)} itens de conteúdo identificados.")

            # C) VISITA CADA ITEM
            for item in atividades_para_ler:
                try:
                    # Pula arquivos diretos (já salvou o link no passo A ou vai salvar agora)
                    if "resource" in item['url'] or "folder" in item['url']:
                        texto_completo += f"\n📍 {item['secao']} | 📎 ARQUIVO: {item['nome']} -> {item['url']}\n"
                        continue

                    # Entra na página (Page, URL, Book)
                    driver.get(item['url'])
                    # time.sleep(1) # Leve pausa

                    conteudo_interno = extrair_conteudo_pagina(driver, wait)

                    texto_completo += f"\n=================================================="
                    texto_completo += f"\n📍 TÓPICO/SEMANA: {item['secao']}"
                    texto_completo += f"\n📝 TÍTULO: {item['nome']}"
                    texto_completo += f"\n🔗 LINK: {item['url']}"
                    texto_completo += f"\n--------------------------------------------------"
                    texto_completo += f"\n{conteudo_interno}"
                    texto_completo += f"\n==================================================\n"

                except Exception:
                    driver.back()

            dados_finais.append({'disc': curso['nome'], 'txt': texto_completo})

        # 4. Salva tudo
        if dados_finais:
            with get_db_connection_scraper() as conn:
                conn.execute('DELETE FROM conteudos_ava WHERE usuario_id = ?', (user_id,))
                for d in dados_finais:
                    conn.execute(
                        'INSERT INTO conteudos_ava (usuario_id, disciplina, conteudo_texto, data_extracao) VALUES (?, ?, ?, CURRENT_TIMESTAMP)',
                        (user_id, d['disc'], d['txt']))
                conn.commit()
            print("✅ Dados salvos no banco!")
        else:
            print("⚠️ Nada salvo.")

    except Exception as e:
        print(f"🔥 Erro fatal: {e}")
        if driver: driver.save_screenshot("erro_fatal.png")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


if __name__ == "__main__":
    pass