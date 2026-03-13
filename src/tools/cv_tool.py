from pypdf import PdfReader
import os
from markitdown import MarkItDown
import re

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
    pdf_path2 = "C:\\Users\\lucas\\Documents\\code_path\\linkevagas\\Lucas_Abner_Engineer.pdf"
    pdf_md = md.convert(pdf_path) if os.path.exists(pdf_path) else md.convert(pdf_path2)

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
    

# if __name__=="__main__":
#     print("Ferramentas de CV carregadas. Use as funções para ler, salvar e converter currículos.")
#     resultado_salvar_md = salvar_cv_otimizado_md("""**LUCAS ABNER CAIXETA DE OLIVEIRA**  
# Junior AI Engineer | Machine Learning | LLMs | Agentic AI | Python

# Campinas, SP | lucascaixeta02@gmail.com | (11) 96013-6292 | GitHub: github.com/lucas-abner | LinkedIn: linkedin.com/in/lucas-abner-caixeta-oliveira

# **RESUMO PROFISSIONAL**                                                   
# Junior AI Engineer com experiência prática no desenvolvimento de soluções de IA aplicada,
# incluindo Machine Learning, LLMs e sistemas multi-agentes. Atuação em ambientes HPC,
# implementando LLMs locais, pipelines de dados end-to-end e APIs escaláveis com FastAPI.
# Experiência em automação de processos e aplicação de modelos preditivos em cenários reais.

# **HABILIDADES TÉCNICAS**                                                   
# Python, SQL, Git, Linux  
# Scikit-learn, Pandas, NumPy  
# LLMs, LangChain, RAG, CrewAI, Fine-tuning  
# FastAPI, Docker, Singularity, MLOps, HPC  

# **EXPERIÊNCIA PROFISSIONAL**                                                   
# Estagiário em Biologia Computacional – Campinas, SP (2025 – Atual)
# - Implementação de LLMs locais (Ollama, Llama.cpp) em ambiente HPC, reduzindo dependência de APIs
# externas e melhorando controle de dados  
# - Aplicação de ML e Deep Learning em problemas biológicos  
# - Criação de agentes de IA para automação de processos internos

# **PROJETO EM DESTAQUE**  
# Sistema Autônomo de Captação e Qualificação de Leads (FastAPI & Agno) | github.com/Lucas-Abner/agent_attract_customer  
# - Desenvolvimento de uma aplicação ponta a ponta com FastAPI para automatizar a atração de clientes no Instagram, com monitorização de 10 em 10 segundos para deteção de mensagens e nutrição de leads.  
# - Orquestração de múltiplos agentes de IA (framework Agno) utilizando modelos LLM (Ollama, GPT-OSS-20B, Qwen, Llama 3.1) para realizar análise de sentimento em tempo real e personalizar interações com base na intenção de compra.  
# - Construção de uma arquitetura baseada na extração inteligente de dados não estruturados, identificação de hashtags e contacto inicial automatizado de elevada precisão.
                                                 
# MedGemma Crew: Sistema Multi-Agente para Análise Radiológica | github.com/Lucas-Abner/med-crew
# - Desenvolvimento de um sistema de IA utilizando a biblioteca CrewAI para orquestrar agentes especializados na análise de imagens de raio-X de tórax e geração de laudos médicos estruturados.  
# - Integração do modelo MedGemma-1.5-4b (via Ollama) para análise textual qualitativa e TorchXRayVision (DenseNet121) para localização espacial de anomalias por meio de mapas de calor.  
# - Criação de pipeline completo com interface visual em Gradio e automação para compilar relatórios médicos dinâmicos em PDF.

# **FORMAÇÃO**                                              
# Tecnologia em Inteligência Artificial e Machine Learning – UniCesumar (2024 – Atual)

# **CERTIFICAÇÕES**  
# LLM Engineering – Udemy Agentic AI  
# Engineering – Udemy  
# Pós-treinamento de LLMs – DeepLearning.AI  
# Fundamentos de Big Data – UniCesumar

# **IDIOMAS**                                                  
# Português: Nativo | Inglês: Intermediário

# """, "Lucas_Abner_Caixeta_CV_AI_Engineer_Jr")

# print(resultado_salvar_md)

# resultado_converter = converter_md_para_pdf("cv_lucasabnercaixetacvaiengineerjr.md")
# print(resultado_converter)
