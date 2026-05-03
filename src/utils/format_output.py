import re

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