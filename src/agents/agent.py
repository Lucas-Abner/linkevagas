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
from src.tools.ats_tool import tool_avaliar_score_ats


MODEL_GPT = OpenAIResponses(id=os.getenv("MODELO_PRINCIPAL", "gpt-4o-mini"), api_key=os.getenv("OPENAI_API_KEY"))  # Configuração para GPT-4.1 mini
MODEL_OLLAMA_QWEN2 = Ollama(id="qwen2.5:7b", host="http://localhost:11434", options={"temperature": 0.7, "num_gpu": 99})
MODEL_OLLAMA_QWEN3 = Ollama(id="qwen3.5:4b", host="http://localhost:11434", options={"temperature": 0.7, "num_gpu": 99})
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
    model=MODEL_OLLAMA_QWEN2,
    description="Extrai palavras-chave de vagas em formato JSON estruturado.",
    instructions=f"""
<task>
Leia o texto da vaga abaixo e extraia palavras-chave para cada categoria do schema JSON.
A vaga pode estar em português ou inglês. Copie os termos NO IDIOMA ORIGINAL da vaga.
</task>

<vaga>
{buscar_vagas}
</vaga>

<rules>
REGRA 1 — Pense passo a passo antes de preencher cada campo:
  (a) Leia toda a vaga uma vez.
  (b) Para cada termo encontrado, decida em qual categoria ele se encaixa.
  (c) Preencha o schema apenas com termos que você encontrou no texto.

REGRA 2 — Cada categoria aceita APENAS estes tipos de termos:

  technical_terms → Ferramentas, linguagens, frameworks, plataformas, protocolos.
    ACEITO: Python, Linux, Bash, REST API, LLMs, Docker, SQL, Git
    RECUSADO: qualquer frase com verbo (ex: "desenvolver sistemas", "trabalhar com")

  soft_skills → Habilidades comportamentais, mentais ou de comunicação.
    ACEITO: attention to detail, problem-solving, analytical skills, teamwork
    RECUSADO: nomes de tecnologias, linguagens ou ferramentas

  desejaveis → Termos das seções "Nice to Have", "Preferred", "Diferencial" ou "Plus".
    ACEITO: RLHF, SFT, CI/CD, browser automation
    RECUSADO: requisitos marcados como obrigatórios

REGRA 3 — Formato dos termos:
  - Entre 1 e 3 palavras por termo.
  - Sem pontuação extra, sem frases longas.
  - Se uma categoria não tiver nenhum termo na vaga, retorne lista vazia [].
</rules>

<output_instructions>
Retorne APENAS o JSON preenchido, sem texto antes ou depois.
Não adicione explicações, comentários ou markdown.
</output_instructions>
""",
    expected_output="""JSON válido preenchendo todos os campos do schema ATSExtract.
Exemplo de saída esperada:
{
  "technical_terms": ["Python", "Linux", "REST API"],
  "soft_skills": ["problem-solving", "attention to detail"],
  "desejaveis": ["RLHF", "CI/CD"]
}""",
    output_schema=ATSExtract
)

agente_leitor = Agent(
    name="Leitor de CV",
    model=MODEL_OLLAMA_QWEN2,
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
        print(f"Breve descrição: {termo['description'][:300]}...\n")
        resultado_ats = analista_ats.run(termo["description"])
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
        palavras_chave_vaga = resultado_ats.content.technical_terms + resultado_ats.content.desejaveis
        termos_formatados = ", ".join(palavras_chave_vaga) # Transforma em texto para o Redator ler

        while not ats_satisfeito:
            prompt_redacao = f"""
                VAGA_ORIGINAL:
                {termo['description']}

                CONTEÚDO_BASE:
                {conteudo_base}

                TERMOS_ATS EXIGIDOS:
                {termos_formatados}
                """
            
            if feedback_do_juiz:
                prompt_redacao += f"\n\nATENÇÃO! A sua versão anterior foi reprovada pelo algoritmo de ATS. Corrija o currículo baseado neste feedback crítico:\n{feedback_do_juiz}"

            # 1. Redator tenta escrever
            resposta_redacao = agente_redator.run(prompt_redacao)
            texto_cv_gerado = resposta_redacao.content

            # 2. Avaliação Matemática (passando a lista diretamente!)
            resultado_matematico = tool_avaliar_score_ats(cv_text=texto_cv_gerado, keywords=palavras_chave_vaga)
            
            print("\n📊 --- RESULTADO DO ALGORITMO ATS ---")
            print(resultado_matematico)
            print("------------------------------------\n")

            # 3. Verifica o veredito
            if "REPROVADA" in resultado_matematico or "MEDIANO" in resultado_matematico:
                print(f"⚠️ O Redator não atingiu o Score necessário. A reiniciar tentativa...")
                feedback_do_juiz = resultado_matematico 
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