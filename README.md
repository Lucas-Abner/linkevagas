# linkevagas

## Executando o agente

Para manter os imports relativos funcionando, execute o agente como módulo a partir da raiz do projeto:

```powershell
.\.venv\Scripts\python.exe -m src.agents.agent
```

Evite executar o arquivo diretamente com:

```powershell
python .\src\agents\agent.py
```

Esse formato roda o arquivo como script isolado e quebra imports relativos como o de [src/agents/agent.py](src/agents/agent.py#L4).