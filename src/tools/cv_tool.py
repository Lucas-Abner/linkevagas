from pypdf import PdfReader
from pdf2docx import Converter
from docx import Document
import os

# def tool_pdf_to_docx(pdf_path, docx_path):
#     """
#     Ferramenta criada para Converter o conteúdo de um arquivo PDF para o formato DOCX, utilizando a biblioteca pdf2docx.
#     Também sera usado para ler o arquivo PDF e extrair seu conteúdo, para isso usaremos a biblioteca python-docx. O objetivo é permitir que o conteúdo do PDF seja manipulado e editado em um formato mais acessível, como o DOCX.
#     """
    
#     cv = Converter(pdf_path)
#     cv.convert(docx_path, start=0, end=None)
#     cv.close()


# Caminho do arquivo
def tool_pdf_cv_reader(pdf_path):

    # Verificação básica de segurança
    if not os.path.exists(pdf_path):
        print(f"Erro: O arquivo não foi encontrado em {pdf_path}")
    else:
        try:
            # Usando o PdfReader diretamente com o caminho (mais estável)
            reader = PdfReader(pdf_path)
            
            # Total de páginas
            num_pages = len(reader.pages)
            print(f"Total de páginas: {num_pages}")

            # Extraindo a primeira página
            if num_pages > 0:
                page = reader.pages[0]
                text = page.extract_text()
                
                if text:
                    return text
                else:
                    print("Aviso: O PDF parece ser uma imagem (precisaria de OCR).")
                    
        except Exception as e:
            print(f"Ocorreu um erro ao processar o PDF: {e}")
