import spacy
# from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json

# O modelo PT é necessário pois possui o parser gramatical (noun_chunks) que extrai os jargões
nlp = spacy.load("pt_core_news_sm")

def tool_avaliar_score_ats(cv_text: str, keywords: list) -> str:
    """
    Avalia a aderência do CV procurando a correspondência exata das palavras-chave da vaga.
    """
    cv_lower = cv_text.lower()
    
    if not keywords:
        return "AVALIAÇÃO APROVADA. Nenhuma palavra-chave técnica específica encontrada para cobrar."

    # Verifica quais palavras estão no CV
    encontradas = []
    faltantes = []

    for kw in keywords:
        kw_lower = kw.strip().lower()
        if not kw_lower: continue
        
        if kw_lower in cv_lower:
            encontradas.append(kw)
        else:
            faltantes.append(kw)

    # Calcula o Score
    total_palavras = len(encontradas) + len(faltantes)
    score_porcentagem = round((len(encontradas) / total_palavras) * 100, 2) if total_palavras > 0 else 0

    # Gera o Feedback
    feedback = f"O Score ATS atual é: {score_porcentagem}% ({len(encontradas)}/{total_palavras} termos encontrados).\n"
    
    if score_porcentagem < 60:
         print(f"DEBUG: Score BAIXO - Faltam: {faltantes}")
         feedback += f"AVALIAÇÃO REPROVADA. O currículo ignorou muitas ferramentas vitais. \nTermos OBRIGATÓRIOS que ESQUECEU de incluir: {', '.join(faltantes)}. \nRefaça o currículo inserindo estas palavras nas experiências."
    elif score_porcentagem < 90:
         print(f"DEBUG: Score MEDIANO - Faltam: {faltantes}")
         feedback += f"AVALIAÇÃO MEDIANA. Quase lá. \nAinda faltam as seguintes palavras-chave: {', '.join(faltantes)}. \nIncorpore-as de forma natural no texto."
    else:
         print(f"DEBUG: Score ALTO ({score_porcentagem}%) - O CV está excelente!")
         feedback += "AVALIAÇÃO APROVADA. Excelente aderência."
         
    return feedback

def extract_entities(text):
    doc = nlp(text)

    termos = set()

    for chunck in doc.noun_chunks:
        termos.add(chunck.text.strip())

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
    stop_words_combined = ["de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "é", "com", "não", "uma", "os", "no", "se", "na", "por", "mais", "as", "dos", "como", "mas", "foi", "ao", "ele", "das", "tem", "à", "seu", "sua", "ou", "ser", "quando", "muito", "há", "nos", "já", "está", "eu", "também", "só", "pelo", "pela", "até", "isso", "ela", "entre", "era", "depois", "sem", "mesmo", "aos", "ter", "seus", "quem", "nas", "me", "esse", "eles", "estão", "você", "tinha", "foram", "essa", "num", "nem", "suas", "meu", "às", "minha", "têm", "numa", "pelos", "elas", "havia", "seja", "qual", "será", "nós", "tenho", "lhe", "deles", "essas", "esses", "pelas", "este", "fosse", "dele", "tu", "te", "vocês", "vos", "lhes", "meus", "minhas", "teu", "tua", "teus", "tuas", "nosso", "nossa", "nossos", "nossas", "dela", "delas", "esta", "estes", "estas", "aquele", "aquela", "aqueles", "aquelas", "isto", "aquilo", "estou", "está", "estamos", "estão", "estive", "esteve", "estivemos", "estiveram", "estava", "estávamos", "estavam", "estivera", "estivéramos", "esteja", "sejamos", "sejam", "fosse", "fôssemos", "fossem", "for", "formos", "forem", "serei", "será", "seremos", "serão", "seria", "seríamos", "seriam", "tenho", "tem", "temos", "tém", "tinha", "tínhamos", "tinham", "tive", "teve", "tivemos", "tiveram", "tivera", "tivéramos", "tenha", "tenhamos", "tenham", "tivesse", "tivéssemos", "tivessem", "tiver", "tivermos", "tiverem", "terei", "terá", "teremos", "terão", "teria", "teríamos", "teriam", "the", "in", "to", "and", "of", "a", "for", "is", "with", "on", "as", "are", "be", "that", "this", "it", "or", "by", "an", "will", "we"]

kw_model = KeyBERT(model="all-MiniLM-L6-v2")

def extrator_keywords_keybert(text):
    keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1,2), stop_words=stop_words_combined, top_n=30)

    return [kw[0] for kw in keywords]

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
    "candidate", "must", "strong", "preferred", "nice", "description", "apply"
}

def clean_and_validate_term(term):
    term = term.lower().strip()
    
    # 1. Remover ruído de pontuação nas pontas
    term = term.strip(".,()/-*[]:")
    
    words = term.split()
    
    # 2. Se for muito longo (mais de 3 palavras), descartar
    if len(words) > 3 or len(words) == 0:
        return None
        
    # 3. Filtrar se TODAS as palavras estiverem nas stopwords
    if all(w in STOPWORDS_PT_EXTRA or len(w) <= 2 for w in words):
        return None
        
    # 4. Remover termos que começam com preposições quebradas ou verbos comuns
    bad_starts = ["em ", "de ", "com ", "para ", "uma ", "um ", "in ", "of ", "with ", "to ", "a ", "an "]
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