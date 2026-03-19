import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json

nlp = spacy.load("en_core_web_sm")

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
    elif score_porcentagem < 80:
         print(f"DEBUG: Score MEDIANO - Faltam: {faltantes}")
         feedback += f"AVALIAÇÃO MEDIANA. Quase lá. \nAinda faltam as seguintes palavras-chave: {', '.join(faltantes)}. \nIncorpore-as de forma natural no texto."
    else:
         print(f"DEBUG: Score ALTO ({score_porcentagem}%) - O CV está excelente!")
         feedback += "AVALIAÇÃO APROVADA. Excelente aderência."
         
    return feedback