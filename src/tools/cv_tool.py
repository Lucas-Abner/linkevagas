from pypdf import PdfReader
import os
import markdown
from weasyprint import HTML
from markitdown import MarkItDown
import re
from dotenv import load_dotenv

load_dotenv()

try:
    from markdown_pdf import MarkdownPdf, Section
except ImportError:
    print("Por favor, instale a biblioteca: uv add markdown-pdf")

def ler_cv_base_md() -> str:
    """
    Ferramenta para a IA ler o currículo base.
    Prioriza o arquivo selecionado no GUI (CV_PATH no .env).
    Usa MarkItDown para PDFs (preserva estrutura) com fallback para PdfReader.
    """
    cv_path_env = os.getenv("CV_PATH")

    # 1. Tenta usar o arquivo definido no CV_PATH (selecionado no GUI)
    if cv_path_env and os.path.exists(cv_path_env):
        print(f"📖 Lendo currículo de: {cv_path_env}")

        # Se for PDF, converte para Markdown preservando estrutura
        if cv_path_env.lower().endswith(".pdf"):
            # Tenta MarkItDown primeiro (preserva headers, bullets, bold)
            try:
                md_converter = MarkItDown()
                result = md_converter.convert(cv_path_env)
                texto_md = result.text_content
                if texto_md and len(texto_md.strip()) > 50:
                    print("  ✅ PDF convertido via MarkItDown (estrutura preservada)")
                    return texto_md
            except Exception as e:
                print(f"  ⚠️ MarkItDown falhou: {e}")

            # Fallback: PdfReader (perde formatação, mas funciona sempre)
            try:
                reader = PdfReader(cv_path_env)
                texto_pdf = ""
                for page in reader.pages:
                    texto_pdf += page.extract_text() + "\n"
                print("  ℹ️ Fallback: PdfReader (texto flat, sem estrutura)")
                return texto_pdf
            except Exception as e:
                print(f"⚠️ Erro ao ler PDF {cv_path_env}: {e}")

        # Se for MD ou outro texto, lê diretamente
        try:
            with open(cv_path_env, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"⚠️ Erro ao ler arquivo {cv_path_env}: {e}")

    # 2. Fallback: Lógica original de mapeamento em src/cvs/
    print("🔍 CV_PATH não encontrado ou inválido. Usando lógica de fallback...")
    buscar_vaga = os.getenv("BUSCAR_VAGA", "").lower()
    base_dir = os.path.join(os.path.dirname(__file__), "..", "cvs")
    caminho_md = os.path.join(base_dir, "cv_base_ia.md")
    mapping_path = os.path.join(base_dir, "cv_mapping.json")

    if os.path.exists(mapping_path):
        try:
            import json
            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping = json.load(f)
            for cv_file, keywords in mapping.items():
                if any(keyword.lower() in buscar_vaga for keyword in keywords):
                    caminho_md = os.path.join(base_dir, cv_file)
                    break
        except Exception as e:
            print(f"Erro ao carregar o mapping de CVs: {e}")

    if os.path.exists(caminho_md):
        with open(caminho_md, "r", encoding="utf-8") as f:
            return f.read()

    return "Erro: Nenhum currículo base encontrado. Por favor, selecione um PDF na interface ou crie um arquivo em src/cvs/cv_base_ia.md"

def salvar_cv_otimizado_md(conteudo_md: str, nome_vaga: str) -> str:
    """
    Ferramenta para a IA salvar o currículo otimizado gerado.
    """
    padrao = r"[^a-zA-Z0-9\s]"
    match = re.search(padrao, nome_vaga)
    if match:
        nome_vaga = re.sub(padrao, "", nome_vaga)
        print(f"Nome da vaga sanitizado para: {nome_vaga}")

    nome_arquivo = f"cv_{nome_vaga[:500].replace(' ', '_').lower()}.md"
    print(f"Salvando currículo otimizado como {nome_arquivo}...")
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write(conteudo_md)
    return nome_arquivo

def _pre_processar_md_para_ats(texto_md: str) -> str:
    """
    Pré-processa o Markdown gerado pelo LLM para garantir boa renderização no PDF.
    
    Problemas resolvidos:
    1. Títulos de empresa/projeto sem negrito → adiciona **negrito**
    2. Linhas de contato sem separação visual → mantém como está
    3. Normaliza quebras de linha para funcionar com nl2br
    """
    linhas = texto_md.split("\n")
    resultado = []
    secao_atual = ""
    
    for i, linha in enumerate(linhas):
        stripped = linha.strip()
        
        # Detecta seção atual
        if stripped.startswith("## "):
            secao_atual = stripped.upper()
            resultado.append(linha)
            continue
        
        # Dentro de EXPERIÊNCIA: formata "Empresa, Cargo, Período" como negrito
        if "EXPERIÊNCIA" in secao_atual or "EXPERIENCIA" in secao_atual:
            # Padrão: "CNPEM, Estagiário em..., 2025 – Presente" ou "Empresa — Cargo"
            if stripped and not stripped.startswith("#") and not stripped.startswith("**"):
                # Detecta linha de cabeçalho de experiência (contém ano ou "Presente")
                if re.search(r'\b(19|20)\d{2}\b', stripped) and any(sep in stripped for sep in [",", "—", "–", "-"]):
                    # Verifica se parece um cabeçalho (tem empresa + cargo + data)
                    if not stripped.startswith("**"):
                        stripped = f"**{stripped}**"
                        resultado.append(stripped)
                        continue
        
        # Dentro de PROJETOS: formata nome do projeto como negrito
        if "PROJETOS" in secao_atual or "PROJETO" in secao_atual:
            if stripped and not stripped.startswith("#") and not stripped.startswith("**"):
                # Detecta nome de projeto (geralmente tem link ou é curto e começa com maiúscula)
                if ("github.com" in stripped.lower() or "gitlab.com" in stripped.lower()) and len(stripped) < 200:
                    if not stripped.startswith("**"):
                        # Separa nome do projeto da URL se possível
                        stripped = f"**{stripped}**"
                        resultado.append(stripped)
                        continue
                # Nome de projeto sem link (linha curta com maiúsculas)
                elif len(stripped.split()) <= 12 and stripped[0].isupper() and i + 1 < len(linhas) and linhas[i+1].strip():
                    prox = linhas[i+1].strip()
                    # Se a próxima linha é um parágrafo descritivo, esta é o título
                    if len(prox) > 50 and not prox.startswith("#") and not prox.startswith("**"):
                        if not stripped.startswith("**"):
                            stripped = f"**{stripped}**"
                            resultado.append(stripped)
                            continue
        
        # Dentro de FORMAÇÃO: formata nome da instituição como negrito
        if "FORMAÇÃO" in secao_atual or "FORMACAO" in secao_atual:
            if stripped and not stripped.startswith("#") and not stripped.startswith("**"):
                # Detecta linha de formação (contém " — " ou "–" com instituição)
                if any(sep in stripped for sep in ["—", "–"]) and len(stripped) < 200:
                    if not stripped.startswith("**"):
                        stripped = f"**{stripped}**"
                        resultado.append(stripped)
                        continue
        
        resultado.append(linha)
    
    return "\n".join(resultado)


def converter_md_para_pdf(caminho_md: str) -> str:
    """
    Ferramenta para a IA converter o arquivo Markdown final em um PDF amigável para ATS.
    
    Usa extensão nl2br para que quebras de linha simples virem <br> no HTML.
    Pré-processa o markdown para garantir títulos em negrito e estrutura visual clara.
    CSS otimizado para garantir que o conteúdo caiba em 1 página A4.
    """
    try:
        with open(caminho_md, "r", encoding="utf-8") as f:
            texto_md = f.read()

        # Pré-processamento: garante negrito em títulos de experiência/projetos
        texto_md = _pre_processar_md_para_ats(texto_md)

        # nl2br: converte quebras de linha simples em <br>, resolvendo o problema
        # de texto colado quando o LLM usa \n simples em vez de \n\n
        conteudo_html = markdown.markdown(texto_md, extensions=["nl2br"])

        html_completo = f"""
        <html>
            <head>
                <meta charset="utf-8">
                <style>
                    @page {{
                        size: A4 portrait;
                        margin: 1.2cm 1.5cm;
                    }}

                    body {{
                        font-family: 'Noto Sans', 'Segoe UI', Arial, sans-serif;
                        font-size: 9pt;
                        line-height: 1.3;
                        color: #1f2937;
                        margin: 0;
                        padding: 0;
                        overflow: hidden;
                    }}

                    /* ── Nome do candidato ── */
                    h1 {{
                        font-family: 'Liberation Serif', 'Times New Roman', serif;
                        font-size: 20pt;
                        font-weight: 700;
                        text-align: center;
                        text-transform: uppercase;
                        color: #000000;
                        margin: 0 0 1px 0;
                        padding: 0;
                    }}

                    /* ── Linha de título (Cargo | Keywords) ── */
                    h1 + p {{
                        text-align: center;
                        font-family: 'Noto Sans', 'Segoe UI', Arial, sans-serif;
                        font-size: 10pt;
                        color: #374151;
                        font-weight: 600;
                        margin: 0 0 2px 0;
                        line-height: 1.3;
                    }}

                    /* ── Linha de contato (segundo parágrafo após h1) ── */
                    h1 + p + p {{
                        text-align: center;
                        font-family: 'Noto Sans Mono', 'Courier New', monospace;
                        font-size: 8.5pt;
                        color: #4b5563;
                        margin-bottom: 8px;
                        line-height: 1.4;
                    }}

                    /* ── Títulos de seção (OBJETIVO, HIGHLIGHTS, EXPERIÊNCIA, etc.) ── */
                    h2 {{
                        font-family: 'Liberation Serif', 'Times New Roman', serif;
                        font-size: 11pt;
                        font-weight: 700;
                        text-transform: uppercase;
                        color: #000000;
                        margin: 7px 0 3px 0;
                        padding: 0;
                        border-bottom: 0.5pt solid #d1d5db;
                        padding-bottom: 2px;
                    }}

                    /* ── Subtítulos de Experiência/Projetos (h3) ── */
                    h3 {{
                        font-family: 'Noto Sans', 'Segoe UI', Arial, sans-serif;
                        font-size: 10pt;
                        font-weight: 700;
                        color: #000000;
                        margin: 7px 0 1px 0;
                        padding: 0;
                    }}

                    /* ── Datas e Períodos (em itálico no md) ── */
                    em {{
                        font-family: 'Noto Sans Mono', 'Courier New', monospace;
                        font-size: 7.5pt;
                        color: #4b5563;
                        font-style: normal;
                        display: block;
                        margin-bottom: 2px;
                    }}

                    /* ── Negrito (títulos de experiência, projetos, formação) ── */
                    strong {{
                        font-weight: 700;
                        color: #000000;
                        display: inline;
                    }}

                    /* ── Negrito como subtítulo visual (quando <strong> abre um parágrafo) ── */
                    p > strong:first-child:last-child {{
                        display: block;
                        font-size: 10pt;
                        margin-bottom: 1px;
                    }}

                    /* ── Parágrafos gerais (texto corrido ATS-friendly) ── */
                    p {{
                        margin: 1px 0 3px 0;
                        line-height: 1.35;
                    }}

                    /* ── Quebras de linha (nl2br) ── */
                    br {{
                        display: block;
                        content: "";
                        margin-top: 1px;
                    }}

                    /* ── Listas (fallback caso bullet points escapem) ── */
                    ul {{
                        margin: 2px 0 5px 0;
                        padding-left: 16px;
                        list-style-type: none;
                    }}

                    li {{
                        margin-bottom: 2px;
                        line-height: 1.35;
                    }}

                    /* ── Links ── */
                    a {{
                        color: #1f2937;
                        text-decoration: none;
                    }}
                </style>
            </head>
            <body>
                {conteudo_html}
            </body>
        </html>
        """

        caminho_pdf = caminho_md.replace(".md", ".pdf")

        HTML(string=html_completo).write_pdf(caminho_pdf)

        return f"PDF de 1 página gerado com sucesso: {caminho_pdf}"


    except Exception as e:
        return f"Erro ao converter PDF: {e}"