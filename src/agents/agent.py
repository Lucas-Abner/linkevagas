from agno.agent import Agent
from pydantic import BaseModel, Field
from typing import List
from agno.models.ollama import Ollama
from agno.models.message import Message
from agno.utils.pprint import pprint_run_response

from src.tools.playwright_tool import buscar_multiplas_vagas
# Importando o novo arsenal de ferramentas
from src.tools.cv_tool import ler_cv_base_md, salvar_cv_otimizado_md, converter_md_para_pdf

support_format_cv = [
    Message(role="system", content="""
LUCAS ABNER CAIXETA DE OLIVEIRA

Campinas, SP  | lucascaixeta02@gmail.com | (11) 96013-6292 
LinkedIn: www.linkedin.com/in/lucas-abner-caixeta/ | GitHub: github.com/lucas-abner 
AI Engineer Júnior | IA Generativa | LLMs | Agentes (LangChain/CrewAI) | Python

RESUMO PROFISSIONAL
Junior AI Engineer com forte foco em Inteligência Artificial Generativa e construção de aplicações inteligentes. Experiência prática no desenvolvimento end-to-end de soluções utilizando LLMs, sistemas multi-agentes (CrewAI, LangChain) e arquiteturas RAG. Vivência no consumo e criação de APIs RESTful utilizando FastAPI, conectando modelos de IA com fluxos de back-end no mundo real. Apaixonado por explorar novos frameworks e construir assistentes que automatizam processos e executam tarefas complexas , com facilidade para leitura de documentação técnica em inglês.

HABILIDADES TÉCNICAS

    IA Generativa & LLMs: Modelos fundacionais (ChatGPT, Claude, Gemini, Ollama, Llama.cpp, MedGemma), Fine-tuning, RAG.

    Frameworks de IA: LangChain, CrewAI, Agno.

    Engenharia de Software & Web: Python, FastAPI (APIs REST), consumo de APIs externas, Docker, SQL, Git, Linux.

    Machine Learning: Scikit-learn, Pandas, NumPy, Deep Learning.

EXPERIÊNCIA PROFISSIONAL
Estagiário em Biologia Computacional | Campinas, SP Fevereiro 2025 – Atual 

    Desenvolvimento de assistentes e agentes de IA utilizando Python para a automação de processos internos e execução de tarefas reais.

    Implementação e orquestração de LLMs locais (Ollama, Llama.cpp) em ambientes HPC, garantindo autonomia, controle de dados e redução de custos com APIs externas.

    Integração de modelos preditivos (Machine Learning e Deep Learning) aplicados a cenários biológicos de alta complexidade.

    Criação de pipelines de dados e APIs escaláveis utilizando FastAPI para servir os modelos desenvolvidos.

PROJETOS EM DESTAQUE
Projeto Med-Crew | Análise de Imagens com Agentes * Desenvolvimento de uma aplicação em Python utilizando a arquitetura multi-agente CrewAI e o modelo MedGemma para análise inteligente de imagens de raio-X.

    Destaque: Participação no "The MedGemma Impact Challenge" no Kaggle, consolidando conhecimentos práticos na aplicação de LLMs open-weight de ponta.

Agente de IA para Análise de Dados e Predição | github.com/Lucas-Abner/agent_ml_analityc 

    Construção de um pipeline completo de back-end para análise de dados utilizando arquitetura multi-agent com CrewAI.

    Implementação de modelos preditivos clássicos (Random Forest, Regressão Linear, Logística e SVM) integrados ao fluxo de decisão do agente de IA.

FORMAÇÃO

Tecnologia em Inteligência Artificial e Machine Learning 
UniCesumar | 2024 – Atual 

CERTIFICAÇÕES

    LLM Engineering – Udemy 

    Agentic AI Engineering – Udemy 

    Pós-treinamento de LLMs – DeepLearning.AI 

IDIOMAS

    Português: Nativo 

    Inglês: Intermediário (Foco em leitura técnica avançada)
""".strip()
    )
]


MODEL_CONFIG = Ollama(
    id="gpt-oss:20b",
    host="http://localhost:11434",
    options={"temperature": 0.3},  # ← reduzido para minimizar alucinação
)

buscar_vagas = "Agente de IA"
quantidade_vagas = 2 # Recomendado processar 1 por vez para não confundir o modelo local

# O Schema se mantém APENAS para o extrator ATS
class ATSExtract(BaseModel):
    technical_terms: List[str] = Field(description="Tecnologias e ferramentas atômicas (ex: Python, AWS)")
    soft_skills: List[str] = Field(description="Habilidades comportamentais")
    desejaveis: List[str] = Field(description="Habilidades desejáveis ou marcadas com 'ou'")

vagas_escolhidas = buscar_multiplas_vagas(buscar_vagas, quantidade_vagas)

analista_ats = Agent(
    name="Analista de ATS",
    model=Ollama(id="qwen2.5:7b", host="http://localhost:11434"),
    description="Analisa descrições de vagas e extrai os termos essenciais.",
    instructions=f"Você é um algoritmo de ATS extraindo dados de vagas de {buscar_vagas}. Extraia as informações de forma ATÔMICA e CURTA (máximo 3 palavras por item). Transforme exigências complexas em tags diretas. Se houver a palavra 'ou', coloque na lista de desejaveis.",
    expected_output="Gere o output estritamente preenchendo o schema de technical_terms, soft_skills e desejaveis.",
    output_schema=ATSExtract
)

# O Redator perde o schema e ganha as TOOLS para ter total liberdade de reescrita


# ═════════════════════════════════════════════
# AGENTE 1 — LEITOR
# Responsabilidade única: ler o CV base e retornar o conteúdo bruto.
# Uma ferramenta → sem ambiguidade de qual chamar.
# ═════════════════════════════════════════════
agente_leitor = Agent(
    name="Leitor de CV",
    model=MODEL_CONFIG,
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


# ═════════════════════════════════════════════
# AGENTE 2 — REDATOR
# Responsabilidade única: reescrever o CV com base nos dados reais
# recebidos do Agente 1 + termos ATS fornecidos no prompt.
# Uma ferramenta → só pode salvar, não pode ler nem converter.
# ═════════════════════════════════════════════
agente_redator = Agent(
    name="Redator de CV",
    model=MODEL_CONFIG,
    description="Reescreve o currículo em Markdown otimizado para ATS e salva o arquivo.",
    instructions=f"""Você recebe dois insumos via prompt:
    - CONTEÚDO_BASE: o currículo original do candidato (fornecido pelo Leitor de CV).
    - TERMOS_ATS: palavras-chave extraídas da vaga.

    PASSOS OBRIGATÓRIOS:
    1. Leia o CONTEÚDO_BASE com atenção. Esse é o único histórico real do candidato.
    2. Cruze o resumo profissional, habilidades técnicas e a experiência do candidato com os TERMOS_ATS.
    3. Reescreva o currículo aplicando:
       - Técnica XYZ no resumo profissional para destacar as palavras-chave.
       - Técnica XYZ na seção de habilidades técnicas para alinhar com os termos ATS.
       - Técnica XYZ nas descrições de experiência (Realizei X medido por Y fazendo Z).
       - Títulos em UPPERCASE → converta para H3 ou H5 Markdown.
       - Insira os termos ATS de forma natural onde houver correspondência real.
    4. REGRA DE OURO: Jamais invente ferramentas, graduações ou cargos ausentes no
       CONTEÚDO_BASE. Se precisar de seções novas, use apenas títulos genéricos como
       "EXPERIÊNCIA ADICIONAL" ou "FORMAÇÃO COMPLEMENTAR".
       Não adicione mais nada além do necessário. Zero criatividade extra. Sua missão é reescrever, não analisar ou comentar.
    """,
    additional_input=support_format_cv,
    # tools=[salvar_cv_otimizado_md],
)

agente_copia_cola = Agent(
    name="Copia e Cola",
    model=MODEL_CONFIG,
    description="Agente intermediário para passar o nome do arquivo Markdown do Redator para o Conversor.",
    instructions=f"""Você tem UMA única responsabilidade: receber o texto reescrito do Redator e salvar usando a ferramenta.

    PASSOS OBRIGATÓRIOS:
    1. Receba a redação, acione a ferramenta `salvar_cv_otimizado_md` passando o texto completo.
    2. Passe no parametro da tool o nome da vaga que é {vagas_escolhidas[1]['titulo']}, depois passe o nome do arquivo salvo para que o próximo agente possa usá-lo.
    3. NÃO faça nada além disso. Zero criatividade extra. Sua missão é reescrever, não analisar ou comentar.
    """,
    tools=[salvar_cv_otimizado_md]
)


# ═════════════════════════════════════════════
# AGENTE 3 — CONVERSOR
# Responsabilidade única: converter o arquivo Markdown salvo em PDF.
# Uma ferramenta → não pode ler nem reescrever, só converter.
# ═════════════════════════════════════════════
agente_conversor = Agent(
    name="Conversor de CV",
    model=MODEL_CONFIG,
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


# ═════════════════════════════════════════════
# ORQUESTRADOR — Pipeline sequencial
# Conecta os três agentes em cadeia, passando o output de um
# como input do próximo. Sem ferramentas próprias = zero alucinação
# de ferramenta no orquestrador.
# ═════════════════════════════════════════════
def pipeline_cv(termos_ats: str) -> str:
    """
    Executa o pipeline completo de otimização de currículo.

    Args:
        termos_ats: Palavras-chave extraídas da vaga pelo sistema ATS.

    Returns:
        Confirmação do PDF gerado.
    """
    
    print("="*60)
    print(f"\n[1/4] Analisando a Vaga: {termos_ats['titulo']}")
    resultado_ats = analista_ats.run(termos_ats["descricao"])
    pprint_run_response(resultado_ats)

    print("\n[2/4] Acionando o Agente Redator...")
    # O comando inicial que dá o gatilho para a IA trabalhar sozinha
    resultado_leitura = agente_leitor.run("Leia o currículo base agora.")
    pprint_run_response(resultado_leitura)
    conteudo_base = resultado_leitura.content

    # ETAPA 2: Redação otimizada
    print("\n[3/4] Reescrevendo CV para ATS...")
    prompt_redacao = f"""
        CONTEÚDO_BASE:
        {conteudo_base}

        TERMOS_ATS:
        {resultado_ats.content}

        Reescreva o currículo seguindo suas instruções e salve o arquivo.
        """
    resultado_redacao = agente_redator.run(prompt_redacao)
    pprint_run_response(resultado_redacao)

    resultado_md = agente_copia_cola.run(resultado_redacao.content)
    pprint_run_response(resultado_md)
    nome_arquivo = resultado_md.content  # ex: "cv_otimizado.md"

    # ETAPA 4: Conversão para PDF
    print("\n[4/4] Convertendo para PDF...")
    prompt_conversao = f"Converta o arquivo '{nome_arquivo}' para PDF agora."
    resultado_conversao = agente_conversor.run(prompt_conversao)

    print("\n✅ Pipeline concluído.")
    return resultado_conversao.content



# ─────────────────────────────────────────────
# EXECUÇÃO
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("Iniciando o pipeline de otimização de currículo...\n")
    print(f"Vaga escolhida para otimização: {vagas_escolhidas[1]['titulo']}\n{vagas_escolhidas[1]['descricao']}")
    pipeline_cv(termos_ats=vagas_escolhidas[1])