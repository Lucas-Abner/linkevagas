import os
import requests
import base64
import json
from datetime import datetime

CACHE_FILE = ".github_cache.json"
CACHE_EXPIRY_HOURS = 24

def _load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                cache_time = datetime.fromisoformat(data.get("timestamp", "2000-01-01"))
                if (datetime.now() - cache_time).total_seconds() < CACHE_EXPIRY_HOURS * 3600:
                    return data.get("repos", [])
        except:
            pass
    return None

def _save_cache(repos):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "repos": repos
        }, f, indent=2)

def extrair_repositorios_github() -> str:
    """
    Ferramenta para a IA extrair e listar os repositórios públicos do GitHub do candidato (lucas-abner).
    Retorna uma lista estruturada contendo o Nome, Descrição, Linguagem, Tópicos e os primeiros 500
    caracteres do README de cada repositório.
    """
    username = "lucas-abner"
    cached_repos = _load_cache()
    if cached_repos is not None:
        return json.dumps(cached_repos, indent=2, ensure_ascii=False)
        
    url = f"https://api.github.com/users/{username}/repos?per_page=30&sort=updated"
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    # Se tiver um token configurado no .env, usa para não cair no rate limit do GitHub
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
        
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return f"Erro ao buscar repositórios: {response.text}"
        
    repos_data = response.json()
    extracted_repos = []
    
    # Processa os repositórios mais recentes (ignorando forks)
    for repo in repos_data:
        if repo.get("fork"):
            continue
            
        repo_name = repo["name"]
        
        # Blacklist simples de repositórios que não agregam ao CV técnico
        if repo_name.lower() in ["lucas-abner", "portfolio", "agenda"]:
            continue
            
        repo_info = {
            "name": repo_name,
            "url": repo.get("html_url", f"https://github.com/{username}/{repo_name}"),
            "description": repo.get("description") or "Sem descrição",
            "language": repo.get("language") or "N/A",
            "topics": repo.get("topics", [])
        }
        
        # Buscar README para dar contexto extra à IA
        readme_url = f"https://api.github.com/repos/{username}/{repo_name}/readme"
        readme_response = requests.get(readme_url, headers=headers)
        
        if readme_response.status_code == 200:
            readme_data = readme_response.json()
            if "content" in readme_data:
                try:
                    content = base64.b64decode(readme_data["content"]).decode('utf-8')
                    # Limpeza básica do README
                    content_clean = " ".join(content.split())
                    repo_info["readme_snippet"] = content_clean[:500] + "..." if len(content_clean) > 500 else content_clean
                except:
                    repo_info["readme_snippet"] = "Erro ao decodificar README"
        else:
            repo_info["readme_snippet"] = "Sem README"
            
        extracted_repos.append(repo_info)
        
        # Limitar a análise aos 15 repos mais relevantes/recentes para não estourar o contexto do LLM
        if len(extracted_repos) >= 15:
            break
            
    _save_cache(extracted_repos)
    return json.dumps(extracted_repos, indent=2, ensure_ascii=False)
