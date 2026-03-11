from pypdf import PdfReader
import os
from markitdown import MarkItDown

try:
    from markdown_pdf import MarkdownPdf, Section
except ImportError:
    print("Por favor, instale a biblioteca: uv add markdown-pdf")

# def tool_pdf_cv_reader(pdf_path: str) -> str:
#     """Lê um arquivo PDF (Mantido caso você precise extrair o seu atual)."""
#     if not os.path.exists(pdf_path):
#         return f"Erro: O arquivo não foi encontrado em {pdf_path}"
#     try:
#         reader = PdfReader(pdf_path)
#         text = ""
#         # Correção do bug: O return estava dentro do for, lendo só a pag 1
#         for page in reader.pages:
#             text += page.extract_text() + "\n"
        
#         if not text.strip():
#             return "Aviso: O PDF parece ser uma imagem (precisaria de OCR)."
#         return text
#     except Exception as e:
#         return f"Ocorreu um erro ao processar o PDF: {e}"

def ler_cv_base_md() -> str:
    """
    Ferramenta para a IA ler o currículo base em formato Markdown.
    """
    md = MarkItDown()
    pdf_path = "/home/lucas.abner/Documentos/code/linkevagas/Lucas_Abner_Caixeta_CV_AI_Engineer_Jr.pdf"
    pdf_path2 = "C:\\Users\\asus\\Documents\\IA\\linkevagas\\Lucas_Abner_Caixeta_CV_AI_Engineer_Jr.pdf"
    pdf_md = md.convert(pdf_path) if os.path.exists(pdf_path) else md.convert(pdf_path2)

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
    nome_arquivo = f"cv_{nome_vaga[:500].replace(' ', '_').lower()}.md"
    print(f"Salvando currículo otimizado como {nome_arquivo}...")
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write(conteudo_md)
    return f"Salvo com sucesso em {nome_arquivo}"

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
    