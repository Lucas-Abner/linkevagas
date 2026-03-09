from playwright.sync_api import sync_playwright

def gerar_sessao_linkedin():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://www.linkedin.com/login")

        page.pause()

        context.storage_state(path="linkedin_session.json")
        browser.close()
        print("Sessão do LinkedIn salva com sucesso!")

def buscar_multiplas_vagas(termo_pesquisa, quantidade_vagas = 5):
    caixa_vagas = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="linkedin_session.json")
        page = context.new_page()


        termo_pesquisa =termo_pesquisa.replace(" ", "%20")
        url_busca = f"https://www.linkedin.com/jobs/search/?keywords={termo_pesquisa}"

        print(f"Buscando vagas para o termo: {url_busca}")
        page.goto(url_busca)

        page.wait_for_selector(".scaffold-layout__list-item")

        page.wait_for_timeout(2000)

        total_vagas = page.locator("li.scaffold-layout__list-item").count()

        quantidade_encontradas = min(quantidade_vagas, total_vagas)
        print(f"Encontradas {total_vagas} vagas. Extraindo as {quantidade_encontradas} primeiras...")

        for i in range(quantidade_encontradas):
            # Aguarda a lista recarregar e re-seleciona o card pelo índice a cada iteração
            page.wait_for_selector("li.scaffold-layout__list-item")
            page.wait_for_timeout(500)

            cards = page.locator("li.scaffold-layout__list-item")
            card = cards.nth(i)

            try:
                card.scroll_into_view_if_needed(timeout=5000)
            except Exception:
                # Se o elemento não estiver disponível, espera mais e tenta novamente
                page.wait_for_timeout(1000)
                cards = page.locator("li.scaffold-layout__list-item")
                card = cards.nth(i)
                card.scroll_into_view_if_needed(timeout=5000)

            card.click()

            page.wait_for_timeout(2000)
            page.wait_for_selector("#job-details", timeout=10000)

            titulo_locator = page.locator(".job-details-jobs-unified-top-card__job-title")
            titulo = titulo_locator.inner_text() if titulo_locator.count() > 0 else "Titulo não encontrado"

            descricao_page = page.locator("#job-details")
            descricao = descricao_page.inner_text() if descricao_page.count() > 0 else "Descrição não encontrada"

            caixa_vagas.append({
                "titulo": titulo,
                "descricao": descricao
            })

            print(f"Vaga {i+1} extraída: {titulo}")

        browser.close()
    return caixa_vagas

# def busca_vagas_tool() -> List:
#     try:
#         vagas = buscar_multiplas_vagas("Desenvolvedor Python", 5)
#         for vaga in vagas:
#             print(f"Titulo: {vaga['titulo']}\nDescrição: {vaga['descricao']}\n{'-'*40}")
#     except FileNotFoundError:
#         print("Sessão do LinkedIn não encontrada. Por favor, execute 'gerar_sessao_linkedin()' primeiro para criar a sessão.")
#         gerar_sessao_linkedin()
#         vagas = buscar_multiplas_vagas("Desenvolvedor Python", 10)
#         for vaga in vagas:
#             print(f"Titulo: {vaga['titulo']}\nDescrição: {vaga['descricao']}\n{'-'*40}")
