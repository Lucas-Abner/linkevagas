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

def converter_md_para_pdf(caminho_md: str) -> str:
    """
    Ferramenta para a IA converter o arquivo Markdown final em um PDF amigável para ATS.
    CSS otimizado para garantir que o conteúdo caiba em 1 página A4.
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
                        margin: 1.2cm 1.5cm;
                    }}

                    body {{
                        font-family: 'Noto Sans', 'Segoe UI', Arial, sans-serif;
                        font-size: 9.5pt;
                        line-height: 1.35;
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

                    /* ── Títulos de seção (RESUMO, EXPERIÊNCIA) ── */
                    h2 {{
                        font-family: 'Liberation Serif', 'Times New Roman', serif;
                        font-size: 12pt;
                        font-weight: 700;
                        text-transform: uppercase;
                        color: #000000;
                        margin: 10px 0 4px 0;
                        padding: 0;
                        border-bottom: 0.5pt solid #d1d5db;
                        padding-bottom: 2px;
                    }}

                    /* ── Subtítulos de Experiência/Projetos ── */
                    h3 {{
                        font-family: 'Noto Sans', 'Segoe UI', Arial, sans-serif;
                        font-size: 10pt;
                        font-weight: 700;
                        color: #000000;
                        margin: 7px 0 1px 0;
                        padding: 0;
                    }}

                    /* ── Cargo/Subtítulo no topo (strong dentro do parágrafo de contato) ── */
                    h1 + p strong {{
                        display: block;
                        font-family: 'Noto Sans Mono', 'Courier New', monospace;
                        font-size: 9pt;
                        color: #4b5563;
                        font-weight: normal;
                        margin-bottom: 3px;
                        text-transform: uppercase;
                    }}

                    /* ── Contato ── */
                    h1 + p {{
                        text-align: center;
                        font-family: 'Noto Sans Mono', 'Courier New', monospace;
                        font-size: 8.5pt;
                        color: #4b5563;
                        margin-bottom: 8px;
                        line-height: 1.4;
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

                    /* ── Negrito genérico nas seções ── */
                    strong {{
                        font-weight: 700;
                        color: #000000;
                    }}

                    /* ── Parágrafos gerais ── */
                    p {{
                        margin: 2px 0 3px 0;
                    }}

                    /* ── Listas (bullet points) ── */
                    ul {{
                        margin: 2px 0 5px 0;
                        padding-left: 16px;
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