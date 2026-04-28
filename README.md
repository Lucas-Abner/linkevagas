# LinkeVagas 🚀

> **Agente de IA com análise estratégica para buscar, otimizar e enviar candidaturas no LinkedIn — maximizando retorno para entrevistas**

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📋 Sobre o Projeto

**LinkeVagas** é uma solução de automação inteligente que utiliza agentes de IA (powered by [Agno](https://github.com/phind-ai/agno)) para automatizar o ciclo completo de candidatura a vagas no LinkedIn — desde a busca até o envio, com otimização inteligente do currículo para cada vaga.

### O que diferencia o LinkeVagas

Diferente de ferramentas que apenas inserem palavras-chave no CV, o LinkeVagas implementa uma **estratégia completa de candidatura**:

1. 🔍 **Busca** vagas no LinkedIn com coleta completa de dados (título, empresa, localização, descrição integral)
2. 🧠 **Analisa estrategicamente** cada vaga — detecta senioridade real, tom da empresa, requisitos essenciais vs. desejáveis
3. 🚦 **Filtra vagas incompatíveis** — evita poluir seu perfil aplicando para posições com fit < 30%
4. ✍️ **Otimiza o CV com inteligência** — recontextualiza experiências, elimina linguagem genérica de IA, usa método CAR
5. 📊 **Avalia com score semântico** — combina keyword matching com similaridade por embeddings
6. 📤 **Envia e registra** — preenche formulários e rastreia cada candidatura para feedback loop

---

## ✨ Funcionalidades

### Pipeline Inteligente (v2.0)

| Funcionalidade | Descrição |
|---------------|-----------|
| **Análise Estratégica de Vagas** | Agente dedicado que avalia fit score, detecta senioridade real, identifica gaps críticos e gera estratégia personalizada para o Redator |
| **Gate de Qualidade** | Vagas com fit score < 30% são automaticamente ignoradas, evitando desperdício e poluição do perfil LinkedIn |
| **Score ATS Combinado** | 40% keyword matching (com sinônimos) + 60% similaridade semântica (sentence-transformers) |
| **Anti-Padrões de IA** | Prompt do Redator proíbe explicitamente frases genéricas de IA, métricas inventadas e keyword stuffing |
| **Tracking de Candidaturas** | Registro completo de cada candidatura em JSON (data, empresa, fit score, CV usado, status) |
| **Metadados Enriquecidos** | Extração de empresa e localização além de título e descrição |
| **Preenchimento Automático** | Formulários Easy Apply preenchidos por LLM com contexto do candidato |
| **Multi-LLM** | OpenAI (GPT-4o/mini), Ollama (Qwen2.5) e Google Gemini |
| **Sessão Persistente** | Sessão do LinkedIn reutilizada automaticamente |
| **Interface Gráfica** | GUI desktop em Tkinter para gerenciar variáveis, executar pipeline e acompanhar logs |

---

## 🏗️ Arquitetura

### Fluxo do Pipeline

```
┌─────────────────────────────────────┐
│  📄 LER CV BASE (1x para todas)    │
└──────────────┬──────────────────────┘
               │
  ┌────────────▼────────────────────────┐
  │  🔍 BUSCAR VAGAS NO LINKEDIN        │
  │  (título + empresa + local + desc)  │
  └────────────┬────────────────────────┘
               │
    ┌──────────▼──────────────────────┐
    │  🧠 ANÁLISE ESTRATÉGICA         │  ← Agente Analista
    │  fit score · senioridade · gaps │
    │  tom da vaga · estratégia CV    │
    └──────────┬──────────────────────┘
               │
          fit < 30%? ──→ ⏭️ IGNORAR (registrado no tracking)
               │
    ┌──────────▼──────────────────────┐
    │  📊 EXTRAÇÃO DE KEYWORDS        │
    │  SpaCy + KeyBERT + LLM cleanup  │
    └──────────┬──────────────────────┘
               │
    ┌──────────▼──────────────────────┐
    │  ✍️  REDAÇÃO OTIMIZADA           │  ← Método CAR
    │  (guiada pela análise)          │
    │  anti-padrões IA · sem métricas │
    │  inventadas · tom adaptado      │
    └──────────┬──────────────────────┘
               │
    ┌──────────▼──────────────────────┐
    │  📊 AVALIAÇÃO COMBINADA         │
    │  40% keyword (+ sinônimos)      │
    │  60% semântico (embeddings)     │
    └──────────┬──────────────────────┘
          score OK? ──→ 🔄 RETRY (até 10x)
               │
    ┌──────────▼──────────────────────┐
    │  📄 SALVAR MD → PDF             │
    └──────────┬──────────────────────┘
               │
    ┌──────────▼──────────────────────┐
    │  📤 ENVIAR CANDIDATURA          │
    │  Easy Apply + formulários LLM   │
    │  + registrar no tracking        │
    └─────────────────────────────────┘
               │
    ┌──────────▼──────────────────────┐
    │  📋 RELATÓRIO FINAL             │
    │  vagas processadas · enviadas   │
    │  ignoradas · taxa de retorno    │
    └─────────────────────────────────┘
```

### Estrutura do Projeto

```
linkevagas/
├── src/
│   ├── agents/
│   │   └── agent.py                  # Orquestração dos agentes e pipeline
│   ├── tools/
│   │   ├── playwright_tool.py        # Automação de navegador (busca + envio)
│   │   ├── cv_tool.py                # Leitura, salvamento e conversão de CV
│   │   ├── ats_tool.py               # Extração de keywords + score ATS (keyword + semântico)
│   │   └── tracking.py               # Registro e relatório de candidaturas
│   └── utils/
│       └── format_output.py          # Formatação de saídas Markdown
├── gui/
│   ├── app.py                        # Janela principal da GUI
│   ├── main.py                       # Entry point da GUI
│   ├── theme.py                      # Tema visual (dark mode)
│   ├── process_manager.py            # Gerenciador de processos
│   ├── env_manager.py                # Gerenciador de variáveis de ambiente
│   └── components/                   # Componentes visuais (painéis, logs, pipeline)
├── .env                              # Variáveis de ambiente (não commitar)
├── linkedin_session.json             # Sessão persistente (auto-gerada)
├── candidaturas_tracking.json        # Histórico de candidaturas (auto-gerado)
├── pyproject.toml                    # Configuração do projeto
└── README.md
```

### Agentes (`src/agents/agent.py`)

| Agente | Modelo | Responsabilidade |
|--------|--------|-----------------|
| **Analista Estratégico** | Inteligente (GPT) | Analisa a vaga profundamente: fit score, senioridade, gaps, tom, e gera estratégia para o Redator |
| **ATS Extractor** | Inteligente (GPT) | Limpa e normaliza termos técnicos extraídos por SpaCy/KeyBERT |
| **ATS Classifier** | Inteligente (GPT) | Classifica termos em: técnicos, soft skills, desejáveis |
| **Leitor de CV** | Inteligente (GPT) | Lê o currículo base sem alterar nada |
| **Redator de CV** | Inteligente (GPT) | Reescreve o CV seguindo a estratégia do Analista e o método CAR |
| **Juiz de ATS** | Burocrático (Ollama) | Avalia matematicamente a aderência do CV à vaga |
| **Copia e Cola** | Burocrático (Ollama) | Salva o CV otimizado em Markdown |
| **Conversor** | Burocrático (Ollama) | Converte Markdown → PDF formatado para ATS |
| **Envio** | Burocrático (Ollama) | Preenche e envia candidatura via Playwright |

### Tools (`src/tools/`)

| Módulo | Funções Principais |
|--------|-------------------|
| **`playwright_tool.py`** | `search_jobs()` · `apply_to_job()` · `_fill_form_fields()` · Gestão de sessão LinkedIn |
| **`ats_tool.py`** | `tool_avaliar_score_ats()` · `avaliar_score_ats_semantico()` · `avaliar_score_combinado()` · `extract_entities()` · `extrator_keywords_keybert()` |
| **`cv_tool.py`** | `ler_cv_base_md()` · `salvar_cv_otimizado_md()` · `converter_md_para_pdf()` |
| **`tracking.py`** | `registrar_candidatura()` · `gerar_relatorio()` |

---

## 🛠️ Requisitos

### Dependências de Sistema

- **Python 3.12+**
- **Node.js** (para Playwright)
- **Navegador Chrome/Chromium**

### Dependências Principais

```bash
agno >= 2.5.8                    # Framework de agentes de IA
langchain >= 1.2.12              # Orquestração de LLMs
playwright >= 1.58.0             # Automação de navegador
openai >= 2.26.0                 # API OpenAI
sentence-transformers >= 5.3.0   # Score ATS semântico (embeddings)
scikit-learn >= 1.8.0            # Cosine similarity
keybert >= 0.9.0                 # Extração de keywords
spacy >= 3.8.11                  # NLP (noun chunks)
weasyprint >= 68.1               # Geração de PDF

# LLMs Locais (Opcional)
ollama >= 0.6.1                  # LLMs open-source locais
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
# ── LLM ──────────────────────────────────────
OPENAI_API_KEY=sk-your-key-here
GOOGLE_API_KEY=your-gemini-key          # opcional
MODELO_PRINCIPAL=gpt-4o-mini
MODO_PROCESSAMENTO=Híbrido (Recomendado)  # ou "100% Local (Ollama)" ou "100% Nuvem (GPT)"

# ── LinkedIn ─────────────────────────────────
LINKEDIN_EMAIL=seu.email@exemplo.com
LINKEDIN_PASSWORD=sua-senha
LINKEDIN_LINK=https://www.linkedin.com/in/seu-perfil
LINKEDIN_PREFIX=https://www.linkedin.com/jobs/search/?f_AL=true&keywords=

# ── Busca ────────────────────────────────────
BUSCAR_VAGA=AI Engineer
QUANTIDADE_VAGAS=5

# ── Candidato ────────────────────────────────
CV_PATH=/caminho/completo/para/seu/cv.pdf
EMAIL=seu.email@exemplo.com
NOME_COMPLETO=Seu Nome
TELEFONE=11999999999
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

### Via Linha de Comando

```bash
# ✅ Correto — como módulo
python -m src.agents.agent

# ❌ Evite — quebra imports relativos
python src/agents/agent.py
```

### Via Interface Gráfica (GUI)

```bash
python -m gui.main
```

A GUI permite:
- Gerenciar variáveis de ambiente (`.env`) visualmente
- Iniciar/parar o pipeline com um clique
- Acompanhar cada etapa em tempo real (pipeline visual)
- Visualizar logs detalhados
- Gerenciar sessão do LinkedIn

---

## 📊 Saída do Pipeline

O pipeline gera outputs detalhados para cada vaga:

```
============================================================
[VAGA 1/5] AI Engineer Jr
  Empresa: TechCorp
  URL: https://www.linkedin.com/jobs/...
============================================================

[0/5] 🔍 Análise estratégica da vaga...
  📊 Fit Score: 72%
  🎯 Senioridade: junior
  💼 Área: AI/ML
  🏠 Modelo: remoto
  🗣️ Idioma: Inglês Intermediário
  🔴 Gaps: Nenhum

[1/5] Extraindo keywords ATS...
[2/5] Reescrevendo CV para ATS...

📊 --- RESULTADO DO ALGORITMO ATS ---
=== AVALIAÇÃO COMBINADA ===
Score Keyword (40%): 87.5%
Score Semântico (60%): 71.2%
SCORE FINAL: 77.7%
AVALIAÇÃO APROVADA. Excelente aderência.
------------------------------------

✅ O currículo atingiu o Score exigido! A prosseguir...

[3/5] Salvando CV otimizado...
[4/5] Convertendo para PDF...
✅ PDF gerado: cv_ai_engineer_jr.pdf

[5/5] Acionando o Agente de Envio...
✅ Candidatura enviada com sucesso!
📋 Candidatura registrada: AI Engineer Jr (enviada)

============================================================
✅ PIPELINE CONCLUÍDO
  Vagas processadas: 5
  Candidaturas enviadas: 3
  Vagas ignoradas (fit baixo): 2
============================================================
```

### Vagas Filtradas (Fit Baixo)

```
[VAGA 4/5] Senior Cloud Architect — AWS
  📊 Fit Score: 18%
  ⏭️ IGNORADA — Fit score muito baixo (18%)
  Gaps críticos: 5+ anos experiência, AWS Solutions Architect, Terraform
📋 Candidatura registrada: Senior Cloud Architect (ignorada)
```

---

## 📋 Tracking de Candidaturas

O arquivo `candidaturas_tracking.json` é gerado automaticamente e registra cada candidatura:

```json
{
  "data": "2026-04-28T10:30:00",
  "titulo": "AI Engineer Jr",
  "empresa": "TechCorp",
  "url": "https://linkedin.com/jobs/...",
  "status": "enviada",
  "cv_usado": "cv_ai_engineer_jr.md",
  "fit_score": 72,
  "motivo": null,
  "retorno": null
}
```

O campo `retorno` pode ser preenchido manualmente (`true`/`false`) para criar um **feedback loop** — correlacionando quais fit scores e estratégias geraram retorno para entrevistas.

Ao final de cada execução, um relatório acumulado é exibido:

```
=== RELATÓRIO DE CANDIDATURAS ===
Total registradas: 23
Enviadas: 18
Ignoradas (fit baixo): 5
Com retorno: 3
Taxa de retorno: 16.7%
```

---

## 🧠 Modelos de IA Suportados

### Modos de Processamento

| Modo | Agentes Inteligentes | Agentes Burocráticos | Custo |
|------|---------------------|---------------------|-------|
| **Híbrido (Recomendado)** | GPT-4o-mini | Qwen2.5:7b (Ollama) | Baixo |
| **100% Nuvem (GPT)** | GPT-4o-mini | GPT-4o-mini | Médio |
| **100% Local (Ollama)** | Qwen2.5:7b | Qwen2.5:7b | Zero |

Configure via `MODO_PROCESSAMENTO` no `.env`.

### Usando Ollama Localmente

```bash
# Instale Ollama (https://ollama.ai)
ollama pull qwen2.5:7b
ollama serve  # Em outro terminal
```

---

## 🔧 Como a Otimização ATS Funciona

### 1. Análise Estratégica (Agente Analista)

O agente analisa a vaga como um **recrutador tech sênior** e gera:

- **Fit Score (0-100)**: Compatibilidade real do perfil com a vaga
- **Senioridade Real**: Detecta se uma vaga "Junior" na verdade pede experiência de Pleno
- **Gaps Críticos**: Requisitos que o candidato não possui e não pode contornar
- **Estratégia de CV**: Instruções específicas para o Redator (quais experiências destacar, que tom usar)

### 2. Score ATS Combinado

```
Score Final = (Keyword × 0.4) + (Semântico × 0.6)
```

- **Keyword (40%)**: Matching exato com suporte a **sinônimos** (ML↔Machine Learning, K8s↔Kubernetes, etc.)
- **Semântico (60%)**: Similaridade por embeddings (sentence-transformers `all-MiniLM-L6-v2`) — entende que "deploy de modelos" é similar a "MLOps" mesmo sem match exato

### 3. Anti-Padrões de IA no CV

O Redator tem instruções explícitas para **evitar linguagem detectável como IA**:

| ❌ Anti-Padrão | ✅ Padrão Correto |
|---------------|-------------------|
| "Contribuindo para melhorias operacionais contínuas" | "Eliminou dependência de APIs externas com deploy local" |
| "Melhorou eficiência em 30%" (inventado) | "Reduziu tempo de processamento ao automatizar pipeline" (fato) |
| "Profissional com experiência em..." | "Engenheiro de IA com foco em sistemas multi-agentes" |
| Listar 15 skills sem contexto | Cada skill justificada por uma experiência real |

---

## 🐛 Troubleshooting

### ❌ "Sessão inválida"

```
❌ Cookie li_at expirado.
⚠️ Sessão inválida. Iniciando autenticação...
```

**Solução**: Delete `linkedin_session.json` e execute novamente:

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

**Solução**: Use um modelo disponível no `.env`:

```env
MODELO_PRINCIPAL=gpt-4o-mini
```

### ❌ "LinkedIn bloqueou automação"

O LinkedIn detectou padrões de bot. **Soluções**:
1. Aguarde 24-48h
2. Use menos vagas por execução (`QUANTIDADE_VAGAS=1`)
3. Adicione delays maiores entre buscas

---

## 🔐 Segurança

- ✅ Credenciais em `.env` (nunca commitar)
- ✅ Sessão do LinkedIn em `linkedin_session.json` (não commitar)
- ✅ Sem armazenamento de senhas em código
- ✅ Apenas cookies de sessão reutilizados

```bash
# Verifique se seu .gitignore inclui:
.env
linkedin_session.json
candidaturas_tracking.json
*.pdf
debug_*.png
```

---

## 📝 Roadmap

- [x] ~~Relatório detalhado de candidaturas~~ ✅ Implementado
- [x] ~~Score ATS semântico~~ ✅ Implementado
- [x] ~~Filtragem inteligente de vagas~~ ✅ Implementado
- [x] ~~Interface gráfica desktop~~ ✅ Implementado
- [ ] Dashboard web para monitoramento
- [ ] Suporte a múltiplas plataformas (Indeed, Glassdoor)
- [ ] Cache de vagas analisadas
- [ ] Integração com Discord/Telegram para notificações
- [ ] Fine-tuning de modelo customizado
- [ ] Feedback loop automatizado (detectar convites de entrevista por email)

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Para reportar bugs ou sugerir features:

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

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
- [Sentence-Transformers](https://www.sbert.net/)
- [KeyBERT](https://maartengr.github.io/KeyBERT/)

---

**Última atualização**: Abril 2026