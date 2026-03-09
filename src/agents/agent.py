from agno.agent import Agent, RunOutput
from pydantic import BaseModel, Field
from typing import List
from agno.models.ollama import Ollama
from ..tools.playwright_tool import buscar_multiplas_vagas 

buscar_vagas = "engenheiro de IA"
quantidade_vagas = 5

class ATSExtract(BaseModel):
    hard_skills: List[str] = Field(description="Tecnologias e ferramentas")
    soft_skills: List[str] = Field(description="Habilidades comportamentais")
    keywords_chave: List[str] = Field(description="Termos específicos que o ATS busca")


analista_vaga = Agent(
    model= Ollama(id="qwen2.5:7b", host="http://localhost:11434"),
    description="Analista de Vagas de Emprego",
    instructions=f"Você é um analista de vagas de emprego. Sua tarefa é chamar a ferramenta buscar_multiplas_vagas para buscar as vagas, analisar a descrição de uma vaga e extrair as hard skills, soft skills e palavras-chave que são relevantes para um sistema de rastreamento de candidatos (ATS). Deve passar como parametro {buscar_vagas} e a quantidade de {quantidade_vagas} vagas.",
    expected_output=("O output deve ser um JSON com as seguintes chaves: hard_skills, soft_skills e keywords_chave. Cada chave deve conter uma lista de strings correspondentes às habilidades e palavras-chave extraídas da descrição da vaga."),
    # output_schema=ATSExtract,
    tool_call_limit=1,
    tools=[buscar_multiplas_vagas],
)

def main() -> None:
    analista_resp = analista_vaga.print_response(
        "Chame a ferramenta buscar_multiplas_vagas analise a descrição da vaga e extraia as hard skills, soft skills e palavras-chave relevantes para um sistema de rastreamento de candidatos (ATS)."
    )
    print(analista_resp)


if __name__ == "__main__":
    main()