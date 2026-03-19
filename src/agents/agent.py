from agno.agent import Agent
from pydantic import BaseModel, Field
from typing import List
from agno.models.openai import OpenAIResponses
from agno.models.ollama import Ollama
from agno.models.message import Message
from agno.utils.pprint import pprint_run_response
import os
from dotenv import load_dotenv
from src.utils.format_output import extrair_bloco_markdown

load_dotenv()

from src.tools.playwright_tool import buscar_multiplas_vagas, tool_envio_candidatura
# Importando o novo arsenal de ferramentas
from src.tools.cv_tool import ler_cv_base_md, salvar_cv_otimizado_md, converter_md_para_pdf

MODEL_GPT = OpenAIResponses(id=os.getenv("MODELO_PRINCIPAL", "gpt-4o-mini"), api_key=os.getenv("OPENAI_API_KEY"))  # Configuração para GPT-4.1 mini
MODEL_OLLAMA_QWEN2 = Ollama(id="qwen2.5:7b", host="http://localhost:11434", options={"temperature": 0.7, "num_gpu": 0})  # Configuração para Ollama local
MODEL_OLLAMA_QWEN3 = Ollama(id="qwen3.5:9b", host="http://localhost:11434", options={"temperature": 0.7, "num_gpu": 0})  # Configuração para Ollama local
MODEL_GPT_OPEN = OpenAIResponses(id=os.getenv("MODELO_GPT_OPEN", "openai/gpt-oss-20b"), api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")  # Configuração para GPT-4.1 mini


buscar_vagas = os.environ.get("BUSCAR_VAGA", "Agente de IA")
quantidade_vagas = os.environ.get("QUANTIDADE_VAGAS", 1)  # Recomendado processar 1 por vez para não confundir o modelo local

class ATSExtract(BaseModel):
    technical_terms: List[str] = Field(description="Tecnologias e ferramentas atômicas (ex: Python, AWS)")
    soft_skills: List[str] = Field(description="Habilidades comportamentais")
    desejaveis: List[str] = Field(description="Habilidades desejáveis ou marcadas com 'ou'")

vagas_escolhidas = buscar_multiplas_vagas(buscar_vagas, quantidade_vagas)

analista_ats = Agent(
    name="Analista de ATS",
    model=MODEL_GPT_OPEN,  # Usando o modelo mais leve para análise de vaga
    description="Analisa descrições de vagas e extrai os termos essenciais.",
    instructions=f"""Você é um algoritmo de ATS extraindo dados de vagas de {buscar_vagas}. 
    Extraia as informações de forma ATÔMICA (máximo 2 a 3 palavras por item). 
    REGRA ATS: Extraia os termos técnicos exatamente como estão escritos na vaga (ex: se diz 'RESTful API', extraia 'RESTful API')\nEscreva também o titulo da vaga como technical_terms. 
    Transforme exigências complexas em tags diretas. Se houver a palavra 'ou', coloque na lista de desejaveis.""",
    expected_output="Gere o output estritamente preenchendo o schema de technical_terms, soft_skills e desejaveis.",
    output_schema=ATSExtract
)

agente_leitor = Agent(
    name="Leitor de CV",
    model=MODEL_GPT_OPEN,
    description="Lê o currículo base em Markdown e retorna seu conteúdo íntegro.",
    instructions="""Você tem UMA única responsabilidade: recuperar o conteúdo do currículo base.

    PASSOS OBRIGATÓRIOS:
    1. Acione IMEDIATAMENTE a ferramenta `ler_cv_base_md`.
    2. Retorne o conteúdo EXATAMENTE como foi lido, sem alterar uma única palavra.
    3. NÃO faça análises, NÃO reescreva, NÃO adicione comentários.

    REGRA DE OURO: Sua saída deve ser idêntica ao arquivo lido. Zero criatividade aqui.
    """,
    tools=[ler_cv_base_md],
)

agente_redator = Agent(
    name="Redator de CV",
    model=MODEL_GPT,
    description="Reescreve o currículo em Markdown otimizado para leitura de robôs ATS, adaptando idioma e neutralizando senioridade.",
    instructions=f"""Você recebe três insumos via prompt:
    - VAGA_ORIGINAL: a descrição da vaga (para você detectar o idioma).
    - CONTEÚDO_BASE: o currículo original do candidato.
    - TERMOS_ATS: palavras-chave extraídas.

    PASSOS OBRIGATÓRIOS PARA OTIMIZAÇÃO ATS:
    1. ESPELHAMENTO DE IDIOMA (CRÍTICO): Leia a VAGA_ORIGINAL. Se a vaga estiver em INGLÊS, traduza TODO o currículo base para um INGLÊS impecável. Mude os títulos para "SUMMARY", "EXPERIENCE", "SKILLS", "PROJECTS". Nunca gere um CV em português para uma vaga gringa.
    2. NEUTRALIZAÇÃO DE SENIORIDADE: Remova TODAS as menções à palavra "Júnior", "Junior", "Trainee" ou "Estagiário". 
       - No topo do CV, use apenas "AI Engineer".
       - Troque o cargo "Estagiário em Biologia Computacional" por "Computational Biology AI Developer" (ou equivalente no idioma da vaga).
    3. MATCH EXATO DE PALAVRAS-CHAVE: Incorpore os TERMOS_ATS de forma natural. Se a vaga pede "AWS", escreva "AWS".
    4. FÓRMULA XYZ NA EXPERIÊNCIA: Reescreva as descrições de experiência e projetos com a estrutura: "Realizei [Ação/Projeto] medido por [Métrica/Impacto] utilizando [Tecnologias ATS]". 
    5. FORMATAÇÃO CLEAN PARA ATS: 
       - Use APENAS cabeçalhos Markdown simples (H1, H2, H3) e bullet points clássicos (- ou *).

    REGRA DE OURO: Jamais invente ferramentas, graduações ou cargos ausentes no CONTEÚDO_BASE. Você tem permissão APENAS para traduzir, omitir o nível júnior e reescrever estrategicamente.
    """
)

agente_copia_cola = Agent(
    name="Copia e Cola",
    model=MODEL_GPT_OPEN,
    description="Agente intermediário para passar o nome do arquivo Markdown do Redator para o Conversor.",
    instructions=f"""Você tem UMA única responsabilidade: receber o texto reescrito do Redator e salvar usando a ferramenta.

    PASSOS OBRIGATÓRIOS:
    1. Receba a redação, acione a ferramenta `salvar_cv_otimizado_md` passando o texto completo.
    2. Passe no parametro da tool o nome da vaga, depois passe o nome do arquivo salvo para que o próximo agente possa usá-lo.
    3. NÃO faça nada além disso. Zero criatividade extra. Sua missão é reescrever, não analisar ou comentar.
    4. REGRA DE OURO: Passe somente o nome do arquivo salvo para o próximo agente, sem nenhum texto adicional. O output deve ser estritamente o nome do arquivo Markdown gerado (ex: "cv_otimizado.md").
    """,
    tools=[salvar_cv_otimizado_md]
)

agente_conversor = Agent(
    name="Conversor de CV",
    model=MODEL_GPT_OPEN,
    description="Converte o arquivo Markdown otimizado em PDF final.",
    instructions="""Você tem UMA única responsabilidade: converter o arquivo Markdown em PDF.

    PASSOS OBRIGATÓRIOS:
    1. Receba o nome do arquivo Markdown via prompt (fornecido pelo Redator de CV).
    2. Acione IMEDIATAMENTE `converter_md_para_pdf` passando exatamente esse nome.
    3. Confirme o caminho do PDF gerado.

    REGRA DE OURO: NÃO altere o conteúdo do arquivo. NÃO leia o conteúdo.
    Apenas converta e confirme a conclusão.
    """,
    tools=[converter_md_para_pdf],
)

agente_envio = Agent(
    name = "Agente de Envio de Candidatura",
    model = MODEL_GPT_OPEN,
    description = "Agente responsável por enviar o currículo otimizado para a vaga usando automação de navegador.",
    instructions = f"""Você tem UMA única responsabilidade: enviar o currículo otimizado para a vaga usando a ferramenta de automação de navegador.
    PASSOS OBRIGATÓRIOS:
    1. Receba o link da vaga e o nome do arquivo PDF otimizado.
    2. Acione IMEDIATAMENTE a ferramenta `tool_envio_candidatura` passando o link da vaga e o caminho do PDF.
    3. Confirme a conclusão do envio.
    """,
    tools=[tool_envio_candidatura]
)

def pipeline_cv(termos_ats: list) -> str:
    """
    Executa o pipeline completo de otimização de currículo.

    Args:
        termos_ats: Palavras-chave extraídas da vaga pelo sistema ATS.

    Returns:
        Confirmação do PDF gerado.
    """

    for _, termo in enumerate(termos_ats):
        print("="*60)
        print(f"\n[1/5] Analisando a Vaga: {termo['titulo']}")
        resultado_ats = analista_ats.run(termo["descricao"])
        pprint_run_response(resultado_ats)

        print("\n[2/5] Acionando o Agente Redator...")
        # O comando inicial que dá o gatilho para a IA trabalhar sozinha
        resultado_leitura = agente_leitor.run("Leia o currículo base agora.")
        pprint_run_response(resultado_leitura)
        conteudo_base = resultado_leitura.content

        # ETAPA 2: Redação otimizada
        print("\n[3/5] Reescrevendo CV para ATS...")
        prompt_redacao = f"""
            VAGA_ORIGINAL (Use para detectar o idioma alvo!):
            {termo['descricao'][:1500]}...

            CONTEÚDO_BASE:
            {conteudo_base}

            TERMOS_ATS:
            {resultado_ats.content}

            Reescreva o currículo seguindo suas instruções e salve o arquivo.
            """
        resultado_redacao = agente_redator.run(prompt_redacao)
        redacao = extrair_bloco_markdown(resultado_redacao.content)  # Limpa o output para pegar só o markdown

        resultado_md = agente_copia_cola.run(f"Pegue o nome da vaga {termo['titulo']} e o conteúdo {redacao}")
        pprint_run_response(resultado_md)
        nome_arquivo = resultado_md.content  # ex: "cv_otimizado.md"

        # ETAPA 4: Conversão para PDF
        print("\n[4/5] Convertendo para PDF...")
        prompt_conversao = f"Converta o arquivo '{nome_arquivo}' para PDF agora."
        resultado_conversao = agente_conversor.run(prompt_conversao)

        print("\n✅ Pipeline concluído.")
        print(f"PDF gerado: {resultado_conversao.content}")

        print("\n[5/5] Acionando o Agente de Envio...")
        prompt_envio = f"Envie o arquivo '{resultado_conversao.content}' para a vaga {termo['url']}."
        agente_envio.run(prompt_envio)

    print("\n✅ Pipeline concluído.")

if __name__ == "__main__":
    print("Iniciando o pipeline de otimização de currículo...\n")
    # print(f"Vaga escolhida para otimização: {vagas_escolhidas[-1]['titulo']}\n{vagas_escolhidas[-1]['descricao']}")
    pipeline_cv(termos_ats=vagas_escolhidas)