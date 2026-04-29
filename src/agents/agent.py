from agno.agent import Agent, RunOutput
from pydantic import BaseModel, Field
from typing import List
from agno.models.openai import OpenAIResponses
from agno.models.ollama import Ollama
from agno.models.message import Message
from agno.eval.performance import PerformanceEval
from agno.utils.pprint import pprint_run_response
import os
from dotenv import load_dotenv
from src.utils.format_output import extrair_bloco_markdown

load_dotenv()

from src.tools.playwright_tool import buscar_multiplas_vagas, tool_envio_candidatura
# Importando o novo arsenal de ferramentas
from src.tools.cv_tool import ler_cv_base_md, salvar_cv_otimizado_md, converter_md_para_pdf
from src.tools.ats_tool import tool_avaliar_score_ats, extract_entities, extrator_keywords_keybert, pre_process_pipeline, avaliar_score_combinado
from src.tools.tracking import registrar_candidatura, gerar_relatorio
from src.tools.github_tool import extrair_repositorios_github

MODEL_GPT = OpenAIResponses(id=os.getenv("MODELO_PRINCIPAL", "gpt-4o-mini"), api_key=os.getenv("OPENAI_API_KEY"))
MODEL_OLLAMA_QWEN2 = Ollama(id="qwen2.5:7b", host="http://localhost:11434", options={"temperature": 0.7, "num_gpu": 99})

MODO_PROCESSAMENTO = os.getenv("MODO_PROCESSAMENTO", "Híbrido (Recomendado)")

if MODO_PROCESSAMENTO == "100% Local (Ollama)":
    MODELO_INTELIGENTE = MODEL_OLLAMA_QWEN2
    MODELO_BUROCRATICO = MODEL_OLLAMA_QWEN2
elif "Nuvem" in MODO_PROCESSAMENTO:
    MODELO_INTELIGENTE = MODEL_GPT
    MODELO_BUROCRATICO = MODEL_GPT
else: # Híbrido
    MODELO_INTELIGENTE = MODEL_GPT
    MODELO_BUROCRATICO = MODEL_OLLAMA_QWEN2


buscar_vagas = os.environ.get("BUSCAR_VAGA", "Agente de IA")
quantidade_vagas = os.environ.get("QUANTIDADE_VAGAS", 1)  # Recomendado processar 1 por vez para não confundir o modelo local

vagas_escolhidas = buscar_multiplas_vagas(buscar_vagas, quantidade_vagas)

class TermosOutput(BaseModel):
    termos_corrigidos: List[str] = Field(
        description="Separação semantica de cada termo técnico, ferramenta ou tecnologia extraída da vaga, corrigida e formatada para otimização ATS."
    )
    
class ATSClassifiedOutput(BaseModel):
    technical_terms: List[str] = Field(
        description="Technologies, tools, programming languages, frameworks."
    )
    soft_skills: List[str] = Field(
        description="Interpersonal and behavioral traits."
    )
    desejaveis: List[str] = Field(
        description="Nice-to-have or preferred skills explicitly or implicitly indicated."
    )

class JobAnalysisOutput(BaseModel):
    """Análise estruturada e profunda da vaga para guiar a otimização do CV."""
    titulo_normalizado: str = Field(description="Título da vaga normalizado")
    senioridade: str = Field(description="junior|pleno|senior|lead|staff")
    area_atuacao: str = Field(description="Área principal: backend, data, AI/ML, devops, fullstack, etc.")
    
    requisitos_essenciais: List[str] = Field(
        description="Skills e experiências OBRIGATÓRIAS, citadas em seção de requisitos"
    )
    requisitos_desejaveis: List[str] = Field(
        description="Skills desejáveis/diferenciais, citadas como nice-to-have"
    )
    habilidades_transferiveis: List[str] = Field(
        description="Skills que o candidato pode demonstrar indiretamente via experiências correlatas"
    )
    
    idioma_requerido: str = Field(description="Idioma e nível exigido (ex: Inglês C1, Português nativo)")
    modelo_trabalho: str = Field(description="remoto|hibrido|presencial")
    
    tom_da_vaga: str = Field(
        description="formal|startup|corporativo|técnico — usado para calibrar o tom do CV"
    )
    gaps_criticos: List[str] = Field(
        description="Requisitos essenciais que o candidato NÃO possui e não pode contornar"
    )
    fit_score: int = Field(
        description="0-100: estimativa de compatibilidade geral do perfil com a vaga"
    )
    estrategia_cv: str = Field(
        description="Instruções específicas para o Redator sobre como adaptar o CV para esta vaga"
    )


analista_classificador = Agent(
    name="ATS Hard Skills Extractor",
    model=MODELO_INTELIGENTE,
    role="Extract ALL technical skills, tools, and technologies from job descriptions.",
        instructions="""
You are given a list of extracted terms from a job description.
Your task is to clean and normalize them.

STRICT RULES:
1. Extract only meaningful skills or technologies
2. Split combined terms (e.g. "python java sql" → "Python", "Java", "SQL")
3. Remove filler words (e.g. "experiência", "trabalhou", "com")
4. Normalize terms (e.g. "deep learning trabalhou" → "Deep Learning")
5. Remove duplicates
6. DO NOT remove valid skills
7. DO NOT invent new terms. If there are no valid skills, return an empty list [].

!!! IMPORTANT: DO NOT COPY THE EXAMPLES BELOW. THEY ARE JUST EXAMPLES. !!!

Example Output:
["Skill 1", "Skill 2", "Skill 3"]

ONLY keep terms that are explicitly present in the input.
REMOVE generic terms like:
"AI", "Coding", "Testing", "Project", "CV", "Proficiency", "Experience", "Knowledge", "Skills", "Work", etc.
""",
    output_schema=TermosOutput,
)

analista_ats = Agent(
    name="ATS Skills Classifier",
    model=MODELO_INTELIGENTE,
    role="Classify normalized ATS terms into technical skills, soft skills, and desirable skills.",
        instructions="""
You are given a CLEANED and NORMALIZED list of terms extracted from a job description.
Your job is ONLY to classify them.

STRICT RULES:
1. DO NOT modify, rewrite, or normalize any term
2. DO NOT remove any valid term
3. DO NOT invent new terms. If the input is empty, return empty lists.
4. Each term MUST go into ONLY ONE category
5. DO NOT copy the examples below.

CLASSIFICATION RULES:
- technical_terms: Tools, technologies, programming languages, etc.
- soft_skills: Behavioral or interpersonal traits.
- desejaveis: Nice-to-have or preferred skills.

Example Input:
["Skill A", "Skill B", "Skill C"]

Example Output:
{
  "technical_terms": ["Skill A"],
  "soft_skills": ["Skill B"],
  "desejaveis": ["Skill C"]
}
""",
    output_schema=ATSClassifiedOutput,
)

analista_vaga = Agent(
    name="Analista Estratégico de Vaga",
    model=MODELO_INTELIGENTE,
    role="Analista estratégico de vagas com expertise em recrutamento tech.",
    instructions="""Você é um recrutador tech sênior com 15 anos de experiência.
    
    Sua missão é fazer uma análise ESTRATÉGICA da vaga, não apenas extrair palavras-chave.
    
    PASSOS OBRIGATÓRIOS:
    
    1. LEIA a descrição completa da vaga com atenção cirúrgica.
    
    2. IDENTIFIQUE a senioridade REAL (não o título — muitas vagas "Junior" pedem experiência de Pleno).
    
    3. SEPARE requisitos em ESSENCIAIS vs DESEJÁVEIS:
       - Essenciais: aparecem em seções de "Requisitos", "Requirements", "Must-have"
       - Desejáveis: aparecem em "Diferenciais", "Nice-to-have", "Preferred"
       - Se não há seção clara, use o verbo: "deve ter" = essencial, "desejável" = desejável
    
    4. ANALISE O TOM da vaga:
       - Corporativo formal: linguagem institucional, processos estruturados
       - Startup: linguagem casual, "move fast", "ownership"
       - Técnico: foco em stack específica, problemas complexos
    
    5. IDENTIFIQUE GAPS CRÍTICOS comparando com o CV do candidato:
       Perfil do candidato: Junior AI Engineer, Python, LLMs, FastAPI, ML, CrewAI, 
       HPC, Docker, SQL, Pandas. Inglês Intermediário. 1 estágio + projetos pessoais.
    
    6. CALCULE O FIT SCORE honestamente (0-100):
       - <30: Não aplicar (perda de tempo e polui perfil)
       - 30-50: Aplicar apenas se a empresa é muito desejada
       - 50-70: Boa chance com CV bem otimizado
       - >70: Match forte
    
    7. ESCREVA A ESTRATÉGIA para o Redator:
       - Quais experiências destacar e como reframear
       - Que linguagem usar (tom formal vs casual)
       - Quais gaps cobrir com habilidades transferíveis
       - O que NÃO tentar fingir (honestidade estratégica)
    
    REGRA DE OURO: Seja BRUTALMENTE honesto. É melhor não aplicar para uma vaga 
    incompatível do que enviar um CV que será descartado em 5 segundos.""",
    output_schema=JobAnalysisOutput,
)


agente_leitor = Agent(
    name="Leitor de CV",
    model=MODELO_INTELIGENTE,
    description="Lê o currículo base em Markdown e retorna seu conteúdo íntegro.",
    instructions="""You have a single responsibility: to retrieve the content of the base resume.

    REQUIRED STEPS:
    1. IMMEDIATELY activate the `ler_cv_base_md` tool.
    2. Return the content EXACTLY as it was read, without changing a single word.
    3. DO NOT perform any analysis, DO NOT rewrite, DO NOT add comments.

    GOLDEN RULE: Your output must be identical to the read file. Zero creativity here.
    """,
    tools=[ler_cv_base_md],
)

agente_curador_github = Agent(
    name="Curador de Projetos GitHub",
    model=MODELO_INTELIGENTE,
    description="Filtra os repositórios públicos do candidato com base na análise estratégica da vaga.",
    instructions="""Você é um Curador Técnico de Portfólio. Sua função é receber a descrição de uma vaga e acionar a ferramenta extrair_repositorios_github para obter a lista completa de repositórios do candidato.
    
    1. Acione imediatamente a ferramenta `extrair_repositorios_github`.
    2. Avalie rigorosamente quais repositórios têm REAL aderência técnica com os requisitos da vaga.
    3. Escolha no MÁXIMO 2 repositórios que tenham Fit Técnico (ex: se pede Python/FastAPI, escolha projetos com essas linguagens).
    4. Se nenhum projeto tiver relação COM A VAGA, você DEVE retornar APENAS a palavra "VAZIO" (em maiúsculas, sem nenhum outro texto, nem parênteses, nem "nenhum projeto"). NUNCA invente projetos.
    5. Retorne os projetos formatados EXATAMENTE no padrão Markdown do currículo:
       
       ## PROJETOS
       ### NOME DO PROJETO (SEM COLCHETES) — [Repositório](URL do repositório retornado)
       *Desenvolvedor | [Período deduzido ou 'Recente']*
       - [Bullet point 1 focado na tecnologia/arquitetura relevante para a vaga, usando o contexto extraído do README]
       - [Bullet point 2]
    
    REGRA DE OURO: NÃO invente projetos que não estejam no retorno da ferramenta.""",
    tools=[extrair_repositorios_github],
)

agente_redator = Agent(
    name="Redator de CV",
    model=MODELO_INTELIGENTE,
    description="Reescreve o currículo para maximizar relevância para a vaga específica.",
    instructions="""Você é um especialista em Career Coaching e otimização de CVs para o mercado tech.
    
    Você receberá: CONTEÚDO_BASE (CV original), ANÁLISE_ESTRATÉGICA (análise da vaga), 
    TERMOS_ATS (keywords extraídas) e VAGA_ORIGINAL (descrição completa).
    
    REGRA OBRIGATÓRIA DE LAYOUT: Independentemente do formato do CV de entrada, o CV otimizado 
    DEVE seguir exatamente o template padrão definido no sistema. Não altere a estrutura, a ordem 
    das seções, os nomes das seções, nem a formatação. Apenas substitua/adapte o conteúdo textual 
    para incluir os termos ATS identificados na vaga.
    
    === FRAMEWORK DE REESCRITA ===
    
    PASSO 1 — RESUMO PROFISSIONAL (3 linhas máximo):
    - Abra com a identidade profissional alinhada à vaga (não "Analista de Dados" se a vaga é AI Engineer)
    - Mencione 2-3 competências ESSENCIAIS da vaga usando a terminologia EXATA da vaga
    - Feche com um diferencial concreto (ex: "com experiência prática em deploy de LLMs em produção")
    - ADAPTE o tom ao tom da vaga (indicado na ANÁLISE_ESTRATÉGICA)
    
    PASSO 2 — EXPERIÊNCIA (Método CAR: Contexto-Ação-Resultado):
    - Cada bullet point deve seguir: "[Ação com verbo forte] [o que fez] resultando em [impacto observável]"
    - Use APENAS métricas que podem ser inferidas logicamente do trabalho real:
      ✅ "Reduziu dependência de APIs externas implementando LLMs locais" (fato)
      ❌ "Melhorou eficiência em 30%" (número inventado — red flag para recrutadores)
    - RECONTEXTUALIZE experiências para a área da vaga:
      Se a vaga é Supply Chain e o candidato tem experiência com pipelines de dados,
      destaque "automação de pipelines de processamento" não "biologia computacional"
    - Use os VERBOS e SUBSTANTIVOS da vaga (ATS match + linguagem familiar ao recrutador)
    
    PASSO 3 — PROJETOS:
    - O agente curador forneceu os projetos mais relevantes na variável PROJETOS_CURADOS.
    - COPIE E COLE os projetos exatamente como fornecidos, posicionando a seção "## PROJETOS" IMEDIATAMENTE ABAIXO da seção "## EXPERIÊNCIA" (e antes da seção "## FORMAÇÃO").
    - NUNCA INVENTE projetos nem "force" palavras-chave em projetos que não foram fornecidos. Se PROJETOS_CURADOS for "VAZIO" ou não trouxer projetos, NÃO crie a seção "## PROJETOS". Omita-a completamente do texto final. Não escreva "Nenhum projeto".
    - FORMATAÇÃO MÁXIMA: Ao escrever os bullet points (na Experiência e Projetos), garanta que cada `- ` inicie em uma nova linha. NUNCA coloque múltiplos bullet points na mesma linha.
    
    PASSO 4 — HABILIDADES:
    - Técnicas: Liste PRIMEIRO as que aparecem nos requisitos essenciais da vaga
    - Adicione habilidades correlatas reais (não invente)
    - Idiomas: Mantenha o nível real. Se o nível requerido é maior, adicione contexto:
      "Inglês Intermediário (leitura e escrita técnica avançada, documentação diária em inglês)"
    
    === REGRAS INVIOLÁVEIS ===
    
    1. NUNCA invente experiência, certificação, ou métrica que não existe no CONTEÚDO_BASE
    2. NUNCA use "keyword stuffing" — cada skill mencionada DEVE estar justificada por uma experiência
    3. NUNCA exceda 1 página (máximo 400 palavras de conteúdo)
    4. NUNCA use linguagem genérica de IA ("contribuindo para melhorias contínuas", 
       "otimizando processos de forma eficiente") — recrutadores detectam isso instantaneamente
    5. USE pronomes masculinos (o candidato é homem)
    6. MANTENHA formatação ATS-safe: H3, negrito, bullet points simples. Sem tabelas, sem emojis, sem colunas.
    7. Contato SEMPRE centralizado no topo: Nome, Email, Telefone, Local, LinkedIn, GitHub
    8. EVITE SENIORIDADE: Se a vaga pede Senior, não coloque Junior. Foque nas habilidades.
    9. SIGA a ESTRATÉGIA DO ANALISTA fornecida na ANÁLISE_ESTRATÉGICA
    
    === ANTI-PADRÕES (evite a todo custo) ===
    
    ❌ "Profissional com experiência em..." → genérico demais
    ❌ "Contribuindo para melhorias operacionais contínuas" → jargão vazio de IA
    ❌ "Melhorou eficiência em X%" sem base real → métrica inventada
    ❌ "Otimizando processos de forma eficiente" → pleonasmo detectável como IA
    ❌ Listar 15 skills sem contexto → keyword stuffing
    ❌ Copiar verbatim trechos da descrição da vaga → flagrante para recrutador
    
    === PADRÕES POSITIVOS ===
    
    ✅ "Engenheiro de IA com foco em sistemas multi-agentes e deploy de LLMs" → específico
    ✅ "Implementei LLMs locais (Ollama, Llama.cpp) em cluster HPC, eliminando dependência 
        de APIs externas" → fato concreto, tecnologias específicas
    ✅ "Desenvolvi API REST com FastAPI para automação de captação de leads, 
        monitorando interações em tempo real" → ação + resultado observável
    """
)

agente_juiz_ats = Agent(
    name="Juiz de ATS",
    model=MODELO_BUROCRATICO, # Modelos locais são ótimos para isso
    description="Avalia matematicamente a similaridade entre o CV gerado e a vaga.",
    instructions="""Você é o guardião da qualidade. 
    1. Receba o currículo redigido pelo Redator e a Descrição original da Vaga.
    2. Acione a ferramenta `ferramenta_avaliar_score_ats` para obter a nota matemática.
    3. Se o feedback da ferramenta for REPROVADO ou MEDIANO, ordene que o Redator refaça o trabalho.
    4. Se for APROVADO, libere o texto para o agente Copia e Cola.""",
    tools=[tool_avaliar_score_ats]
)

agente_copia_cola = Agent(
    name="Copia e Cola",
    model=MODELO_BUROCRATICO,
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
    model=MODELO_BUROCRATICO,
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
    model = MODELO_BUROCRATICO,
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
    Agora com: análise estratégica, gate de fit score, score semântico,
    e tracking de candidaturas.

    Args:
        termos_ats: Lista de vagas extraídas pelo Playwright.

    Returns:
        Confirmação do pipeline.
    """

    # Lê o CV base UMA VEZ (não precisa ler a cada vaga)
    print("\n📄 Lendo currículo base...")
    resultado_leitura = agente_leitor.run("Leia o currículo base agora.")
    pprint_run_response(resultado_leitura)
    conteudo_base = resultado_leitura.content

    vagas_aplicadas = 0
    vagas_ignoradas = 0

    for idx, termo in enumerate(termos_ats):
        print("="*60)
        print(f"\n[VAGA {idx+1}/{len(termos_ats)}] {termo['title']}")
        print(f"  Empresa: {termo.get('company', 'N/A')}")
        print(f"  URL: {termo['url']}")
        print("="*60)

        # ═══════════════════════════════════════════════════════════
        # ETAPA 0: ANÁLISE ESTRATÉGICA DA VAGA (NOVO!)
        # ═══════════════════════════════════════════════════════════
        print("\n[0/5] 🔍 Análise estratégica da vaga...")
        try:
            analise = analista_vaga.run(f"""
                TÍTULO DA VAGA: {termo['title']}
                EMPRESA: {termo.get('company', 'N/A')}
                LOCALIZAÇÃO: {termo.get('location', 'N/A')}
                
                DESCRIÇÃO COMPLETA:
                {termo['description']}
            """)
            analise_data = analise.content
            
            print(f"  📊 Fit Score: {analise_data.fit_score}%")
            print(f"  🎯 Senioridade: {analise_data.senioridade}")
            print(f"  💼 Área: {analise_data.area_atuacao}")
            print(f"  🏠 Modelo: {analise_data.modelo_trabalho}")
            print(f"  🗣️ Idioma: {analise_data.idioma_requerido}")
            print(f"  🔴 Gaps: {', '.join(analise_data.gaps_criticos) if analise_data.gaps_criticos else 'Nenhum'}")

            # GATE: Não aplicar para vagas com fit < 30
            if analise_data.fit_score < 30:
                print(f"\n  ⏭️ IGNORADA — Fit score muito baixo ({analise_data.fit_score}%)")
                print(f"  Gaps críticos: {', '.join(analise_data.gaps_criticos)}")
                registrar_candidatura(
                    vaga=termo, status="ignorada",
                    fit_score=analise_data.fit_score,
                    motivo=f"Fit {analise_data.fit_score}% - Gaps: {', '.join(analise_data.gaps_criticos)}"
                )
                vagas_ignoradas += 1
                continue
                
        except Exception as e:
            print(f"  ⚠️ Erro na análise estratégica: {str(e)[:60]}")
            print("  Continuando com pipeline padrão...")
            analise_data = None

        # ═══════════════════════════════════════════════════════════
        # ETAPA 1: EXTRAÇÃO DE KEYWORDS (mantém pipeline original)
        # ═══════════════════════════════════════════════════════════
        print(f"\n[1/5] Extraindo keywords ATS...")
        spacy_terms = extract_entities(termo["description"])
        keybert_terms = extrator_keywords_keybert(termo["description"])

        combined = list(set(spacy_terms + keybert_terms))
        cleaned_terms = pre_process_pipeline(combined)

        if not cleaned_terms:
            print("⚠️ Nenhum termo extraído, usando combinados brutos.")
            cleaned_terms = combined

        resultado_classificador = analista_classificador.run(cleaned_terms)
        pprint_run_response(resultado_classificador)

        resultado_ats = analista_ats.run(resultado_classificador.content.termos_corrigidos)
        ats_data = resultado_ats.content

        todas_keywords = (
            ats_data.technical_terms +
            ats_data.soft_skills +
            ats_data.desejaveis
        )

        # FALLBACK: Se a extração falhou completamente, usar requisitos do Analista Estratégico
        if not todas_keywords and analise_data:
            print("⚠️ Extração automática falhou — usando requisitos do Analista Estratégico como fallback")
            todas_keywords = list(set(
                analise_data.requisitos_essenciais +
                analise_data.requisitos_desejaveis
            ))
            print(f"  📋 {len(todas_keywords)} termos recuperados: {', '.join(todas_keywords[:10])}...")

        pprint_run_response(resultado_ats)

        # ═══════════════════════════════════════════════════════════
        # ETAPA 1.5: CURADORIA DINÂMICA DE PROJETOS GITHUB
        # ═══════════════════════════════════════════════════════════
        print("\n[1.5/5] Buscando e curando projetos do GitHub...")
        prompt_curador = f"Vaga: {termo['title']}\nDescrição: {termo['description']}\nAnalise e retorne os projetos mais relevantes."
        resultado_curadoria = agente_curador_github.run(prompt_curador)
        projetos_curados = resultado_curadoria.content
        pprint_run_response(resultado_curadoria)

        # ═══════════════════════════════════════════════════════════
        # ETAPA 2: REDAÇÃO OTIMIZADA (com análise estratégica e curadoria)
        # ═══════════════════════════════════════════════════════════
        print("\n[2/5] Reescrevendo CV para ATS...")

        ats_satisfeito = False
        resultado_redacao = ""
        feedback_do_juiz = ""
        
        termos_formatados = ", ".join(todas_keywords)

        # Monta bloco de análise estratégica para o prompt
        analise_bloco = ""
        if analise_data:
            analise_bloco = f"""
                ANÁLISE_ESTRATÉGICA:
                - Senioridade detectada: {analise_data.senioridade}
                - Área de atuação: {analise_data.area_atuacao}
                - Tom da vaga: {analise_data.tom_da_vaga}
                - Fit Score: {analise_data.fit_score}%
                - Requisitos Essenciais: {', '.join(analise_data.requisitos_essenciais)}
                - Requisitos Desejáveis: {', '.join(analise_data.requisitos_desejaveis)}
                - Habilidades Transferíveis: {', '.join(analise_data.habilidades_transferiveis)}
                - Gaps Críticos: {', '.join(analise_data.gaps_criticos) if analise_data.gaps_criticos else 'Nenhum'}
                - Idioma Requerido: {analise_data.idioma_requerido}
                - ESTRATÉGIA DO ANALISTA: {analise_data.estrategia_cv}
            """

        while not ats_satisfeito:
            prompt_redacao = f"""
                VAGA_ORIGINAL:
                {termo['description']}
                
                {analise_bloco}

                CONTEÚDO_BASE:
                {conteudo_base}

                PROJETOS_CURADOS:
                {projetos_curados}

                TERMOS_ATS EXIGIDOS:
                {termos_formatados}
                """
            
            if feedback_do_juiz and ("REPROVADA" in feedback_do_juiz or "MEDIANO" in feedback_do_juiz):
                prompt_redacao += f"\n\nATENÇÃO! A sua versão anterior foi reprovada pelo algoritmo de ATS. Corrija o currículo baseado neste feedback crítico:\n{feedback_do_juiz}"

            # 1. Redator tenta escrever
            resposta_redacao = agente_redator.run(prompt_redacao)
            texto_cv_gerado = resposta_redacao.content

            # 2. Avaliação com score combinado (keyword + semântico)
            try:
                feedback_ats, score_final = avaliar_score_combinado(
                    cv_text=texto_cv_gerado,
                    keywords=todas_keywords,
                    job_description=termo['description']
                )
            except Exception:
                # Fallback para keyword-only se semântico falhar
                feedback_ats, _ = tool_avaliar_score_ats(cv_text=texto_cv_gerado, keywords=todas_keywords)
                score_final = 0

            print("\n📊 --- RESULTADO DO ALGORITMO ATS ---")
            print(feedback_ats)
            print("------------------------------------\n")

            # 3. Verifica o veredito
            if "REPROVADA" in feedback_ats or "MEDIANO" in feedback_ats:
                print(f"⚠️ O Redator não atingiu o Score necessário. A reiniciar tentativa...")
                feedback_do_juiz = feedback_ats
            else:
                print("✅ O currículo atingiu o Score exigido! A prosseguir...")
                resultado_redacao = texto_cv_gerado 
                ats_satisfeito = True


        redacao = extrair_bloco_markdown(resultado_redacao)  # Limpa o output para pegar só o markdown

        # ═══════════════════════════════════════════════════════════
        # ETAPA 3: SALVAR E CONVERTER
        # ═══════════════════════════════════════════════════════════
        print("\n[3/5] Salvando CV otimizado...")
        resultado_md = agente_copia_cola.run(f"Pegue o nome da vaga {termo['title']} e o conteúdo {redacao}")
        pprint_run_response(resultado_md)
        nome_arquivo = resultado_md.content

        print("\n[4/5] Convertendo para PDF...")
        prompt_conversao = f"Converta o arquivo '{nome_arquivo}' para PDF agora."
        resultado_conversao = agente_conversor.run(prompt_conversao)

        print(f"\n✅ PDF gerado: {resultado_conversao.content}")

        # ═══════════════════════════════════════════════════════════
        # ETAPA 4: ENVIO
        # ═══════════════════════════════════════════════════════════
        print("\n[5/5] Acionando o Agente de Envio...")
        prompt_envio = f"Envie o arquivo '{resultado_conversao.content}' para a vaga {termo['url']}."
        print(prompt_envio)
        agente_envio.run(prompt_envio)

        # Registra candidatura no tracking
        registrar_candidatura(
            vaga=termo,
            status="enviada",
            cv_usado=str(nome_arquivo),
            fit_score=analise_data.fit_score if analise_data else None
        )
        vagas_aplicadas += 1

    # ═══════════════════════════════════════════════════════════
    # RELATÓRIO FINAL
    # ═══════════════════════════════════════════════════════════
    print("\n" + "="*60)
    print("✅ PIPELINE CONCLUÍDO")
    print(f"  Vagas processadas: {len(termos_ats)}")
    print(f"  Candidaturas enviadas: {vagas_aplicadas}")
    print(f"  Vagas ignoradas (fit baixo): {vagas_ignoradas}")
    print("="*60)

    # Exibe relatório acumulado
    print(gerar_relatorio())

if __name__ == "__main__":
    print("Iniciando o pipeline de otimização de currículo...\n")
    pipeline_cv(termos_ats=vagas_escolhidas)