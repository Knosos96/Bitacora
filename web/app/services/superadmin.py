"""Servicios de consulta histórica, auditoría y documentación del Superusuario."""
import csv
import io
import uuid
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.enums import Estado, EstadoCompromiso, Tipo
from app.models import (
    ActividadBitacora,
    Compromiso,
    CuentaHistorica,
    Evento,
    EventoOrigen,
    Seguimiento,
)
from app.schemas.superadmin import (
    ActividadOut,
    CuentaHistoricaOut,
    ExpedienteCuentaOut,
    PendienteHistoricoCompOut,
    ReferenciaArchivoOut,
    RegistroHistoricoOut,
    RespaldoArchivoOut,
    SuperArchivosOut,
    SuperPendientesOut,
    SuperResumenOut,
)
from app.services.eventos import _celda, hoy_en_zona
from app.services.historial import sincronizar_existentes

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RESPALDOS_DIR = BASE_DIR / "respaldos"
ESTADOS_ABIERTOS = (Estado.abierto, Estado.en_proceso, Estado.en_espera, Estado.resuelto)


def _inicio_dia_utc(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=ZoneInfo(settings.zona_horaria)).astimezone(timezone.utc)


def _estados_por_cuenta(db: Session) -> dict[uuid.UUID, str]:
    return {
        row[0]: row[1]
        for row in db.execute(select(CuentaHistorica.id, CuentaHistorica.estado)).all()
    }


def _conteos_evento(db: Session) -> tuple[dict[uuid.UUID, int], dict[uuid.UUID, int]]:
    notas = {
        row[0]: row[1]
        for row in db.execute(select(Seguimiento.evento_id, func.count()).group_by(Seguimiento.evento_id)).all()
    }
    comps = {
        row[0]: row[1]
        for row in db.execute(select(Compromiso.evento_id, func.count()).group_by(Compromiso.evento_id)).all()
    }
    return notas, comps


def _armar_registro(
    ev: Evento,
    origen: EventoOrigen | None,
    estados_cuentas: dict[uuid.UUID, str],
    notas_map: dict[uuid.UUID, int],
    comps_map: dict[uuid.UUID, int],
) -> RegistroHistoricoOut:
    autor_id = origen.autor_id if origen else ev.autor_id
    autor_nombre = origen.autor_nombre if origen else ev.autor.nombre
    autor_correo = origen.autor_correo if origen else ev.autor.correo
    resp_id = origen.responsable_id if origen else ev.responsable_id
    resp_nombre = origen.responsable_nombre if origen else (ev.responsable.nombre if ev.responsable else None)

    return RegistroHistoricoOut(
        id=ev.id,
        folio=ev.folio,
        tipo=ev.tipo.value,
        subtipo=ev.subtipo,
        titulo=ev.titulo,
        descripcion=ev.descripcion,
        referencia=ev.referencia,
        fecha_hecho=ev.fecha_hecho,
        estado=ev.estado.value,
        prioridad=ev.prioridad.value if ev.prioridad else None,
        requiere_seguimiento=ev.requiere_seguimiento,
        area_nombre=ev.area.nombre if ev.area else None,
        solicitante=ev.solicitante_nombre,
        autor_original_id=autor_id,
        autor_original_nombre=autor_nombre,
        autor_original_correo=autor_correo,
        autor_original_estado=estados_cuentas.get(autor_id, "activa"),
        responsable_original_id=resp_id,
        responsable_original_nombre=resp_nombre,
        responsable_original_estado=estados_cuentas.get(resp_id, "activa") if resp_id else None,
        creado_en=ev.creado_en,
        cerrado_en=ev.cerrado_en,
        notas_count=notas_map.get(ev.id, 0),
        compromisos_count=comps_map.get(ev.id, 0),
    )


def _actividad_a_out(a: ActividadBitacora) -> ActividadOut:
    return ActividadOut(
        id=a.id,
        actor_id=a.actor_id,
        actor_nombre=a.actor_nombre,
        actor_correo=a.actor_correo,
        actor_rol=a.actor_rol,
        accion=a.accion,
        entidad=a.entidad,
        entidad_id=a.entidad_id,
        folio=a.folio,
        titulo=a.titulo,
        detalle=a.detalle,
        creado_en=a.creado_en,
    )


def _archivos_respaldo() -> list[RespaldoArchivoOut]:
    if not RESPALDOS_DIR.is_dir():
        return []
    salida = []
    for p in sorted(RESPALDOS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not p.is_file() or p.name.startswith("."):
            continue
        st = p.stat()
        salida.append(RespaldoArchivoOut(
            nombre=p.name,
            tamano_bytes=st.st_size,
            modificado_en=datetime.fromtimestamp(st.st_mtime, tz=timezone.utc),
        ))
    return salida


def resumen(db: Session) -> SuperResumenOut:
    sincronizar_existentes(db)
    hoy = hoy_en_zona()

    cuentas = dict(
        db.execute(select(CuentaHistorica.estado, func.count()).group_by(CuentaHistorica.estado)).all()
    )
    activas = cuentas.get("activa", 0)
    inactivas = cuentas.get("inactiva", 0)
    eliminadas = cuentas.get("eliminada", 0)

    eventos_total = db.scalar(select(func.count()).select_from(Evento)) or 0
    incidencias_total = db.scalar(
        select(func.count()).select_from(Evento).where(Evento.tipo == Tipo.incidencia)
    ) or 0
    pendientes_eventos = db.scalar(
        select(func.count()).select_from(Evento).where(
            Evento.requiere_seguimiento.is_(True), Evento.estado.in_(ESTADOS_ABIERTOS)
        )
    ) or 0
    pendientes_compromisos = db.scalar(
        select(func.count()).select_from(Compromiso).where(Compromiso.estado == EstadoCompromiso.pendiente)
    ) or 0
    compromisos_vencidos = db.scalar(
        select(func.count()).select_from(Compromiso).where(
            Compromiso.estado == EstadoCompromiso.pendiente, Compromiso.fecha_limite < hoy
        )
    ) or 0
    actividades_total = db.scalar(select(func.count()).select_from(ActividadBitacora)) or 0

    exportaciones = db.scalar(
        select(func.count()).select_from(ActividadBitacora).where(ActividadBitacora.accion == "csv_exportado")
    ) or 0
    referencias = db.scalar(
        select(func.count()).select_from(Evento).where(Evento.referencia.is_not(None), Evento.referencia != "")
    ) or 0
    respaldos = len(_archivos_respaldo())

    return SuperResumenOut(
        cuentas_total=activas + inactivas + eliminadas,
        cuentas_activas=activas,
        cuentas_inactivas=inactivas,
        cuentas_eliminadas=eliminadas,
        eventos_total=eventos_total,
        incidencias_total=incidencias_total,
        pendientes_eventos=pendientes_eventos,
        pendientes_compromisos=pendientes_compromisos,
        compromisos_vencidos=compromisos_vencidos,
        actividades_total=actividades_total,
        archivos_total=exportaciones + referencias + respaldos,
    )


def _cuenta_out(
    c: CuentaHistorica,
    ev_counts: dict[uuid.UUID, int],
    inc_counts: dict[uuid.UUID, int],
    pen_counts: dict[uuid.UUID, int],
    act_counts: dict[uuid.UUID, int],
) -> CuentaHistoricaOut:
    return CuentaHistoricaOut(
        id=c.id,
        nombre=c.nombre,
        correo=c.correo,
        rol=c.rol,
        rol_custom_nombre=c.rol_custom_nombre,
        estado=c.estado,
        creado_en=c.creado_en,
        actualizado_en=c.actualizado_en,
        eliminado_en=c.eliminado_en,
        eliminado_por_nombre=c.eliminado_por_nombre,
        eliminado_por_correo=c.eliminado_por_correo,
        eventos_creados=ev_counts.get(c.id, 0),
        incidencias_creadas=inc_counts.get(c.id, 0),
        pendientes_abiertos=pen_counts.get(c.id, 0),
        actividades_count=act_counts.get(c.id, 0),
    )


def _mapas_cuentas(db: Session):
    ev_counts = dict(
        db.execute(select(EventoOrigen.autor_id, func.count()).group_by(EventoOrigen.autor_id)).all()
    )
    inc_counts = dict(
        db.execute(
            select(EventoOrigen.autor_id, func.count())
            .join(Evento, Evento.id == EventoOrigen.evento_id)
            .where(Evento.tipo == Tipo.incidencia)
            .group_by(EventoOrigen.autor_id)
        ).all()
    )
    pen_counts = dict(
        db.execute(
            select(EventoOrigen.autor_id, func.count())
            .join(Evento, Evento.id == EventoOrigen.evento_id)
            .where(Evento.requiere_seguimiento.is_(True), Evento.estado.in_(ESTADOS_ABIERTOS))
            .group_by(EventoOrigen.autor_id)
        ).all()
    )
    act_counts = dict(
        db.execute(
            select(ActividadBitacora.actor_id, func.count())
            .where(ActividadBitacora.actor_id.is_not(None))
            .group_by(ActividadBitacora.actor_id)
        ).all()
    )
    return ev_counts, inc_counts, pen_counts, act_counts


def listar_cuentas(db: Session, estado: str | None = None, q: str | None = None) -> list[CuentaHistoricaOut]:
    sincronizar_existentes(db)
    consulta = select(CuentaHistorica).order_by(CuentaHistorica.creado_en.desc())
    if estado:
        consulta = consulta.where(CuentaHistorica.estado == estado)
    cuentas = list(db.scalars(consulta).all())
    if q:
        ql = q.strip().lower()
        cuentas = [
            c for c in cuentas
            if ql in c.nombre.lower() or ql in c.correo.lower() or ql in c.rol.lower()
            or (c.rol_custom_nombre and ql in c.rol_custom_nombre.lower())
        ]
    ev_counts, inc_counts, pen_counts, act_counts = _mapas_cuentas(db)
    return [_cuenta_out(c, ev_counts, inc_counts, pen_counts, act_counts) for c in cuentas]


def listar_registros(
    db: Session,
    cuenta_id: uuid.UUID | None = None,
    tipo: Tipo | None = None,
    estado: Estado | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    q: str | None = None,
) -> list[RegistroHistoricoOut]:
    sincronizar_existentes(db)
    consulta = (
        select(Evento, EventoOrigen)
        .outerjoin(EventoOrigen, EventoOrigen.evento_id == Evento.id)
        .options(joinedload(Evento.area), joinedload(Evento.autor), joinedload(Evento.responsable))
        .order_by(Evento.fecha_hecho.desc(), Evento.creado_en.desc())
    )
    if cuenta_id is not None:
        consulta = consulta.where(
            (EventoOrigen.autor_id == cuenta_id) | (EventoOrigen.responsable_id == cuenta_id)
        )
    if tipo is not None:
        consulta = consulta.where(Evento.tipo == tipo)
    if estado is not None:
        consulta = consulta.where(Evento.estado == estado)
    if desde is not None:
        consulta = consulta.where(Evento.fecha_hecho >= desde)
    if hasta is not None:
        consulta = consulta.where(Evento.fecha_hecho <= hasta)

    filas = db.execute(consulta).unique().all()
    estados_cuentas = _estados_por_cuenta(db)
    notas_map, comps_map = _conteos_evento(db)
    registros = [_armar_registro(ev, orig, estados_cuentas, notas_map, comps_map) for ev, orig in filas]
    if q:
        ql = q.strip().lower()
        registros = [
            r for r in registros
            if ql in r.folio.lower()
            or ql in r.titulo.lower()
            or ql in r.descripcion.lower()
            or ql in r.autor_original_nombre.lower()
            or ql in r.autor_original_correo.lower()
            or (r.responsable_original_nombre and ql in r.responsable_original_nombre.lower())
        ]
    return registros


def listar_pendientes(db: Session, cuenta_id: uuid.UUID | None = None) -> SuperPendientesOut:
    sincronizar_existentes(db)
    hoy = hoy_en_zona()
    estados_cuentas = _estados_por_cuenta(db)
    notas_map, comps_map = _conteos_evento(db)

    q_ev = (
        select(Evento, EventoOrigen)
        .outerjoin(EventoOrigen, EventoOrigen.evento_id == Evento.id)
        .options(joinedload(Evento.area), joinedload(Evento.autor), joinedload(Evento.responsable))
        .where(Evento.requiere_seguimiento.is_(True), Evento.estado.in_(ESTADOS_ABIERTOS))
        .order_by(Evento.fecha_hecho.asc(), Evento.creado_en.asc())
    )
    if cuenta_id is not None:
        q_ev = q_ev.where((EventoOrigen.autor_id == cuenta_id) | (EventoOrigen.responsable_id == cuenta_id))
    ev_filas = db.execute(q_ev).unique().all()

    q_comp = (
        select(Compromiso)
        .options(joinedload(Compromiso.responsable), joinedload(Compromiso.evento))
        .where(Compromiso.estado == EstadoCompromiso.pendiente)
        .order_by(Compromiso.fecha_limite.asc())
    )
    comp_filas = db.scalars(q_comp).unique().all()
    if cuenta_id is not None:
        ev_ids_cuenta = {ev.id for ev, _ in ev_filas}
        comp_filas = [c for c in comp_filas if c.responsable_id == cuenta_id or c.evento_id in ev_ids_cuenta]

    return SuperPendientesOut(
        eventos=[_armar_registro(ev, orig, estados_cuentas, notas_map, comps_map) for ev, orig in ev_filas],
        compromisos=[
            PendienteHistoricoCompOut(
                id=c.id,
                evento_folio=c.evento.folio,
                evento_titulo=c.evento.titulo,
                evento_tipo=c.evento.tipo.value,
                descripcion=c.descripcion,
                responsable_nombre=c.responsable.nombre if c.responsable else "—",
                fecha_limite=c.fecha_limite,
                vencido=c.fecha_limite < hoy,
            )
            for c in comp_filas
        ],
    )


def listar_archivos(db: Session) -> SuperArchivosOut:
    sincronizar_existentes(db)
    estados_cuentas = _estados_por_cuenta(db)
    exportaciones = [
        _actividad_a_out(a)
        for a in db.scalars(
            select(ActividadBitacora)
            .where(ActividadBitacora.accion == "csv_exportado")
            .order_by(ActividadBitacora.creado_en.desc())
            .limit(300)
        ).all()
    ]
    refs_rows = db.execute(
        select(Evento, EventoOrigen)
        .outerjoin(EventoOrigen, EventoOrigen.evento_id == Evento.id)
        .options(joinedload(Evento.autor))
        .where(Evento.referencia.is_not(None), Evento.referencia != "")
        .order_by(Evento.fecha_hecho.desc(), Evento.creado_en.desc())
        .limit(300)
    ).unique().all()

    referencias = []
    for ev, orig in refs_rows:
        aid = orig.autor_id if orig else ev.autor_id
        anom = orig.autor_nombre if orig else ev.autor.nombre
        referencias.append(ReferenciaArchivoOut(
            folio=ev.folio,
            titulo=ev.titulo,
            tipo=ev.tipo.value,
            fecha_hecho=ev.fecha_hecho,
            referencia=ev.referencia or "",
            autor_nombre=anom,
            autor_estado=estados_cuentas.get(aid, "activa"),
        ))

    return SuperArchivosOut(
        exportaciones=exportaciones,
        respaldos=_archivos_respaldo(),
        referencias=referencias,
    )


def listar_actividad(
    db: Session,
    cuenta_id: uuid.UUID | None = None,
    accion: str | None = None,
    entidad: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    q: str | None = None,
    limit: int = 250,
) -> list[ActividadOut]:
    consulta = select(ActividadBitacora).order_by(ActividadBitacora.creado_en.desc()).limit(limit)
    if cuenta_id is not None:
        consulta = consulta.where(ActividadBitacora.actor_id == cuenta_id)
    if accion:
        consulta = consulta.where(ActividadBitacora.accion == accion)
    if entidad:
        consulta = consulta.where(ActividadBitacora.entidad == entidad)
    if desde is not None:
        consulta = consulta.where(ActividadBitacora.creado_en >= _inicio_dia_utc(desde))
    if hasta is not None:
        from datetime import timedelta
        consulta = consulta.where(ActividadBitacora.creado_en < _inicio_dia_utc(hasta + timedelta(days=1)))
    filas = list(db.scalars(consulta).all())
    if q:
        ql = q.strip().lower()
        filas = [
            a for a in filas
            if ql in a.actor_nombre.lower()
            or ql in a.actor_correo.lower()
            or ql in a.accion.lower()
            or (a.folio and ql in a.folio.lower())
            or (a.titulo and ql in a.titulo.lower())
            or (a.detalle and ql in a.detalle.lower())
        ]
    return [_actividad_a_out(a) for a in filas]


def expediente_cuenta(db: Session, cuenta_id: uuid.UUID) -> ExpedienteCuentaOut:
    sincronizar_existentes(db)
    cuenta = db.get(CuentaHistorica, cuenta_id)
    if cuenta is None:
        raise HTTPException(404, "Cuenta histórica no encontrada")
    ev_counts, inc_counts, pen_counts, act_counts = _mapas_cuentas(db)
    registros = listar_registros(db, cuenta_id=cuenta_id)
    incidencias = [r for r in registros if r.tipo == Tipo.incidencia.value]
    pendientes = listar_pendientes(db, cuenta_id=cuenta_id)
    actividades = listar_actividad(db, cuenta_id=cuenta_id, limit=500)
    exportaciones = [a for a in actividades if a.accion == "csv_exportado"]
    return ExpedienteCuentaOut(
        cuenta=_cuenta_out(cuenta, ev_counts, inc_counts, pen_counts, act_counts),
        registros=registros,
        incidencias=incidencias,
        pendientes=pendientes,
        actividades=actividades,
        exportaciones=exportaciones,
    )


def exportar_dossier_csv(db: Session, seccion: str = "actividad", cuenta_id: uuid.UUID | None = None) -> tuple[bytes, str]:
    salida = io.StringIO()
    w = csv.writer(salida)

    if seccion == "cuentas":
        w.writerow(["id", "nombre", "correo", "rol", "rol_personalizado", "estado",
                    "creado_en", "eliminado_en", "eliminado_por", "eventos", "incidencias", "pendientes", "actividades"])
        for c in listar_cuentas(db):
            w.writerow([_celda(v) for v in (
                c.id, c.nombre, c.correo, c.rol, c.rol_custom_nombre, c.estado,
                c.creado_en, c.eliminado_en, c.eliminado_por_nombre,
                c.eventos_creados, c.incidencias_creadas, c.pendientes_abiertos, c.actividades_count,
            )])
    elif seccion == "registros":
        w.writerow(["folio", "fecha_hecho", "tipo", "subtipo", "titulo", "estado", "prioridad",
                    "autor_original", "correo_autor", "estado_cuenta_autor",
                    "responsable_original", "area", "referencia", "creado_en", "cerrado_en"])
        for r in listar_registros(db, cuenta_id=cuenta_id):
            w.writerow([_celda(v) for v in (
                r.folio, r.fecha_hecho, r.tipo, r.subtipo, r.titulo, r.estado, r.prioridad,
                r.autor_original_nombre, r.autor_original_correo, r.autor_original_estado,
                r.responsable_original_nombre, r.area_nombre, r.referencia, r.creado_en, r.cerrado_en,
            )])
    else:
        w.writerow(["fecha", "actor_nombre", "actor_correo", "actor_rol", "accion", "entidad", "folio", "titulo", "detalle"])
        for a in listar_actividad(db, cuenta_id=cuenta_id, limit=2000):
            w.writerow([_celda(v) for v in (
                a.creado_en, a.actor_nombre, a.actor_correo, a.actor_rol,
                a.accion, a.entidad, a.folio, a.titulo, a.detalle,
            )])

    cuerpo = ("\ufeff" + salida.getvalue()).encode("utf-8")
    nombre = f"dossier-superadmin-{seccion}-{hoy_en_zona().isoformat()}.csv"
    return cuerpo, nombre
