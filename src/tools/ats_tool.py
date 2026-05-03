import spacy
import re
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# O modelo PT é necessário pois possui o parser gramatical (noun_chunks) que extrai os jargões
# Instalado via pyproject.toml como dependência direta (pt-core-news-sm)
nlp = spacy.load("pt_core_news_sm")

# ═══════════════════════════════════════════════════════════════════════════════
# SYNONYM MAP — Mapeamento bidirecional de sinônimos/variações técnicas
# Cada entrada mapeia um termo normalizado para suas variações conhecidas.
# Usado para keyword matching inteligente (ex: "LLM" matcha com "Large Language Model").
# ═══════════════════════════════════════════════════════════════════════════════

SYNONYM_MAP = {
    # --- AI / ML Core ---
    "ml": ["machine learning", "aprendizado de máquina"],
    "machine learning": ["ml", "aprendizado de máquina"],
    "ai": ["artificial intelligence", "inteligência artificial", "ia"],
    "ia": ["artificial intelligence", "inteligência artificial", "ai"],
    "dl": ["deep learning", "aprendizado profundo"],
    "deep learning": ["dl", "aprendizado profundo"],
    "nlp": ["natural language processing", "processamento de linguagem natural", "pln"],
    "pln": ["nlp", "natural language processing", "processamento de linguagem natural"],
    "cv": ["computer vision", "visão computacional"],
    "computer vision": ["cv", "visão computacional"],
    "genai": ["generative ai", "gen ai", "ia generativa"],
    "generative ai": ["genai", "gen ai", "ia generativa"],
    "llm": ["llms", "large language model", "large language models", "modelo de linguagem"],
    "llms": ["llm", "large language model", "large language models", "modelo de linguagem"],
    "rag": ["retrieval augmented generation", "retrieval-augmented generation"],
    "agentic": ["agentic ai", "agentes de ia", "ai agents", "multi-agent"],
    "multi-agent": ["multi agent", "multiagent", "multi-agente", "agentic"],

    # --- Linguagens de Programação ---
    "js": ["javascript"],
    "javascript": ["js"],
    "ts": ["typescript"],
    "typescript": ["ts"],
    "py": ["python"],
    "python": ["py"],

    # --- Frameworks & Libs ---
    "pytorch": ["torch"],
    "torch": ["pytorch"],
    "tensorflow": ["tf"],
    "tf": ["tensorflow"],
    "scikit-learn": ["sklearn", "scikit learn"],
    "sklearn": ["scikit-learn", "scikit learn"],
    "fastapi": ["fast api"],
    "langchain": ["lang chain"],
    "crewai": ["crew ai"],
    "llamaindex": ["llama index", "llama_index"],

    # --- Cloud & Infra ---
    "k8s": ["kubernetes"],
    "kubernetes": ["k8s"],
    "aws": ["amazon web services"],
    "amazon web services": ["aws"],
    "gcp": ["google cloud platform", "google cloud"],
    "google cloud": ["gcp", "google cloud platform"],
    "azure": ["microsoft azure"],
    "ci/cd": ["cicd", "ci cd", "continuous integration", "integração contínua"],
    "devops": ["dev ops"],
    "docker": ["containers", "containerização", "containerization"],
    "containerização": ["docker", "containers", "containerization"],
    "hpc": ["high performance computing", "computação de alto desempenho", "alto desempenho"],
    "alto desempenho": ["hpc", "high performance computing"],

    # --- Dados ---
    "sql": ["structured query language"],
    "nosql": ["no-sql", "non-relational", "não relacional"],
    "etl": ["extract transform load"],
    "erp": ["enterprise resource planning", "erp protheus", "protheus"],
    "erp protheus": ["erp", "protheus", "totvs protheus", "totvs"],
    "protheus": ["erp protheus", "erp", "totvs protheus", "totvs"],
    "totvs": ["totvs protheus", "erp protheus", "protheus"],
    "totvs protheus": ["totvs", "erp protheus", "protheus"],
    "bi": ["business intelligence", "inteligência de negócios"],

    # --- APIs & Protocolos ---
    "api": ["apis", "api rest", "rest api", "via api"],
    "apis": ["api", "via api"],
    "rest": ["restful", "rest api", "api rest"],
    "restful": ["rest", "rest api", "api rest"],
    "graphql": ["graph ql"],
    "grpc": ["g rpc"],

    # --- RAG (todas as variações contam como o mesmo conceito) ---
    "rag": ["retrieval augmented generation", "retrieval-augmented generation",
            "retrieval-augmented", "augmented generation", "retrieval", "augmented", "generation"],
    "retrieval augmented generation": ["rag", "retrieval-augmented generation"],
    "retrieval-augmented generation": ["rag", "retrieval augmented generation"],
    "retrieval-augmented": ["rag"],
    "retrieval": ["rag"],
    "augmented generation": ["rag"],
    "augmented": ["rag"],
    "generation": ["rag"],

    # --- Metodologias ---
    "scm": ["supply chain management"],
    "mlops": ["ml ops", "machine learning operations"],
    "deploy": ["deployment", "implantação"],
    "sre": ["site reliability engineering"],
    "agile": ["ágil", "metodologia ágil"],

    # --- Frameworks Agênticos ---
    "autogen": ["auto gen", "auto-gen"],
    "langgraph": ["lang graph", "lang-graph"],
    "crewai": ["crew ai", "crew-ai"],
    "agno": [],
}


def _keyword_found_with_synonyms(kw_lower: str, cv_lower: str) -> bool:
    """
    Verifica se a keyword ou algum sinônimo dela está presente no CV.
    Usa word boundary matching para evitar falsos positivos
    (ex: "AI" não deve matchar dentro de "email").
    """
    # Termos muito curtos (1-2 chars) precisam de word boundary rígido
    if len(kw_lower) <= 3:
        pattern = r'\b' + re.escape(kw_lower) + r'\b'
        if re.search(pattern, cv_lower):
            return True
    else:
        # Termos mais longos: substring match é seguro
        if kw_lower in cv_lower:
            return True

    # Checa sinônimos com a mesma lógica
    synonyms = SYNONYM_MAP.get(kw_lower, [])
    for syn in synonyms:
        syn_lower = syn.lower()
        if len(syn_lower) <= 3:
            pattern = r'\b' + re.escape(syn_lower) + r'\b'
            if re.search(pattern, cv_lower):
                return True
        else:
            if syn_lower in cv_lower:
                return True

    return False


def tool_avaliar_score_ats(cv_text: str, keywords: list, attempt: int = 0) -> tuple[str, int]:
    """
    Avalia a aderência do CV procurando correspondência das palavras-chave da vaga.
    Com suporte a sinônimos (ex: ML ↔ Machine Learning) e word boundary matching.

    Args:
        cv_text: Texto completo do CV gerado
        keywords: Lista de keywords extraídas da vaga
        attempt: Número da tentativa atual (para controle de loop)

    Returns:
        Tuple (feedback_string, attempt_count)
    """
    cv_lower = cv_text.lower()

    if not keywords:
        return "AVALIAÇÃO APROVADA. Nenhuma palavra-chave técnica específica encontrada para cobrar.", attempt

    # Verifica quais palavras estão no CV (com sinônimos)
    encontradas = []
    faltantes = []

    for kw in keywords:
        kw_lower = kw.strip().lower()
        if not kw_lower:
            continue

        if _keyword_found_with_synonyms(kw_lower, cv_lower):
            encontradas.append(kw)
        else:
            faltantes.append(kw)

    # Calcula o Score
    total_palavras = len(encontradas) + len(faltantes)
    score_porcentagem = round((len(encontradas) / total_palavras) * 100, 2) if total_palavras > 0 else 0

    # Gera o Feedback
    feedback = f"O Score ATS (keyword) atual é: {score_porcentagem}% ({len(encontradas)}/{total_palavras} termos encontrados).\n"

    if score_porcentagem < 50:
        print(f"DEBUG: Score BAIXO - Faltam: {faltantes}")
        feedback += f"AVALIAÇÃO REPROVADA. O currículo ignorou muitas ferramentas vitais. \nTermos OBRIGATÓRIOS que ESQUECEU de incluir: {', '.join(faltantes)}. \nRefaça o currículo inserindo estas palavras nas experiências."
    elif score_porcentagem < 75:
        print(f"DEBUG: Score MEDIANO - Faltam: {faltantes}")
        feedback += f"AVALIAÇÃO MEDIANA. Quase lá. \nAinda faltam as seguintes palavras-chave: {', '.join(faltantes)}. \nIncorpore-as de forma natural no texto."
    else:
        print(f"DEBUG: Score ALTO ({score_porcentagem}%) - O CV está excelente!")
        feedback += "AVALIAÇÃO APROVADA. Excelente aderência."
        return feedback, attempt

    print(f"DEBUG: Tentativa atual: {attempt}")

    return feedback, attempt


def avaliar_score_ats_semantico(cv_text: str, job_description: str) -> tuple[str, float]:
    """
    Avalia a aderência do CV à vaga usando similaridade semântica (embeddings)
    em vez de keyword matching exato. Complementa o score de keywords.
    """
    from sentence_transformers import SentenceTransformer

    _embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    # Divide o CV e a vaga em sentenças/chunks significativos
    cv_sentences = [s.strip() for s in cv_text.split('\n') if len(s.strip()) > 20]
    job_sentences = [s.strip() for s in job_description.split('\n') if len(s.strip()) > 20]

    if not cv_sentences or not job_sentences:
        return "Erro: texto insuficiente para análise semântica.", 0.0

    # Gera embeddings
    cv_embeddings = _embed_model.encode(cv_sentences)
    job_embeddings = _embed_model.encode(job_sentences)

    # Para cada requisito da vaga, encontra a melhor correspondência no CV
    similarity_matrix = cosine_similarity(job_embeddings, cv_embeddings)

    # Score = média das melhores correspondências de cada requisito
    best_matches = similarity_matrix.max(axis=1)
    overall_score = float(np.mean(best_matches)) * 100

    # Identifica gaps (requisitos com baixa correspondência)
    gaps = []
    for i, score in enumerate(best_matches):
        if score < 0.4:
            gaps.append((job_sentences[i], round(score * 100, 1)))

    feedback = f"Score Semântico ATS: {overall_score:.1f}%\n"
    if gaps:
        feedback += "\nGaps identificados (baixa correspondência semântica):\n"
        for gap_text, gap_score in gaps[:5]:
            feedback += f"  - [{gap_score}%] {gap_text[:80]}...\n"

    return feedback, overall_score


def avaliar_score_combinado(cv_text: str, keywords: list, job_description: str,
                            attempt: int = 0) -> tuple[str, float]:
    """
    Score combinado: 70% keyword matching + 30% semântico.
    Reflete a realidade dos ATS reais que são predominantemente keyword-based.

    Returns:
        Tuple (feedback_detalhado, score_final)
    """
    # Score de keywords
    kw_feedback, _ = tool_avaliar_score_ats(cv_text, keywords, attempt)
    cv_lower = cv_text.lower()
    kw_encontradas = sum(1 for kw in keywords if _keyword_found_with_synonyms(kw.strip().lower(), cv_lower))
    kw_score = (kw_encontradas / max(len(keywords), 1)) * 100

    # Score semântico
    try:
        sem_feedback, sem_score = avaliar_score_ats_semantico(cv_text, job_description)
    except Exception as e:
        print(f"⚠️ Erro no score semântico: {e}. Usando apenas keywords.")
        sem_feedback = "Score semântico indisponível."
        sem_score = kw_score  # Fallback: usa keyword score

    # Combinação ponderada: 70% keyword + 30% semântico
    score_final = (kw_score * 0.7) + (sem_score * 0.3)

    # Determina veredito com base no score FINAL
    if score_final >= 75:
        veredito = "APROVADA"
    elif score_final >= 50:
        veredito = "MEDIANO"
    else:
        veredito = "REPROVADA"

    feedback = (
        f"=== AVALIAÇÃO COMBINADA ===\n"
        f"Score Keyword (70%): {kw_score:.1f}%\n"
        f"Score Semântico (30%): {sem_score:.1f}%\n"
        f"SCORE FINAL: {score_final:.1f}%\n"
        f"VEREDITO: {veredito}\n\n"
        f"{kw_feedback}\n{sem_feedback}"
    )

    return feedback, score_final


# ═══════════════════════════════════════════════════════════════════════════════
# EXTRAÇÃO DE ENTIDADES E KEYWORDS
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_language(text: str) -> str:
    """Detecta se o texto é predominantemente em inglês ou português."""
    en_markers = ["the ", "and ", "with ", "for ", "you ", "will ", "are ", "this ", "that ", "have ",
                  "requirements", "responsibilities", "experience", "looking for", "about the"]
    pt_markers = ["você ", "para ", "com ", "requisitos", "responsabilidades", "experiência",
                  "sobre a vaga", "estamos buscando", "habilidades"]

    text_lower = text.lower()
    en_count = sum(1 for m in en_markers if m in text_lower)
    pt_count = sum(1 for m in pt_markers if m in text_lower)

    return "en" if en_count > pt_count else "pt"


# Dicionário curado de termos técnicos que devem ser capturados mesmo em lowercase.
# Usado como supplemento ao regex de capitalização.
CURATED_TECH_TERMS = {
    # Linguagens
    "python", "java", "javascript", "typescript", "golang", "rust", "scala", "kotlin",
    "ruby", "swift", "dart", "julia", "matlab", "perl", "lua", "elixir",
    # Frameworks & Libs
    "react", "angular", "vue", "svelte", "nextjs", "next.js", "nuxt", "django",
    "flask", "fastapi", "spring", "express", "nestjs", "rails",
    "pytorch", "tensorflow", "keras", "scikit-learn", "pandas", "numpy", "scipy",
    "matplotlib", "seaborn", "plotly", "streamlit", "gradio",
    "langchain", "llamaindex", "crewai", "autogen", "agno",
    "huggingface", "transformers", "ollama",
    # Cloud & Infra
    "docker", "kubernetes", "terraform", "ansible", "jenkins", "github actions",
    "circleci", "gitlab", "prometheus", "grafana", "datadog",
    "kafka", "rabbitmq", "redis", "elasticsearch", "mongodb", "postgresql",
    "mysql", "sqlite", "dynamodb", "cassandra",
    "nginx", "apache", "gunicorn", "uvicorn",
    # AI/ML Específico
    "embeddings", "fine-tuning", "finetuning", "fine tuning",
    "prompt engineering", "retrieval augmented generation",
    "reinforcement learning", "supervised learning", "unsupervised learning",
    "neural networks", "convolutional", "transformer", "attention mechanism",
    "tokenization", "vectorization", "chunking",
    # DevOps & Metodologias
    "agile", "scrum", "kanban", "microservices", "serverless",
    "ci/cd", "devops", "mlops", "dataops", "gitops",
    # Protocolos & Padrões
    "rest", "graphql", "grpc", "websocket", "oauth", "jwt",
}


def _extract_terms_regex(text: str) -> list:
    """Extração de termos por regex — funciona para qualquer idioma.
    Captura termos técnicos, acrônimos, compostos capitalizados,
    e termos do dicionário curado."""
    termos = set()

    # 1. Acrônimos e termos em maiúsculas (AI, ML, NLP, SQL, etc.)
    acronyms = re.findall(r'\b[A-Z]{2,}(?:\.[A-Z]+)*\b', text)
    termos.update(acronyms)

    # 2. Termos compostos capitalizados ("Data Labeling", "Machine Learning")
    capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
    termos.update(capitalized)

    # 3. Termos técnicos com hífen ou barra ("Fact-Checking", "CI/CD")
    hyphenated = re.findall(r'\b[A-Za-z]+[-/][A-Za-z]+\b', text)
    termos.update(hyphenated)

    # 4. Palavras capitalizadas isoladas (potenciais termos técnicos)
    single_caps = re.findall(r'\b[A-Z][a-z]{2,}\b', text)
    common_starts = {"The", "This", "That", "What", "Where", "When", "How", "Who",
                     "Our", "Your", "Their", "Some", "Any", "All", "Each", "Every",
                     "And", "But", "Not", "Are", "Were", "Was", "Has", "Had",
                     "Will", "Can", "May", "Must", "Should", "Could", "Would",
                     "About", "Over", "Under", "With", "From", "Into", "Also",
                     "Como", "Para", "Sobre", "Uma", "Nosso", "Nossa", "Você",
                     "They", "There", "Then", "Than", "These", "Those",
                     "Being", "Been", "Before", "After", "During", "While",
                     "Including", "Using", "Working", "Building", "Creating",
                     "Looking", "Seeking", "Hiring", "Joining", "Growing"}
    for w in single_caps:
        if w not in common_starts:
            termos.add(w)

    # 5. Termos do dicionário curado (captura termos em lowercase)
    text_lower = text.lower()
    for tech_term in CURATED_TECH_TERMS:
        if len(tech_term) <= 3:
            # Word boundary para termos curtos
            if re.search(r'\b' + re.escape(tech_term) + r'\b', text_lower):
                termos.add(tech_term)
        else:
            if tech_term in text_lower:
                termos.add(tech_term)

    return list(termos)


def strip_non_technical_sections(text: str) -> str:
    """Remove seções de benefícios, sobre a empresa, e RH da descrição da vaga.
    Essas seções poluem a extração de keywords com termos irrelevantes
    como 'odontológico', 'wellhub', 'day-off', 'nutricionista', etc.
    
    Mantém apenas: responsabilidades, requisitos, qualificações, diferenciais."""
    # Marcadores que indicam INÍCIO de seção não-técnica
    cut_markers_pt = [
        r'benefícios',
        r'o que oferecemos',
        r'oferecemos',
        r'nossos benefícios',
        r'vantagens',
        r'por que trabalhar',
        r'por que se juntar',
        r'sobre a empresa',
        r'sobre nós',
        r'quem somos',
        r'nossa cultura',
        r'nosso time',
        r'ambiente de trabalho',
        r'remuneração',
        r'pacote de benefícios',
        r'o que você vai encontrar',
        r'etapas do processo',
        r'processo seletivo',
        r'informações adicionais',
    ]
    cut_markers_en = [
        r'benefits',
        r'what we offer',
        r'perks',
        r'why join us',
        r'about us',
        r'about the company',
        r'our culture',
        r'compensation',
        r'equal opportunity',
        r'hiring process',
    ]
    
    all_markers = cut_markers_pt + cut_markers_en
    text_lower = text.lower()
    
    # Encontra o marcador que aparece mais cedo no texto
    earliest_cut = len(text)
    for marker in all_markers:
        # Procura o marcador como início de linha ou após quebra de linha
        pattern = r'(?:^|\n)\s*(?:#+\s*|\*+\s*|•\s*|\d+\.\s*)?(' + marker + r')'
        match = re.search(pattern, text_lower)
        if match and match.start() < earliest_cut:
            # Só corta se o marcador está na segunda metade do texto
            # (evita cortar se "benefícios" aparece como skill no início)
            if match.start() > len(text) * 0.3:
                earliest_cut = match.start()
    
    if earliest_cut < len(text):
        cleaned = text[:earliest_cut].strip()
        cut_pct = round((1 - len(cleaned) / len(text)) * 100)
        print(f"  ✂️ Seção de benefícios/RH removida ({cut_pct}% do texto cortado)")
        return cleaned
    
    return text


def extract_entities(text):
    """Extrai entidades do texto usando SpaCy (PT) + regex (ambos idiomas).
    Combina as duas abordagens para cobertura máxima.
    IMPORTANTE: Remove seções de benefícios/RH antes da extração."""
    # PASSO 0: Remover seções de benefícios/RH
    text = strip_non_technical_sections(text)
    
    lang = _detect_language(text)
    termos = set()

    # Sempre usa regex — funciona para qualquer idioma
    regex_terms = _extract_terms_regex(text)
    termos.update(regex_terms)

    if lang == "pt":
        # SpaCy PT adiciona noun_chunks extras para português
        try:
            doc = nlp(text)
            for chunk in doc.noun_chunks:
                chunk_text = chunk.text.strip()
                # Filtro: SpaCy noun_chunks só aceita se tiver pelo menos 1 palavra técnica
                if len(chunk_text.split()) <= 3:  # Não aceitar chunks longos
                    termos.add(chunk_text)
        except Exception:
            pass
    else:
        print("  ℹ️ Texto em inglês detectado — usando extração por regex + dicionário curado")

    return list(termos)


from keybert import KeyBERT
from nltk.corpus import stopwords
import nltk

try:
    nltk.download('stopwords', quiet=True)
    stop_words_pt = set(stopwords.words('portuguese'))
    stop_words_en = set(stopwords.words('english'))
    stop_words_combined = list(stop_words_pt.union(stop_words_en))
except Exception:
    stop_words_combined = ["de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "é", "com", "não", "uma", "os", "no", "se", "na", "por", "mais", "as", "dos", "como", "mas", "the", "in", "to", "and", "of", "a", "for", "is", "with", "on", "as", "are", "be", "that", "this", "it", "or", "by", "an", "will", "we"]

kw_model = KeyBERT(model="all-MiniLM-L6-v2")

def extrator_keywords_keybert(text):
    # Remove seções de benefícios/RH antes da extração
    text_limpo = strip_non_technical_sections(text)
    keywords = kw_model.extract_keywords(text_limpo, keyphrase_ngram_range=(1,2), stop_words=stop_words_combined, top_n=30)
    return [kw[0] for kw in keywords]


# ═══════════════════════════════════════════════════════════════════════════════
# PRÉ-PROCESSAMENTO DE TERMOS
# ═══════════════════════════════════════════════════════════════════════════════

# Termos técnicos curtos que NUNCA devem ser filtrados
PROTECTED_TERMS = {
    "ai", "ml", "dl", "cv", "nlp", "qa", "ui", "ux", "db", "ci", "cd",
    "api", "sql", "css", "git", "aws", "gcp", "rag", "llm", "hpc", "erp",
    "scm", "etl", "rpa", "ocr", "gpu", "cpu", "sre", "iot", "bi",
    "r", "c", "go",  # linguagens de programação de 1-2 chars
    "js", "ts", "tf", "k8s",
}

STOPWORDS_PT_EXTRA = {
    # PT — Termos genéricos de vagas/RH
    "vaga", "sobre", "empresa", "empresas", "você", "experiência", "conhecimento",
    "habilidades", "trabalho", "como", "para", "nós", "nossa", "nossos", "nosso",
    "será", "requisitos", "diferenciais", "responsabilidades", "benefícios",
    "aqui", "identificando", "posição", "atuar", "ter", "modelo", "contratação",
    "time", "equipe", "célula", "área", "setor",
    "somos", "estamos", "expandindo", "buscando", "procurando",
    "focada", "focado", "consultoria", "tecnologia", "transformação",
    "remoto", "presencial", "híbrido", "contrato", "clt", "pj",
    "ecossistema", "informações", "serviços", "processos",
    "garantir", "colaborar", "desenvolver", "implementar", "manter", "construir", "criar",
    "robusto", "robusta", "complexos", "complexo", "digital",
    "avançado", "intermediário", "equivalente",
    # PT — Termos contextuais não-técnicos
    "produção", "integração", "automação", "manipulação",
    "extração", "processamento", "versionamento", "orquestração",
    "familiaridade", "infraestrutura",
    # PT — Benefícios/RH (vagas do LinkedIn têm seções inteiras disso)
    "saúde", "odontológico", "nutricionista", "psicólogo", "farmácia",
    "wellhub", "gympass", "totalpass", "vale", "refeição", "alimentação",
    "transporte", "estacionamento", "plano", "seguro", "vida",
    "aniversário", "day-off", "dayoff", "day", "celebre", "cuide",
    "desconto", "subsídio", "bolsa", "auxílio", "bônus", "premiação",
    "férias", "licença", "maternidade", "paternidade",
    "oportunidades", "crescimento", "carreira", "vivência",
    "ambiente", "dinâmico", "inovador", "acolhedor",
    "pessoas", "diversidade", "inclusão", "pertencimento",
    "oferecemos", "vantagens", "clube", "acompanhamento",
    "liderança", "mentoria", "treinamento",
    # PT — Verbos genéricos de vagas
    "participar", "contribuir", "apoiar", "atuar", "executar",
    "realizar", "auxiliar", "acompanhar", "elaborar", "propor",
    "buscamos", "buscando", "precisamos", "procuramos",
    # PT — Substantivos genéricos
    "evolução", "construção", "decisões", "negócios", "soluções",
    "mercado", "lógica", "boa", "base", "jeito", "anos",
    "desenvolvimento", "interfaces", "produto", "execução",
    "desenvolvedor", "programação", "front", "end", "minima",
    "conhecimento", "experiência", "futuro", "modernas",
    "vivência", "familiaridade", "diferencial", "relevante",
    # EN — Termos genéricos de vagas/RH
    "role", "about", "company", "you", "experience", "knowledge",
    "skills", "work", "how", "for", "we", "our", "us",
    "will", "requirements", "differentials", "responsibilities", "benefits",
    "here", "identifying", "position", "act", "have", "looking", "seeking",
    "candidate", "must", "strong", "preferred", "nice", "description", "apply",
    "overview", "key", "join", "team", "help", "ensure", "able",
    "access", "currently", "recent", "enrolled", "encouraged",
    "ideal", "passionate", "motivated", "driven", "dynamic",
    "build", "create", "develop", "implement", "maintain",
    # EN — Benefits
    "health", "dental", "vision", "insurance", "pto", "vacation",
    "401k", "equity", "bonus", "perks", "wellness", "gym",
}

# Termos que NUNCA devem ser aceitos como keywords ATS, mesmo em compostos
BLACKLISTED_TERMS = {
    "o time", "a empresa", "a vaga", "as empresas", "os requisitos",
    "nossa célula", "nosso time", "a equipe", "o ecossistema",
    "o erp", "a consultoria", "o candidato",
    "erp responsabilidades", "erp desenvolver", "ia erp", "autônomos erp",
    "ações erp", "artificial automatizar", "engineer integração",
    "rest implementar", "avançado modelo", "modelos produção",
    "web equivalente", "manter apis",
    "informações protheus", "nossa célula",
    "orquestração serviços", "serviços ia", "agentes ia",
    "extração processamento", "processamento informações",
    "implementar sistemas", "executar ações", "integração robusta",
    "interpretar linguagem", "dados corporativos",
    "automatizar processos", "consulta inteligente",
}

def clean_and_validate_term(term):
    term = term.lower().strip()

    # 1. Remover ruído de pontuação nas pontas
    term = term.strip(".,()/-*[]:")

    # 0. Se é um termo técnico protegido, aceitar IMEDIATAMENTE
    if term in PROTECTED_TERMS:
        return term

    # BLACKLIST: rejeitar termos sabidamente ruins
    if term in BLACKLISTED_TERMS:
        return None

    words = term.split()

    # 2. Se for muito longo (mais de 3 palavras) ou vazio, descartar
    if len(words) > 3 or len(words) == 0:
        return None

    # 3. Filtrar se TODAS as palavras estiverem nas stopwords
    if all((w in STOPWORDS_PT_EXTRA or len(w) <= 2) and w not in PROTECTED_TERMS for w in words):
        return None

    # 4. Se é um termo de 1 palavra, verificar se é genérico
    if len(words) == 1 and words[0] in STOPWORDS_PT_EXTRA:
        return None

    # 5. Remover termos que começam com artigos ou preposições
    bad_starts = [
        "em ", "de ", "com ", "para ", "uma ", "um ", "in ", "of ", "with ", "to ", "an ",
        "o ", "a ", "os ", "as ", "ao ", "à ", "no ", "na ", "nos ", "nas ",
        "do ", "da ", "dos ", "das ", "pelo ", "pela ",
        "the ", "this ", "that ", "our ", "your ", "their ",
    ]
    if any(term.startswith(bad) for bad in bad_starts):
        return None

    # 6. Se contém marcadores de seção, é seção de vaga, não keyword
    section_markers = ["responsabilidades", "diferenciais", "requisitos", "benefícios", "contratação"]
    if any(marker in term for marker in section_markers):
        return None

    # 7. Rejeitar termos que contêm números ("2 anos", "3 meses", etc.)
    if re.search(r'\d', term):
        return None

    # 8. Para termos de 2 palavras: rejeitar se AMBAS são genéricas
    if len(words) == 2:
        has_tech = any(w in CURATED_TECH_TERMS or w in PROTECTED_TERMS for w in words)
        both_stop = all(w in STOPWORDS_PT_EXTRA or len(w) <= 3 for w in words)
        if both_stop and not has_tech:
            return None

    return term

def pre_process_pipeline(terms):
    """Pipeline de limpeza e validação de termos extraídos.
    Corrigido: termos protegidos (AI, ML, Go, etc.) NUNCA são filtrados.
    Aprimorado: filtragem agressiva de lixo textual de vagas."""
    cleaned = []
    for t in terms:
        valid_term = clean_and_validate_term(t)
        if valid_term is None:
            continue
        # Termos protegidos passam independente do comprimento
        if valid_term in PROTECTED_TERMS or len(valid_term) > 2:
            cleaned.append(valid_term)

    return list(set(cleaned))