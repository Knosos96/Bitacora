import enum


class Rol(str, enum.Enum):
    jefe = "jefe"
    encargado = "encargado"
    asistente = "asistente"


class Tipo(str, enum.Enum):
    solicitud = "solicitud"
    incidencia = "incidencia"
    tarea = "tarea"
    visita = "visita"
    otro = "otro"


class Estado(str, enum.Enum):
    informativo = "informativo"
    abierto = "abierto"
    en_proceso = "en_proceso"
    en_espera = "en_espera"
    resuelto = "resuelto"
    cerrado = "cerrado"
    cancelado = "cancelado"


class EstadoCompromiso(str, enum.Enum):
    pendiente = "pendiente"
    cumplido = "cumplido"
    cancelado = "cancelado"


class Prioridad(str, enum.Enum):
    baja = "baja"
    media = "media"
    alta = "alta"


# Subtipos iniciales (sección 4 del diseño). Se validan al crear el evento.
SUBTIPOS: dict[Tipo, set[str]] = {
    Tipo.solicitud: {"desarrollo", "informacion", "acceso", "soporte"},
    Tipo.incidencia: {"falla", "bloqueo", "degradacion"},
    Tipo.tarea: {"interna", "mantenimiento", "despliegue"},
    Tipo.visita: {"presencial", "remota"},
    Tipo.otro: {"prestamo", "entrega", "aviso"},
}
