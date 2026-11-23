"""Funciones de dominio y lógica de negocio de eventos."""
import csv
import io
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.deps import Acceso, tiene_permiso
from app.core.enums import Estado, EstadoCompromiso, Permiso, Prioridad, Tipo
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
from app.services.busqueda import condicion_busqueda, es_folio, fragmento, reindexar
from app.services.estados import ASISTENTE_PUEDE, CIERRE_CON_ATAJO, transicion_valida
from app.services.folio import siguiente_folio
from app.services.historial import registrar_actividad, registrar_evento_origen
from app.services.subtipos import vigentes

COLUMNAS_CSV = [
    "folio", "fecha_hecho", "tipo", "subtipo", "titulo", "descripcion", "referencia",
    "area", "solicitante", "estado", "requiere_seguimiento", "prioridad", "autor",
    "responsable", "creado_en", "cerrado_en",
]
MAX_FILAS_CSV = 20000

CAMPOS_CABECERA = (
    "tipo", "subtipo", "titulo", "descripcion", "referencia",
    "fecha_hecho", "area_id", "solicitante_nombre",
)
OBLIGATORIOS = {"tipo", "titulo", "descripcion", "fecha_hecho"}  # un null explícito se ignora


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


def con_relaciones():
    return select(Evento).options(
        joinedload(Evento.area), joinedload(Evento.autor), joinedload(Evento.responsable)
    )


# alias usado por kpi/pendientes
_con_relaciones = con_relaciones


def conflicto(codigo: str, detalle: str) -> HTTPException:
    return HTTPException(409, {"codigo": codigo, "detalle": detalle})


def buscar_evento(db: Session, folio: str) -> Evento:
    try:
        condicion = Evento.id == uuid.UUID(folio)
    except ValueError:
        condicion = Evento.folio == folio.upper()
    e = db.scalars(
        con_relaciones().where(condicion).execution_options(populate_existing=True)
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


def usuario_activo(db: Session, usuario_id: uuid.UUID) -> bool:
    u = db.get(Usuario, usuario_id)
    return bool(u and u.activo)


def nota(db: Session, e: Evento, autor: Usuario, texto: str, anterior=None, nuevo=None) -> Seguimiento:
    n = Seguimiento(
        evento_id=e.id, autor_id=autor.id, nota=texto, estado_anterior=anterior, estado_nuevo=nuevo,
        creado_en=_ahora(),
    )
    db.add(n)
    return n


def pendientes_del_evento(db: Session, e: Evento) -> list[Compromiso]:
    return list(
        db.scalars(
            select(Compromiso).where(
                Compromiso.evento_id == e.id, Compromiso.estado == EstadoCompromiso.pendiente
            )
        ).all()
    )


def lista_seguimientos(db: Session, e: Evento) -> list[SeguimientoOut]:
    filas = db.scalars(
        select(Seguimiento)
        .options(joinedload(Seguimiento.autor))
        .where(Seguimiento.evento_id == e.id)
        .order_by(Seguimiento.creado_en, Seguimiento.id)
    ).all()
    return [SeguimientoOut.model_validate(n) for n in filas]


def lista_compromisos(db: Session, e: Evento) -> list[CompromisoOut]:
    filas = db.scalars(
        select(Compromiso)
        .options(joinedload(Compromiso.responsable))
        .where(Compromiso.evento_id == e.id)
        .order_by(Compromiso.fecha_limite, Compromiso.creado_en)
    ).all()
    return [compromiso_a_salida(c, e.folio) for c in filas]


def crear(db: Session, datos: EventoIn, usuario: Usuario) -> EventoOut:
    subtipo = (datos.subtipo or "").strip() or None
    referencia = (datos.referencia or "").strip() or None
    solicitante_nombre = (datos.solicitante_nombre or "").strip() or None
    if datos.area_id:
        area = db.get(Area, datos.area_id)
        if not area or not area.activa:
            raise HTTPException(400, "El área no existe o está inactiva")
    if subtipo and subtipo not in vigentes(db, datos.tipo):
        validos = ", ".join(sorted(vigentes(db, datos.tipo)))
        raise HTTPException(422, f"subtipo '{subtipo}' no válido para {datos.tipo.value}. Opciones: {validos}")

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
        if not usuario_activo(db, responsable_id):
            raise HTTPException(400, "El responsable no existe o está inactivo")

    evento = Evento(
        folio=siguiente_folio(db, fecha.year),
        tipo=datos.tipo,
        subtipo=subtipo,
        titulo=datos.titulo.strip(),
        descripcion=datos.descripcion.strip(),
        referencia=referencia,
        fecha_hecho=fecha,
        area_id=datos.area_id,
        solicitante_nombre=solicitante_nombre,
        requiere_seguimiento=datos.requiere_seguimiento,
        estado=estado,
        prioridad=prioridad,
        autor_id=usuario.id,
        responsable_id=responsable_id,
    )
    db.add(evento)
    db.flush()
    resp_obj = db.get(Usuario, responsable_id) if responsable_id else None
    registrar_evento_origen(db, evento, usuario, resp_obj)
    registrar_actividad(
        db,
        usuario,
        accion="incidencia_creada" if evento.tipo == Tipo.incidencia else "evento_creado",
        entidad="evento",
        entidad_id=str(evento.id),
        folio=evento.folio,
        titulo=evento.titulo,
        detalle=f"Tipo: {evento.tipo.value}" + (f"/{evento.subtipo}" if evento.subtipo else ""),
    )
    reindexar(db, evento)
    db.commit()
    evento = db.scalars(con_relaciones().where(Evento.id == evento.id)).unique().one()
    return a_salida(evento)


def armar_filtros(
    desde, hasta, tipo, estado, q, area_id, responsable_id, seguimiento, vencidos, tope_siempre=False,
):
    """Filtros compartidos por la lista, la exportación y la API. Devuelve (condiciones, q_efectivo).

    `tope_siempre`: la clave de API siempre respeta el máximo de 366 días, aunque busque por texto.
    """
    q = (q or "").strip() or None
    busca_amplia = bool(q or estado or area_id or responsable_id or seguimiento or vencidos)

    if q and es_folio(q):
        return [Evento.folio == q.upper()], None  # un folio abre ese evento, sin otros filtros

    if desde is None and hasta is None and not busca_amplia:
        desde = hasta = hoy_en_zona()  # la pantalla Hoy
    if not busca_amplia:
        desde = desde or hasta
        hasta = hasta or desde
    if desde and hasta and desde > hasta:
        raise HTTPException(400, "'desde' no puede ser posterior a 'hasta'")
    if desde and hasta and (not busca_amplia or tope_siempre) and (hasta - desde).days > 366:
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
        filtros += condicion_busqueda(q)
    return filtros, q


def listar(
    db: Session,
    acceso: Acceso,
    desde: date | None = None,
    hasta: date | None = None,
    tipo: list[Tipo] | None = None,
    estado: list[Estado] | None = None,
    q: str | None = None,
    area_id: uuid.UUID | None = None,
    responsable_id: uuid.UUID | None = None,
    seguimiento: str | None = None,
    vencidos: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> EventosPagina:
    if acceso.clave is not None:
        if desde is None or hasta is None:
            raise HTTPException(400, "Con clave de API, 'desde' y 'hasta' son obligatorios")
        if responsable_id or seguimiento or vencidos:
            raise HTTPException(400, "Ese filtro no está disponible para claves de API")
    filtros, q = armar_filtros(
        desde, hasta, tipo or [], estado or [], q, area_id, responsable_id, seguimiento, vencidos,
        tope_siempre=acceso.clave is not None,
    )

    total = db.scalar(select(func.count()).select_from(Evento).where(*filtros))
    filas = (
        db.scalars(
            con_relaciones()
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


def _rango_obligatorio(desde: date, hasta: date) -> None:
    if desde > hasta:
        raise HTTPException(400, "'desde' no puede ser posterior a 'hasta'")
    if (hasta - desde).days > 366:
        raise HTTPException(400, "El rango máximo es de 366 días")


def resumen(db: Session, desde: date, hasta: date, tipo: list[Tipo] | None = None) -> dict:
    _rango_obligatorio(desde, hasta)
    cond = [Evento.fecha_hecho >= desde, Evento.fecha_hecho <= hasta]
    if tipo:
        cond.append(Evento.tipo.in_(tipo))
    por_tipo = {t.value: 0 for t in Tipo}
    for t, n in db.execute(select(Evento.tipo, func.count()).where(*cond).group_by(Evento.tipo)):
        por_tipo[t.value] = n
    return {"desde": desde, "hasta": hasta, "total": sum(por_tipo.values()), "por_tipo": por_tipo}


def _celda(v) -> str:
    """Evita que Excel interprete como fórmula un texto que empieza con = + - @ (inyección en CSV)."""
    if v is None:
        return ""
    t = getattr(v, "value", v)
    t = t.isoformat() if hasattr(t, "isoformat") else str(t)
    if t[:1] in ("=", "+", "-", "@", "\t", "\r") or t.lstrip()[:1] in ("=", "+", "-", "@"):
        return "'" + t
    return t


def exportar_csv(
    db: Session,
    desde: date | None = None,
    hasta: date | None = None,
    tipo: list[Tipo] | None = None,
    estado: list[Estado] | None = None,
    q: str | None = None,
    area_id: uuid.UUID | None = None,
    responsable_id: uuid.UUID | None = None,
    seguimiento: str | None = None,
    vencidos: bool = False,
    actor: Usuario | None = None,
) -> tuple[bytes, str]:
    filtros, _q = armar_filtros(
        desde, hasta, tipo or [], estado or [], q, area_id, responsable_id, seguimiento, vencidos
    )
    total = db.scalar(select(func.count()).select_from(Evento).where(*filtros))
    if total > MAX_FILAS_CSV:
        raise HTTPException(400, f"Son {total} eventos; el máximo por exportación es {MAX_FILAS_CSV}. Afina el filtro.")
    filas = db.scalars(
        con_relaciones().where(*filtros).order_by(Evento.fecha_hecho.desc(), Evento.creado_en.desc())
    ).unique().all()

    salida = io.StringIO()
    w = csv.writer(salida)
    w.writerow(COLUMNAS_CSV)
    for e in filas:
        w.writerow([_celda(v) for v in (
            e.folio, e.fecha_hecho, e.tipo, e.subtipo, e.titulo, e.descripcion, e.referencia,
            e.area.nombre if e.area else None, e.solicitante_nombre, e.estado,
            "sí" if e.requiere_seguimiento else "no", e.prioridad, e.autor.nombre,
            e.responsable.nombre if e.responsable else None, e.creado_en, e.cerrado_en,
        )])
    # utf-8 con BOM para que Excel respete los acentos.
    cuerpo = ("\ufeff" + salida.getvalue()).encode("utf-8")
    nombre = f"bitacora-{hoy_en_zona().isoformat()}.csv"
    if actor is not None:
        registrar_actividad(
            db,
            actor,
            accion="csv_exportado",
            entidad="archivo",
            titulo=nombre,
            detalle=f"Filas exportadas: {len(filas)}" + (f" · filtro q={q}" if q else ""),
        )
        db.commit()
    return cuerpo, nombre


def obtener(db: Session, folio: str, incluir: list[str], acceso: Acceso) -> EventoDetalleOut:
    pedidos = {x.strip() for item in incluir for x in item.split(",") if x.strip()}
    if acceso.clave is not None and not pedidos <= {"seguimientos", "compromisos"}:
        raise HTTPException(400, "Con clave de API solo se puede incluir seguimientos y compromisos")
    e = buscar_evento(db, folio)
    salida = EventoDetalleOut(**a_salida(e).model_dump())
    if "seguimientos" in pedidos:
        salida.seguimientos = lista_seguimientos(db, e)
    if "compromisos" in pedidos:
        salida.compromisos = lista_compromisos(db, e)
    if "auditoria" in pedidos:
        filas = db.scalars(
            select(Auditoria).options(joinedload(Auditoria.usuario))
            .where(Auditoria.evento_id == e.id).order_by(Auditoria.creado_en, Auditoria.id)
        ).all()
        salida.auditoria = [AuditoriaOut.model_validate(a) for a in filas]
    return salida


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
    if not (tiene_permiso(usuario, Permiso.editar_cabecera) or es_autor_mismo_dia):
        raise conflicto("sin_permiso", "El autor corrige el mismo día; después, solo el encargado o el jefe")

    nuevo_tipo = pedidos.get("tipo", e.tipo)
    nuevo_subtipo = pedidos["subtipo"] if "subtipo" in pedidos else e.subtipo
    cambia_clasificacion = nuevo_tipo != e.tipo or nuevo_subtipo != e.subtipo
    if cambia_clasificacion and nuevo_subtipo and nuevo_subtipo not in vigentes(db, nuevo_tipo):
        raise HTTPException(400, f"El subtipo '{nuevo_subtipo}' no es válido para {nuevo_tipo.value}")
    if pedidos.get("fecha_hecho") and pedidos["fecha_hecho"] > hoy_en_zona():
        raise HTTPException(400, "La fecha del hecho no puede estar en el futuro")
    area_nueva = None
    if pedidos.get("area_id"):
        area_nueva = db.get(Area, pedidos["area_id"])
        if not area_nueva or (not area_nueva.activa and pedidos["area_id"] != e.area_id):
            raise HTTPException(400, "El área no existe o está inactiva")

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
        db.add(Auditoria(
            evento_id=e.id, campo=etiqueta, valor_anterior=antes, valor_nuevo=despues,
            usuario_id=usuario.id, creado_en=_ahora(),
        ))
        hubo = True
    return hubo


def modificar(db: Session, folio: str, datos: EventoPatch, usuario: Usuario) -> EventoOut:
    """CU-04 (seguimiento), CU-05 (responsable y prioridad) y CU-23 (corregir cabecera)."""
    e = buscar_evento(db, folio)
    toca_cabecera = any(c in datos.model_fields_set for c in CAMPOS_CABECERA)
    toca_seguimiento = (
        datos.requiere_seguimiento is not None or datos.responsable_id is not None or datos.prioridad is not None
    )

    if toca_cabecera:
        hubo_cab = _corregir_cabecera(db, e, datos, usuario)
        if hubo_cab:
            registrar_actividad(
                db,
                usuario,
                accion="cabecera_corregida",
                entidad="evento",
                entidad_id=str(e.id),
                folio=e.folio,
                titulo=e.titulo,
                detalle="Corrección de cabecera del evento",
            )

    if toca_seguimiento:
        if e.estado in (Estado.cerrado, Estado.cancelado):
            raise conflicto("evento_cerrado", "El evento está cerrado o cancelado")
        if datos.responsable_id is not None and not usuario_activo(db, datos.responsable_id):
            raise HTTPException(400, "El responsable no existe o está inactivo")

        anterior = e.estado
        if datos.requiere_seguimiento is True and not e.requiere_seguimiento:
            # CU-04: activar. Cualquier miembro del equipo.
            e.requiere_seguimiento = True
            e.estado = Estado.abierto
            e.responsable_id = datos.responsable_id or e.responsable_id or usuario.id
            e.prioridad = datos.prioridad or e.prioridad or Prioridad.media
            nota(db, e, usuario, datos.nota or "Se activó el seguimiento.", anterior, Estado.abierto)
        elif datos.requiere_seguimiento is False and e.requiere_seguimiento:
            # CU-04: quitar. Solo encargado/jefe y sin compromisos pendientes.
            if not tiene_permiso(usuario, Permiso.cancelar_cerrar, Permiso.editar_cabecera):
                raise conflicto("sin_permiso", "Solo el encargado o el jefe pueden quitar el seguimiento")
            if pendientes_del_evento(db, e):
                raise conflicto("compromisos_pendientes", "Hay compromisos pendientes en este evento")
            e.requiere_seguimiento = False
            e.estado = Estado.informativo
            e.responsable_id = None
            e.prioridad = None
            nota(db, e, usuario, datos.nota or "Se quitó el seguimiento.", anterior, Estado.informativo)

        if datos.responsable_id is not None or datos.prioridad is not None:
            # CU-05: asignar responsable y prioridad. Encargado/jefe (o quien activa el seguimiento).
            puede_asignar = tiene_permiso(usuario, Permiso.cancelar_cerrar, Permiso.editar_cabecera)
            if not puede_asignar and not (datos.requiere_seguimiento is True and anterior == Estado.informativo):
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
                nota(db, e, usuario, datos.nota or "Se cambió: " + ", ".join(cambios) + ".")

        resp_obj = db.get(Usuario, e.responsable_id) if e.responsable_id else None
        registrar_evento_origen(db, e, e.autor, resp_obj)
        registrar_actividad(
            db,
            usuario,
            accion="evento_modificado",
            entidad="evento",
            entidad_id=str(e.id),
            folio=e.folio,
            titulo=e.titulo,
            detalle=f"Seguimiento={e.requiere_seguimiento}, estado={e.estado.value}",
        )

    reindexar(db, e)
    db.commit()
    return a_salida(buscar_evento(db, e.folio))


def cambiar_estado(db: Session, folio: str, datos: CambioEstadoIn, usuario: Usuario) -> EventoOut:
    """CU-08 y CU-09. Cada cambio escribe una nota automática además de la nota de la persona."""
    e = buscar_evento(db, folio)
    desde, hacia = e.estado, datos.estado

    if not e.requiere_seguimiento:
        raise conflicto("sin_seguimiento", "El evento no tiene seguimiento; actívalo primero")
    reabriendo = desde == Estado.cerrado and hacia == Estado.abierto
    if desde == Estado.cancelado or (desde == Estado.cerrado and not reabriendo):
        raise conflicto("evento_cerrado", "El evento está cerrado o cancelado")
    puede_reabrir = tiene_permiso(usuario, Permiso.reabrir_eventos)
    puede_cerrar = tiene_permiso(usuario, Permiso.cancelar_cerrar)
    if reabriendo and not puede_reabrir:
        raise conflicto("sin_permiso", "Solo el encargado o el jefe pueden reabrir un evento")
    if not transicion_valida(desde, hacia, usuario.rol, gestor=(puede_reabrir if reabriendo else puede_cerrar)):
        raise conflicto("transicion_invalida", f"No se puede pasar de {desde.value} a {hacia.value}")

    if not puede_cerrar and not (reabriendo and puede_reabrir):
        if not tiene_permiso(usuario, Permiso.cambiar_estado):
            raise conflicto("sin_permiso", "Tu rol no permite cambiar el estado de eventos")
        es_suyo = usuario.id in (e.autor_id, e.responsable_id)
        if hacia not in ASISTENTE_PUEDE or not es_suyo:
            raise conflicto(
                "sin_permiso",
                "Solo el encargado o el jefe cancelan o cierran; el asistente solo avanza sus eventos hasta resuelto",
            )

    texto_nota = (datos.nota or "").strip()
    if hacia == Estado.en_espera and not texto_nota:
        raise HTTPException(422, "En espera exige una nota que diga de quién se espera")
    if hacia == Estado.cerrado and desde in CIERRE_CON_ATAJO and not texto_nota:
        raise HTTPException(422, "Cerrar desde " + desde.value + " exige una nota de cierre")
    if reabriendo and not texto_nota:
        raise HTTPException(422, "Reabrir exige una nota con el motivo")

    if hacia in (Estado.cerrado, Estado.cancelado):
        pendientes = pendientes_del_evento(db, e)
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
    elif reabriendo:
        e.cerrado_en = None  # vuelve al stock abierto; el cierre anterior queda en las notas
    nota(db, e, usuario, f"Estado: {desde.value} → {hacia.value}.", desde, hacia)  # automática
    if texto_nota:
        nota(db, e, usuario, texto_nota)
    registrar_actividad(
        db,
        usuario,
        accion="estado_cambiado",
        entidad="evento",
        entidad_id=str(e.id),
        folio=e.folio,
        titulo=e.titulo,
        detalle=f"{desde.value} → {hacia.value}" + (f" · {texto_nota}" if texto_nota else ""),
    )
    reindexar(db, e)
    db.commit()
    return a_salida(buscar_evento(db, e.folio))


def obtener_seguimientos(db: Session, folio: str) -> list[SeguimientoOut]:
    return lista_seguimientos(db, buscar_evento(db, folio))


def agregar_nota(db: Session, folio: str, datos: SeguimientoIn, usuario: Usuario) -> SeguimientoOut:
    """CU-07. La nota no se edita. En un evento cerrado solo encargado/jefe, y no lo reabre."""
    e = buscar_evento(db, folio)
    if e.estado == Estado.cancelado:
        raise conflicto("evento_cerrado", "El evento está cancelado")
    if e.estado == Estado.cerrado and not tiene_permiso(usuario, Permiso.cancelar_cerrar, Permiso.reabrir_eventos):
        raise conflicto("sin_permiso", "En un evento cerrado solo el encargado o el jefe agregan notas")
    n = nota(db, e, usuario, datos.nota.strip())
    registrar_actividad(
        db,
        usuario,
        accion="nota_agregada",
        entidad="evento",
        entidad_id=str(e.id),
        folio=e.folio,
        titulo=e.titulo,
        detalle=datos.nota.strip()[:300],
    )
    reindexar(db, e)
    db.commit()
    return SeguimientoOut.model_validate(n)


def obtener_compromisos(db: Session, folio: str) -> list[CompromisoOut]:
    return lista_compromisos(db, buscar_evento(db, folio))


def crear_compromiso(db: Session, folio: str, datos: CompromisoIn, usuario: Usuario) -> CompromisoOut:
    """CU-06. Requiere seguimiento y que el evento no esté cerrado ni cancelado."""
    e = buscar_evento(db, folio)
    if not e.requiere_seguimiento:
        raise conflicto("sin_seguimiento", "El evento no tiene seguimiento; actívalo para registrar compromisos")
    if e.estado in (Estado.cerrado, Estado.cancelado):
        raise conflicto("evento_cerrado", "El evento está cerrado o cancelado")
    if datos.fecha_limite < hoy_en_zona():
        raise HTTPException(400, "La fecha límite no puede estar en el pasado")
    responsable_id = datos.responsable_id or usuario.id
    if not usuario_activo(db, responsable_id):
        raise HTTPException(400, "El responsable no existe o está inactivo")

    c = Compromiso(
        evento_id=e.id,
        descripcion=datos.descripcion.strip(),
        responsable_id=responsable_id,
        fecha_limite=datos.fecha_limite,
        estado=EstadoCompromiso.pendiente,
    )
    db.add(c)
    db.flush()
    nota(db, e, usuario, f"Compromiso registrado para el {datos.fecha_limite.isoformat()}: {c.descripcion}")
    registrar_actividad(
        db,
        usuario,
        accion="compromiso_creado",
        entidad="compromiso",
        entidad_id=str(c.id),
        folio=e.folio,
        titulo=c.descripcion,
        detalle=f"Fecha límite: {datos.fecha_limite.isoformat()}",
    )
    reindexar(db, e)
    db.commit()
    c = db.scalars(select(Compromiso).options(joinedload(Compromiso.responsable)).where(Compromiso.id == c.id)).one()
    return compromiso_a_salida(c, e.folio)
