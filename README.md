# LinkEvagas 🚀

> **Um agente de IA automatizado para buscar, otimizar e enviar candidaturas no LinkedIn**

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📋 Sobre o Projeto

**LinkEvagas** é uma solução de automação inteligente que utiliza agentes de IA (powered by [Agno](https://github.com/phind-ai/agno)) para:

1. 🔍 **Buscar** vagas no LinkedIn baseado em critério de pesquisa
2. 📄 **Otimizar** seu currículo com técnicas de ATS para cada vaga
3. ✅ **Preencher** formulários de candidatura automaticamente
4. 📤 **Enviar** suas candidaturas ao LinkedIn com um clique

### Funcionalidades Principais

- ✨ **Análise Inteligente de Vagas**: Extrai termos técnicos, soft skills e requisitos desejáveis
- 🎯 **Otimização de Currículo**: Adapta seu CV para cada vaga usando técnicas de ATS (Applicant Tracking System)
- 🤖 **Preenchimento Automático**: Preenche formulários Easy Apply com informações inteligentes
- 🔐 **Sessão Persistente**: Mantém sua sessão do LinkedIn segura e autenticada
- 🧠 **Multi-LLM Support**: Funciona com OpenAI, Ollama e Google Gemini
- 📊 **Pipeline End-to-End**: Desde busca até envio, tudo automatizado

---

## 🛠️ Requisitos

### Dependências de Sistema

- **Python 3.12+**
- **Node.js** (para Playwright)
- **Navegador Chrome/Chromium**

### Dependências de Software

```bash
# Principais
agno >= 2.5.8                    # Framework de agentes de IA
langchain >= 1.2.12              # Orquestração de LLMs
playwright >= 1.58.0             # Automação de navegador
openai >= 2.26.0                 # API OpenAI

# LLMs Locais (Opcional)
ollama >= 0.6.1                  # LLMs open-source locais

# Processamento de Documentos
markdown-pdf >= 1.13.1           # Converter MD para PDF
markitdown >= 0.1.5              # Análise de Markdown
pdf2docx >= 0.5.11               # Conversão PDF ↔ DOCX

# Análise de Dados
langchain-ollama >= 1.0.1        # Integração com Ollama
langchain-openai >= 1.1.11       # Integração com OpenAI
```

---

## 📦 Instalação

### 1. Clonar o Repositório

```bash
git clone https://github.com/lucas-abner/linkevagas.git
cd linkevagas
```

### 2. Criar Ambiente Virtual (Recomendado)

#### Usando `uv` (mais rápido):
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

### 3. Instalar Dependências

```bash
uv pip install -e .
# ou
pip install -e .
```

### 4. Configurar Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# OpenAI (se usar GPT)
OPENAI_API_KEY=sk-your-key-here

# Google Gemini (opcional)
GOOGLE_API_KEY=your-gemini-key

# LinkedIn Credentials
LINKEDIN_EMAIL=seu.email@exemplo.com
LINKEDIN_PASSWORD=sua-senha

# Configurações Opcionais
BUSCAR_VAGA=Agente de IA
QUANTIDADE_VAGAS=1
MODELO_PRINCIPAL=gpt-4o-mini
```

### 5. Instalar Playwright Browsers

```bash
playwright install chromium
```

### 6. Configurar Sessão do LinkedIn

Na primeira execução, você será redirecionado para fazer login no LinkedIn:

```bash
python -m src.agents.agent
```

A sessão será salva em `linkedin_session.json` e reutilizada automaticamente.

---

## 🚀 Como Usar

### Execução Básica

```bash
python -m src.agents.agent
```

**Importante**: Execute como módulo para manter imports relativos funcionando:

```bash
# ✅ Correto
python -m src.agents.agent

# ❌ Evite
python src/agents/agent.py
```

### Fluxo de Execução

```
┌─────────────────────────────────────┐
│  1️⃣  BUSCAR VAGAS NO LINKEDIN      │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  2️⃣  ANALISAR COM ATS EXTRACTOR     │
│  (Extrai termos técnicos)          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  3️⃣  LER CURRÍCULO BASE             │
│  (MD → conteúdo original)          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  4️⃣  OTIMIZAR CURRÍCULO             │
│  (Reescreve com técnicas ATS)      │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  5️⃣  CONVERTER PARA PDF             │
│  (MD → PDF formatado)              │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  6️⃣  ENVIAR CANDIDATURA             │
│  (Easy Apply + Formulários)        │
└─────────────────────────────────────┘
```

---

## 📁 Estrutura do Projeto

```
linkevagas/
├── src/
│   ├── agents/
│   │   └── agent.py                 # Orquestração dos agentes
│   ├── tools/
│   │   ├── playwright_tool.py       # Automação de navegador
│   │   └── cv_tool.py               # Processamento de CV
│   └── utils/
│       └── format_output.py         # Formatação de saídas
├── .env                              # Variáveis de ambiente
├── linkedin_session.json             # Sessão persistente (auto-gerada)
├── pyproject.toml                    # Configuração do projeto
└── README.md                         # Este arquivo
```

### Componentes Principais

#### **Agentes** (`src/agents/agent.py`)

| Agente | Responsabilidade |
|--------|------------------|
| **Analista de ATS** | Extrai termos técnicos e soft skills das vagas |
| **Leitor de CV** | Lê e preserva o currículo original |
| **Redator de CV** | Otimiza o currículo com termos ATS |
| **Copia e Cola** | Salva o CV otimizado em Markdown |
| **Conversor de CV** | Converte Markdown para PDF |
| **Agente de Envio** | Automatiza o preenchimento e envio no LinkedIn |

#### **Tools** (`src/tools/`)

- **`playwright_tool.py`**: Automação web com Playwright
  - `buscar_multiplas_vagas()`: Busca vagas no LinkedIn
  - `tool_envio_candidatura()`: Preenche e envia candidaturas
  - `descobrir_e_preencher_todos_campos()`: Inteligência para preencher formulários

- **`cv_tool.py`**: Processamento de currículos
  - `ler_cv_base_md()`: Lê CV em Markdown
  - `salvar_cv_otimizado_md()`: Salva versão otimizada
  - `converter_md_para_pdf()`: Converte para PDF

---

## 🧠 Modelos de IA Suportados

### OpenAI (Recomendado para Produção)

```python
MODEL_GPT = OpenAIResponses(
    id="gpt-4o",  # ou gpt-4o-mini para economia
    api_key=os.getenv("OPENAI_API_KEY")
)
```

### Ollama (Local - Sem Custos)

```python
MODEL_LOCAL = Ollama(
    id="qwen2.5:7b",
    host="http://localhost:11434",
    options={"temperature": 0.7}
)
```

**Para usar Ollama localmente:**

```bash
# Instale Ollama (https://ollama.ai)
ollama pull qwen2.5:7b
ollama serve  # Em outro terminal
```

### Google Gemini (Alternativa)

```python
MODEL_GEMINI = ...  # Suportado via langchain-google
```

---

## ⚙️ Configuração Avançada

### Customizar Informações Pessoais

Edite `src/agents/agent.py` - seção `support_format_cv`:

```python
support_format_cv = [
    Message(role="system", content="""
###SEU NOME COMPLETO

Cidade, Estado | seu.email@exemplo.com | (XX) XXXXX-XXXX
LinkedIn: seu-link | GitHub: seu-github

# Personalize seu CV base aqui
# ...
""".strip())
]
```

### Customizar Respostas de Formulários

Em `src/tools/playwright_tool.py` - `descobrir_e_preencher_todos_campos()`:

```python
respostas_mapeadas = {
    "python": "3",              # Nível de experiência
    "salary": "8000",           # Pretensão salarial
    "disponibilidade": "Imediata",
    "linkedin": "seu-link",
    # Adicione mais...
}
```

### Aumentar Tempo de Espera para Conexões Lentas

```python
page.wait_for_load_state("domcontentloaded", timeout=15000)  # 15 segundos
```

---

## 🐛 Troubleshooting

### ❌ "Sessão inválida"

```
❌ Cookie li_at expirado.
⚠️ Sessão inválida. Iniciando autenticação...
```

**Solução**: Delete `linkedin_session.json` e execute novamente. Você será redirecionado para fazer login.

```bash
rm linkedin_session.json
python -m src.agents.agent
```

### ❌ "Timeout esperando página"

```
ERROR: Page.wait_for_selector: Timeout 10000ms exceeded.
```

**Soluções**:
1. Aumentar timeout em `src/tools/playwright_tool.py`
2. Verificar conexão de internet
3. Verificar se o LinkedIn mudou estrutura (screenshots em `debug_*.png`)

### ❌ "Modelo não encontrado"

```
ERROR: Project does not have access to model `gpt-4o`
```

**Solução**: Use um modelo disponível:

```python
MODEL_GPT = OpenAIResponses(id="gpt-4o-mini", api_key=...)
```

### ❌ "Playwright não encontrado"

```
ERROR: No module named 'playwright'
```

**Solução**:
```bash
pip install playwright
playwright install chromium
```

### ❌ "LinkedIn bloqueou automação"

O LinkedIn detectou padrões de bot. **Soluções**:
1. Aguarde 24-48h
2. Use menos vagas por execução (`QUANTIDADE_VAGAS=1`)
3. Adicione delays maiores entre buscas

---

## 📊 Métricas e Monitoring

O projeto gera outputs detalhados:

```
[1/5] Analisando a Vaga: Agente de IA
✅ Termos extraídos: python, langchain, fastapi...

[2/5] Acionando o Agente Redator...
✅ CV otimizado com 85% de match ATS

[3/5] Convertendo para PDF...
✅ PDF gerado: cv_otimizado_agente_ia.pdf

[4/5] Enviando candidatura...
✅ Candidatura enviada com sucesso!
```

---

## 🔐 Segurança

- ✅ Credenciais em `.env` (nunca commitar)
- ✅ Sessão do LinkedIn em `linkedin_session.json` (não commitar)
- ✅ Sem armazenamento de senhas
- ✅ Apenas cookies de sessão reutilizados

### Recomendações

```bash
# Adicione ao .gitignore
echo ".env" >> .gitignore
echo "linkedin_session.json" >> .gitignore
echo "*.pdf" >> .gitignore
echo "debug_*.png" >> .gitignore
```

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Para reportar bugs ou sugerir features:

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

---

## 📝 Roadmap

- [ ] Dashboard web para monitoramento
- [ ] Suporte a múltiplas plataformas (Indeed, Glassdoor)
- [ ] Cache de vagas analisadas
- [ ] Relatório detalhado de candidaturas
- [ ] Integração com Discord/Telegram para notificações
- [ ] Fine-tuning de modelo customizado

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

- [Agno Documentation](https://github.com/phind-ai/agno)
- [Playwright Documentation](https://playwright.dev/python/)
- [LangChain Documentation](https://python.langchain.com/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)

---

**Última atualização**: Março 2026