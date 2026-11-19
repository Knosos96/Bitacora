import enum


class Rol(str, enum.Enum):
    jefe = "jefe"
    encargado = "encargado"
    asistente = "asistente"


class Permiso(str, enum.Enum):
    """Permisos granulares para roles personalizados."""
    # Usuarios
    ver_usuarios = "ver_usuarios"
    crear_usuarios = "crear_usuarios"
    editar_usuarios = "editar_usuarios"
    # Roles personalizados
    gestionar_roles = "gestionar_roles"
    # KPI / tablero
    ver_kpi = "ver_kpi"
    # Eventos
    crear_eventos = "crear_eventos"
    editar_cabecera = "editar_cabecera"       # corregir título, descripción, etc.
    cambiar_estado = "cambiar_estado"          # avanzar hasta resuelto
    cancelar_cerrar = "cancelar_cerrar"        # cancelar o cerrar eventos
    reabrir_eventos = "reabrir_eventos"        # reabrir cerrados/cancelados
    # Compromisos
    gestionar_compromisos = "gestionar_compromisos"
    # Áreas
    gestionar_areas = "gestionar_areas"
    # Subtipos
    gestionar_subtipos = "gestionar_subtipos"
    # Claves API
    gestionar_claves_api = "gestionar_claves_api"
    # Exportar
    exportar_csv = "exportar_csv"


# Permisos que tiene cada rol base por defecto
PERMISOS_BASE: dict[Rol, set[Permiso]] = {
    Rol.jefe: set(Permiso),  # todo
    Rol.encargado: {
        Permiso.ver_usuarios,
        Permiso.ver_kpi,
        Permiso.crear_eventos,
        Permiso.editar_cabecera,
        Permiso.cambiar_estado,
        Permiso.cancelar_cerrar,
        Permiso.reabrir_eventos,
        Permiso.gestionar_compromisos,
        Permiso.gestionar_areas,
        Permiso.gestionar_subtipos,
        Permiso.exportar_csv,
    },
    Rol.asistente: {
        Permiso.crear_eventos,
        Permiso.cambiar_estado,
        Permiso.gestionar_compromisos,
        Permiso.exportar_csv,
    },
}


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
