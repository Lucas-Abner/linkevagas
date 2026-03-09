from agno.agent import Agent, RunOutput
from pydantic import BaseModel, Field
from typing import List
from agno.models.ollama import Ollama
from agno.utils.pprint import pprint_run_response
from src.tools.playwright_tool import buscar_multiplas_vagas
from src.tools.cv_tool import tool_pdf_cv_reader

buscar_vagas = "agentes IA"
quantidade_vagas = 2

class ATSExtract(BaseModel):
    hard_skills: List[str] = Field(description="Tecnologias e ferramentas")
    soft_skills: List[str] = Field(description="Habilidades comportamentais")
    keywords_chave: List[str] = Field(description="Termos específicos que o ATS busca")
    desejaveis: List[str] = Field(description="Habilidades ou qualificações que são desejáveis, mas não obrigatórias")

class AnaliseRHOutput(BaseModel):
    areas_acordo: List[str] = Field(description="Áreas do currículo que estão de acordo com as exigências da vaga")
    areas_destacar: List[str] = Field(description="Áreas do currículo que devem ser destacadas para chamar a atenção dos recrutadores")
    areas_melhoria: List[str] = Field(description="Áreas do currículo que precisam de melhorias")
    sugestoes_ajustes: List[str] = Field(description="Sugestões específicas para ajustar o currículo e aumentar as chances de aprovação")



vagas_escolhidas = buscar_multiplas_vagas(buscar_vagas, quantidade_vagas)
descricao_cv = tool_pdf_cv_reader("/home/lucas.abner/Documentos/code/linkevagas/Lucas_Abner_Caixeta_CV_AI_Engineer_Jr.pdf")

analista_ats = Agent(
    name="Analista de ATS",
    model=Ollama(id="qwen2.5:7b", host="http://localhost:11434"),
    description="Analisa descrições de vagas e extrai hard skills, soft skills e keywords chave para otimizar currículos.",
    instructions=f"Você é um analista de ATS especializado em otimizar currículos para vagas de {buscar_vagas}. Analise as descrições das vagas e extraia as hard skills, soft skills, keywords e desejaveis mais relevantes. Se houver campo de desejaveis ou na descrição tiver a palavra **ou**, acrescente na lista de 'desejaveis'. Use o pydantic para formatar os resultados.",
    expected_output="Use o modelo ATSExtract para formatar a resposta, preenchendo as listas de hard_skills, soft_skills e keywords_chave com base nas descrições das vagas extraídas.",
    output_schema=ATSExtract
)

rh_analist = Agent(
    name="Analista de RH",
    model=Ollama(id="llama3.1:8b", host="http://localhost:11434"),
    description="Analisa descrições de vagas e extrai hard skills, soft skills e keywords chave para otimizar currículos.",
    instructions=f"Você é um analista de RH especializado em otimizar currículos para vagas de {buscar_vagas}. Faça uma comparação entre as informações extraidas pelo analista ATS e o curriculo do candidato, destacando as áreas de melhoria e sugerindo ajustes para aumentar as chances de aprovação no processo seletivo. **{descricao_cv}**",
    expected_output="Use uma estrutura clara para apresentar as áreas de melhoria, como um relatório ou uma lista de sugestões, destacando quais hard skills, soft skills e keywords chave estão faltando ou precisam ser reforçadas no currículo do candidato em relação às exigências da vaga.",
    output_schema=AnaliseRHOutput
)


if __name__ == "__main__":
    resultado = analista_ats.run(vagas_escolhidas[0]["descricao"])
    print("Resultados extraidos")
    
    print("\nTítulo da vaga analisada:")
    print(vagas_escolhidas[0]["titulo"])
    print("\nDescrição da vaga analisada:")
    print(vagas_escolhidas[0]["descricao"])

    print("\nAnálise do ATS:")
    pprint_run_response(resultado)

    analise_feita = rh_analist.run(f"Análise ATS:\n{resultado.content}\n\nCurrículo do candidato:\n{descricao_cv}")
    print("\nAnálise do RH:")
    pprint_run_response(analise_feita)
