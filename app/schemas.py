import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.enums import SUBTIPOS, Estado, Prioridad, Rol, Tipo


class LoginIn(BaseModel):
    correo: EmailStr
    clave: str


class UsuarioIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    correo: EmailStr
    clave: str = Field(min_length=8)
    rol: Rol


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    correo: str
    rol: Rol
    activo: bool


class TokenOut(BaseModel):
    token: str
    tipo: str = "bearer"
    usuario: UsuarioOut


class UsuarioRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str


class AreaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)


class AreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    activa: bool


class AreaRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str


class EventoIn(BaseModel):
    tipo: Tipo
    subtipo: str | None = None
    titulo: str = Field(min_length=1, max_length=200)
    descripcion: str = Field(min_length=1)
    referencia: str | None = None
    fecha_hecho: date | None = None  # si falta: hoy en la zona del área
    area_id: uuid.UUID | None = None
    solicitante_nombre: str | None = None
    requiere_seguimiento: bool = False
    prioridad: Prioridad | None = None
    responsable_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validar(self):
        if self.subtipo and self.subtipo not in SUBTIPOS[self.tipo]:
            validos = ", ".join(sorted(SUBTIPOS[self.tipo]))
            raise ValueError(f"subtipo '{self.subtipo}' no válido para {self.tipo.value}. Opciones: {validos}")
        return self


class EventoOut(BaseModel):
    """Contrato de la sección 10.1. No renombrar campos."""

    id: uuid.UUID
    folio: str
    tipo: Tipo
    subtipo: str | None
    titulo: str
    descripcion: str
    referencia: str | None
    fecha_hecho: date
    estado: Estado
    requiere_seguimiento: bool
    prioridad: Prioridad | None
    area_origen: AreaRef | None
    solicitante: str | None
    autor: UsuarioRef
    responsable: UsuarioRef | None
    creado_en: datetime
    cerrado_en: datetime | None


class Meta(BaseModel):
    page: int
    page_size: int
    total: int


class EventosPagina(BaseModel):
    data: list[EventoOut]
    meta: Meta


# ---------------------------------------------------------------- Sprint 2
from app.enums import EstadoCompromiso  # noqa: E402


class EventoPatch(BaseModel):
    """CU-04 y CU-05: activar/quitar seguimiento, responsable y prioridad."""

    requiere_seguimiento: bool | None = None
    responsable_id: uuid.UUID | None = None
    prioridad: Prioridad | None = None
    nota: str | None = Field(default=None, max_length=5000)


class CambioEstadoIn(BaseModel):
    estado: Estado
    nota: str | None = Field(default=None, max_length=5000)
    # Al cerrar con compromisos pendientes: "cumplir" o "cancelar". Sin esto, el cierre se rechaza.
    resolver_compromisos: str | None = Field(default=None, pattern="^(cumplir|cancelar)$")


class SeguimientoIn(BaseModel):
    nota: str = Field(min_length=1, max_length=5000)


class SeguimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    autor: UsuarioRef
    nota: str
    estado_anterior: Estado | None
    estado_nuevo: Estado | None
    creado_en: datetime


class CompromisoIn(BaseModel):
    descripcion: str = Field(min_length=1, max_length=2000)
    fecha_limite: date
    responsable_id: uuid.UUID | None = None  # por defecto, quien lo registra


class CompromisoPatch(BaseModel):
    estado: EstadoCompromiso


class CompromisoOut(BaseModel):
    id: uuid.UUID
    evento_folio: str
    descripcion: str
    responsable: UsuarioRef
    fecha_limite: date
    estado: EstadoCompromiso
    vencido: bool  # calculado: pendiente y con fecha límite anterior a hoy
    cumplido_en: datetime | None
    creado_en: datetime


class CompromisoPendienteOut(CompromisoOut):
    evento_titulo: str
    evento_tipo: Tipo


class EventoDetalleOut(EventoOut):
    # Solo se llenan si se pide ?incluir=seguimientos,compromisos
    seguimientos: list[SeguimientoOut] | None = None
    compromisos: list[CompromisoOut] | None = None


class PendientesOut(BaseModel):
    eventos: list[EventoOut]
    compromisos: list[CompromisoPendienteOut]
