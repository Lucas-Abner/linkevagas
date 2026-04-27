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
    Ferramenta para a IA ler o currículo base em formato Markdown.
    """
    md = MarkItDown()
    pdf_path = str(os.getenv("CV_PATH"))
    pdf_md = md.convert(pdf_path)

    conteudo_cv = pdf_md.text_content

    caminho_md = pdf_path.replace(".pdf", ".md")
    # display(Markdown(f"{caminho_md}"))

    with open(caminho_md, "w", encoding="utf-8") as f:
        f.write(conteudo_cv)

    if not os.path.exists(caminho_md):
        return f"Erro: Arquivo {caminho_md} não encontrado. Por favor, crie este arquivo com as informações base."
    with open(caminho_md, "r", encoding="utf-8") as f:
        return f.read()

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
                        font-family: 'Calibri', 'Helvetica Neue', Arial, sans-serif;
                        font-size: 10pt;
                        line-height: 1.5;
                        word-spacing: 0.04em;
                        color: #222;
                        margin: 0;
                        padding: 0;
                    }}

                    /* ── Nome do candidato (h3 no topo) ── */
                    h3:first-of-type {{
                        font-size: 18pt;
                        font-weight: 700;
                        text-align: center;
                        text-transform: uppercase;
                        letter-spacing: 0.08em;
                        color: #1a1a1a;
                        margin: 0 0 2px 0;
                        padding: 0;
                    }}

                    /* ── Títulos de seção (h3 restantes) ── */
                    h3 {{
                        font-size: 11pt;
                        font-weight: 700;
                        text-transform: uppercase;
                        letter-spacing: 0.06em;
                        color: #1a1a1a;
                        margin: 14px 0 6px 0;
                        padding-bottom: 3px;
                        border-bottom: 1.5px solid #333;
                    }}

                    /* ── Separadores entre seções ── */
                    hr {{
                        border: none;
                        height: 0;
                        margin: 8px 0;
                    }}

                    /* ── Subtítulos em negrito (cargo, projeto) ── */
                    strong {{
                        font-weight: 700;
                        font-size: 10pt;
                        color: #111;
                    }}

                    /* ── Parágrafos (contato, datas, etc.) ── */
                    p {{
                        margin: 3px 0 5px 0;
                        color: #333;
                    }}

                    /* Linha logo após o nome (contato) — centro */
                    h3:first-of-type + p {{
                        text-align: center;
                        font-size: 9pt;
                        color: #555;
                        margin-bottom: 4px;
                    }}

                    /* Segunda linha de contato (links) */
                    h3:first-of-type + p + p {{
                        text-align: center;
                        font-size: 9pt;
                        color: #555;
                        margin-bottom: 10px;
                    }}

                    /* ── Listas (bullet points) ── */
                    ul {{
                        margin: 4px 0 8px 0;
                        padding-left: 18px;
                    }}

                    li {{
                        margin-bottom: 4px;
                        line-height: 1.45;
                        color: #333;
                    }}

                    /* ── Links ── */
                    a {{
                        color: #2563eb;
                        text-decoration: none;
                    }}

                    /* ── Headings não usados mas para segurança ── */
                    h1 {{
                        font-size: 18pt;
                        text-align: center;
                        margin: 0 0 4px 0;
                        text-transform: uppercase;
                        letter-spacing: 0.08em;
                    }}

                    h2 {{
                        font-size: 12pt;
                        font-weight: 700;
                        text-transform: uppercase;
                        letter-spacing: 0.05em;
                        border-bottom: 1.5px solid #333;
                        margin: 14px 0 6px 0;
                        padding-bottom: 3px;
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