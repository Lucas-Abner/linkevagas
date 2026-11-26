import re


def normalizar_formatacao_projetos(texto: str) -> str:
    """Padroniza os títulos dos projetos sem alterar as demais seções.

    Cada projeto deve aparecer como um parágrafo comum, com somente o nome
    do projeto em negrito. Assim o PDF não transforma o projeto em um título
    maior (``###``) nem deixa sua descrição inteira em negrito.
    """
    if not texto or not texto.strip():
        return texto

    linhas = texto.splitlines()
    resultado = []
    em_projetos = False

    def titulo_como_paragrafo(conteudo: str) -> str:
        conteudo = conteudo.strip()
        conteudo = re.sub(r"^\*+|\*+$", "", conteudo).strip()

        # O nome vem antes do separador usado pelo modelo para a descrição,
        # período ou link do repositório.
        separador = re.search(r"\s+([—–-])\s+", conteudo)
        if separador:
            nome = conteudo[:separador.start()].strip(" *")
            restante = conteudo[separador.end():].replace("**", "")
            return f"**{nome}** {separador.group(1)} {restante.strip()}"

        return f"**{conteudo.replace('**', '').strip()}**"

    for linha in linhas:
        if re.match(r"^##\s+PROJETOS\s*$", linha, flags=re.IGNORECASE):
            em_projetos = True
            resultado.append(linha)
            continue

        if em_projetos and re.match(r"^##\s+", linha):
            em_projetos = False

        if em_projetos:
            heading = re.match(r"^#{3,}\s+(.+?)\s*$", linha)
            if heading:
                resultado.append(titulo_como_paragrafo(heading.group(1)))
                continue

            # Corrige também o formato comum "**Projeto — descrição**".
            bold_line = re.match(r"^\*\*(.+)\*\*\s*$", linha.strip())
            if bold_line:
                resultado.append(titulo_como_paragrafo(bold_line.group(1)))
                continue

            # Mantém em negrito somente o nome quando a linha já está no
            # formato correto, mas contém uma descrição após ele.
            mixed_line = re.match(r"^\s*\*\*(.+?)\*\*(.*)$", linha)
            if mixed_line:
                nome = mixed_line.group(1).strip()
                restante = mixed_line.group(2).replace("**", "")
                resultado.append(f"**{nome}**{restante}")
                continue

            # Recupera o formato "Nome do Projeto: descrição" quando o
            # modelo não aplicou nenhuma marcação ao nome.
            plain_title = re.match(r"^\s*([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][^:]{1,80}):\s+(.+)$", linha)
            if plain_title:
                resultado.append(f"**{plain_title.group(1).strip()}**: {plain_title.group(2).replace('**', '')}")
                continue

            plain_separator = re.match(r"^\s*([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][^|—–-]{1,80}?)\s+([|—–-])\s+(.+)$", linha)
            if plain_separator:
                resultado.append(
                    f"**{plain_separator.group(1).strip()}** {plain_separator.group(2)} "
                    f"{plain_separator.group(3).replace('**', '')}"
                )
                continue

            # Fora do nome do projeto, nenhum trecho deve permanecer em
            # negrito dentro da seção.
            if linha.strip():
                resultado.append(linha.replace("**", ""))
                continue

        resultado.append(linha)

    return "\n".join(resultado)

def extrair_bloco_markdown(texto: str) -> str:
    """
    Extrai o conteúdo de um bloco de código Markdown, removendo as marcações de início e fim.
    Usa re.search (não re.match) para funcionar mesmo com texto antes do bloco.
    Também sanitiza prefixos comuns de LLMs ("Aqui está o CV:", thinking tags, etc.)
    """
    if not texto or not texto.strip():
        return ""

    # 1. Remove thinking tags (<think>...</think>) se existirem
    texto = re.sub(r'<think>.*?</think>', '', texto, flags=re.DOTALL)

    # 2. Tenta extrair bloco de código markdown
    padrao = r"```(?:markdown)?\s*\n(.*?)```"
    match = re.search(padrao, texto, re.DOTALL)

    if match:
        return match.group(1).strip()

    # 3. Remove prefixos comuns de LLMs
    prefixos_llm = [
        r"^(?:Aqui está|Here is|Here's|Segue|Abaixo)[^\n]*:\s*\n",
        r"^(?:O currículo|The resume|The CV)[^\n]*:\s*\n",
        r"^(?:Claro|Sure|Of course|Certainly)[^\n]*:\s*\n",
    ]
    resultado = texto.strip()
    for prefixo in prefixos_llm:
        resultado = re.sub(prefixo, '', resultado, flags=re.IGNORECASE)

    return resultado.strip()