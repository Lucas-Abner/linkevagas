from agno.agent import Agent
from agno.models.ollama import Ollama
from pathlib import Path
import os

filee = Path(__file__).parent / 'analise.py'

llm = Ollama(id="qwen2.5:7b", host='http://localhost:11434')

def ver_codigo(caminho: str | None = filee):
    with open(caminho, 'r', encoding='utf-8') as f:
        return f.read()

def dev_codigo(caminho: str | None = filee, conteudo: str | None = None):

    with open(caminho, 'w', encoding='utf-8') as f:
        return f.write(conteudo)

agent = Agent(
    name='Desenvolvedor',
    model=llm,
    role='Desenvolvedor de IA/ML com experiencia em desenvolvimento de modelos de machine learning tradicional',
    instructions='''
    Usando sua expertise no desenvolvimento de modelos ML tradicional, seu objetivo é analisar dados e 
    desenvolver codigos em python limpos e coesos para implementar modelos de ML.

    Irei destacar as tools e as descrições entre "<<" e ">>".

    Você deve fazer o processo de EDA, tratamento de dados, normalização dos dados, transformação e desenvolver modelos
    que podem ser de regressão, classificação, clusters ou Series temporais.

    Esta disponivel para seu uso ferramentas de desenvolvimento, onde você podera ler o codigo que foi feito por você e alterar para assim conseguir
    chegar em uma acuracia aceitavel para esse caso

    TOOLS:
        Para visualizar o código, você deve chamar a tool << ver_codigo >>
        Para escrever no script, você deve chamar a tool << dev_codigo >>

    INSTRÇÕES:
        É OBRIGATÓRIO o uso das ferramentas
        NÃO pergunte nada nem tente entender, somente faça
        Você TEM que entregar um arquivo formatado com linguagem python
        Não pense, não fale, somente redija o arquivo com a linguagem python
''',
    tools=[ver_codigo, dev_codigo]
    
)

result = agent.run(f"Veja o conteudo do arquivo, o caminho para o arquivo é esse {filee}, o conteudo é {ver_codigo()}")
print(result.content)
