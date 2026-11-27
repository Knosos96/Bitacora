"""Esquemas Pydantic para el portal documental del Superusuario."""
import uuid
from datetime import date, datetime

from pydantic import BaseModel


class SuperResumenOut(BaseModel):
    cuentas_total: int
    cuentas_activas: int
    cuentas_inactivas: int
    cuentas_eliminadas: int
    eventos_total: int
    incidencias_total: int
    pendientes_eventos: int
    pendientes_compromisos: int
    compromisos_vencidos: int
    actividades_total: int
    archivos_total: int


class CuentaHistoricaOut(BaseModel):
    id: uuid.UUID
    nombre: str
    correo: str
    rol: str
    rol_custom_nombre: str | None
    estado: str
    creado_en: datetime
    actualizado_en: datetime
    eliminado_en: datetime | None
    eliminado_por_nombre: str | None
    eliminado_por_correo: str | None
    eventos_creados: int = 0
    incidencias_creadas: int = 0
    pendientes_abiertos: int = 0
    actividades_count: int = 0


class RegistroHistoricoOut(BaseModel):
    id: uuid.UUID
    folio: str
    tipo: str
    subtipo: str | None
    titulo: str
    descripcion: str
    referencia: str | None
    fecha_hecho: date
    estado: str
    prioridad: str | None
    requiere_seguimiento: bool
    area_nombre: str | None
    solicitante: str | None
    autor_original_id: uuid.UUID
    autor_original_nombre: str
    autor_original_correo: str
    autor_original_estado: str
    responsable_original_id: uuid.UUID | None
    responsable_original_nombre: str | None
    responsable_original_estado: str | None
    creado_en: datetime
    cerrado_en: datetime | None
    notas_count: int = 0
    compromisos_count: int = 0


class ActividadOut(BaseModel):
    id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_nombre: str
    actor_correo: str
    actor_rol: str
    accion: str
    entidad: str
    entidad_id: str | None
    folio: str | None
    titulo: str | None
    detalle: str
    creado_en: datetime


class PendienteHistoricoCompOut(BaseModel):
    id: uuid.UUID
    evento_folio: str
    evento_titulo: str
    evento_tipo: str
    descripcion: str
    responsable_nombre: str
    responsable_estado: str = "activa"
    fecha_limite: date
    vencido: bool


class SuperPendientesOut(BaseModel):
    eventos: list[RegistroHistoricoOut]
    compromisos: list[PendienteHistoricoCompOut]


class RespaldoArchivoOut(BaseModel):
    nombre: str
    tamano_bytes: int
    modificado_en: datetime


class ReferenciaArchivoOut(BaseModel):
    folio: str
    titulo: str
    tipo: str
    fecha_hecho: date
    referencia: str
    autor_nombre: str
    autor_estado: str


class SuperArchivosOut(BaseModel):
    exportaciones: list[ActividadOut]
    respaldos: list[RespaldoArchivoOut]
    referencias: list[ReferenciaArchivoOut]


class ExpedienteCuentaOut(BaseModel):
    cuenta: CuentaHistoricaOut
    registros: list[RegistroHistoricoOut]
    incidencias: list[RegistroHistoricoOut]
    pendientes: SuperPendientesOut
    actividades: list[ActividadOut]
    exportaciones: list[ActividadOut]


class SeguimientoDocOut(BaseModel):
    id: uuid.UUID
    autor_id: uuid.UUID
    autor_nombre: str
    autor_correo: str
    autor_estado: str
    nota: str
    estado_anterior: str | None
    estado_nuevo: str | None
    creado_en: datetime


class CompromisoDocOut(BaseModel):
    id: uuid.UUID
    descripcion: str
    responsable_id: uuid.UUID
    responsable_nombre: str
    responsable_correo: str
    responsable_estado: str
    fecha_limite: date
    estado: str
    vencido: bool = False
    cumplido_en: datetime | None
    creado_en: datetime


class AuditoriaDocOut(BaseModel):
    id: uuid.UUID
    campo: str
    valor_anterior: str | None
    valor_nuevo: str | None
    usuario_id: uuid.UUID
    usuario_nombre: str
    usuario_correo: str
    usuario_estado: str
    creado_en: datetime


class RegistroDetalleOut(BaseModel):
    registro: RegistroHistoricoOut
    notas: list[SeguimientoDocOut]
    compromisos: list[CompromisoDocOut]
    auditoria: list[AuditoriaDocOut]


class PurgaResumenCuentaOut(BaseModel):
    cuenta_id: uuid.UUID
    nombre: str
    correo: str
    rol: str
    estado: str
    eventos_creados: int
    eventos_asignados: int
    notas_en_otros_eventos: int
    compromisos_en_otros_eventos: int
    auditorias_en_otros_eventos: int
    claves_api: int
    roles_creados: int
    actividades: int
    es_protegida: bool


class PurgaCuentaIn(BaseModel):
    eliminar_eventos_creados: bool = False
    eliminar_notas: bool = False
    eliminar_compromisos: bool = False
    eliminar_auditorias: bool = False
    eliminar_claves_api: bool = False
    eliminar_actividades: bool = False
    eliminar_cuenta: bool = False


class PurgaCuentaOut(BaseModel):
    cuenta_id: uuid.UUID
    eventos_eliminados: int = 0
    notas_eliminadas: int = 0
    compromisos_eliminados: int = 0
    auditorias_eliminadas: int = 0
    claves_api_eliminadas: int = 0
    actividades_eliminadas: int = 0
    cuenta_eliminada: bool = False
