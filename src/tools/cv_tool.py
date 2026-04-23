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
                    @page{{
                        size: A4 portrait;
                        margin: 1.0cm;
                    }}
                    body{{
                        font-family: Arial, sans-serif;
                        font-size: 9.5pt;
                        line-height: 1.35;
                        word-spacing: 0.05em;
                        letter-spacing: 0.01em;
                        color: #000;
                    }}
                    h1 {{
                        font-size: 13pt;
                        text-align: center;
                        margin-bottom: 6px;
                        text-transform: uppercase;
                        letter-spacing: 0.03em;
                    }}
                    h2 {{
                        font-size: 11pt;
                        border-bottom: 1px solid #000;
                        margin-top: 10px;
                        margin-bottom: 6px;
                        padding-bottom: 2px;
                    }}
                    h3 {{
                        font-size: 10pt;
                        margin-top: 6px;
                        margin-bottom: 3px;
                    }}
                    p {{
                        margin-top: 3px;
                        margin-bottom: 3px;
                    }}
                    ul {{
                        margin-top: 3px;
                        margin-bottom: 6px;
                        padding-left: 20px;
                    }}
                    li {{
                        margin-bottom: 3px;
                    }}
                    .contatos {{
                        text-align: center;
                        font-size: 8.5pt;
                        margin-bottom: 10px;
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