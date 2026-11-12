"""Indicadores K1 a K12 (sección 9 del diseño) y las listas que los explican.

Todos los indicadores dependen del rango de fechas consultado [desde, hasta].
"""
import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.enums import Estado, EstadoCompromiso, Tipo
from app.estados import ABIERTOS
from app.models import Area, Compromiso, Evento, Usuario
from app.routers.eventos import _con_relaciones
from app.schemas import Indicador

NOMBRES = {
    "K1": "Volumen por tipo",
    "K2": "Con seguimiento vs informativos",
    "K3": "Stock abierto",
    "K4": "Resueltos sin cerrar",
    "K5": "Tiempo medio de atención",
    "K6": "Cerrados en el rango",
    "K7": "Cumplimiento de compromisos",
    "K8": "Vencidos ahora",
    "K9": "Carga por persona",
    "K10": "Áreas de origen",
    "K11": "Antigüedad máxima",
    "K12": "Incidencias del rango",
}


def _zona() -> ZoneInfo:
    return ZoneInfo(settings.zona_horaria)


def _aware(dt: datetime) -> datetime:
    """SQLite devuelve fechas sin zona (guardadas en UTC); PostgreSQL las devuelve con zona."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def inicio_del_dia_utc(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=_zona()).astimezone(timezone.utc)


def semana_de(hoy: date) -> tuple[date, date]:
    lunes = hoy - timedelta(days=hoy.weekday())
    return lunes, lunes + timedelta(days=6)


def _stock():
    return (Evento.requiere_seguimiento.is_(True), Evento.estado.in_(ABIERTOS))


def _en_rango(desde: date, hasta: date):
    return (Evento.fecha_hecho >= desde, Evento.fecha_hecho <= hasta)


def _cerrados_k5(desde: date, hasta: date):
    return (
        Evento.estado == Estado.cerrado,
        Evento.requiere_seguimiento.is_(True),
        Evento.cerrado_en.is_not(None),
        *_en_rango(desde, hasta),
    )


def _a_tiempo(c: Compromiso) -> bool:
    """Cumplido y con cumplido_en <= fin del día de fecha_limite (en la zona del área)."""
    return (
        c.estado == EstadoCompromiso.cumplido
        and c.cumplido_en is not None
        and _aware(c.cumplido_en) < inicio_del_dia_utc(c.fecha_limite + timedelta(days=1))
    )


def _compromisos_del_rango(db: Session, desde: date, hasta: date) -> list[Compromiso]:
    return list(
        db.scalars(
            select(Compromiso)
            .options(joinedload(Compromiso.responsable), joinedload(Compromiso.evento))
            .where(
                Compromiso.fecha_limite >= desde,
                Compromiso.fecha_limite <= hasta,
                Compromiso.estado != EstadoCompromiso.cancelado,
            )
            .order_by(Compromiso.fecha_limite, Compromiso.creado_en)
        )
        .unique()
        .all()
    )


def _vencidos(db: Session, hoy: date, desde: date | None = None, hasta: date | None = None) -> list[Compromiso]:
    cond = [Compromiso.estado == EstadoCompromiso.pendiente, Compromiso.fecha_limite < hoy]
    if desde is not None:
        cond.append(Compromiso.fecha_limite >= desde)
    if hasta is not None:
        cond.append(Compromiso.fecha_limite <= hasta)
    return list(
        db.scalars(
            select(Compromiso)
            .options(joinedload(Compromiso.responsable), joinedload(Compromiso.evento))
            .where(*cond)
            .order_by(Compromiso.fecha_limite, Compromiso.creado_en)
        )
        .unique()
        .all()
    )


def calcular(db: Session, desde: date, hasta: date, hoy: date, ahora: datetime) -> list[Indicador]:
    def contar(*cond) -> int:
        return db.scalar(select(func.count()).select_from(Evento).where(*cond)) or 0

    r = _en_rango(desde, hasta)
    ind: list[Indicador] = []

    # K1 y K12
    por_tipo = {t.value: 0 for t in Tipo}
    for tipo, n in db.execute(select(Evento.tipo, func.count()).where(*r).group_by(Evento.tipo)):
        por_tipo[tipo.value] = n
    ind.append(Indicador(id="K1", nombre=NOMBRES["K1"], valor=sum(por_tipo.values()), unidad="eventos",
                         detalle={"por_tipo": por_tipo}))

    # K2
    con = contar(*r, Evento.requiere_seguimiento.is_(True))
    sin = contar(*r, Evento.requiere_seguimiento.is_(False))
    ind.append(Indicador(id="K2", nombre=NOMBRES["K2"], valor=con, unidad="con seguimiento",
                         detalle={"con_seguimiento": con, "informativos": sin}))

    # K3, K4 (en el rango)
    ind.append(Indicador(id="K3", nombre=NOMBRES["K3"], valor=contar(*r, *_stock()), unidad="eventos"))
    ind.append(Indicador(id="K4", nombre=NOMBRES["K4"], valor=contar(*r, Evento.estado == Estado.resuelto), unidad="eventos"))

    # K5: cierre menos registro, en horas, por tipo. Un informativo o cancelado nunca entra.
    horas_por_tipo: dict[str, list[float]] = {}
    for tipo, creado, cerrado in db.execute(select(Evento.tipo, Evento.creado_en, Evento.cerrado_en).where(*_cerrados_k5(desde, hasta))):
        h = (_aware(cerrado) - _aware(creado)).total_seconds() / 3600
        horas_por_tipo.setdefault(tipo.value, []).append(max(h, 0.0))
    todas = [h for v in horas_por_tipo.values() for h in v]
    ind.append(Indicador(
        id="K5", nombre=NOMBRES["K5"], valor=round(sum(todas) / len(todas), 1) if todas else None, unidad="horas",
        detalle={"cerrados": len(todas),
                 "por_tipo": {t: round(sum(v) / len(v), 1) for t, v in horas_por_tipo.items()}},
    ))

    # K6: cierres ocurridos dentro del rango (día completo en la zona del área)
    ini, fin = inicio_del_dia_utc(desde), inicio_del_dia_utc(hasta + timedelta(days=1))
    ind.append(Indicador(id="K6", nombre=NOMBRES["K6"], unidad="eventos", valor=contar(
        Evento.estado == Estado.cerrado, Evento.cerrado_en >= ini, Evento.cerrado_en < fin)))

    # K7
    comps = _compromisos_del_rango(db, desde, hasta)
    a_tiempo = sum(1 for c in comps if _a_tiempo(c))
    ind.append(Indicador(
        id="K7", nombre=NOMBRES["K7"], unidad="%",
        valor=round(100 * a_tiempo / len(comps), 1) if comps else None,
        detalle={"cumplidos_a_tiempo": a_tiempo, "total": len(comps)},
    ))

    # K8 (vencidos en el rango)
    ind.append(Indicador(id="K8", nombre=NOMBRES["K8"], valor=len(_vencidos(db, hoy, desde, hasta)), unidad="compromisos"))

    # K9
    stock_ev = list(db.scalars(_con_relaciones().where(*r, *_stock()).order_by(Evento.creado_en)).unique().all())
    carga: dict[str, dict] = {}
    for e in stock_ev:
        clave = str(e.responsable_id) if e.responsable_id else "sin"
        fila = carga.setdefault(clave, {"responsable_id": e.responsable_id and str(e.responsable_id),
                                        "nombre": e.responsable.nombre if e.responsable else "Sin responsable",
                                        "abiertos": 0})
        fila["abiertos"] += 1
    lista = sorted(carga.values(), key=lambda f: -f["abiertos"])
    ind.append(Indicador(id="K9", nombre=NOMBRES["K9"], valor=lista[0]["abiertos"] if lista else 0,
                         unidad="máx. por persona", detalle={"por_responsable": lista}))

    # K10
    filas = db.execute(
        select(Area.id, Area.nombre, func.count()).join(Evento, Evento.area_id == Area.id)
        .where(*r).group_by(Area.id, Area.nombre).order_by(func.count().desc(), Area.nombre).limit(5)
    ).all()
    ind.append(Indicador(id="K10", nombre=NOMBRES["K10"], unidad="eventos con área",
                         valor=contar(*r, Evento.area_id.is_not(None)),
                         detalle={"top": [{"area_id": str(a), "nombre": n, "total": t} for a, n, t in filas]}))

    # K11
    if stock_ev:
        viejo = stock_ev[0]  # ya viene ordenado por creado_en
        ind.append(Indicador(id="K11", nombre=NOMBRES["K11"], unidad="días",
                             valor=max((ahora - _aware(viejo.creado_en)).days, 0),
                             detalle={"folio": viejo.folio, "titulo": viejo.titulo}))
    else:
        ind.append(Indicador(id="K11", nombre=NOMBRES["K11"], valor=None, unidad="días"))

    ind.append(Indicador(id="K12", nombre=NOMBRES["K12"], unidad="incidencias",
                         valor=contar(*r, Evento.tipo == Tipo.incidencia)))
    ind.sort(key=lambda i: int(i.id[1:]))
    return ind


def lista_de(db: Session, kid: str, desde: date, hasta: date, hoy: date, clave: str | None = None):
    """Eventos o compromisos que componen el indicador. Devuelve (eventos, compromisos, texto_vacio)."""
    r = _en_rango(desde, hasta)
    q = _con_relaciones()

    def eventos(*cond, orden=None):
        consulta = q.where(*cond).order_by(orden if orden is not None else Evento.fecha_hecho.desc(), Evento.creado_en.desc())
        return list(db.scalars(consulta).unique().all())

    if kid == "K1":
        extra = [Evento.tipo == Tipo(clave)] if clave else []
        return eventos(*r, *extra), [], None
    if kid == "K2":
        extra = [Evento.requiere_seguimiento.is_(clave == "con")] if clave in ("con", "sin") else []
        return eventos(*r, *extra), [], None
    if kid == "K3":
        return eventos(*r, *_stock()), [], None
    if kid == "K4":
        return eventos(*r, Evento.estado == Estado.resuelto), [], None
    if kid == "K5":
        extra = [Evento.tipo == Tipo(clave)] if clave else []
        return eventos(*_cerrados_k5(desde, hasta), *extra), [], None
    if kid == "K6":
        ini, fin = inicio_del_dia_utc(desde), inicio_del_dia_utc(hasta + timedelta(days=1))
        return eventos(Evento.estado == Estado.cerrado, Evento.cerrado_en >= ini, Evento.cerrado_en < fin,
                       orden=Evento.cerrado_en.desc()), [], None
    if kid == "K7":
        comps = _compromisos_del_rango(db, desde, hasta)
        if clave == "a_tiempo":
            comps = [c for c in comps if _a_tiempo(c)]
        elif clave == "fuera":
            comps = [c for c in comps if not _a_tiempo(c)]
        return [], comps, None
    if kid == "K8":
        return [], _vencidos(db, hoy, desde, hasta), "No hay compromisos vencidos"
    if kid == "K9":
        extra = []
        if clave == "sin":
            extra = [Evento.responsable_id.is_(None)]
        elif clave:
            extra = [Evento.responsable_id == uuid.UUID(clave)]
        return eventos(*r, *_stock(), *extra), [], None
    if kid == "K10":
        extra = [Evento.area_id == uuid.UUID(clave)] if clave else []
        return eventos(*r, Evento.area_id.is_not(None), *extra), [], None
    if kid == "K11":
        return eventos(*r, *_stock(), orden=Evento.creado_en.asc()), [], None
    if kid == "K12":
        return eventos(*r, Evento.tipo == Tipo.incidencia), [], None
    raise KeyError(kid)
