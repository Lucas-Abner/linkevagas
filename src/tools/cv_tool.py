from pypdf import PdfReader
import os
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

    caminho_md = pdf_path.replace(".pdf", ".md") if os.path.exists(pdf_path) else pdf_path2.replace(".pdf", ".md")
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
        pdf = MarkdownPdf(toc_level=0)
        with open(caminho_md, "r", encoding="utf-8") as f:
            pdf.add_section(Section(f.read()))
        
        caminho_pdf = caminho_md.replace(".md", ".pdf")
        pdf.save(caminho_pdf)
        return f"PDF gerado com sucesso em {caminho_pdf}"
    except Exception as e:
        return f"Erro ao converter PDF: {e}"