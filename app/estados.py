"""Máquina de estados del evento (sección 5 del diseño). Sin acceso a la base: se prueba sola."""
from app.enums import Estado, Rol

ABIERTOS = (Estado.abierto, Estado.en_proceso, Estado.en_espera)  # "stock abierto" (K3)

# Transiciones permitidas, sin contar el atajo de cierre del encargado/jefe.
TRANSICIONES: dict[Estado, set[Estado]] = {
    Estado.informativo: set(),  # solo se sale activando seguimiento
    Estado.abierto: {Estado.en_proceso, Estado.en_espera, Estado.resuelto, Estado.cancelado},
    Estado.en_proceso: {Estado.en_espera, Estado.resuelto, Estado.cancelado},
    Estado.en_espera: {Estado.en_proceso, Estado.resuelto, Estado.cancelado},
    Estado.resuelto: {Estado.en_proceso, Estado.cerrado},
    Estado.cerrado: set(),  # reabrir es CU-10, sprint 6
    Estado.cancelado: set(),
}

# Lo que puede hacer el asistente si es autor o responsable (hasta resuelto).
ASISTENTE_PUEDE = {Estado.en_proceso, Estado.en_espera, Estado.resuelto}

# Cerrar desde estos estados exige nota de cierre (atajo de encargado/jefe).
CIERRE_CON_ATAJO = {Estado.en_proceso, Estado.en_espera}


def es_gestor(rol: Rol) -> bool:
    return rol in (Rol.encargado, Rol.jefe)


def transicion_valida(desde: Estado, hacia: Estado, rol: Rol) -> bool:
    if hacia in TRANSICIONES[desde]:
        return True
    # Atajo: el encargado o el jefe cierran directo desde en_proceso / en_espera (con nota).
    return hacia == Estado.cerrado and desde in CIERRE_CON_ATAJO and es_gestor(rol)
