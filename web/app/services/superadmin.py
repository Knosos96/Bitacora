"""Servicios de consulta histórica, auditoría y documentación del Superusuario."""
import csv
import io
import uuid
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.enums import Estado, EstadoCompromiso, Rol, Tipo
from app.models import (
    ActividadBitacora,
    Auditoria,
    ClaveApi,
    Compromiso,
    CuentaHistorica,
    Evento,
    EventoOrigen,
    RolPersonalizado,
    Seguimiento,
    UsoClaveApi,
    Usuario,
)
from app.schemas.superadmin import (
    ActividadOut,
    AuditoriaDocOut,
    CompromisoDocOut,
    CuentaHistoricaOut,
    ExpedienteCuentaOut,
    PendienteHistoricoCompOut,
    PurgaCuentaIn,
    PurgaCuentaOut,
    PurgaResumenCuentaOut,
    ReferenciaArchivoOut,
    RegistroDetalleOut,
    RegistroHistoricoOut,
    RespaldoArchivoOut,
    SeguimientoDocOut,
    SuperArchivosOut,
    SuperPendientesOut,
    SuperResumenOut,
)
from app.services.eventos import _celda, hoy_en_zona
from app.services.historial import registrar_actividad, sincronizar_existentes

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
        area_nombre=ev.area.nombre if ev.area else (origen.area_nombre if origen else None),
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
                responsable_estado=estados_cuentas.get(c.responsable_id, "activa") if c.responsable_id else "activa",
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


def _datos_actor(cuentas_map: dict[uuid.UUID, CuentaHistorica], usuario_id: uuid.UUID, fallback_obj) -> tuple[str, str, str]:
    c = cuentas_map.get(usuario_id)
    if c is not None:
        return c.nombre, c.correo, c.estado
    if fallback_obj is not None:
        return fallback_obj.nombre, fallback_obj.correo, ("activa" if fallback_obj.activo and fallback_obj.eliminado_en is None else "inactiva")
    return "—", "—", "activa"


def detalle_registro(db: Session, folio: str) -> RegistroDetalleOut:
    sincronizar_existentes(db)
    ev: Evento | None = None
    try:
        eid = uuid.UUID(folio)
        ev = db.scalar(
            select(Evento)
            .options(joinedload(Evento.area), joinedload(Evento.autor), joinedload(Evento.responsable))
            .where(Evento.id == eid)
        )
    except ValueError:
        ev = db.scalar(
            select(Evento)
            .options(joinedload(Evento.area), joinedload(Evento.autor), joinedload(Evento.responsable))
            .where(Evento.folio == folio.upper())
        )
    if ev is None:
        raise HTTPException(404, "Registro no encontrado")

    origen = db.get(EventoOrigen, ev.id)
    cuentas_map = {c.id: c for c in db.scalars(select(CuentaHistorica)).all()}
    estados_cuentas = {cid: c.estado for cid, c in cuentas_map.items()}
    notas_map, comps_map = _conteos_evento(db)

    notas_filas = list(
        db.scalars(
            select(Seguimiento)
            .options(joinedload(Seguimiento.autor))
            .where(Seguimiento.evento_id == ev.id)
            .order_by(Seguimiento.creado_en.asc())
        ).all()
    )
    comp_filas = list(
        db.scalars(
            select(Compromiso)
            .options(joinedload(Compromiso.responsable))
            .where(Compromiso.evento_id == ev.id)
            .order_by(Compromiso.fecha_limite.asc())
        ).all()
    )
    aud_filas = list(
        db.scalars(
            select(Auditoria)
            .options(joinedload(Auditoria.usuario))
            .where(Auditoria.evento_id == ev.id)
            .order_by(Auditoria.creado_en.asc())
        ).all()
    )

    notas = []
    for n in notas_filas:
        nombre, correo, estado_cuenta = _datos_actor(cuentas_map, n.autor_id, n.autor)
        notas.append(SeguimientoDocOut(
            id=n.id,
            autor_id=n.autor_id,
            autor_nombre=nombre,
            autor_correo=correo,
            autor_estado=estado_cuenta,
            nota=n.nota,
            estado_anterior=n.estado_anterior.value if n.estado_anterior else None,
            estado_nuevo=n.estado_nuevo.value if n.estado_nuevo else None,
            creado_en=n.creado_en,
        ))

    hoy = hoy_en_zona()
    compromisos = []
    for c in comp_filas:
        nombre, correo, estado_cuenta = _datos_actor(cuentas_map, c.responsable_id, c.responsable)
        compromisos.append(CompromisoDocOut(
            id=c.id,
            descripcion=c.descripcion,
            responsable_id=c.responsable_id,
            responsable_nombre=nombre,
            responsable_correo=correo,
            responsable_estado=estado_cuenta,
            fecha_limite=c.fecha_limite,
            estado=c.estado.value,
            vencido=(c.estado == EstadoCompromiso.pendiente and c.fecha_limite < hoy),
            cumplido_en=c.cumplido_en,
            creado_en=c.creado_en,
        ))

    auditoria = []
    for a in aud_filas:
        nombre, correo, estado_cuenta = _datos_actor(cuentas_map, a.usuario_id, a.usuario)
        auditoria.append(AuditoriaDocOut(
            id=a.id,
            campo=a.campo,
            valor_anterior=a.valor_anterior,
            valor_nuevo=a.valor_nuevo,
            usuario_id=a.usuario_id,
            usuario_nombre=nombre,
            usuario_correo=correo,
            usuario_estado=estado_cuenta,
            creado_en=a.creado_en,
        ))

    return RegistroDetalleOut(
        registro=_armar_registro(ev, origen, estados_cuentas, notas_map, comps_map),
        notas=notas,
        compromisos=compromisos,
        auditoria=auditoria,
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
    elif seccion == "expediente":
        if cuenta_id is None:
            raise HTTPException(400, "Debes indicar cuenta_id para exportar un expediente individual")
        exp = expediente_cuenta(db, cuenta_id)
        c = exp.cuenta
        w.writerow(["EXPEDIENTE INDIVIDUAL DE CUENTA"])
        w.writerow(["id", "nombre", "correo", "rol", "rol_personalizado", "estado",
                    "creado_en", "eliminado_en", "eliminado_por", "eventos", "incidencias", "pendientes", "actividades"])
        w.writerow([_celda(v) for v in (
            c.id, c.nombre, c.correo, c.rol, c.rol_custom_nombre, c.estado,
            c.creado_en, c.eliminado_en, c.eliminado_por_nombre,
            c.eventos_creados, c.incidencias_creadas, c.pendientes_abiertos, c.actividades_count,
        )])
        w.writerow([])
        w.writerow(["REGISTROS E INCIDENCIAS DEL USUARIO"])
        w.writerow(["folio", "fecha_hecho", "tipo", "subtipo", "titulo", "estado", "prioridad",
                    "autor_original", "responsable_original", "area", "referencia", "creado_en", "cerrado_en"])
        for r in exp.registros:
            w.writerow([_celda(v) for v in (
                r.folio, r.fecha_hecho, r.tipo, r.subtipo, r.titulo, r.estado, r.prioridad,
                r.autor_original_nombre, r.responsable_original_nombre, r.area_nombre, r.referencia,
                r.creado_en, r.cerrado_en,
            )])
        w.writerow([])
        w.writerow(["COMPROMISOS PENDIENTES DEL USUARIO"])
        w.writerow(["fecha_limite", "evento_folio", "evento_titulo", "descripcion", "responsable", "vencido"])
        for cp in exp.pendientes.compromisos:
            w.writerow([_celda(v) for v in (
                cp.fecha_limite, cp.evento_folio, cp.evento_titulo, cp.descripcion,
                cp.responsable_nombre, "SI" if cp.vencido else "NO",
            )])
        w.writerow([])
        w.writerow(["BITACORA DE ACTIVIDAD DEL USUARIO"])
        w.writerow(["fecha", "actor_nombre", "actor_correo", "accion", "entidad", "folio", "titulo", "detalle"])
        for a in exp.actividades:
            w.writerow([_celda(v) for v in (
                a.creado_en, a.actor_nombre, a.actor_correo, a.accion, a.entidad, a.folio, a.titulo, a.detalle,
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


def _cuenta_protegida_para_purga(db: Session, cuenta: CuentaHistorica, actor: Usuario) -> bool:
    if cuenta.id == actor.id or cuenta.rol == Rol.superusuario.value:
        return True
    u = db.get(Usuario, cuenta.id)
    if u is not None and u.rol == Rol.jefe and u.activo and u.eliminado_en is None:
        otros_jefes = db.scalar(
            select(func.count()).select_from(Usuario).where(
                Usuario.rol == Rol.jefe,
                Usuario.activo,
                Usuario.eliminado_en.is_(None),
                Usuario.id != u.id,
            )
        )
        if not otros_jefes:
            return True
    return False


def resumen_purga_cuenta(db: Session, cuenta_id: uuid.UUID, actor: Usuario) -> PurgaResumenCuentaOut:
    sincronizar_existentes(db)
    cuenta = db.get(CuentaHistorica, cuenta_id)
    if cuenta is None:
        raise HTTPException(404, "Cuenta histórica no encontrada")

    ev_creados_ids = select(Evento.id).where(Evento.autor_id == cuenta_id)
    eventos_creados = db.scalar(select(func.count()).select_from(Evento).where(Evento.autor_id == cuenta_id)) or 0
    eventos_asignados = db.scalar(
        select(func.count()).select_from(Evento).where(Evento.responsable_id == cuenta_id, Evento.autor_id != cuenta_id)
    ) or 0
    notas_otros = db.scalar(
        select(func.count()).select_from(Seguimiento).where(
            Seguimiento.autor_id == cuenta_id, ~Seguimiento.evento_id.in_(ev_creados_ids)
        )
    ) or 0
    comp_otros = db.scalar(
        select(func.count()).select_from(Compromiso).where(
            Compromiso.responsable_id == cuenta_id, ~Compromiso.evento_id.in_(ev_creados_ids)
        )
    ) or 0
    aud_otros = db.scalar(
        select(func.count()).select_from(Auditoria).where(
            Auditoria.usuario_id == cuenta_id, ~Auditoria.evento_id.in_(ev_creados_ids)
        )
    ) or 0
    claves_api = db.scalar(select(func.count()).select_from(ClaveApi).where(ClaveApi.creada_por_id == cuenta_id)) or 0
    roles_creados = db.scalar(
        select(func.count()).select_from(RolPersonalizado).where(RolPersonalizado.creado_por_id == cuenta_id)
    ) or 0
    actividades = db.scalar(
        select(func.count()).select_from(ActividadBitacora).where(ActividadBitacora.actor_id == cuenta_id)
    ) or 0

    return PurgaResumenCuentaOut(
        cuenta_id=cuenta.id,
        nombre=cuenta.nombre,
        correo=cuenta.correo,
        rol=cuenta.rol,
        estado=cuenta.estado,
        eventos_creados=eventos_creados,
        eventos_asignados=eventos_asignados,
        notas_en_otros_eventos=notas_otros,
        compromisos_en_otros_eventos=comp_otros,
        auditorias_en_otros_eventos=aud_otros,
        claves_api=claves_api,
        roles_creados=roles_creados,
        actividades=actividades,
        es_protegida=_cuenta_protegida_para_purga(db, cuenta, actor),
    )


def _eliminar_seguimientos(db: Session, condicion) -> int:
    es_pg = db.bind is not None and db.bind.dialect.name == "postgresql"
    if es_pg:
        db.execute(text("ALTER TABLE seguimiento DISABLE TRIGGER seguimiento_inmutable"))
    try:
        res = db.execute(delete(Seguimiento).where(condicion))
        return res.rowcount or 0
    finally:
        if es_pg:
            db.execute(text("ALTER TABLE seguimiento ENABLE TRIGGER seguimiento_inmutable"))


def purgar_datos_cuenta(
    db: Session,
    cuenta_id: uuid.UUID,
    datos: PurgaCuentaIn,
    actor: Usuario,
) -> PurgaCuentaOut:
    """Elimina de forma permanente y selectiva los datos relacionados a una cuenta de la BD."""
    sincronizar_existentes(db)
    cuenta = db.get(CuentaHistorica, cuenta_id)
    if cuenta is None:
        raise HTTPException(404, "Cuenta histórica no encontrada")

    if not any([
        datos.eliminar_eventos_creados,
        datos.eliminar_notas,
        datos.eliminar_compromisos,
        datos.eliminar_auditorias,
        datos.eliminar_claves_api,
        datos.eliminar_actividades,
        datos.eliminar_cuenta,
    ]):
        raise HTTPException(400, "Selecciona al menos un tipo de información para eliminar")

    if datos.eliminar_cuenta and _cuenta_protegida_para_purga(db, cuenta, actor):
        raise HTTPException(
            409,
            {"codigo": "sin_permiso", "detalle": "No se puede eliminar completamente la cuenta protegida o el último jefe activo"},
        )

    borrar_eventos = datos.eliminar_eventos_creados or datos.eliminar_cuenta
    borrar_notas = datos.eliminar_notas or datos.eliminar_cuenta
    borrar_compromisos = datos.eliminar_compromisos or datos.eliminar_cuenta
    borrar_auditorias = datos.eliminar_auditorias or datos.eliminar_cuenta
    borrar_claves = datos.eliminar_claves_api or datos.eliminar_cuenta
    borrar_actividades = datos.eliminar_actividades or datos.eliminar_cuenta

    eventos_eliminados = 0
    notas_eliminadas = 0
    compromisos_eliminados = 0
    auditorias_eliminadas = 0
    claves_eliminadas = 0
    actividades_eliminadas = 0

    if borrar_eventos:
        ev_ids = list(db.scalars(select(Evento.id).where(Evento.autor_id == cuenta_id)).all())
        if ev_ids:
            auditorias_eliminadas += db.execute(delete(Auditoria).where(Auditoria.evento_id.in_(ev_ids))).rowcount or 0
            compromisos_eliminados += db.execute(delete(Compromiso).where(Compromiso.evento_id.in_(ev_ids))).rowcount or 0
            notas_eliminadas += _eliminar_seguimientos(db, Seguimiento.evento_id.in_(ev_ids))
            db.execute(delete(EventoOrigen).where(EventoOrigen.evento_id.in_(ev_ids)))
            eventos_eliminados += db.execute(delete(Evento).where(Evento.id.in_(ev_ids))).rowcount or 0

    if borrar_notas:
        notas_eliminadas += _eliminar_seguimientos(db, Seguimiento.autor_id == cuenta_id)

    if borrar_compromisos:
        compromisos_eliminados += db.execute(delete(Compromiso).where(Compromiso.responsable_id == cuenta_id)).rowcount or 0

    if borrar_auditorias:
        auditorias_eliminadas += db.execute(delete(Auditoria).where(Auditoria.usuario_id == cuenta_id)).rowcount or 0

    if borrar_claves:
        clave_ids = list(db.scalars(select(ClaveApi.id).where(ClaveApi.creada_por_id == cuenta_id)).all())
        if clave_ids:
            db.execute(delete(UsoClaveApi).where(UsoClaveApi.clave_id.in_(clave_ids)))
            claves_eliminadas += db.execute(delete(ClaveApi).where(ClaveApi.id.in_(clave_ids))).rowcount or 0

    if borrar_actividades:
        actividades_eliminadas += db.execute(
            delete(ActividadBitacora).where(ActividadBitacora.actor_id == cuenta_id)
        ).rowcount or 0

    cuenta_eliminada = False
    if datos.eliminar_cuenta:
        db.execute(
            update(Evento).where(Evento.responsable_id == cuenta_id).values(responsable_id=None)
        )
        db.execute(
            update(EventoOrigen)
            .where(EventoOrigen.responsable_id == cuenta_id)
            .values(responsable_id=None, responsable_nombre=None, responsable_correo=None)
        )
        for rol in db.scalars(select(RolPersonalizado).where(RolPersonalizado.creado_por_id == cuenta_id)).all():
            en_uso = db.scalar(
                select(func.count()).select_from(Usuario).where(
                    Usuario.rol_custom_id == rol.id, Usuario.id != cuenta_id
                )
            )
            if en_uso:
                rol.creado_por_id = actor.id
            else:
                db.delete(rol)
        db.flush()
        db.execute(delete(CuentaHistorica).where(CuentaHistorica.id == cuenta_id))
        db.execute(delete(Usuario).where(Usuario.id == cuenta_id))
        cuenta_eliminada = True

    registrar_actividad(
        db,
        actor,
        accion="purga_datos_cuenta",
        entidad="usuario",
        entidad_id=str(cuenta_id),
        titulo=f"{cuenta.nombre} ({cuenta.correo})",
        detalle=(
            f"Eliminación permanente: eventos={eventos_eliminados}, notas={notas_eliminadas}, "
            f"compromisos={compromisos_eliminados}, auditorias={auditorias_eliminadas}, "
            f"claves={claves_eliminadas}, actividades={actividades_eliminadas}, cuenta_eliminada={cuenta_eliminada}"
        ),
    )
    db.commit()

    return PurgaCuentaOut(
        cuenta_id=cuenta_id,
        eventos_eliminados=eventos_eliminados,
        notas_eliminadas=notas_eliminadas,
        compromisos_eliminados=compromisos_eliminados,
        auditorias_eliminadas=auditorias_eliminadas,
        claves_api_eliminadas=claves_eliminadas,
        actividades_eliminadas=actividades_eliminadas,
        cuenta_eliminada=cuenta_eliminada,
    )
