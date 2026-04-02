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
from src.tools.ats_tool import tool_avaliar_score_ats, extract_entities, extrator_keywords_keybert, pre_process_pipeline


MODEL_GPT = OpenAIResponses(id=os.getenv("MODELO_PRINCIPAL", "gpt-4o-mini"), api_key=os.getenv("OPENAI_API_KEY"))  # Configuração para GPT-4.1 mini
MODEL_OLLAMA_QWEN2 = Ollama(id="qwen2.5:7b", host="http://localhost:11434", options={"temperature": 0.7, "num_gpu": 99})
MODEL_OLLAMA_QWEN3 = Ollama(id="qwen3.5:4b", host="http://localhost:11434", options={"temperature": 0.7, "num_gpu": 99})
MODEL_GPT_OPEN = OpenAIResponses(id=os.getenv("MODELO_GPT_OPEN", "openai/gpt-oss-20b"), api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")  # Configuração para GPT-4.1 mini


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


analista_classificador = Agent(
    name="ATS Hard Skills Extractor",
    # model=Ollama(id="qwen2.5:7b", host="http://localhost:11434", options={"temperature": 0.0, "num_gpu": 99}),
    model=MODEL_GPT,
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
    # model=Ollama(id="qwen2.5:7b", host="http://localhost:11434", options={"temperature": 0.0, "num_gpu": 99}),
    model=MODEL_GPT,
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


agente_leitor = Agent(
    name="Leitor de CV",
    model=MODEL_GPT,
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

agente_redator = Agent(
    name="Redator de CV",
    model=MODEL_GPT,
    description="Reescreve o currículo base para otimização ATS, seguindo as regras de formatação e estratégia.",
    # additional_input=support_format_cv, # Restaurando o suporte de formato!
    instructions=f"""
    Você recebe insumos via prompt: CONTEÚDO_BASE e TERMOS_ATS.
    
    PASSOS OBRIGATÓRIOS PARA OTIMIZAÇÃO ATS:
    1. MATCH EXATO DE PALAVRAS-CHAVE: Ao adicionar ferramentas aos requisitos, use a grafia EXATA extraída pela análise da vaga.
    2. RESUMO PROFISSIONAL: Incorpore os termos técnicos e soft skills mais importantes da vaga de forma natural nas três primeiras linhas.
    3. FÓRMULA XYZ NA EXPERIÊNCIA: Reescreva as descrições de experiência e projetos utilizando a estrutura: "Realizei [Ação/Projeto] medido por [Métrica/Impacto] utilizando [Tecnologias ATS]". 
    4. FORMATAÇÃO CLEAN PARA ATS: Use APENAS cabeçalhos (H3 e Negrito), textos simples e bullet points clássicos (- ou *). NUNCA use tabelas ou caracteres complexos.
    5. EVITE SENIORIDADE: Se a vaga pede Senior, não coloque Junior. Foque em destacar as habilidades e experiências que provam que o candidato é apto para a vaga, sem mencionar níveis de senioridade.
    6. ADICIONE VALOR: Mostre que os projetos e experiências trouxeram resultados concretos, usando números e métricas sempre que possível. Isso é mais importante do que simplesmente listar responsabilidades.
    7. FALE A MESMA LINGUAGEM DA VAGA: Se a vaga enfatiza certas habilidades ou termos, certifique-se de que eles estejam presentes no currículo de forma natural. O objetivo é passar pelo filtro do ATS, então a correspondência de palavras-chave é crucial.
    8. NÃO SE ESQUEÇA: Eu sou homem, então use pronomes masculinos. Mantenha a essência do meu perfil, mas otimize para a vaga.

    REGRAS DE ESTRATÉGIA ATS (EVITAR KEYWORD STUFFING E GAPS):
    1. TRADUÇÃO DE HABILIDADES TRANSFERÍVEIS: Se a vaga pedir ferramentas específicas que não estão no CONTEÚDO_BASE, NÃO minta. Reescreva a experiência destacando as bases técnicas que provam que o candidato pode aprender essas ferramentas rápido.
    2. PROIBIÇÃO DE 'KEYWORD STUFFING': Não crie listas de "Skills" com palavras da vaga que não estejam justificadas nas experiências profissionais com a Fórmula XYZ.
    3. SINCERIDADE ESTRATÉGICA: Se a vaga exige níveis específicos de idiomas (ex: Inglês C1), mantenha o nível real do candidato, mas adicione contexto de uso prático (ex: "Leitura técnica avançada").
    4. FOCO NO DOMÍNIO DA VAGA: Reduza o destaque de projetos acadêmicos e foque na arquitetura técnica que mais se assemelha à vaga.
    5. NUNCA, NUNCA MESMO, invente experiências ou habilidades. Se algo não está no CONTEÚDO_BASE, reescreva a experiência mais próxima de forma convincente, mas sem mentir. A honestidade é a melhor política para evitar reprovações por ATS.
    6. MANTENHA A ESSÊNCIA DO CANDIDATO: O objetivo é otimizar o currículo para passar pelo ATS, mas sem perder a autenticidade do candidato. O CV deve parecer uma evolução natural do conteúdo base, não uma versão fabricada.
    7. REGRA DE TAMANHO (1 PÁGINA): O currículo DEVE obrigatoriamente caber numa única página. Para isso, seja extremamente conciso. Use no máximo 3 a 4 bullet points curtos por experiência. Remova adjetivos desnecessários e vá direto ao ponto métrico. O texto inteiro não deve ultrapassar 350 palavras.
    """
)

agente_juiz_ats = Agent(
    name="Juiz de ATS",
    model=MODEL_OLLAMA_QWEN2, # Modelos locais são ótimos para isso
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
    model=MODEL_OLLAMA_QWEN2,
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
    model=MODEL_OLLAMA_QWEN2,
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
    model = MODEL_OLLAMA_QWEN2,
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
        print(f"\n[1/5] Analisando a Vaga: {termo['title']}\n URL: {termo['url']}")
        spacy_terms = extract_entities(termo["description"])
        keybert_terms = extrator_keywords_keybert(termo["description"])
        print("DEBUG: Termos Spacy:", spacy_terms)
        print("DEBUG: Termos KeyBERT:", keybert_terms)

        combined = list(set(spacy_terms + keybert_terms))
        print("DEBUG: Termos combinados:", combined)

        cleaned_terms = pre_process_pipeline(combined) # Limpeza prévia para remover ruídos óbvios antes de passar para o agente

        if not cleaned_terms:
            print("⚠️ ATENÇÃO: Nenhum termo técnico relevante foi extraído da vaga. O pipeline continuará, mas a otimização ATS pode ser prejudicada.")
            cleaned_terms = combined # Se não sobrar nada, tenta mandar o combined para o LLM mesmo

        print("Termos extraídos:", cleaned_terms)

        resultado_classificador = analista_classificador.run(cleaned_terms)
        pprint_run_response(resultado_classificador)

        resultado_ats = analista_ats.run(resultado_classificador.content.termos_corrigidos)
        ats_data = resultado_ats.content

        todas_keywords = (
            ats_data.technical_terms +
            ats_data.soft_skills +
            ats_data.desejaveis
        )

        pprint_run_response(resultado_ats)
        print("\n[2/5] Acionando o Agente Redator...")
        # O comando inicial que dá o gatilho para a IA trabalhar sozinha
        resultado_leitura = agente_leitor.run("Leia o currículo base agora.")
        pprint_run_response(resultado_leitura)
        conteudo_base = resultado_leitura.content

        # ETAPA 2: Redação otimizada
        print("\n[3/5] Reescrevendo CV para ATS...")

        ats_satisfeito = False
        resultado_redacao = ""
        feedback_do_juiz = "" 
        
        # Extrai as listas do objeto Pydantic
        termos_formatados = ", ".join(todas_keywords) # Transforma em texto para o Redator ler

        while not ats_satisfeito:
            prompt_redacao = f"""
                VAGA_ORIGINAL:
                {termo['description']}

                CONTEÚDO_BASE:
                {conteudo_base}

                TERMOS_ATS EXIGIDOS:
                {termos_formatados}
                """
            
            if feedback_do_juiz and ("REPROVADA" in feedback_do_juiz or "MEDIANO" in feedback_do_juiz):
                prompt_redacao += f"\n\nATENÇÃO! A sua versão anterior foi reprovada pelo algoritmo de ATS. Corrija o currículo baseado neste feedback crítico:\n{feedback_do_juiz}"

            # 1. Redator tenta escrever
            resposta_redacao = agente_redator.run(prompt_redacao)
            texto_cv_gerado = resposta_redacao.content

            counter = 0

            # 2. Avaliação Matemática (passando a lista diretamente!)
            feedback_ats, counter = tool_avaliar_score_ats(cv_text=texto_cv_gerado, keywords=todas_keywords, count=counter)

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

        resultado_md = agente_copia_cola.run(f"Pegue o nome da vaga {termo['title']} e o conteúdo {redacao}")
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
    # print(vagas_escolhidas[-1]["description"])