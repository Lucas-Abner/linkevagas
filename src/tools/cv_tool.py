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
    """
    cv_path_env = os.getenv("CV_PATH")
    
    # 1. Tenta usar o arquivo definido no CV_PATH (selecionado no GUI)
    if cv_path_env and os.path.exists(cv_path_env):
        print(f"📖 Lendo currículo de: {cv_path_env}")
        
        # Se for PDF, extrai o texto
        if cv_path_env.lower().endswith(".pdf"):
            try:
                reader = PdfReader(cv_path_env)
                texto_pdf = ""
                for page in reader.pages:
                    texto_pdf += page.extract_text() + "\n"
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

def converter_md_para_pdf(caminho_md: str) -> str:
    """
    Ferramenta para a IA converter o arquivo Markdown final em um PDF amigável para ATS.
    """
    try:
        with open(caminho_md, "r", encoding="utf-8") as f:
            texto_md = f.read()

        conteudo_html = markdown.markdown(texto_md)

        html_completo = f"""
        <html>
            <head>
                <meta charset="utf-8">
                <style>
                    @page {{
                        size: A4 portrait;
                        margin: 1.5cm 1.8cm;
                    }}

                    body {{
                        font-family: 'Noto Sans', 'Segoe UI', Arial, sans-serif;
                        font-size: 10pt;
                        line-height: 1.4;
                        color: #1f2937;
                        margin: 0;
                        padding: 0;
                    }}

                    /* ── Nome do candidato ── */
                    h1 {{
                        font-family: 'Liberation Serif', 'Times New Roman', serif;
                        font-size: 21pt;
                        font-weight: 700;
                        text-align: center;
                        text-transform: uppercase;
                        color: #000000;
                        margin: 0 0 2px 0;
                        padding: 0;
                    }}

                    /* ── Títulos de seção (RESUMO, EXPERIÊNCIA) ── */
                    h2 {{
                        font-family: 'Liberation Serif', 'Times New Roman', serif;
                        font-size: 13pt;
                        font-weight: 700;
                        text-transform: uppercase;
                        color: #000000;
                        margin: 16px 0 6px 0;
                        padding: 0;
                    }}

                    /* ── Subtítulos de Experiência/Projetos ── */
                    h3 {{
                        font-family: 'Noto Sans', 'Segoe UI', Arial, sans-serif;
                        font-size: 10.5pt;
                        font-weight: 700;
                        color: #000000;
                        margin: 10px 0 2px 0;
                        padding: 0;
                    }}

                    /* ── Cargo/Subtítulo no topo (strong dentro do parágrafo de contato) ── */
                    h1 + p strong {{
                        display: block;
                        font-family: 'Noto Sans Mono', 'Courier New', monospace;
                        font-size: 9.5pt;
                        color: #4b5563;
                        font-weight: normal;
                        margin-bottom: 4px;
                        text-transform: uppercase;
                    }}

                    /* ── Contato ── */
                    h1 + p {{
                        text-align: center;
                        font-family: 'Noto Sans Mono', 'Courier New', monospace;
                        font-size: 9pt;
                        color: #4b5563;
                        margin-bottom: 12px;
                        line-height: 1.5;
                    }}

                    /* ── Datas e Períodos (em itálico no md) ── */
                    em {{
                        font-family: 'Noto Sans Mono', 'Courier New', monospace;
                        font-size: 8pt;
                        color: #4b5563;
                        font-style: normal;
                        display: block;
                        margin-bottom: 4px;
                    }}

                    /* ── Negrito genérico nas seções ── */
                    strong {{
                        font-weight: 700;
                        color: #000000;
                    }}

                    /* ── Parágrafos gerais ── */
                    p {{
                        margin: 3px 0 5px 0;
                    }}

                    /* ── Listas (bullet points) ── */
                    ul {{
                        margin: 4px 0 8px 0;
                        padding-left: 18px;
                    }}

                    li {{
                        margin-bottom: 4px;
                        line-height: 1.4;
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