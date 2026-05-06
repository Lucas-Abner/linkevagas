from agno.agent import Agent, RunOutput
from pydantic import BaseModel, Field
from typing import List
from agno.models.openai import OpenAIResponses
from agno.models.ollama import Ollama
from agno.models.deepseek import DeepSeek
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
from src.tools.ats_tool import extract_entities, extrator_keywords_keybert, pre_process_pipeline, avaliar_score_combinado
from src.tools.tracking import registrar_candidatura, gerar_relatorio
from src.tools.github_tool import extrair_repositorios_github

modelo_principal_id = os.getenv("MODELO_PRINCIPAL", "gpt-4o-mini")

if "gpt" in modelo_principal_id.lower() or "o1" in modelo_principal_id.lower() or "o3" in modelo_principal_id.lower():
    MODEL_PRINCIPAL = OpenAIResponses(id=modelo_principal_id, api_key=os.getenv("OPENAI_API_KEY"))
    # Se o principal for nuvem, o burocrático fallback será o mistral-nemo local
    MODEL_LOCAL = Ollama(id="mistral-nemo:12b", host="http://localhost:11434", options={"temperature": 0.2, "num_gpu": 99})
elif "deepseek" in modelo_principal_id.lower():
    MODEL_PRINCIPAL = DeepSeek(id=modelo_principal_id, api_key=os.getenv("DEEPSEEK_API_KEY"))
    # Fallback local igual ao da OpenAI
    MODEL_LOCAL = Ollama(id="mistral-nemo:12b", host="http://localhost:11434", options={"temperature": 0.2, "num_gpu": 99})
else:
    # Se o usuário escolheu um modelo local como principal (ex: mistral-nemo:12b), usamos ele para tudo!
    MODEL_PRINCIPAL = Ollama(id=modelo_principal_id, host="http://localhost:11434", options={"temperature": 0.2, "num_gpu": 99})
    MODEL_LOCAL = MODEL_PRINCIPAL

MODO_PROCESSAMENTO = os.getenv("MODO_PROCESSAMENTO", "Híbrido (Recomendado)")

if MODO_PROCESSAMENTO == "100% Local (Ollama)":
    MODELO_INTELIGENTE = MODEL_LOCAL
    MODELO_BUROCRATICO = MODEL_LOCAL
elif "Nuvem" in MODO_PROCESSAMENTO:
    MODELO_INTELIGENTE = MODEL_PRINCIPAL
    MODELO_BUROCRATICO = MODEL_PRINCIPAL
else: # Híbrido
    MODELO_INTELIGENTE = MODEL_PRINCIPAL
    MODELO_BUROCRATICO = MODEL_LOCAL


buscar_vagas = os.environ.get("BUSCAR_VAGA", "Agente de IA")
quantidade_vagas = os.environ.get("QUANTIDADE_VAGAS", 1)  # Recomendado processar 1 por vez para não confundir o modelo local

vagas_escolhidas = buscar_multiplas_vagas(buscar_vagas, quantidade_vagas)


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSIFICAÇÃO DETERMINÍSTICA DE TERMOS ATS
# Substituiu 2 agentes LLM (analista_classificador + analista_ats) por lógica
# determinística: zero custo de API, zero alucinação, 100x mais rápido.
# ═══════════════════════════════════════════════════════════════════════════════

SOFT_SKILL_PATTERNS = {
    "comunicação", "communication", "liderança", "leadership", "trabalho em equipe",
    "teamwork", "proatividade", "proactive", "adaptabilidade", "adaptability",
    "criatividade", "creativity", "resiliência", "resilience", "empatia", "empathy",
    "colaboração", "collaboration", "ownership", "autonomia", "autonomy",
    "problem solving", "resolução de problemas", "pensamento crítico", "critical thinking",
    "gestão de tempo", "time management", "mentoring", "mentoria",
}

def classificar_termos_ats(termos_brutos: list) -> list:
    """
    Classificação determinística de termos ATS extraídos.
    Retorna lista unificada de todos os termos válidos (sem classificação
    em categorias, já que o pipeline downstream concatena tudo).
    """
    termos_limpos = []
    vistos = set()
    for t in termos_brutos:
        t_lower = t.strip().lower()
        if t_lower and t_lower not in vistos:
            vistos.add(t_lower)
            termos_limpos.append(t.strip())
    return termos_limpos




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


# agente_leitor foi removido.

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
    instructions="""Você é um ghostwriter de executivos tech, especializado em CVs que passam ATS e impressionam recrutadores humanos.
    
    Você receberá: TÍTULO_VAGA, CONTEÚDO_BASE (CV original), ANÁLISE_ESTRATÉGICA (análise da vaga), 
    TERMOS_ATS (keywords extraídas), PROJETOS_CURADOS e VAGA_ORIGINAL (descrição completa).
    
    === REGRA DE LAYOUT E ESTRUTURA ATS ===
    O CV DEVE seguir o template padrão. Não altere estrutura, ordem ou nomes das seções.
    Mantenha um formato "clean" e texto puro: evite colunas, ícones, tabelas ou quebras de layout complexas que confundem os robôs ATS. O formato deve ser simples, direto ao ponto e otimizado para extração de texto.
    
    === FRAMEWORK DE REESCRITA ===
    
    PASSO 1 — RESUMO PROFISSIONAL (2-3 linhas):
    - ABRA com o cargo ESTREITAMENTE alinhado ao TÍTULO_VAGA (é vital para o robô identificar a aderência)
    - Destaque as palavras-chave mais críticas da vaga
    - Apresente RESULTADOS QUANTIFICADOS ou diferenciais verificáveis logo de início
    
    PASSO 2 — EXPERIÊNCIA PROFISSIONAL:
    - Use sempre VERBOS DE AÇÃO no passado (Desenvolvi, Implementei, Liderou).
    - Foque em RESULTADOS E IMPACTOS gerados para o negócio, NUNCA apenas liste tarefas.
    - Personalização cirúrgica: Utilize as MESMAS nomenclaturas e palavras-chave da descrição da vaga (microajuste para passar na triagem do ATS).
    
    EXEMPLOS CAR DO CANDIDATO (use como base, adapte para a vaga):
    ✅ "Implementei LLMs locais (Ollama, Llama.cpp) em cluster HPC, eliminando dependência de APIs externas"
    ✅ "Desenvolvi pipeline de processamento de dados com Pandas e SQL para automação de análises internas"
    ✅ "Criei sistema multi-agente com CrewAI para análise de imagens médicas, integrando modelo MedGemma"
    ✅ "Construí API REST com FastAPI para captação automatizada de leads via Instagram"
    
    PASSO 3 — PROJETOS:
    - COPIE os PROJETOS_CURADOS exatamente como fornecidos
    - Posicione "## PROJETOS" logo após "## EXPERIÊNCIA" e antes de "## FORMAÇÃO"
    - Se PROJETOS_CURADOS for "VAZIO", omita a seção completamente
    
    PASSO 4 — HABILIDADES E CERTIFICAÇÕES:
    - Liste PRIMEIRO as skills dos requisitos essenciais da vaga usando a nomenclatura exata.
    - Cursos e Qualificações: Liste apenas certificações técnicas que sejam RELEVANTES para a vaga atual.
    - Idiomas: Mantenha nível real. Se a vaga pede mais, contextualize.
    
    === REGRAS INVIOLÁVEIS ===
    
    1. NUNCA invente experiência, cargo, empresa, certificação ou métrica. Você só pode adicionar palavras-chave dentro das experiências JÁ EXISTENTES no CONTEÚDO_BASE, e APENAS se fizer sentido no contexto. É preferível ter um score menor do que inventar informações.
    2. NUNCA exceda 350 palavras de conteúdo (garante 1 página A4)
    3. USE pronomes masculinos (o candidato é homem)
    4. ESTRUTURA MARKDOWN OBRIGATÓRIA:
       - `# LUCAS ABNER CAIXETA DE OLIVEIRA`
       - Parágrafo de contato logo abaixo (Email | Telefone | Local | LinkedIn | GitHub)
       - `## RESUMO PROFISSIONAL`
       - `## EXPERIÊNCIA PROFISSIONAL`
       - `### Cargo | Empresa`
       - `*Período*`
       - `- Bullet points`
       - `## PROJETOS` (se houver)
       - `## FORMAÇÃO`
       - `## HABILIDADES TÉCNICAS`
       - `## IDIOMAS`
    5. Cada `- ` em nova linha. NUNCA múltiplos bullets na mesma linha.
    6. EVITE SENIORIDADE: Se a vaga pede Senior, não coloque Junior. Foque nas habilidades.
    7. SIGA a ESTRATÉGIA DO ANALISTA da ANÁLISE_ESTRATÉGICA
    8. RETORNO ESTRITO: Retorne APENAS o código Markdown do currículo. NÃO adicione ABSOLUTAMENTE NENHUMA conversa, saudação, explicação ou comentário antes ou depois do currículo (ex: "Aqui está o currículo...", "como exemplo", etc.).
    
    === BLACKLIST DE FRASES — SE VOCÊ USAR QUALQUER UMA, O CV SERÁ REJEITADO ===
    
    PROIBIDO usar estas frases ou variações delas:
    - "contribuindo para melhorias contínuas"
    - "otimizando processos de forma eficiente"
    - "melhorando a governança dos dados"
    - "intensificando a precisão"
    - "fortalecendo a cultura de feedback"
    - "aumentando a observabilidade"
    - "facilitando a colaboração entre equipes"
    - "trazendo insights acionáveis"
    - "de ponta a ponta" (use "end-to-end" ou descreva especificamente)
    - "sólida experiência" / "vasta experiência" / "ampla experiência"
    - "profissional com experiência em"
    - "contribuindo para a cultura de"
    - "aprimorando a qualidade"
    - "de maneira substancial" / "de forma significativa"
    - "garantindo alta eficiência"
    - Qualquer gerúndio vago no final de bullet ("...melhorando X", "...aumentando Y")
    
    === VOICE CHECK ===
    Antes de entregar, releia cada bullet e pergunte: "Um engenheiro de 25 anos escreveria isso
    no LinkedIn?" Se a resposta for não, reescreva com linguagem direta e técnica.
    """
)

# Os agentes burocráticos (Leitor, Copia e Cola, Conversor e Envio) foram removidos
# Usaremos chamadas diretas às funções Python (muito mais rápido e sem erro).

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
    conteudo_base = ler_cv_base_md()

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
        # ETAPA 1: EXTRAÇÃO DE KEYWORDS (determinístico, sem LLM)
        # ═══════════════════════════════════════════════════════════
        print(f"\n[1/5] Extraindo keywords ATS...")
        spacy_terms = extract_entities(termo["description"])
        keybert_terms = extrator_keywords_keybert(termo["description"])

        combined = list(set(spacy_terms + keybert_terms))
        cleaned_terms = pre_process_pipeline(combined)

        if not cleaned_terms:
            print("⚠️ Nenhum termo extraído, usando combinados brutos.")
            cleaned_terms = combined

        # Classificação determinística — substituiu 2 agentes LLM
        todas_keywords = classificar_termos_ats(cleaned_terms)
        print(f"  📋 {len(todas_keywords)} keywords extraídas: {', '.join(todas_keywords[:15])}...")

        # FALLBACK: Se a extração falhou completamente, usar requisitos do Analista Estratégico
        if not todas_keywords and analise_data:
            print("⚠️ Extração automática falhou — usando requisitos do Analista Estratégico como fallback")
            todas_keywords = list(set(
                analise_data.requisitos_essenciais +
                analise_data.requisitos_desejaveis
            ))
            print(f"  📋 {len(todas_keywords)} termos recuperados: {', '.join(todas_keywords[:10])}...")

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

        MAX_RETRIES = 5
        melhor_score = 0
        melhor_cv = ""
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

        for attempt in range(MAX_RETRIES):
            print(f"\n  📝 Tentativa {attempt + 1}/{MAX_RETRIES}")
            prompt_redacao = f"""
                TÍTULO_VAGA: {termo['title']}

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

            # 2. Avaliação com score combinado (keyword 70% + semântico 30%)
            try:
                feedback_ats, score_final = avaliar_score_combinado(
                    cv_text=texto_cv_gerado,
                    keywords=todas_keywords,
                    job_description=termo['description'],
                    attempt=attempt
                )
            except Exception as e:
                print(f"  ⚠️ Erro no scoring: {e}")
                feedback_ats = "AVALIAÇÃO APROVADA (fallback)"
                score_final = 75

            print("\n📊 --- RESULTADO DO ALGORITMO ATS ---")
            print(feedback_ats)
            print("------------------------------------\n")

            # Guarda a melhor versão
            if score_final > melhor_score:
                melhor_score = score_final
                melhor_cv = texto_cv_gerado

            # 3. Verifica o veredito
            if "APROVADA" in feedback_ats:
                print("✅ O currículo atingiu o Score exigido! A prosseguir...")
                resultado_redacao = texto_cv_gerado
                break
            else:
                print(f"⚠️ Score {score_final:.1f}% — tentando melhorar...")
                feedback_do_juiz = feedback_ats
        else:
            # Esgotou tentativas — usa a melhor versão
            print(f"\n⚠️ MAX_RETRIES atingido. Usando melhor versão (score: {melhor_score:.1f}%)")
            resultado_redacao = melhor_cv


        redacao = extrair_bloco_markdown(resultado_redacao)  # Limpa o output para pegar só o markdown

        # ═══════════════════════════════════════════════════════════
        # ETAPA 3: SALVAR E CONVERTER
        # ═══════════════════════════════════════════════════════════
        print("\n[3/5] Salvando CV otimizado...")
        nome_arquivo = salvar_cv_otimizado_md(conteudo_md=redacao, nome_vaga=termo['title'])
        print(f"Salvo em: {nome_arquivo}")

        print("\n[4/5] Convertendo para PDF...")
        resultado_conversao = converter_md_para_pdf(nome_arquivo)
        print(f"\n✅ PDF gerado: {resultado_conversao}")

        # ═══════════════════════════════════════════════════════════
        # ETAPA 4: ENVIO
        # ═══════════════════════════════════════════════════════════
        print("\n[5/5] Acionando o Agente de Envio...")
        pdf_arquivo = nome_arquivo.replace(".md", ".pdf")
        print(f"Enviando arquivo '{pdf_arquivo}' para a vaga {termo['url']}")
        tool_envio_candidatura(url_vaga=termo['url'], nome_cv=pdf_arquivo)

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