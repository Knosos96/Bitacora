import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.db import get_db
from app.deps import usuario_actual
from app.busqueda import condicion_busqueda, es_folio, fragmento, reindexar
from app.enums import SUBTIPOS, Estado, EstadoCompromiso, Prioridad, Rol, Tipo
from app.estados import ASISTENTE_PUEDE, CIERRE_CON_ATAJO, es_gestor, transicion_valida
from app.folio import siguiente_folio
from app.models import Area, Auditoria, Compromiso, Evento, Seguimiento, Usuario, _ahora
from app.schemas import (
    AreaRef,
    AuditoriaOut,
    CambioEstadoIn,
    CompromisoIn,
    CompromisoOut,
    EventoBusquedaOut,
    EventoDetalleOut,
    EventoIn,
    EventoOut,
    EventoPatch,
    EventosPagina,
    Meta,
    SeguimientoIn,
    SeguimientoOut,
    UsuarioRef,
)

router = APIRouter(prefix="/eventos", tags=["eventos"])


def hoy_en_zona() -> date:
    return datetime.now(ZoneInfo(settings.zona_horaria)).date()


def a_salida(e: Evento) -> EventoOut:
    return EventoOut(
        id=e.id,
        folio=e.folio,
        tipo=e.tipo,
        subtipo=e.subtipo,
        titulo=e.titulo,
        descripcion=e.descripcion,
        referencia=e.referencia,
        fecha_hecho=e.fecha_hecho,
        estado=e.estado,
        requiere_seguimiento=e.requiere_seguimiento,
        prioridad=e.prioridad,
        area_origen=AreaRef.model_validate(e.area) if e.area else None,
        solicitante=e.solicitante_nombre,
        autor=UsuarioRef.model_validate(e.autor),
        responsable=UsuarioRef.model_validate(e.responsable) if e.responsable else None,
        creado_en=e.creado_en,
        cerrado_en=e.cerrado_en,
    )


def _con_relaciones():
    return select(Evento).options(
        joinedload(Evento.area), joinedload(Evento.autor), joinedload(Evento.responsable)
    )


@router.post("", response_model=EventoOut, status_code=201)
def crear_evento(
    datos: EventoIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    if datos.area_id and not db.get(Area, datos.area_id):
        raise HTTPException(400, "El área no existe")

    fecha = datos.fecha_hecho or hoy_en_zona()
    if fecha > hoy_en_zona():
        raise HTTPException(400, "La fecha del hecho no puede estar en el futuro")

    responsable_id = None
    prioridad = None
    estado = Estado.informativo
    if datos.requiere_seguimiento:
        estado = Estado.abierto
        responsable_id = datos.responsable_id or usuario.id  # por defecto, el autor
        prioridad = datos.prioridad or Prioridad.media
        if not db.get(Usuario, responsable_id):
            raise HTTPException(400, "El responsable no existe")

    evento = Evento(
        folio=siguiente_folio(db, fecha.year),
        tipo=datos.tipo,
        subtipo=datos.subtipo,
        titulo=datos.titulo.strip(),
        descripcion=datos.descripcion.strip(),
        referencia=datos.referencia,
        fecha_hecho=fecha,
        area_id=datos.area_id,
        solicitante_nombre=datos.solicitante_nombre,
        requiere_seguimiento=datos.requiere_seguimiento,
        estado=estado,
        prioridad=prioridad,
        autor_id=usuario.id,
        responsable_id=responsable_id,
    )
    db.add(evento)
    reindexar(db, evento)
    db.commit()
    evento = db.scalars(_con_relaciones().where(Evento.id == evento.id)).unique().one()
    return a_salida(evento)


@router.get("", response_model=EventosPagina)
def listar_eventos(
    desde: date | None = None,
    hasta: date | None = None,
    tipo: list[Tipo] = Query(default=[]),
    estado: list[Estado] = Query(default=[]),
    q: str | None = Query(None, description="Texto a buscar (CU-11) o un folio"),
    area_id: uuid.UUID | None = None,
    responsable_id: uuid.UUID | None = None,
    seguimiento: str | None = Query(None, pattern="^(con|sin)$"),
    vencidos: bool = Query(False, description="Solo eventos con compromisos pendientes vencidos"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_actual),
):
    """CU-11 y CU-12. Sin filtros ni fechas es la pantalla Hoy.

    Cuando hay texto, estado, área, responsable, seguimiento o vencidos y no se dan fechas, se busca en
    todo el histórico: quien busca no suele saber cuándo ocurrió.
    """
    q = (q or "").strip() or None
    busca_amplia = bool(q or estado or area_id or responsable_id or seguimiento or vencidos)

    if q and es_folio(q):
        filtros = [Evento.folio == q.upper()]  # un folio abre ese evento, sin otros filtros
        q = None
    else:
        if desde is None and hasta is None and not busca_amplia:
            desde = hasta = hoy_en_zona()  # la pantalla Hoy
        if not busca_amplia:
            desde = desde or hasta
            hasta = hasta or desde
        if desde and hasta and desde > hasta:
            raise HTTPException(400, "'desde' no puede ser posterior a 'hasta'")
        if desde and hasta and not busca_amplia and (hasta - desde).days > 366:
            raise HTTPException(400, "El rango máximo es de 366 días")

        filtros = []
        if desde:
            filtros.append(Evento.fecha_hecho >= desde)
        if hasta:
            filtros.append(Evento.fecha_hecho <= hasta)
        if tipo:
            filtros.append(Evento.tipo.in_(tipo))
        if estado:
            filtros.append(Evento.estado.in_(estado))
        if area_id:
            filtros.append(Evento.area_id == area_id)
        if responsable_id:
            filtros.append(Evento.responsable_id == responsable_id)
        if seguimiento:
            filtros.append(Evento.requiere_seguimiento == (seguimiento == "con"))
        if vencidos:
            filtros.append(Evento.id.in_(
                select(Compromiso.evento_id).where(
                    Compromiso.estado == EstadoCompromiso.pendiente, Compromiso.fecha_limite < hoy_en_zona()
                )
            ))
        if q:
            dialect = db.get_bind().dialect.name
            filtros += condicion_busqueda(q, dialect_name=dialect)

    total = db.scalar(select(func.count()).select_from(Evento).where(*filtros))
    filas = (
        db.scalars(
            _con_relaciones()
            .where(*filtros)
            .order_by(Evento.fecha_hecho.desc(), Evento.creado_en.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .unique()
        .all()
    )

    notas, comps = {}, {}
    if q and filas:
        ids = [e.id for e in filas]
        for n in db.scalars(select(Seguimiento).where(Seguimiento.evento_id.in_(ids)).order_by(Seguimiento.creado_en)):
            notas.setdefault(n.evento_id, []).append(n)
        for c in db.scalars(select(Compromiso).where(Compromiso.evento_id.in_(ids))):
            comps.setdefault(c.evento_id, []).append(c)

    return EventosPagina(
        data=[
            EventoBusquedaOut(
                **a_salida(e).model_dump(),
                fragmento=fragmento(q, e, notas.get(e.id, []), comps.get(e.id, [])) if q else None,
            )
            for e in filas
        ],
        meta=Meta(page=page, page_size=page_size, total=total),
    )


def conflicto(codigo: str, detalle: str) -> HTTPException:
    """Error de dominio con código estable (sección 10.4)."""
    return HTTPException(409, {"codigo": codigo, "detalle": detalle})


def buscar_evento(db: Session, folio: str) -> Evento:
    """Acepta el folio (BIT-2026-00041) o el uuid."""
    try:
        condicion = Evento.id == uuid.UUID(folio)
    except ValueError:
        condicion = Evento.folio == folio.upper()
    e = db.scalars(
        _con_relaciones().where(condicion).execution_options(populate_existing=True)
    ).unique().one_or_none()
    if e is None:
        raise HTTPException(404, "Evento no encontrado")
    return e


def compromiso_a_salida(c: Compromiso, folio: str) -> CompromisoOut:
    return CompromisoOut(
        id=c.id,
        evento_folio=folio,
        descripcion=c.descripcion,
        responsable=UsuarioRef.model_validate(c.responsable),
        fecha_limite=c.fecha_limite,
        estado=c.estado,
        vencido=c.estado == EstadoCompromiso.pendiente and c.fecha_limite < hoy_en_zona(),
        cumplido_en=c.cumplido_en,
        creado_en=c.creado_en,
    )


def _nota(db: Session, e: Evento, autor: Usuario, texto: str, anterior=None, nuevo=None) -> Seguimiento:
    n = Seguimiento(
        evento_id=e.id, autor_id=autor.id, nota=texto, estado_anterior=anterior, estado_nuevo=nuevo,
        creado_en=_ahora(),
    )
    db.add(n)
    return n


def _pendientes_del_evento(db: Session, e: Evento) -> list[Compromiso]:
    return list(
        db.scalars(
            select(Compromiso).where(
                Compromiso.evento_id == e.id, Compromiso.estado == EstadoCompromiso.pendiente
            )
        ).all()
    )


def _lista_seguimientos(db: Session, e: Evento) -> list[SeguimientoOut]:
    filas = db.scalars(
        select(Seguimiento)
        .options(joinedload(Seguimiento.autor))
        .where(Seguimiento.evento_id == e.id)
        .order_by(Seguimiento.creado_en, Seguimiento.id)
    ).all()
    return [SeguimientoOut.model_validate(n) for n in filas]


def _lista_compromisos(db: Session, e: Evento) -> list[CompromisoOut]:
    filas = db.scalars(
        select(Compromiso)
        .options(joinedload(Compromiso.responsable))
        .where(Compromiso.evento_id == e.id)
        .order_by(Compromiso.fecha_limite, Compromiso.creado_en)
    ).all()
    return [compromiso_a_salida(c, e.folio) for c in filas]


@router.get("/{folio}", response_model=EventoDetalleOut)
def obtener_evento(
    folio: str,
    incluir: list[str] = Query(default=[], description="seguimientos, compromisos, auditoria (separados por coma o repetidos)"),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_actual),
):
    e = buscar_evento(db, folio)
    pedidos = {x.strip() for item in incluir for x in item.split(",") if x.strip()}
    salida = EventoDetalleOut(**a_salida(e).model_dump())
    if "seguimientos" in pedidos:
        salida.seguimientos = _lista_seguimientos(db, e)
    if "compromisos" in pedidos:
        salida.compromisos = _lista_compromisos(db, e)
    if "auditoria" in pedidos:
        filas = db.scalars(
            select(Auditoria).options(joinedload(Auditoria.usuario))
            .where(Auditoria.evento_id == e.id).order_by(Auditoria.creado_en, Auditoria.id)
        ).all()
        salida.auditoria = [AuditoriaOut.model_validate(a) for a in filas]
    return salida


# ---------------------------------------------------------------- Sprint 2
CAMPOS_CABECERA = ("tipo", "subtipo", "titulo", "descripcion", "referencia", "fecha_hecho", "area_id", "solicitante_nombre")
OBLIGATORIOS = {"tipo", "titulo", "descripcion", "fecha_hecho"}  # un null explícito se ignora


def _fecha_local(dt: datetime) -> date:
    if dt.tzinfo is None:  # SQLite devuelve fechas sin zona; se guardan en UTC
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo(settings.zona_horaria)).date()


def _txt(v):
    if v is None:
        return None
    return getattr(v, "value", None) or (v.isoformat() if hasattr(v, "isoformat") else str(v))


def _corregir_cabecera(db: Session, e: Evento, datos: EventoPatch, usuario: Usuario) -> bool:
    """CU-23. El autor corrige el mismo día; después, encargado o jefe. Cada cambio queda en auditoría."""
    pedidos = {
        c: getattr(datos, c)
        for c in CAMPOS_CABECERA
        if c in datos.model_fields_set and not (getattr(datos, c) is None and c in OBLIGATORIOS)
    }
    for c in ("referencia", "solicitante_nombre", "subtipo"):
        if c in pedidos and isinstance(pedidos[c], str):
            pedidos[c] = pedidos[c].strip() or None
    if not pedidos:
        return False

    es_autor_mismo_dia = (
        usuario.id == e.autor_id
        and _fecha_local(e.creado_en) == hoy_en_zona()
        and e.estado not in (Estado.cerrado, Estado.cancelado)
    )
    if not (es_gestor(usuario.rol) or es_autor_mismo_dia):
        raise conflicto("sin_permiso", "El autor corrige el mismo día; después, solo el encargado o el jefe")

    nuevo_tipo = pedidos.get("tipo", e.tipo)
    nuevo_subtipo = pedidos["subtipo"] if "subtipo" in pedidos else e.subtipo
    if nuevo_subtipo and nuevo_subtipo not in SUBTIPOS[nuevo_tipo]:
        raise HTTPException(400, f"El subtipo '{nuevo_subtipo}' no es válido para {nuevo_tipo.value}")
    if pedidos.get("fecha_hecho") and pedidos["fecha_hecho"] > hoy_en_zona():
        raise HTTPException(400, "La fecha del hecho no puede estar en el futuro")
    area_nueva = None
    if pedidos.get("area_id"):
        area_nueva = db.get(Area, pedidos["area_id"])
        if not area_nueva:
            raise HTTPException(400, "El área no existe")

    hubo = False
    for campo, nuevo in pedidos.items():
        if campo in ("titulo", "descripcion") and isinstance(nuevo, str):
            nuevo = nuevo.strip()
        if campo == "area_id":
            antes = e.area.nombre if e.area else None
            despues = area_nueva.nombre if area_nueva else None
            if e.area_id == nuevo:
                continue
            etiqueta = "area"
        else:
            antes, despues, etiqueta = _txt(getattr(e, campo)), _txt(nuevo), campo
            if getattr(e, campo) == nuevo:
                continue
        setattr(e, campo, nuevo)
        db.add(Auditoria(evento_id=e.id, campo=etiqueta, valor_anterior=antes, valor_nuevo=despues,
                         usuario_id=usuario.id, creado_en=_ahora()))
        hubo = True
    return hubo


@router.patch("/{folio}", response_model=EventoOut)
def modificar_evento(
    folio: str,
    datos: EventoPatch,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    """CU-04 (seguimiento), CU-05 (responsable y prioridad) y CU-23 (corregir cabecera)."""
    e = buscar_evento(db, folio)
    toca_cabecera = any(c in datos.model_fields_set for c in CAMPOS_CABECERA)
    toca_seguimiento = (
        datos.requiere_seguimiento is not None or datos.responsable_id is not None or datos.prioridad is not None
    )

    if toca_cabecera:
        _corregir_cabecera(db, e, datos, usuario)

    if toca_seguimiento:
        if e.estado in (Estado.cerrado, Estado.cancelado):
            raise conflicto("evento_cerrado", "El evento está cerrado o cancelado")
        if datos.responsable_id is not None and not db.get(Usuario, datos.responsable_id):
            raise HTTPException(400, "El responsable no existe")

        anterior = e.estado
        if datos.requiere_seguimiento is True and not e.requiere_seguimiento:
            # CU-04: activar. Cualquier miembro del equipo.
            e.requiere_seguimiento = True
            e.estado = Estado.abierto
            e.responsable_id = datos.responsable_id or e.responsable_id or usuario.id
            e.prioridad = datos.prioridad or e.prioridad or Prioridad.media
            _nota(db, e, usuario, datos.nota or "Se activó el seguimiento.", anterior, Estado.abierto)
        elif datos.requiere_seguimiento is False and e.requiere_seguimiento:
            # CU-04: quitar. Solo encargado/jefe y sin compromisos pendientes.
            if not es_gestor(usuario.rol):
                raise conflicto("sin_permiso", "Solo el encargado o el jefe pueden quitar el seguimiento")
            if _pendientes_del_evento(db, e):
                raise conflicto("compromisos_pendientes", "Hay compromisos pendientes en este evento")
            e.requiere_seguimiento = False
            e.estado = Estado.informativo
            e.responsable_id = None
            e.prioridad = None
            _nota(db, e, usuario, datos.nota or "Se quitó el seguimiento.", anterior, Estado.informativo)

        if datos.responsable_id is not None or datos.prioridad is not None:
            # CU-05: asignar responsable y prioridad. Encargado/jefe (o quien activa el seguimiento).
            if not es_gestor(usuario.rol) and not (datos.requiere_seguimiento is True and anterior == Estado.informativo):
                raise conflicto("sin_permiso", "Solo el encargado o el jefe asignan responsable y prioridad")
            if not e.requiere_seguimiento:
                raise conflicto("sin_seguimiento", "El evento no tiene seguimiento activo")
            cambios = []
            if datos.responsable_id is not None and datos.responsable_id != e.responsable_id:
                e.responsable_id = datos.responsable_id
                cambios.append("responsable")
            if datos.prioridad is not None and datos.prioridad != e.prioridad:
                e.prioridad = datos.prioridad
                cambios.append(f"prioridad {datos.prioridad.value}")
            if cambios:
                _nota(db, e, usuario, datos.nota or "Se cambió: " + ", ".join(cambios) + ".")

    reindexar(db, e)
    db.commit()
    return a_salida(buscar_evento(db, e.folio))


@router.post("/{folio}/estado", response_model=EventoOut)
def cambiar_estado(
    folio: str,
    datos: CambioEstadoIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    """CU-08 y CU-09. Cada cambio escribe una nota automática además de la nota de la persona."""
    e = buscar_evento(db, folio)
    desde, hacia = e.estado, datos.estado

    if not e.requiere_seguimiento:
        raise conflicto("sin_seguimiento", "El evento no tiene seguimiento; actívalo primero")
    if desde in (Estado.cerrado, Estado.cancelado):
        raise conflicto("evento_cerrado", "El evento está cerrado o cancelado")
    if not transicion_valida(desde, hacia, usuario.rol):
        raise conflicto("transicion_invalida", f"No se puede pasar de {desde.value} a {hacia.value}")

    if not es_gestor(usuario.rol):
        es_suyo = usuario.id in (e.autor_id, e.responsable_id)
        if hacia not in ASISTENTE_PUEDE or not es_suyo:
            raise conflicto("sin_permiso", "Solo el encargado o el jefe cancelan o cierran; el asistente solo avanza sus eventos hasta resuelto")

    nota = (datos.nota or "").strip()
    if hacia == Estado.en_espera and not nota:
        raise HTTPException(422, "En espera exige una nota que diga de quién se espera")
    if hacia == Estado.cerrado and desde in CIERRE_CON_ATAJO and not nota:
        raise HTTPException(422, "Cerrar desde " + desde.value + " exige una nota de cierre")

    if hacia in (Estado.cerrado, Estado.cancelado):
        pendientes = _pendientes_del_evento(db, e)
        if pendientes:
            if datos.resolver_compromisos is None:
                raise conflicto(
                    "compromisos_pendientes",
                    f"Hay {len(pendientes)} compromiso(s) pendiente(s). Resuélvelos o indica resolver_compromisos.",
                )
            nuevo = EstadoCompromiso.cumplido if datos.resolver_compromisos == "cumplir" else EstadoCompromiso.cancelado
            for c in pendientes:
                c.estado = nuevo
                if nuevo == EstadoCompromiso.cumplido:
                    c.cumplido_en = _ahora()

    e.estado = hacia
    if hacia == Estado.cerrado:
        e.cerrado_en = _ahora()
    _nota(db, e, usuario, f"Estado: {desde.value} → {hacia.value}.", desde, hacia)  # automática
    if nota:
        _nota(db, e, usuario, nota)
    reindexar(db, e)
    db.commit()
    return a_salida(buscar_evento(db, e.folio))


@router.get("/{folio}/seguimientos", response_model=list[SeguimientoOut])
def listar_seguimientos(folio: str, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    return _lista_seguimientos(db, buscar_evento(db, folio))


@router.post("/{folio}/seguimientos", response_model=SeguimientoOut, status_code=201)
def agregar_nota(
    folio: str,
    datos: SeguimientoIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    """CU-07. La nota no se edita. En un evento cerrado solo encargado/jefe, y no lo reabre."""
    e = buscar_evento(db, folio)
    if e.estado == Estado.cancelado:
        raise conflicto("evento_cerrado", "El evento está cancelado")
    if e.estado == Estado.cerrado and not es_gestor(usuario.rol):
        raise conflicto("sin_permiso", "En un evento cerrado solo el encargado o el jefe agregan notas")
    n = _nota(db, e, usuario, datos.nota.strip())
    reindexar(db, e)
    db.commit()
    return SeguimientoOut.model_validate(n)


@router.get("/{folio}/compromisos", response_model=list[CompromisoOut])
def listar_compromisos(folio: str, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    return _lista_compromisos(db, buscar_evento(db, folio))


@router.post("/{folio}/compromisos", response_model=CompromisoOut, status_code=201)
def crear_compromiso(
    folio: str,
    datos: CompromisoIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    """CU-06. Requiere seguimiento y que el evento no esté cerrado ni cancelado."""
    e = buscar_evento(db, folio)
    if not e.requiere_seguimiento:
        raise conflicto("sin_seguimiento", "El evento no tiene seguimiento; actívalo para registrar compromisos")
    if e.estado in (Estado.cerrado, Estado.cancelado):
        raise conflicto("evento_cerrado", "El evento está cerrado o cancelado")
    if datos.fecha_limite < hoy_en_zona():
        raise HTTPException(400, "La fecha límite no puede estar en el pasado")
    responsable_id = datos.responsable_id or usuario.id
    if not db.get(Usuario, responsable_id):
        raise HTTPException(400, "El responsable no existe")

    c = Compromiso(
        evento_id=e.id,
        descripcion=datos.descripcion.strip(),
        responsable_id=responsable_id,
        fecha_limite=datos.fecha_limite,
        estado=EstadoCompromiso.pendiente,
    )
    db.add(c)
    _nota(db, e, usuario, f"Compromiso registrado para el {datos.fecha_limite.isoformat()}: {c.descripcion}")
    reindexar(db, e)
    db.commit()
    c = db.scalars(select(Compromiso).options(joinedload(Compromiso.responsable)).where(Compromiso.id == c.id)).one()
    return compromiso_a_salida(c, e.folio)
