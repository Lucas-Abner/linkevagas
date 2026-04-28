"""
Sistema de registro e análise de candidaturas para feedback loop.
Registra cada candidatura com metadados completos para análise posterior.
"""
import json
from datetime import datetime
from pathlib import Path

TRACKING_FILE = Path(__file__).resolve().parent.parent.parent / "candidaturas_tracking.json"


def registrar_candidatura(vaga: dict, status: str, cv_usado: str = None,
                          fit_score: int = None, motivo: str = None) -> None:
    """Registra cada candidatura com metadados completos."""
    historico = _carregar_historico()

    registro = {
        "data": datetime.now().isoformat(),
        "titulo": vaga.get("title", "N/A"),
        "empresa": vaga.get("company", "N/A"),
        "url": vaga.get("url", "N/A"),
        "status": status,  # "enviada", "ignorada", "erro"
        "cv_usado": cv_usado,
        "fit_score": fit_score,
        "motivo": motivo,
        "retorno": None,  # Preenchido manualmente depois
    }

    historico.append(registro)
    _salvar_historico(historico)
    print(f"📋 Candidatura registrada: {registro['titulo']} ({status})")


def gerar_relatorio() -> str:
    """Gera relatório com estatísticas de candidaturas."""
    historico = _carregar_historico()

    total = len(historico)
    enviadas = [h for h in historico if h["status"] == "enviada"]
    ignoradas = [h for h in historico if h["status"] == "ignorada"]
    com_retorno = [h for h in historico if h.get("retorno") is True]

    relatorio = (
        f"\n=== RELATÓRIO DE CANDIDATURAS ===\n"
        f"Total registradas: {total}\n"
        f"Enviadas: {len(enviadas)}\n"
        f"Ignoradas (fit baixo): {len(ignoradas)}\n"
        f"Com retorno: {len(com_retorno)}\n"
        f"Taxa de retorno: {len(com_retorno) / max(len(enviadas), 1) * 100:.1f}%\n"
    )

    if com_retorno:
        relatorio += f"Fit scores das com retorno: {[h['fit_score'] for h in com_retorno]}\n"

    sem_retorno = [h for h in enviadas if not h.get("retorno")]
    if sem_retorno:
        relatorio += f"Fit scores das sem retorno: {[h['fit_score'] for h in sem_retorno]}\n"

    return relatorio


def _carregar_historico() -> list:
    if TRACKING_FILE.exists():
        try:
            with open(TRACKING_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def _salvar_historico(historico: list) -> None:
    with open(TRACKING_FILE, "w", encoding="utf-8") as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)
