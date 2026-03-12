import re

def extrair_bloco_markdown(texto: str) -> str:
    """
    Extrai o conteúdo de um bloco de código Markdown, removendo as marcações de início e fim.
    """
    
    padrao = r"```(?:markdown)?\s*\n(.*?)```"
    match = re.match(padrao, texto, re.DOTALL)

    if match:
        return match.group(1).strip()
    return texto.strip()