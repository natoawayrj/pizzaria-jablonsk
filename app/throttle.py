"""
Throttle de login em memória — proteção básica contra brute force.
Single-process (suficiente p/ PythonAnywhere free tier). Para multi-worker,
trocar por Redis/Flask-Limiter.
"""
import time
from collections import defaultdict

_MAX_TENTATIVAS = 5        # falhas permitidas
_JANELA_SEG     = 300      # dentro de 5 min

_tentativas = defaultdict(list)  # chave -> [timestamps de falha]


def bloqueado(chave: str) -> bool:
    agora = time.time()
    recentes = [t for t in _tentativas[chave] if agora - t < _JANELA_SEG]
    _tentativas[chave] = recentes
    return len(recentes) >= _MAX_TENTATIVAS


def registrar_falha(chave: str) -> None:
    _tentativas[chave].append(time.time())


def limpar(chave: str) -> None:
    _tentativas.pop(chave, None)
