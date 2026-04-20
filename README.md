# LinkEvagas 🚀

> **Pipeline de IA que busca vagas no LinkedIn, otimiza seu currículo com técnicas de ATS e envia candidaturas automaticamente**

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📋 Sobre o Projeto

**LinkEvagas** é uma solução de automação inteligente que utiliza agentes de IA (powered by [Agno](https://github.com/agno-ai/agno)) para:

1. 🔍 **Buscar** vagas no LinkedIn baseado em um critério de pesquisa
2. 🧩 **Extrair** palavras-chave e habilidades da descrição da vaga (spaCy + KeyBERT)
3. 📄 **Otimizar** seu currículo com técnicas de ATS para cada vaga
4. 📊 **Avaliar** o score ATS do currículo gerado e refazer se necessário
5. 🖨️ **Converter** o currículo Markdown para PDF pronto para envio
6. 📤 **Enviar** a candidatura via Easy Apply com preenchimento automático de formulários

### Funcionalidades Principais

- ✨ **Extração de Palavras-chave**: Combina spaCy (NLP) e KeyBERT (embeddings semânticos) para extrair termos técnicos, soft skills e diferenciais da vaga
- 🎯 **Otimização ATS**: Reescreve o CV aplicando a fórmula XYZ, inserindo os termos exatos exigidos pela vaga
- 📊 **Avaliação com Score**: Um agente "Juiz" avalia matematicamente o score de aderência e repete o ciclo até atingir 90% de match
- 🤖 **Formulários Easy Apply**: Usa LLM local (Ollama) para responder qualquer pergunta dos formulários de candidatura
- 🔐 **Sessão Persistente**: Salva e reutiliza a sessão do LinkedIn via cookies, com fallback para login manual
- 🧠 **Multi-LLM**: Pipeline principal usa OpenAI (GPT); agentes auxiliares e formulários usam Ollama localmente

---

## 🛠️ Requisitos

### Dependências de Sistema

- **Python 3.12+**
- **Navegador Chromium** (instalado via Playwright)
- **Ollama** em execução local (para agentes auxiliares e formulários)

### Dependências Python

As principais dependências declaradas em `pyproject.toml`:

```
agno                 # Framework de agentes de IA
openai               # API OpenAI (GPT)
google-genai         # API Google Gemini
langchain / langchain-openai / langchain-ollama / langchain-community
ollama               # SDK Ollama
playwright           # Automação de navegador
spacy                # NLP para extração de entidades
keybert              # Extração de palavras-chave via embeddings
sentence-transformers# Modelo de embeddings para KeyBERT
scikit-learn         # Similaridade coseno para score ATS
torch                # Backend dos modelos de embeddings
markdown             # Renderização de Markdown
weasyprint           # Conversão Markdown → PDF (via HTML)
markitdown           # Leitura de PDFs/documentos como Markdown
pypdf                # Leitura de PDFs
pdf2docx             # Conversão PDF ↔ DOCX
```

---

## 📦 Instalação

### 1. Clonar o Repositório

```bash
git clone https://github.com/lucas-abner/linkevagas.git
cd linkevagas
```

### 2. Criar Ambiente Virtual

#### Usando `uv` (recomendado):
```bash
uv venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate      # Windows
```

#### Ou usando `venv` padrão:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate      # Windows
```

### 3. Instalar Dependências Python

```bash
uv pip install -e .
# ou
pip install -e .
```

### 4. Baixar Modelo spaCy

```bash
python -m spacy download pt_core_news_sm
```

### 5. Instalar Navegador via Playwright

```bash
playwright install chromium
```

### 6. Instalar e Configurar Ollama

Os agentes auxiliares (Juiz de ATS, Copia e Cola, Conversor, Envio) e o preenchimento de formulários rodam com Ollama localmente.

```bash
# Instale Ollama: https://ollama.ai
ollama pull qwen2.5:7b
ollama serve   # Em terminal separado (manter rodando)
```

### 7. Configurar Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# OpenAI — usado pelos agentes principais (extração ATS, redação do CV)
OPENAI_API_KEY=sk-your-key-here

# Modelo GPT a usar (padrão: gpt-4o-mini)
MODELO_PRINCIPAL=gpt-4o-mini

# Caminho absoluto para o seu currículo base em PDF
CV_PATH=/caminho/para/seu_curriculo.pdf

# Credenciais do LinkedIn
LINKEDIN_EMAIL=seu.email@exemplo.com
LINKEDIN_PASSWORD=sua-senha

# URL de busca de vagas do LinkedIn (com parâmetros de filtro desejados)
LINKEDIN_PREFIX=https://www.linkedin.com/jobs/search/?keywords=

# Busca e quantidade de vagas
BUSCAR_VAGA=Agente de IA
QUANTIDADE_VAGAS=1
```

> **Dica**: Para `LINKEDIN_PREFIX`, você pode copiar a URL da busca do LinkedIn com filtros de localização, modalidade, etc. e usar como prefixo.

### 8. Configurar Sessão do LinkedIn

Na primeira execução, o sistema validará a sessão. Se não existir, abrirá o navegador para login:

```bash
python -m src.agents.agent
```

A sessão é salva em `linkedin_session.json` e reutilizada automaticamente nas próximas execuções.

---

## 🚀 Como Usar

### Execução

```bash
python -m src.agents.agent
```

> **Importante**: Execute sempre como módulo para que os imports relativos funcionem corretamente.
>
> ✅ `python -m src.agents.agent`  
> ❌ `python src/agents/agent.py`

### Fluxo de Execução

```
┌──────────────────────────────────────────────┐
│  1️⃣  BUSCAR VAGAS NO LINKEDIN                │
│  (Playwright → lista de título, descrição,   │
│   URL — apenas vagas com Easy Apply)         │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│  2️⃣  EXTRAIR E CLASSIFICAR TERMOS ATS        │
│  spaCy (noun_chunks) + KeyBERT (embeddings)  │
│  → Limpeza → Classificador LLM               │
│  → technical_terms / soft_skills / desejaveis│
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│  3️⃣  LER CV BASE E REESCREVER PARA ATS       │
│  Agente Leitor → lê PDF do CV base           │
│  Agente Redator → reescreve com fórmula XYZ  │
│  Agente Juiz → avalia score (meta: ≥ 90%)    │
│  ↑ Repete se REPROVADO ou MEDIANO (max 10x)  │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│  4️⃣  SALVAR E CONVERTER PARA PDF             │
│  Agente Copia e Cola → salva .md             │
│  Agente Conversor → gera PDF via WeasyPrint  │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│  5️⃣  ENVIAR CANDIDATURA                      │
│  Playwright → Easy Apply                     │
│  LLM (Ollama) → responde formulários         │
└──────────────────────────────────────────────┘
```

---

## 📁 Estrutura do Projeto

```
linkevagas/
├── src/
│   ├── agents/
│   │   └── agent.py              # Definição dos agentes e orquestração do pipeline
│   ├── tools/
│   │   ├── ats_tool.py           # Extração de keywords (spaCy + KeyBERT) e score ATS
│   │   ├── cv_tool.py            # Leitura, salvamento e conversão MD → PDF do CV
│   │   └── playwright_tool.py    # Automação do LinkedIn (busca, sessão, envio de candidatura)
│   └── utils/
│       └── format_output.py      # Utilitário para limpar blocos Markdown do output LLM
├── .env                          # Variáveis de ambiente (não commitar)
├── linkedin_session.json         # Sessão persistente do LinkedIn (auto-gerada, não commitar)
├── pyproject.toml                # Configuração do projeto e dependências
└── README.md                     # Este arquivo
```

### Agentes (`src/agents/agent.py`)

| Agente | Modelo | Responsabilidade |
|--------|--------|------------------|
| **ATS Hard Skills Extractor** | GPT (OpenAI) | Limpa e normaliza os termos extraídos da vaga |
| **ATS Skills Classifier** | GPT (OpenAI) | Classifica termos em técnicos, soft skills e desejáveis |
| **Leitor de CV** | GPT (OpenAI) | Lê o CV base em PDF e retorna o conteúdo íntegro |
| **Redator de CV** | GPT (OpenAI) | Reescreve o CV com técnicas ATS (fórmula XYZ, 1 página) |
| **Juiz de ATS** | Ollama local | Avalia o score de aderência e repete se < 90% |
| **Copia e Cola** | Ollama local | Salva o CV otimizado como arquivo Markdown |
| **Conversor de CV** | Ollama local | Converte o Markdown para PDF via WeasyPrint |
| **Agente de Envio** | Ollama local | Aciona o Playwright para enviar a candidatura |

### Tools (`src/tools/`)

**`ats_tool.py`** — Análise de vagas e avaliação de currículo:
- `extract_entities(text)`: Extrai noun chunks com spaCy (`pt_core_news_sm`)
- `extrator_keywords_keybert(text)`: Extrai até 30 keywords com KeyBERT (`all-MiniLM-L6-v2`)
- `pre_process_pipeline(terms)`: Remove ruídos, stopwords e termos muito longos
- `tool_avaliar_score_ats(cv_text, keywords)`: Calcula score de match exato e retorna feedback (REPROVADA / MEDIANA / APROVADA)

**`cv_tool.py`** — Processamento de currículos:
- `ler_cv_base_md()`: Converte o PDF do CV base (`CV_PATH`) para Markdown usando MarkItDown
- `salvar_cv_otimizado_md(conteudo_md, nome_vaga)`: Salva o CV otimizado como `cv_<nome_vaga>.md`
- `converter_md_para_pdf(caminho_md)`: Converte Markdown para PDF formatado (A4, ATS-friendly) via WeasyPrint

**`playwright_tool.py`** — Automação do LinkedIn:
- `_validate_session()` / `_create_session()`: Valida ou cria sessão por cookies
- `search_jobs(search_term, quantity)`: Busca vagas e filtra apenas as com Easy Apply
- `buscar_multiplas_vagas(search_term, quantity)`: Wrapper chamado pelo pipeline principal
- `tool_envio_candidatura(vaga_url, cv_path)`: Abre o modal Easy Apply e envia a candidatura
- `_fill_form_fields(modal, page, cv_path)`: Percorre todos os campos e usa LLM (Ollama) para respondê-los

---

## 🧠 Modelos de IA

### OpenAI — Agentes principais

Usado para extração de termos ATS, classificação e redação do CV (requer `OPENAI_API_KEY`):

```python
MODEL_GPT = OpenAIResponses(
    id=os.getenv("MODELO_PRINCIPAL", "gpt-4o-mini"),
    api_key=os.getenv("OPENAI_API_KEY")
)
```

### Ollama — Agentes auxiliares e formulários

Roda localmente, sem custo. Modelos configurados no código:

```python
MODEL_OLLAMA_QWEN2 = Ollama(id="qwen2.5:7b", host="http://localhost:11434")
```

O preenchimento de formulários também usa Ollama via LangChain:

```python
# playwright_tool.py
chat = ChatOllama(base_url="http://localhost:11434", model="qwen2.5:7b")
```

### API-compatible (Groq, etc.)

O código já possui suporte a endpoints compatíveis com a API OpenAI:

```python
MODEL_GPT_OPEN = OpenAIResponses(
    id=os.getenv("MODELO_GPT_OPEN", "openai/gpt-oss-20b"),
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)
```

---

## ⚙️ Configuração Avançada

### Personalizar o Contexto do Candidato nos Formulários

O preenchimento automático de formulários usa um contexto hardcoded em `playwright_tool.py`. Edite a função `_get_llm_response()` para adaptar ao seu perfil:

```python
system_prompt = """...
CONTEXTO DO CANDIDATO:
- Nome: Seu Nome Completo
- Email: seu.email@exemplo.com
- Telefone: 11999999999
- Localização: Cidade, UF
- Experiência: suas habilidades aqui
- Salário pretendido: 8000
...
"""
```

### Ajustar Critérios de Score ATS

Em `ats_tool.py`, os thresholds de aprovação são:

```python
if score_porcentagem < 60:   # REPROVADA — refaz
elif score_porcentagem < 90: # MEDIANA — refaz
else:                        # APROVADA — avança
```

O pipeline tenta no máximo **10 vezes** antes de prosseguir com o melhor resultado disponível.

### Aumentar Timeout para Conexões Lentas

Em `playwright_tool.py`, ajuste os timeouts de espera:

```python
page.wait_for_timeout(1500)      # Espera entre cliques
page.wait_for_selector(selector, timeout=5000)  # Espera por elementos
```

---

## 🐛 Troubleshooting

### ❌ "Cookie li_at expirado" / Sessão inválida

```
❌ Cookie li_at expirado.
⚠️ Sessão inválida. Criando nova...
```

**Solução**: Delete o arquivo de sessão e execute novamente para refazer o login:

```bash
rm linkedin_session.json
python -m src.agents.agent
```

### ❌ "Seletor de vagas não encontrado"

```
Exception: Seletor de vagas não encontrado
```

O LinkedIn pode ter atualizado o HTML. Um screenshot `debug_linkedin.png` será salvo para inspeção.

**Soluções**:
1. Abra `debug_linkedin.png` para ver o estado da página
2. Atualize os seletores CSS em `search_jobs()` no `playwright_tool.py`
3. Verifique se a URL em `LINKEDIN_PREFIX` é válida e retorna vagas

### ❌ "Modelo não encontrado" (OpenAI)

```
ERROR: Project does not have access to model `gpt-4o`
```

**Solução**: Use `gpt-4o-mini` ou outro modelo disponível na sua conta:

```env
MODELO_PRINCIPAL=gpt-4o-mini
```

### ❌ Ollama não responde

```
httpx.ConnectError: Connection refused
```

**Solução**: Certifique-se de que o Ollama está em execução:

```bash
ollama serve
# Em outro terminal:
ollama list  # Confirma que qwen2.5:7b está instalado
```

### ❌ Erro ao instalar dependências (`torch`, `spacy`, etc.)

Para instalações em sistemas sem GPU, force a versão CPU do PyTorch antes:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -e .
```

### ❌ "LinkedIn bloqueou automação"

O LinkedIn detectou padrão de bot. **Soluções**:
1. Aguarde 24–48h antes de tentar novamente
2. Use `QUANTIDADE_VAGAS=1` para processar uma vaga por vez
3. Aumente os timeouts entre ações no `playwright_tool.py`

---

## 🔐 Segurança

- ✅ Credenciais em `.env` (nunca commitar — já no `.gitignore`)
- ✅ Sessão do LinkedIn em `linkedin_session.json` (não commitar — já no `.gitignore`)
- ✅ Nenhuma senha é armazenada — apenas cookies de sessão são reutilizados
- ✅ PDFs e arquivos Markdown gerados ignorados pelo `.gitignore`

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Para reportar bugs ou sugerir features:

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'feat: descrição da mudança'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

---

## 📝 Roadmap

- [ ] Dashboard web para monitoramento das candidaturas
- [ ] Suporte a múltiplas plataformas (Indeed, Glassdoor)
- [ ] Cache de vagas já analisadas para evitar reprocessamento
- [ ] Relatório detalhado de candidaturas enviadas
- [ ] Integração com Discord/Telegram para notificações
- [ ] Suporte a Google Gemini como modelo principal

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja [LICENSE](LICENSE) para mais detalhes.

---

## 👨‍💻 Autor

**Lucas Abner Caixeta de Oliveira**

- 📧 Email: lucascaixeta02@gmail.com
- 🔗 LinkedIn: [lucas-abner-caixeta](https://www.linkedin.com/in/lucas-abner-caixeta/)
- 🐙 GitHub: [lucas-abner](https://github.com/lucas-abner)

---

## ⭐ Se Este Projeto Ajudou Você

Deixe uma star ⭐ no GitHub!

---

## 📚 Referências

- [Agno Documentation](https://github.com/agno-ai/agno)
- [Playwright for Python](https://playwright.dev/python/)
- [LangChain Documentation](https://python.langchain.com/)
- [KeyBERT](https://github.com/MaartenGr/KeyBERT)
- [spaCy](https://spacy.io/)
- [WeasyPrint](https://weasyprint.org/)
- [Ollama](https://ollama.ai)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)