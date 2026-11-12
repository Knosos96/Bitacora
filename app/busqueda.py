"""Búsqueda de texto (CU-11).

Usa PostgreSQL tsvector con diccionario 'spanish' e índice GIN.
Para pruebas locales en SQLite, mantiene compatibilidad con fallback a LIKE sobre texto normalizado.
"""
import re
import unicodedata

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Compromiso, Evento, Seguimiento

FOLIO_RE = re.compile(r"^BIT-\d{4}-\d{5}$", re.IGNORECASE)


def normalizar(texto: str | None) -> str:
    if not texto:
        return ""
    sin_acentos = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return sin_acentos.lower()


def _raiz(palabra: str) -> str:
    """Quita la terminación de plural para que 'licencias' encuentre 'licencia' y viceversa."""
    if len(palabra) > 5 and palabra.endswith("es"):
        return palabra[:-2]
    if len(palabra) > 3 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


def terminos(consulta: str) -> list[str]:
    palabras = re.findall(r"\w+", normalizar(consulta))
    return [_raiz(p) for p in palabras if p]


def es_folio(consulta: str) -> bool:
    return bool(FOLIO_RE.match(consulta.strip()))


def _escapar_like(t: str) -> str:
    return t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def condicion_busqueda(consulta: str, dialect_name: str = "postgresql"):
    """Condición SQL para búsqueda por texto.
    En PostgreSQL usa tsvector @@ plainto_tsquery('spanish', ...).
    En SQLite busca todas las palabras en el texto normalizado.
    """
    if dialect_name == "postgresql":
        return [Evento.busqueda.match(consulta, postgresql_regconfig="spanish")]
    return [Evento.busqueda.like(f"%{_escapar_like(t)}%", escape="\\") for t in terminos(consulta)]


def _campos(e: Evento, notas: list[Seguimiento], compromisos: list[Compromiso]) -> list[tuple[str, str]]:
    campos = [
        ("título", e.titulo),
        ("descripción", e.descripcion),
        ("solicitante", e.solicitante_nombre or ""),
        ("referencia", e.referencia or ""),
    ]
    # Las notas automáticas ("Estado: abierto → en_proceso") no son contenido para buscar.
    campos += [("nota", n.nota) for n in notas if n.estado_nuevo is None]
    campos += [("compromiso", c.descripcion) for c in compromisos]
    return campos


def texto_busqueda(e: Evento, notas: list[Seguimiento], compromisos: list[Compromiso]) -> str:
    return " \n ".join(t for _, t in _campos(e, notas, compromisos) if t)


def reindexar(db: Session, e: Evento) -> None:
    """Recalcula el vector o texto de búsqueda del evento. Llamar antes de cada commit que cambie su contenido."""
    db.flush()
    notas = db.scalars(select(Seguimiento).where(Seguimiento.evento_id == e.id)).all()
    comps = db.scalars(select(Compromiso).where(Compromiso.evento_id == e.id)).all()
    texto = texto_busqueda(e, list(notas), list(comps))
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        e.busqueda = func.to_tsvector("spanish", texto)
    else:
        e.busqueda = normalizar(texto)


def fragmento(consulta: str, e: Evento, notas: list[Seguimiento], compromisos: list[Compromiso], ancho: int = 60) -> str | None:
    """Trozo de texto, con su campo de origen, donde apareció la primera palabra buscada."""
    ts = terminos(consulta)
    if not ts:
        return None
    for nombre, original in _campos(e, notas, compromisos):
        if not original:
            continue
        norm = normalizar(original)
        if len(norm) != len(original):  # caso raro de normalización que cambia el largo
            continue
        for t in ts:
            i = norm.find(t)
            if i >= 0:
                ini, fin = max(0, i - ancho), min(len(original), i + len(t) + ancho)
                trozo = original[ini:fin].replace("\n", " ").strip()
                return f"{nombre}: " + ("…" if ini > 0 else "") + trozo + ("…" if fin < len(original) else "")
    return None
