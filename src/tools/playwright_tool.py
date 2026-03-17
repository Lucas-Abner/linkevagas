from playwright.sync_api import sync_playwright
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
import json
import time
import os
from pathlib import Path

def sessao_esta_valida() -> bool:
    """Verifica se o arquivo de sessão existe e se o cookie li_at não expirou."""
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
                return True
        
        print("❌ Cookie li_at não encontrado.")
        return False
    
    except (FileNotFoundError, json.JSONDecodeError):
        print("❌ Arquivo de sessão não encontrado ou corrompido.")
        return False

def gerar_sessao_linkedin():
    """Abre o browser para o usuário fazer login e salva a sessão."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://www.linkedin.com/login")
        print("⏳ Faça login no LinkedIn e pressione 'Resume' no Playwright Inspector...")
        page.pause()

        context.storage_state(path="linkedin_session.json")
        print("✅ Sessão do LinkedIn salva com sucesso!")
        browser.close()

def buscar_multiplas_vagas(termo_pesquisa: str, quantidade_vagas=1):
    """
    Ferramenta para a IA buscar múltiplas vagas no LinkedIn com base em um termo de pesquisa, utilizando a sessão autenticada previamente salva. A IA deve ser capaz de extrair o título, descrição e URL de cada vaga encontrada, garantindo que as informações sejam relevantes e atualizadas.

        1. A IA deve navegar até a página de busca de vagas do LinkedIn utilizando o termo de pesquisa fornecido.
        2. Extrair o título, descrição e URL das vagas listadas na página de resultados.
        3. Armazenar as informações extraídas em uma estrutura organizada (ex: lista de dicionários).
        4. Retornar as informações das vagas encontradas para uso posterior no processo de otimização e candidatura.

        Observação: A IA deve ser capaz de lidar com variações na estrutura das páginas de resultados do LinkedIn, garantindo que a extração das informações seja realizada de forma robusta e eficiente.
    """

    # Verifica sessão ANTES de abrir o browser
    if not sessao_esta_valida():
        print("⚠️  Sessão inválida. Iniciando autenticação...")
        gerar_sessao_linkedin()

    caixa_vagas = []
    quantidade_vagas = int(quantidade_vagas) if isinstance(quantidade_vagas, str) and quantidade_vagas.isdigit() else 5

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="linkedin_session.json")
        page = context.new_page()

        termo_pesquisa = termo_pesquisa.replace(" ", "%20")
        url_busca = f"https://www.linkedin.com/jobs/search/?currentJobId=4382594108&f_AL=true&geoId=106057199&keywords={termo_pesquisa}"

        print(f"Buscando vagas para o termo: {url_busca}")
        page.goto(url_busca)

        # Verifica se foi redirecionado para o login (sessão expirada)
        if "linkedin.com/login" in page.url or "linkedin.com/checkpoint" in page.url:
            browser.close()
            raise Exception("Sessão do LinkedIn expirada. Execute gerar_sessao_linkedin() para renovar.")

        # Tenta seletores alternativos (o LinkedIn muda a estrutura HTML com frequência)
        seletores = [
            ".scaffold-layout__list-item",
            "li[data-occludable-job-id]",
            ".jobs-search-results__list-item",
            ".job-card-container",
        ]
        seletor_ativo = None
        for seletor in seletores:
            try:
                page.wait_for_selector(seletor, timeout=10000)
                seletor_ativo = seletor
                print(f"Seletor encontrado: {seletor_ativo}")
                break
            except Exception:
                continue

        if not seletor_ativo:
            # Tira um screenshot para debug e encerra
            page.screenshot(path="debug_linkedin.png")
            browser.close()
            raise Exception("Nenhum seletor de vagas encontrado. Verifique 'debug_linkedin.png' para inspecionar a página.")

        page.wait_for_timeout(2000)

        total_vagas = page.locator(seletor_ativo).count()

        quantidade_encontradas = min(quantidade_vagas, total_vagas)

        print(f"Total da contagem: {quantidade_encontradas}")
        print(f"Encontradas {total_vagas} vagas. Extraindo as {quantidade_encontradas} primeiras...")

        indice_atual = 0

        while len(caixa_vagas) < quantidade_encontradas and indice_atual < total_vagas:

            page.wait_for_selector(seletor_ativo)
            page.wait_for_timeout(500)

            cards = page.locator(seletor_ativo)
            card = cards.nth(indice_atual)

            try:
                card.scroll_into_view_if_needed(timeout=5000)
            except Exception:
                # Se o elemento não estiver disponível, espera mais e tenta novamente
                page.wait_for_timeout(1000)
                cards = page.locator(seletor_ativo)
                card = cards.nth(indice_atual)
                card.scroll_into_view_if_needed(timeout=5000)

            card.click()
            page.wait_for_timeout(2000)

            try:
                page.wait_for_selector(".jobs-apply-button--top-card", timeout=5000)
            except Exception:
                print("Botão de candidatura não encontrado. Pular para proxima vaga.")
                indice_atual += 1
                continue

            url_vaga = page.url

            page.wait_for_timeout(2000)
            page.wait_for_selector("#job-details", timeout=10000)

            titulo_locator = page.locator(".job-details-jobs-unified-top-card__job-title")
            titulo = titulo_locator.inner_text() if titulo_locator.count() > 0 else "Titulo não encontrado"

            descricao_page = page.locator("#job-details")
            descricao = descricao_page.inner_text() if descricao_page.count() > 0 else "Descrição não encontrada"

            caixa_vagas.append({
                "titulo": titulo,
                "descricao": descricao,
                "url": url_vaga
            })

            print(f"Vaga {indice_atual+1} extraída: {titulo}\nURL: {url_vaga}\n{'-'*40}")

            indice_atual += 1

        browser.close()
    return caixa_vagas

def descobrir_e_preencher_todos_campos(modal, page):
    """
    Descobre TODOS os campos disponíveis no formulário (inputs, selects, 
    checkboxes, textareas) mesmo sem labels, e preenche com LLM.
    """
    respostas_mapeadas = {
        "python": "2",
        "rag": "1",
        "retrieval-augmented": "1",
        "langchain": "1",
        "fastapi": "1",
        "machine learning": "1",
        "deep learning": "1",
        "clt": "Yes",
        "aceita": "Yes",
        "accept": "Yes",
        "reside": "Yes",
        "llm": "1",
        "e-mail": "lucascaixeta02@gmail.com",
        "english": "1",
        "inglês": "1",
        "artificial intelligence": "1",
        "inteligência artificial": "1",
        "ia": "1",
        "agentes ia": "1",
        "disponibilidade para início": "Imediata",
        "linkedin": "https://www.linkedin.com/in/lucas-abner-caixeta-oliveira",
        "nome completo": "Lucas Abner Caixeta de Oliveira",
        "telefone": "11960136292"
    }

    page.wait_for_timeout(1000)
    campos_processados = set()

    # ═══════════════════════════════════════════════════════════════
    # 1️⃣ INPUTS DE TEXTO - com ou sem label
    # ═══════════════════════════════════════════════════════════════
    print("\n📝 Processando INPUTS DE TEXTO...")
    inputs = modal.locator("input.artdeco-text-input--input, input[type='text']")
    
    for i in range(inputs.count()):
        inp = inputs.nth(i)
        input_id = inp.get_attribute("id") or f"input_{i}"
        
        if input_id in campos_processados:
            continue
        campos_processados.add(input_id)

        # Tenta encontrar a pergunta de diferentes formas
        pergunta = extrair_texto_pergunta(modal, inp, input_id)
        
        if not pergunta:
            print(f"  ⏭️  Input {i} sem pergunta detectável. Pulando...")
            continue

        print(f"  Pergunta: {pergunta[:60]}...")

        # Tenta mapeamento pré-definido
        valor = None
        for chave, resposta in respostas_mapeadas.items():
            if chave in pergunta.lower():
                valor = resposta
                break

        # Se não encontrou, pede para LLM
        if not valor:
            valor = resposta_pergunta_llm(pergunta, respostas_mapeadas)
        
        inp.fill(valor)
        print(f"  ✅ Preenchido com: {valor}")

    # ═══════════════════════════════════════════════════════════════
    # 2️⃣ TEXTAREAS
    # ═══════════════════════════════════════════════════════════════
    print("\n📝 Processando TEXTAREAS...")
    textareas = modal.locator("textarea")
    
    for i in range(textareas.count()):
        ta = textareas.nth(i)
        ta_id = ta.get_attribute("id") or f"textarea_{i}"
        
        if ta_id in campos_processados:
            continue
        campos_processados.add(ta_id)

        pergunta = extrair_texto_pergunta(modal, ta, ta_id)
        
        if not pergunta:
            print(f"  ⏭️  Textarea {i} sem pergunta detectável. Pulando...")
            continue

        print(f"  Pergunta: {pergunta[:60]}...")

        valor = None
        for chave, resposta in respostas_mapeadas.items():
            if chave in pergunta.lower():
                valor = resposta
                break

        if not valor:
            valor = resposta_pergunta_llm(pergunta, respostas_mapeadas)
        
        ta.fill(valor)
        print(f"  ✅ Preenchido com: {valor[:50]}...")

    # ═══════════════════════════════════════════════════════════════
    # 3️⃣ DROPDOWNS/SELECTS
    # ═══════════════════════════════════════════════════════════════
    print("\n🔽 Processando DROPDOWNS...")
    selects = modal.locator("select")
    
    for i in range(selects.count()):
        sel = selects.nth(i)
        sel_id = sel.get_attribute("id") or f"select_{i}"
        
        if sel_id in campos_processados:
            continue
        campos_processados.add(sel_id)

        pergunta = extrair_texto_pergunta(modal, sel, sel_id)
        
        if not pergunta:
            print(f"  ⏭️  Select {i} sem pergunta detectável. Pulando...")
            continue

        print(f"  Pergunta: {pergunta[:60]}...")

        opcoes = sel.locator("option").all_inner_texts()
        opcoes = [op.strip() for op in opcoes if op.strip()]

        valor = None
        for chave, resposta in respostas_mapeadas.items():
            if chave in pergunta.lower():
                valor = resposta
                break

        if not valor:
            contexto = f"Pergunta: {pergunta}\nOpções: {opcoes}\nEscolha UMA opção exatamente como escrita."
            valor = resposta_pergunta_llm(contexto, respostas_mapeadas)

        # Encontra a opção que melhor combina
        opcao_selecionada = None
        for op in opcoes:
            if valor.lower() in op.lower() or op.lower() in valor.lower():
                opcao_selecionada = op
                break
        
        opcao_selecionada = opcao_selecionada or opcoes[0]
        sel.select_option(label=opcao_selecionada)
        print(f"  ✅ Selecionado: {opcao_selecionada}")

    # ═══════════════════════════════════════════════════════════════
    # 4️⃣ CHECKBOXES e RADIO BUTTONS
    # ═══════════════════════════════════════════════════════════════
    print("\n☑️  Processando CHECKBOXES/RADIO BUTTONS...")
    checkboxes = modal.locator("input[type='checkbox'], input[type='radio']")
    
    for i in range(checkboxes.count()):
        cb = checkboxes.nth(i)
        cb_id = cb.get_attribute("id") or f"checkbox_{i}"
        
        if cb_id in campos_processados:
            continue
        campos_processados.add(cb_id)

        pergunta = extrair_texto_pergunta(modal, cb, cb_id)
        
        if not pergunta:
            print(f"  ⏭️  Checkbox {i} sem pergunta detectável. Pulando...")
            continue

        print(f"  Pergunta: {pergunta[:60]}...")

        valor = None
        for chave, resposta in respostas_mapeadas.items():
            if chave in pergunta.lower():
                valor = resposta
                break

        if not valor:
            valor = resposta_pergunta_llm(pergunta, respostas_mapeadas)

        # Convert para boolean
        deve_marcar = valor.lower() in ["yes", "sim", "true", "1", "aceito"]
        
        if deve_marcar and not cb.is_checked():
            cb.check()
            print(f"  ✅ Marcado")
        elif not deve_marcar and cb.is_checked():
            cb.uncheck()
            print(f"  ✅ Desmarcado")

def extrair_texto_pergunta(modal, elemento, elemento_id: str) -> str:
    """
    Tenta extrair o texto da pergunta de várias formas:
    1. Label com 'for' attribute
    2. aria-label do elemento
    3. placeholder
    4. Title/tooltip
    5. Texto próximo visualmente
    """
    
    # Tenta label[for='id']
    label = modal.locator(f"label[for='{elemento_id}']")
    if label.count() > 0:
        texto = label.inner_text().strip()
        if texto:
            return texto
    
    # Tenta aria-label
    aria_label = elemento.get_attribute("aria-label")
    if aria_label:
        return aria_label.strip()
    
    # Tenta placeholder
    placeholder = elemento.get_attribute("placeholder")
    if placeholder:
        return placeholder.strip()
    
    # Tenta title/tooltip
    title = elemento.get_attribute("title")
    if title:
        return title.strip()
    
    # Tenta encontrar label genérico próximo
    parent = elemento.locator("..")
    labels_proximo = parent.locator("label")
    if labels_proximo.count() > 0:
        texto = labels_proximo.first.inner_text().strip()
        if texto:
            return texto
    
    return ""

# ═══════════════════════════════════════════════════════════════
# USAR ASSIM NA FUNÇÃO detectar_e_preencher_tela:
# ═══════════════════════════════════════════════════════════════
def detectar_e_preencher_tela_v2(modal, page, nome_cv: str) -> str:
    """Versão melhorada que usa a nova função"""
    page.wait_for_timeout(1000)

    # ... código anterior para nome, email, telefone, CV ...

    # ── Tela de perguntas adicionais (NOVO) ──
    inputs_adicionais = modal.locator("input, textarea, select")
    if inputs_adicionais.count() > 0:
        descobrir_e_preencher_todos_campos(modal, page)  # 👈 NOVA FUNÇÃO
        return "perguntas"

    return "desconhecida"

def resposta_pergunta_llm(label_text: str, respostas: dict) -> str:
    """
    Chama a LLM para obter uma resposta para uma pergunta adicional do Easy Apply, com base no texto do label.
    """

    chat = ChatOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", "GROQ_API_KEY_REMOVED"),
        base_url="https://api.groq.com/openai/v1",
        model="openai/gpt-oss-20b",
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Você é um assistente especializado em preencher formulários de candidatura do LinkedIn. Com base no texto da pergunta, forneça a resposta mais adequada e concisa possível. Use as seguintes dicas para interpretar as perguntas:\n\n- Se a pergunta mencionar habilidades técnicas (ex: Python, Machine Learning), responda com o nível de experiência (0-5) ou 'Yes' se for uma pergunta de checkbox.\n- Se a pergunta for sobre salário, forneça um valor realista baseado no mercado para um cargo de AI Engineer Jr no Brasil e SOMENTE números.\n- Se a pergunta for sobre disponibilidade ou localização, responda com informações reais (ex: 'Imediata', 'Campinas').\n- Se a pergunta for sobre aceitar termos ou residir em determinado local, responda com 'Yes' ou 'No' conforme apropriado.\nSe perguntar o genero, sempre responda masculino\n- Para perguntas que não se encaixem nas categorias acima, use seu conhecimento geral para inferir a resposta mais provável\nSe a mensagem for dropdown, responda apenas com a opção exata a ser selecionada, sem explicações ou texto adicional.\nREGRA DE OURO: Tudo que exige números, responda somente com números. Para perguntas de checkbox, responda apenas 'Yes' ou 'No'. Evite qualquer texto explicativo ou adicional. Responda apenas o valor a ser preenchido no formulário.\nPegue essa lista pré-existente de respostas: {respostas}\nUse essa lista para responder perguntas semelhantes, mas se a pergunta for diferente, use seu conhecimento para inferir a resposta correta. Seja conciso e direto ao ponto."),
        ("human", "{pergunta}")]
    )

    chain = prompt | chat

    resposta = chain.invoke({"pergunta": label_text, "respostas": respostas})


    return resposta.content if hasattr(resposta, "content") else str(resposta) 

def detectar_e_preencher_tela(modal, page, nome_cv: str) -> str:
    """
    Detecta o conteúdo da tela atual do Easy Apply e preenche os campos.
    Retorna o tipo de tela detectada.
    """
    page.wait_for_timeout(1000)

    # ── Tela de informações de contato (nome, email, localização) ──
    first_name = modal.get_by_label("First name")
    if first_name.count() > 0 and first_name.is_visible():
        first_name.fill("Lucas Abner")
        
        last_name = modal.get_by_label("Last name")
        if last_name.count() > 0 and last_name.is_visible():
            last_name.fill("Caixeta de Oliveira")

    email = modal.get_by_label("Email address")
    if email.count() > 0 and email.is_visible():
        try:
            email.select_option(value="lucascaixeta02@gmail.com")
        except Exception:
            pass  # Já preenchido ou campo de texto

    loc_input = modal.get_by_label("Location (city)")
    if loc_input.count() > 0 and loc_input.is_visible():
        loc_input.click()
        loc_input.fill("Campinas")
        page.wait_for_timeout(500)
        loc_input.press("ArrowDown")
        loc_input.press("Enter")


    # ── Tela de telefone ──
    telefone = modal.get_by_label("Phone number")
    if telefone.count() > 0 and telefone.is_visible():
        telefone.fill("11960136292")
        print("✅ Telefone preenchido")
        return "telefone"
        

    # ── Tela de upload de CV ──
    upload_input = modal.locator("input[type='file']")
    if upload_input.count() > 0:
        caminho_path = Path(__file__).parent.parent.parent / f"{nome_cv}"
        upload_input.set_input_files(str(caminho_path))
        print(f"✅ CV anexado: {caminho_path}")
        return "cv_upload"

    # ── Tela de perguntas adicionais ──
    inputs_adicionais = modal.locator("input.artdeco-text-input--input")
    selects_adicionais = modal.locator("select[data-test-text-entity-list-form-select]")
    if inputs_adicionais.count() > 0:
        descobrir_e_preencher_todos_campos(modal, page)
        return "perguntas"

    return "desconhecida"

def tool_envio_candidatura(url_vaga: str, nome_cv: str) -> str:
    """
    Ferramenta para a IA realizar o envio de candidatura diretamente pelo LinkedIn,
    utilizando a sessão autenticada previamente salva.
    """
    if not sessao_esta_valida():
        print("⚠️  Sessão inválida. Iniciando autenticação...")
        gerar_sessao_linkedin()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="linkedin_session.json")
        page = context.new_page()

        page.goto(url_vaga)
        page.wait_for_selector(".jobs-apply-button--top-card", timeout=15000)
        print("Botão de candidatura encontrado. Iniciando processo...")

        page.click(".jobs-apply-button--top-card")
        page.wait_for_selector(".jobs-easy-apply-modal", timeout=10000)
        print("Modal Easy Apply aberto!")

        MAX_TELAS = 10  # Limite de segurança para não entrar em loop infinito

        for tela_num in range(1, MAX_TELAS + 1):
            modal = page.locator(".jobs-easy-apply-modal")
            page.wait_for_timeout(1000)

            # ── Verifica se é a tela final (botão Enviar/Submit) ──
            botao_enviar = modal.locator("button[aria-label='Enviar candidatura']")
            botao_enviar_alt = modal.locator("button[aria-label='Submit application']")
            botao_enviar_data = modal.locator("button[data-easy-apply-submit-button]")

            for btn in [botao_enviar, botao_enviar_alt, botao_enviar_data]:
                if btn.count() > 0 and btn.is_visible():
                    btn.click()
                    print(f"✅ Candidatura enviada com sucesso na tela {tela_num}!")
                    page.wait_for_timeout(2000)
                    browser.close()
                    return f"Candidatura enviada para: {nome_cv.replace('.pdf', '').replace('_', ' ')}"

            # ── Detecta e preenche a tela atual ──
            tipo_tela = detectar_e_preencher_tela(modal, page, nome_cv)
            print(f"📄 Tela {tela_num}: {tipo_tela}")

            page.wait_for_timeout(500)

            # ── Tenta avançar: Revisar > Avançar > Enviar ──
            botao_revisar = modal.locator("button:has-text('Revisar'), button:has-text('Review')")
            botao_avancar = modal.locator("button[data-easy-apply-next-button]")

            if botao_revisar.count() > 0 and botao_revisar.is_visible():
                botao_revisar.click()
                print(f"  ➡️ Clicou em Revisar")
            elif botao_avancar.count() > 0 and botao_avancar.is_visible():
                botao_avancar.click()
                print(f"  ➡️ Avançou para próxima tela")
            else:
                print(f"  ⚠️ Nenhum botão de avanço encontrado na tela {tela_num}")
                page.screenshot(path=f"debug_tela_{tela_num}.png")
                # Tenta clicar em qualquer botão primário visível como fallback
                botao_generico = modal.locator("button.artdeco-button--primary")
                if botao_generico.count() > 0 and botao_generico.first.is_visible():
                    botao_generico.first.click()
                    print(f"  ➡️ Clicou no botão primário genérico")
                else:
                    break

            page.wait_for_timeout(1500)

        # Se saiu do loop sem enviar
        print("⚠️ Limite de telas atingido. Pausando para verificação manual.")
        browser.close()
        return "⚠️ Candidatura não foi enviada automaticamente. Verifique manualmente."

# if __name__ == "__main__":
#     # caixa = buscar_multiplas_vagas("Desenvolvedor Python", 1)
#     # print(caixa[0]["titulo"][:500].replace(" ", "_").lower())

#     # r = tool_envio_candidatura("https://www.linkedin.com/jobs/search/?currentJobId=4381833617&keywords=Desenvolvedor%20Python", "/home/lucas.abner/Documentos/code/linkevagas/Lucas_Abner_Caixeta_CV_AI_Engineer_Jr.pdf")

#     # print(r)

    # gerar_sessao_linkedin()
