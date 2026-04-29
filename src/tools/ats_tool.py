import spacy
# from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json

# O modelo PT é necessário pois possui o parser gramatical (noun_chunks) que extrai os jargões
# Instalado via pyproject.toml como dependência direta (pt-core-news-sm)
nlp = spacy.load("pt_core_news_sm")
COUNT = 0

# Mapa de sinônimos/variações comuns para keyword matching inteligente
SYNONYM_MAP = {
    "ml": ["machine learning", "aprendizado de máquina"],
    "machine learning": ["ml", "aprendizado de máquina"],
    "ai": ["artificial intelligence", "inteligência artificial", "ia"],
    "ia": ["artificial intelligence", "inteligência artificial", "ai"],
    "dl": ["deep learning", "aprendizado profundo"],
    "deep learning": ["dl", "aprendizado profundo"],
    "nlp": ["natural language processing", "processamento de linguagem natural", "pln"],
    "js": ["javascript"],
    "javascript": ["js"],
    "ts": ["typescript"],
    "typescript": ["ts"],
    "k8s": ["kubernetes"],
    "kubernetes": ["k8s"],
    "ci/cd": ["cicd", "continuous integration", "integração contínua"],
    "aws": ["amazon web services"],
    "gcp": ["google cloud platform", "google cloud"],
    "devops": ["dev ops"],
    "sql": ["structured query language"],
    "nosql": ["no-sql", "non-relational"],
    "api": ["apis", "rest api", "restful"],
    "llm": ["llms", "large language model", "large language models"],
    "llms": ["llm", "large language model", "large language models"],
    "rag": ["retrieval augmented generation"],
    "erp": ["enterprise resource planning"],
    "scm": ["supply chain management"],
}

def _keyword_found_with_synonyms(kw_lower: str, cv_lower: str) -> bool:
     """Verifica se a keyword ou algum sinônimo dela está presente no CV."""
     if kw_lower in cv_lower:
          return True
     # Checa sinônimos
     synonyms = SYNONYM_MAP.get(kw_lower, [])
     return any(syn.lower() in cv_lower for syn in synonyms)

def tool_avaliar_score_ats(cv_text: str, keywords: list) -> tuple[str, int]:
     """
     Avalia a aderência do CV procurando correspondência das palavras-chave da vaga.
     Agora com suporte a sinônimos (ex: ML ↔ Machine Learning).
     """

     global COUNT
     cv_lower = cv_text.lower()
     
     if not keywords:
          return "AVALIAÇÃO APROVADA. Nenhuma palavra-chave técnica específica encontrada para cobrar.", COUNT

     # Verifica quais palavras estão no CV (com sinônimos)
     encontradas = []
     faltantes = []

     for kw in keywords:
          kw_lower = kw.strip().lower()
          if not kw_lower: continue
          
          if _keyword_found_with_synonyms(kw_lower, cv_lower):
               encontradas.append(kw)
          else:
               faltantes.append(kw)

     # Calcula o Score
     total_palavras = len(encontradas) + len(faltantes)
     score_porcentagem = round((len(encontradas) / total_palavras) * 100, 2) if total_palavras > 0 else 0

     # Gera o Feedback
     feedback = f"O Score ATS (keyword) atual é: {score_porcentagem}% ({len(encontradas)}/{total_palavras} termos encontrados).\n"

     if COUNT == 10:
          feedback += "\nAVISO: Você atingiu o limite de 10 avaliações. Por favor, Envie o curriculo da maneira que estiver."
          COUNT = 0
          return feedback, COUNT
     
     if score_porcentagem < 60:
          print(f"DEBUG: Score BAIXO - Faltam: {faltantes}")
          feedback += f"AVALIAÇÃO REPROVADA. O currículo ignorou muitas ferramentas vitais. \nTermos OBRIGATÓRIOS que ESQUECEU de incluir: {', '.join(faltantes)}. \nRefaça o currículo inserindo estas palavras nas experiências."
          COUNT += 1
     elif score_porcentagem < 90:
          print(f"DEBUG: Score MEDIANO - Faltam: {faltantes}")
          feedback += f"AVALIAÇÃO MEDIANA. Quase lá. \nAinda faltam as seguintes palavras-chave: {', '.join(faltantes)}. \nIncorpore-as de forma natural no texto."
          COUNT += 1
     else:
          print(f"DEBUG: Score ALTO ({score_porcentagem}%) - O CV está excelente!")
          feedback += "AVALIAÇÃO APROVADA. Excelente aderência."
          COUNT = 0  # Reseta o contador se estiver aprovado
          return feedback, COUNT

     print(f"DEBUG: Counter atual: {COUNT}\nRestão: {10 - COUNT} tentativas restantes antes de atingir o limite.")

          
     return feedback, COUNT


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


def avaliar_score_combinado(cv_text: str, keywords: list, job_description: str) -> tuple[str, float]:
     """
     Score combinado: 40% keyword matching + 60% semântico.
     Retorna feedback detalhado e score final.
     """
     # Score de keywords
     kw_feedback, _ = tool_avaliar_score_ats(cv_text, keywords)
     cv_lower = cv_text.lower()
     kw_encontradas = sum(1 for kw in keywords if _keyword_found_with_synonyms(kw.strip().lower(), cv_lower))
     kw_score = (kw_encontradas / max(len(keywords), 1)) * 100

     # Score semântico
     sem_feedback, sem_score = avaliar_score_ats_semantico(cv_text, job_description)

     # Combinação ponderada
     score_final = (kw_score * 0.4) + (sem_score * 0.6)

     feedback = (
          f"=== AVALIAÇÃO COMBINADA ===\n"
          f"Score Keyword (40%): {kw_score:.1f}%\n"
          f"Score Semântico (60%): {sem_score:.1f}%\n"
          f"SCORE FINAL: {score_final:.1f}%\n\n"
          f"{kw_feedback}\n{sem_feedback}"
     )

     return feedback, score_final


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


def _extract_terms_regex(text: str) -> list:
    """Extração de termos por regex — fallback quando SpaCy não é adequado.
    Captura termos técnicos, acrônimos e compostos capitalizados."""
    import re
    termos = set()
    
    # 1. Acrônimos e termos em maiúsculas (AI, ML, NLP, SQL, etc.)
    acronyms = re.findall(r'\b[A-Z]{2,}(?:\.[A-Z]+)*\b', text)
    termos.update(acronyms)
    
    # 2. Termos compostos capitalizados ("Data Labeling", "Machine Learning")
    capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
    termos.update(capitalized)
    
    # 3. Termos técnicos com hífen ou barra ("Fact-Checking", "CI/CD")
    hyphenated = re.findall(r'\b[A-Za-z]+-[A-Za-z]+\b', text)
    termos.update(hyphenated)
    
    # 4. Palavras capitalizadas isoladas (potenciais termos técnicos)
    single_caps = re.findall(r'\b[A-Z][a-z]{2,}\b', text)
    # Filtra palavras comuns de início de frase
    common_starts = {"The", "This", "That", "What", "Where", "When", "How", "Who",
                     "Our", "Your", "Their", "Some", "Any", "All", "Each", "Every",
                     "And", "But", "Not", "Are", "Were", "Was", "Has", "Had",
                     "Will", "Can", "May", "Must", "Should", "Could", "Would",
                     "About", "Over", "Under", "With", "From", "Into", "Also",
                     "Como", "Para", "Sobre", "Uma", "Nosso", "Nossa", "Você"}
    for w in single_caps:
        if w not in common_starts:
            termos.add(w)
    
    return list(termos)


def extract_entities(text):
    """Extrai entidades do texto usando SpaCy (PT) ou regex (EN)."""
    lang = _detect_language(text)
    
    if lang == "pt":
        # SpaCy PT funciona bem para português
        doc = nlp(text)
        termos = set()
        for chunk in doc.noun_chunks:
            termos.add(chunk.text.strip())
        return list(termos)
    else:
        # Para inglês, SpaCy PT não funciona — usar regex
        print("  ℹ️ Texto em inglês detectado — usando extração por regex")
        return _extract_terms_regex(text)

from keybert import KeyBERT
from nltk.corpus import stopwords
import nltk

try:
    nltk.download('stopwords', quiet=True)
    stop_words_pt = set(stopwords.words('portuguese'))
    stop_words_en = set(stopwords.words('english'))
    stop_words_combined = list(stop_words_pt.union(stop_words_en))
except Exception:
    stop_words_combined = ["de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "é", "com", "não", "uma", "os", "no", "se", "na", "por", "mais", "as", "dos", "como", "mas", "foi", "ao", "ele", "das", "tem", "à", "seu", "sua", "ou", "ser", "quando", "muito", "há", "nos", "já", "está", "eu", "também", "só", "pelo", "pela", "até", "isso", "ela", "entre", "era", "depois", "sem", "mesmo", "aos", "ter", "seus", "quem", "nas", "me", "esse", "eles", "estão", "você", "tinha", "foram", "essa", "num", "nem", "suas", "meu", "às", "minha", "têm", "numa", "pelos", "elas", "havia", "seja", "qual", "será", "nós", "tenho", "lhe", "deles", "essas", "esses", "pelas", "este", "fosse", "dele", "tu", "te", "vocês", "vos", "lhes", "meus", "minhas", "teu", "tua", "teus", "tuas", "nosso", "nossa", "nossos", "nossas", "dela", "delas", "esta", "estes", "estas", "aquele", "aquela", "aqueles", "aquelas", "isto", "aquilo", "estou", "está", "estamos", "estão", "estive", "esteve", "estivemos", "estiveram", "estava", "estávamos", "estavam", "estivera", "estivéramos", "esteja", "sejamos", "sejam", "fosse", "fôssemos", "fossem", "for", "formos", "forem", "serei", "será", "seremos", "serão", "seria", "seríamos", "seriam", "tenho", "tem", "temos", "tém", "tinha", "tínhamos", "tinham", "tive", "teve", "tivemos", "tiveram", "tivera", "tivéramos", "tenha", "tenhamos", "tenham", "tivesse", "tivéssemos", "tivessem", "tiver", "tivermos", "tiverem", "terei", "terá", "teremos", "terão", "teria", "teríamos", "teriam", "the", "in", "to", "and", "of", "a", "for", "is", "with", "on", "as", "are", "be", "that", "this", "it", "or", "by", "an", "will", "we"]

kw_model = KeyBERT(model="all-MiniLM-L6-v2")

def extrator_keywords_keybert(text):
    keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1,2), stop_words=stop_words_combined, top_n=30)

    return [kw[0] for kw in keywords]

# Termos técnicos curtos que NUNCA devem ser filtrados
PROTECTED_TERMS = {
    "ai", "ml", "dl", "cv", "nlp", "qa", "ui", "ux", "db", "ci", "cd",
    "api", "sql", "css", "git", "aws", "gcp", "rag", "llm", "hpc", "erp",
    "scm", "etl", "rpa", "ocr", "gpu", "cpu", "sre", "iot", "bi",
    "r", "c", "go",  # linguagens de programação de 1-2 chars
}

STOPWORDS_PT_EXTRA = {
    # PT
    "vaga", "sobre", "empresa", "você", "experiência", "conhecimento",
    "habilidades", "trabalho", "como", "para", "nós", "nossa", "nossos",
    "será", "requisitos", "diferenciais", "responsabilidades", "benefícios",
    "aqui", "identificando", "posição", "atuar", "ter",
    # EN
    "role", "about", "company", "you", "experience", "knowledge",
    "skills", "work", "how", "for", "we", "our", "us",
    "will", "requirements", "differentials", "responsibilities", "benefits",
    "here", "identifying", "position", "act", "have", "looking", "seeking",
    "candidate", "must", "strong", "preferred", "nice", "description", "apply",
    # Genéricos extras EN
    "overview", "key", "join", "team", "help", "ensure", "able",
    "access", "currently", "recent", "enrolled", "encouraged",
}

def clean_and_validate_term(term):
    term = term.lower().strip()
    
    # 1. Remover ruído de pontuação nas pontas
    term = term.strip(".,()/-*[]:")
    
    # 0. Se é um termo técnico protegido, aceitar imediatamente
    if term in PROTECTED_TERMS:
        return term
    
    words = term.split()
    
    # 2. Se for muito longo (mais de 4 palavras), descartar
    if len(words) > 4 or len(words) == 0:
        return None
        
    # 3. Filtrar se TODAS as palavras estiverem nas stopwords
    #    Mas NÃO filtrar se alguma palavra for um termo protegido
    if all((w in STOPWORDS_PT_EXTRA or len(w) <= 2) and w not in PROTECTED_TERMS for w in words):
        return None
        
    # 4. Remover termos que começam com preposições quebradas
    bad_starts = ["em ", "de ", "com ", "para ", "uma ", "um ", "in ", "of ", "with ", "to ", "an "]
    if any(term.startswith(bad) for bad in bad_starts):
        return None
        
    return term

def pre_process_pipeline(terms):
    """Substitui o hard_filter_terms por algo que funciona melhor"""
    cleaned = []
    for t in terms:
        valid_term = clean_and_validate_term(t)
        if valid_term and len(valid_term) > 2:
            cleaned.append(valid_term)
            
    return list(set(cleaned))