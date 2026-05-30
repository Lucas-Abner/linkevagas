from playwright.sync_api import sync_playwright
import json
import time
import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    """Lê uma variável booleana do .env com suporte a valores comuns."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on", "sim"}


def _launch_browser(playwright):
    """Abre o Chromium respeitando a flag do .env."""
    return playwright.chromium.launch(headless=_env_bool("PLAYWRIGHT_HEADLESS", False))

# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÃO 1: Validar e Gerenciar Sessão
# ═══════════════════════════════════════════════════════════════════════════════

def _validate_session() -> bool:
    """
    Valida se a sessão do LinkedIn existe e é válida.
    Se inválida, oferece opção de fazer login novamente.
    """
    try:
        with open("linkedin_session.json", "r") as f:
            session = json.load(f)
        
        agora = time.time()
        for cookie in session.get("cookies", []):
            if cookie["name"] == "li_at":
                expires = cookie.get("expires", -1)
                if expires != -1 and expires < agora:
                    print("❌ Cookie li_at expirado.")
                    return False
                print("✅ Sessão válida!")
                return True
        
        print("❌ Cookie li_at não encontrado.")
        return False
    
    except (FileNotFoundError, json.JSONDecodeError):
        print("❌ Arquivo de sessão não encontrado ou corrompido.")
        return False


def _create_session(p=None):
    """Cria uma nova sessão do LinkedIn automaticamente ou manualmente."""
    if p is None:
        with sync_playwright() as playwright:
            return _create_session(playwright)
            
    browser = _launch_browser(p)
    context = browser.new_context()
    page = context.new_page()

    page.goto("https://www.linkedin.com/login")
    print("⏳ Fazendo login no LinkedIn...")
    
    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")

    if email and password:
        try:
            # O LinkedIn usa seletores diferentes dependendo de como a página de login é carregada
            # Para a página /login, costuma ser id="username" e id="password"
            # Para a homepage, costuma ser name="session_key" e name="session_password"
            
            # 1. Tenta preencher o email
            if page.locator("input#username").count() > 0:
                page.locator("input#username").fill(email)
            else:
                page.locator("input[name='session_key']").fill(email)
                
            # 2. Tenta preencher a senha
            if page.locator("input#password").count() > 0:
                page.locator("input#password").fill(password)
            else:
                page.locator("input[name='session_password']").fill(password)
                
            # 3. Clica no botão de submit
            page.locator("button[type='submit']").click()
            
            print("🔑 Login automático realizado com as credenciais do .env")
            page.wait_for_timeout(5000)
        except Exception as e:
            print(f"⚠️ Erro ao fazer login automático: {e}")
            print("ℹ️ Por favor, faça o login manualmente na janela do navegador que se abriu...")
            page.pause()
    else:
        print("ℹ️ Faça login manualmente no navegador que se abriu...")
        page.pause()

    context.storage_state(path="linkedin_session.json")
    print("✅ Sessão do LinkedIn salva com sucesso!")
    browser.close()

# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÃO 2: Buscar Múltiplas Vagas
# ═══════════════════════════════════════════════════════════════════════════════

def search_jobs(search_term: str, quantity: int = 5, regiao: str = None) -> list:
    """
    Busca múltiplas vagas no LinkedIn baseado em um termo de pesquisa.
    
    Args:
        search_term: Termo de busca (ex: "AI Engineer")
        quantity: Quantidade de vagas a extrair
        regiao: Região para filtrar as vagas
    Returns:
        Lista de vagas com título, descrição e URL
    """
    if not _validate_session():
        print("⚠️ Sessão inválida. Criando nova...")
        _create_session()

    jobs_list = []
    quantity = int(quantity) if isinstance(quantity, str) and quantity.isdigit() else 5

    with sync_playwright() as p:
        browser = _launch_browser(p)
        context = browser.new_context(storage_state="linkedin_session.json")
        page = context.new_page()

        import urllib.parse
        search_term_encoded = urllib.parse.quote(search_term)
        base_prefix = os.getenv('LINKEDIN_PREFIX', 'https://www.linkedin.com/jobs/search/?f_AL=true&keywords=')
        search_url = f"{base_prefix}{search_term_encoded}"

        local_busca = os.getenv("LOCAL_BUSCA", "")
        if local_busca:
            import re
            # Extrai apenas os números (ex: de "Brasil (106057199)" extrai "106057199")
            match = re.search(r'\d+', local_busca)
            if match:
                geo_id = match.group()
                search_url += f"&geoId={geo_id}"
            else:
                # Fallback caso o usuário digite texto livre
                local_encoded = urllib.parse.quote(local_busca)
                search_url += f"&location={local_encoded}"

        print(f"🔍 Buscando vagas: {search_term}")
        if local_busca:
            print(f"📍 Local: {local_busca}")
        page.goto(search_url)

        # ─────────────────────────────────────────────────────────────────
        # Verifica se o LinkedIn invalidou a sessão no servidor
        # ─────────────────────────────────────────────────────────────────
        page.wait_for_timeout(2000)
        is_logged_out = (
            "linkedin.com/login" in page.url or 
            page.locator("a:has-text('Entrar')").count() > 0 or
            page.locator("button:has-text('Continuar com o Google')").count() > 0 or
            page.locator("a[href*='login']").count() > 0
        )

        if is_logged_out:
            print("⚠️ O LinkedIn desconectou sua sessão! Recriando...")
            browser.close()
            if os.path.exists("linkedin_session.json"):
                os.remove("linkedin_session.json")
            
            # Tenta logar de novo
            _create_session(p)
            
            # Reabre a página de busca com a nova sessão
            browser = _launch_browser(p)
            context = browser.new_context(storage_state="linkedin_session.json")
            page = context.new_page()
            page.goto(search_url)
            page.wait_for_timeout(2000)

        # Detecta seletor de vagas
        selectors = [
            ".scaffold-layout__list-item",
            "li[data-occludable-job-id]",
            ".jobs-search-results__list-item",
            ".job-card-container",
        ]
        
        active_selector = None
        for selector in selectors:
            try:
                page.wait_for_selector(selector, timeout=5000)
                active_selector = selector
                break
            except:
                continue

        if not active_selector:
            page.screenshot(path="debug_linkedin.png")
            browser.close()
            raise Exception("Seletor de vagas não encontrado")

        page.wait_for_timeout(1500)
        total_jobs = page.locator(active_selector).count()
        quantity = min(quantity, total_jobs)

        print(f"Encontradas {total_jobs} vagas. Extraindo {quantity}...")

        for idx in range(quantity):
            try:
                cards = page.locator(active_selector)
                card = cards.nth(idx)
                # card.scroll_into_view_if_needed()
                card.click()
                page.wait_for_timeout(1500)

                apply_buttons_selectors = [
                    ".jobs-apply-button--top-card",
                    "button[aria-label*='Apply']",
                    "button[aria-label*='apply']",
                    "button:has-text('Easy Apply')",
                    ".jobs-apply-button",
                ]

                button_found = False

                for btn in apply_buttons_selectors:
                    if page.locator(btn).count() > 0:
                        button_found = True
                        break
                
                if not button_found:
                    print(f"⚠️ Botão de candidatura não encontrado para vaga {idx + 1}")
                    continue

                job_url = page.url
                
                title_elem = page.locator(".job-details-jobs-unified-top-card__job-title")
                title = title_elem.inner_text() if title_elem.count() > 0 else "N/A"

                desc_elem = page.locator("#job-details")
                description = desc_elem.inner_text() if desc_elem.count() > 0 else ""

                # Extrai metadados adicionais da vaga
                company_elem = page.locator(".job-details-jobs-unified-top-card__company-name")
                company = company_elem.inner_text().strip() if company_elem.count() > 0 else "N/A"

                location_elem = page.locator(".job-details-jobs-unified-top-card__bullet")
                location = location_elem.first.inner_text().strip() if location_elem.count() > 0 else "N/A"

                jobs_list.append({
                    "title": title,
                    "description": description,  # SEM TRUNCAMENTO — texto completo da vaga
                    "company": company,
                    "location": location,
                    "url": job_url
                })

                print(f"✅ Vaga {idx + 1}: {title}")
                print(f"   URL: {job_url}")
                print("="*60)
            except Exception as e:
                print(f"⚠️ Erro ao extrair vaga {idx + 1}: {str(e)[:50]}")
                continue

        browser.close()

    return jobs_list


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÃO 3: Aplicar para Vaga com LLM Respondendo Tudo
# ═══════════════════════════════════════════════════════════════════════════════

def _get_llm_response(question: str) -> str:
    """
    Chama a LLM para obter resposta para qualquer pergunta do formulário.
    A LLM responde basicamente tudo exceto o CV.
    """
    modelo_principal_id = os.getenv("MODELO_PRINCIPAL", "gpt-4o-mini")
    
    if "gpt" in modelo_principal_id.lower() or "o1" in modelo_principal_id.lower() or "o3" in modelo_principal_id.lower():
        from agno.models.openai import OpenAIResponses
        model = OpenAIResponses(id=modelo_principal_id, api_key=os.getenv("OPENAI_API_KEY"))
    elif "deepseek" in modelo_principal_id.lower():
        from agno.models.deepseek import DeepSeek
        model = DeepSeek(id=modelo_principal_id, api_key=os.getenv("DEEPSEEK_API_KEY"))
    else:
        from agno.models.ollama import Ollama
        model = Ollama(id=modelo_principal_id, host="http://localhost:11434", options={"temperature": 0.7})
        
    from agno.agent import Agent
    
    system_prompt = """Você é um assistente especializado em preencher formulários de candidatura do LinkedIn para uma posição de AI Engineer Jr.

REGRAS IMPORTANTES:
- Responda APENAS o valor a ser preenchido, sem explicações ou texto adicional
- Para checkboxes: responda apenas 'Yes' ou 'No'
- Para números (salário, experiência): responda SOMENTE números
- Para dropdowns: responda EXATAMENTE com uma opção disponível
- Para campos de texto: responda de forma concisa e profissional

CONTEXTO DO CANDIDATO:
- Nome: Lucas Abner Caixeta de Oliveira
- Email: lucascaixeta02@gmail.com
- Telefone: 11960136292
- Localização: Campinas, SP
- Experiência: IA, Python, Machine Learning, LLMs, Fast API, Agentes IA
- Disponibilidade: Imediata
- Gênero: Masculino
- Salário pretendido: 4000
- CPF: 45829395894
- Location: Campinas

PROCESSO DE RESPOSTA:
1. Leia a pergunta cuidadosamente
2. Identifique o tipo de resposta esperada (texto, número, sim/não, opção)
3. Responda apropriadamente baseado no contexto do candidato
4. SEMPRE responda positivamente as questões, leia as perguntas atentamente e responda de forma otimista, destacando as habilidades do candidato
4. Sempre responda positivamente a perguntas sobre: LLMs, IA, automação, Python, disponibilidade imediata, termos e condições, relocation
5. Se não souber, use o melhor palpite baseado no perfil do candidato"""

    agent = Agent(
        model=model,
        instructions=system_prompt,
    )
    
    response = agent.run(question)
    return response.content.strip() if response and response.content else ""


def _extract_field_question(modal, element, element_id: str) -> str:
    """
    Extrai o texto da pergunta REAL associado ao campo buscando o <label>.
    """
    # Estratégia 1: Procurar por <label for="element_id">
    if element_id:
        try:
            label = modal.locator(f"label[for='{element_id}']")
            if label.count() > 0:
                text = label.inner_text().strip()
                if text and len(text) > 2:
                    return text
        except:
            pass
    
    # Estratégia 2: aria-label (geralmente tem a pergunta)
    aria_label = element.get_attribute("aria-label")
    if aria_label and aria_label.strip() and len(aria_label) > 2:
        return aria_label.strip()
    
    # Estratégia 3: placeholder
    placeholder = element.get_attribute("placeholder")
    if placeholder and placeholder.strip() and len(placeholder) > 2:
        return placeholder.strip()
    
    # Estratégia 4: Procurar no parent mais próximo por texto
    try:
        parent = element.locator("xpath=ancestor::div[1]")
        if parent.count() > 0:
            parent_text = parent.inner_text().strip()
            if parent_text and len(parent_text) > 10:
                first_line = parent_text.split('\n')[0].strip()
                if len(first_line) > 3:
                    return first_line
    except:
        pass
    
    # Fallback
    field_type = element.get_attribute("type") or element.get_attribute("name") or "campo"
    return f"Campo de {field_type}"


def _fill_form_fields(modal, page, cv_path: str) -> bool:
    """
    Descobre TODOS os campos do formulário ANTES de responder.
    Extrai a pergunta REAL (label) para cada campo.
    LLM responde com contexto claro.
    """
    page.wait_for_timeout(800)
    
    # ─────────────────────────────────────────────────────────────────
    # FASE 1: DESCOBRIR TODOS OS CAMPOS
    # ─────────────────────────────────────────────────────────────────
    
    fields_to_fill = []
    
    # 1️⃣ INPUTS DE TEXTO
    print("\n� Descobrindo campos de texto...")
    text_inputs = modal.locator("input[type='text'].artdeco-text-input--input")
    for i in range(text_inputs.count()):
        inp = text_inputs.nth(i)
        if not inp.is_visible():
            continue
        field_id = inp.get_attribute("id") or f"text_input_{i}"
        question = _extract_field_question(modal, inp, field_id)
        fields_to_fill.append({
            "type": "text",
            "element": inp,
            "id": field_id,
            "question": question
        })
        print(f"  ✓ {question[:50]}")
    
    # 2️⃣ TEXTAREAS
    print("\n� Descobrindo textareas...")
    textareas = modal.locator("textarea")
    for i in range(textareas.count()):
        ta = textareas.nth(i)
        if not ta.is_visible():
            continue
        field_id = ta.get_attribute("id") or f"textarea_{i}"
        question = _extract_field_question(modal, ta, field_id)
        fields_to_fill.append({
            "type": "textarea",
            "element": ta,
            "id": field_id,
            "question": question
        })
        print(f"  ✓ {question[:50]}")
    
    # 3️⃣ SELECTS/DROPDOWNS
    print("\n� Descobrindo dropdowns...")
    selects = modal.locator("select")
    for i in range(selects.count()):
        sel = selects.nth(i)
        if not sel.is_visible():
            continue
        field_id = sel.get_attribute("id") or f"select_{i}"
        question = _extract_field_question(modal, sel, field_id)
        options = sel.locator("option").all_inner_texts()
        options = [op.strip() for op in options if op.strip() and op.strip() != "Selecionar opção"]
        
        fields_to_fill.append({
            "type": "select",
            "element": sel,
            "id": field_id,
            "question": question,
            "options": options
        })
        print(f"  ✓ {question[:50]} ({len(options)} opções)")
    
    # 4️⃣ CHECKBOXES E RADIO BUTTONS
    print("\n🔍 Descobrindo checkboxes/radios...")
    checkboxes = modal.locator("input[type='checkbox'], input[type='radio']")
    for i in range(checkboxes.count()):
        cb = checkboxes.nth(i)
        if not cb.is_visible():
            continue
        field_id = cb.get_attribute("id") or f"checkbox_{i}"
        question = _extract_field_question(modal, cb, field_id)
        
        fields_to_fill.append({
            "type": "checkbox" if cb.get_attribute("type") == "checkbox" else "radio",
            "element": cb,
            "id": field_id,
            "question": question
        })
        print(f"  ✓ {question[:50]}")
    
    # ─────────────────────────────────────────────────────────────────
    # FASE 2: PREENCHER TODOS OS CAMPOS AGORA
    # ─────────────────────────────────────────────────────────────────
    
    print(f"\n📝 Preenchendo {len(fields_to_fill)} campos...\n")
    
    for field in fields_to_fill:
        try:
            question = field["question"]
            elem = field["element"]
            
            print(f"❓ {question}")
            
            # Chama LLM com contexto claro
            if field["type"] == "select":
                # Para dropdowns, informar as opções
                options_text = f"\nOpções: {field['options']}"
                answer = _get_llm_response(question + options_text)
                
                # Encontra opção que corresponde
                answer_lower = answer.strip().lower()
                selected = None
                for opt in field["options"]:
                    if answer_lower in opt.lower() or opt.lower() in answer_lower:
                        selected = opt
                        break
                selected = selected or field["options"][0]
                
                elem.select_option(label=selected)
                print(f"✅ Selecionado: {selected}\n")
            
            elif field["type"] in ["checkbox", "radio"]:
                # Para checkbox/radio
                answer = _get_llm_response(question)
                should_mark = answer.strip().lower() in ["yes", "sim", "true", "1", "aceito", "sim, aceito", "aplicar", "select this"]
                
                is_marked = False
                try:
                    is_marked = elem.is_checked()
                except:
                    pass
                
                if should_mark != is_marked:
                    # Tenta clicar na label associada
                    label = modal.locator(f"label[for='{field['id']}']")
                    if label.count() > 0:
                        label.click(timeout=3000)
                    else:
                        elem.click(force=True, timeout=3000)
                
                print(f"✅ {'Marcado' if should_mark else 'Desmarcado'}\n")
            
            else:
                # Para texto/textarea
                answer = _get_llm_response(question)
                if answer and answer.strip():
                    elem.fill(answer.strip())
                    print(f"✅ Preenchido: {answer[:50]}\n")
        
        except Exception as e:
            print(f"⚠️  Erro ao processar campo: {str(e)[:50]}\n")
    
    # ─────────────────────────────────────────────────────────────────
    # FASE 3: UPLOAD DE CV
    # ─────────────────────────────────────────────────────────────────
    
    print("\n📄 Processando upload de CV...")
    file_inputs = modal.locator("input[type='file']")
    
    if file_inputs.count() > 0:
        cv_full_path = str(Path(__file__).parent.parent.parent / cv_path)
        try:
            file_inputs.first.set_input_files(cv_full_path)
            print(f"✅ CV anexado: {cv_path}")
        except Exception as e:
            print(f"⚠️  Erro ao anexar CV: {str(e)[:40]}")
    
    return True


def apply_to_job(job_url: str, cv_filename: str) -> str:
    """
    Aplica automaticamente para uma vaga no LinkedIn.
    Preenche TODOS os campos usando LLM para responder as perguntas.
    Apenas o CV é pré-definido (passado como parâmetro).
    
    Args:
        job_url: URL da vaga no LinkedIn
        cv_filename: Nome do arquivo CV na raiz do projeto (ex: "CV_Lucas.pdf")
        
    Returns:
        Mensagem de sucesso ou erro
    """
    if not _validate_session():
        print("⚠️ Sessão inválida. Criando nova...")
        _create_session()

    with sync_playwright() as p:
        browser = _launch_browser(p)
        context = browser.new_context(storage_state="linkedin_session.json")
        page = context.new_page()

        page.goto(job_url)
        
        try:
            page.wait_for_load_state("domcontentloaded", timeout=8000)
        except:
            pass
            
        page.wait_for_timeout(2000)
        is_logged_out = (
            "linkedin.com/login" in page.url or 
            page.locator("a:has-text('Entrar')").count() > 0 or
            page.locator("button:has-text('Continuar com o Google')").count() > 0 or
            page.locator("a[href*='login']").count() > 0
        )

        if is_logged_out:
            print("⚠️ O LinkedIn desconectou sua sessão! Recriando...")
            browser.close()
            if os.path.exists("linkedin_session.json"):
                os.remove("linkedin_session.json")
            
            _create_session(p)
            browser = _launch_browser(p)
            context = browser.new_context(storage_state="linkedin_session.json")
            page = context.new_page()
            page.goto(job_url)
            page.wait_for_timeout(2000)
        
        page.wait_for_timeout(1500)

        # ─────────────────────────────────────────────────────────────────
        # Encontra botão de candidatura
        # ─────────────────────────────────────────────────────────────────
        apply_buttons = [
            ".jobs-apply-button--top-card",
            "button[aria-label*='Apply']",
            "button[aria-label*='apply']",
            "button:has-text('Easy Apply')",
            ".jobs-apply-button",
        ]
        
        button_clicked = False
        for selector in apply_buttons:
            try:
                page.wait_for_selector(selector, timeout=3000)
                page.click(selector)
                button_clicked = True
                print("✅ Botão de candidatura clicado")
                break
            except:
                continue

        if not button_clicked:
            page.screenshot(path="debug_apply_button.png")
            browser.close()
            return "❌ Botão de candidatura não encontrado"

        # ─────────────────────────────────────────────────────────────────
        # Aguarda e processa o modal
        # ─────────────────────────────────────────────────────────────────
        try:
            page.wait_for_selector(".jobs-easy-apply-modal", timeout=8000)
        except:
            browser.close()
            return "❌ Modal Easy Apply não aberto"

        print("🎯 Modal aberto! Preenchendo formulário...")

        MAX_SCREENS = 15
        current_screen = 0

        try:
            while current_screen < MAX_SCREENS:
                current_screen += 1
                page.wait_for_timeout(800)

                modal = page.locator(".jobs-easy-apply-modal")
                if modal.count() == 0:
                    break

                # Verifica se é última tela (botão enviar)
                submit_buttons = [
                    modal.locator("button[aria-label*='Submit']"),
                    modal.locator("button[aria-label*='Enviar']"),
                    modal.locator("button[data-easy-apply-submit-button]"),
                ]

                for submit_btn in submit_buttons:
                    if submit_btn.count() > 0 and submit_btn.is_visible():
                        submit_btn.click()
                        print(f"✅ Candidatura enviada na tela {current_screen}!")
                        page.wait_for_timeout(2000)
                        browser.close()
                        return f"✅ Candidatura enviada com sucesso! (CV: {cv_filename})"

                # ─────────────────────────────────────────────────────────────────
                # Preenche os campos da tela atual
                # ─────────────────────────────────────────────────────────────────
                print(f"\n📋 Tela {current_screen}")
                _fill_form_fields(modal, page, cv_filename)

                page.wait_for_timeout(500)

                # ─────────────────────────────────────────────────────────────────
                # Avança para próxima tela
                # ─────────────────────────────────────────────────────────────────
                next_buttons = [
                    modal.locator("button:has-text('Review')"),
                    modal.locator("button:has-text('Revisar')"),
                    modal.locator("button[data-easy-apply-next-button]"),
                    modal.locator("button.artdeco-button--primary"),
                ]

                advanced = False
                for next_btn in next_buttons:
                    if next_btn.count() > 0 and next_btn.is_visible():
                        try:
                            next_btn.click()
                            print(f"  ➡️ Avançando...")
                            advanced = True
                            break
                        except:
                            continue

                if not advanced:
                    print(f"  ⚠️ Nenhum botão de avanço encontrado")
                    page.screenshot(path=f"debug_screen_{current_screen}.png")
                    break

                page.wait_for_timeout(1200)
            return "Candidatura realizada com sucesso."
            

        except Exception as e:
            print(f"❌ Erro: {str(e)[:60]}")

        browser.close()
        return "⚠️ Candidatura não foi enviada automaticamente. Verifique manualmente."


# ─────────────────────────────────────────────────────────────────────────────
# COMPATIBILIDADE COM NOMES ANTIGOS
# ─────────────────────────────────────────────────────────────────────────────

def sessao_esta_valida():
    """Alias para compatibilidade"""
    return _validate_session()

def gerar_sessao_linkedin():
    """Alias para compatibilidade"""
    return _create_session()

def buscar_multiplas_vagas(termo_pesquisa: str, quantidade_vagas=1):
    """Alias para compatibilidade"""
    return search_jobs(termo_pesquisa, quantidade_vagas)

def tool_envio_candidatura(url_vaga: str, nome_cv: str) -> str:
    """Alias para compatibilidade"""
    return apply_to_job(url_vaga, nome_cv)


if __name__ == "__main__":
    # Exemplos de uso:
    # _create_session()
    # jobs = search_jobs("AI Engineer", 5)
    # result = apply_to_job("https://www.linkedin.com/jobs/search/?currentJobId=4385479016&keywords=(IA)&origin=SUGGESTION", "C:\\Users\\lucas\\OneDrive\\Documentos\\coders\\linkevagas\\cv_desenvolvedor_de_agente_ia__remoto.pdf")
    pass
