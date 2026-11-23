"""Limitador simple en memoria para proteger endpoints sensibles contra fuerza bruta."""
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException


class RateLimiter:
    def __init__(self, max_intentos: int = 10, ventana_seg: int = 60):
        self.max_intentos = max_intentos
        self.ventana_seg = ventana_seg
        self._eventos: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _purgar(self, q: deque[float], ahora: float) -> None:
        limite = ahora - self.ventana_seg
        while q and q[0] <= limite:
            q.popleft()

    def verificar(self, clave: str) -> None:
        ahora = time.monotonic()
        with self._lock:
            q = self._eventos[clave]
            self._purgar(q, ahora)
            if len(q) >= self.max_intentos:
                reintento = max(1, int(self.ventana_seg - (ahora - q[0])))
                raise HTTPException(
                    429,
                    detail="Demasiados intentos fallidos. Espera unos segundos antes de intentar de nuevo.",
                    headers={"Retry-After": str(reintento)},
                )

    def registrar_fallo(self, clave: str) -> None:
        ahora = time.monotonic()
        with self._lock:
            q = self._eventos[clave]
            self._purgar(q, ahora)
            q.append(ahora)

    def limpiar(self, clave: str) -> None:
        with self._lock:
            self._eventos.pop(clave, None)


login_limiter = RateLimiter(max_intentos=10, ventana_seg=60)
login_ip_limiter = RateLimiter(max_intentos=60, ventana_seg=60)
