"""La máquina de estados no toca la base: se prueba sola."""
from app.core.enums import Estado, Rol
from app.services.estados import transicion_valida


def test_avance_normal():
    assert transicion_valida(Estado.abierto, Estado.en_proceso, Rol.asistente)
    assert transicion_valida(Estado.en_proceso, Estado.resuelto, Rol.asistente)
    assert transicion_valida(Estado.resuelto, Estado.cerrado, Rol.encargado)


def test_informativo_no_avanza_solo():
    assert not transicion_valida(Estado.informativo, Estado.en_proceso, Rol.jefe)


def test_atajo_de_cierre_solo_gestores():
    assert transicion_valida(Estado.en_proceso, Estado.cerrado, Rol.encargado)
    assert transicion_valida(Estado.en_espera, Estado.cerrado, Rol.jefe)
    assert not transicion_valida(Estado.en_proceso, Estado.cerrado, Rol.asistente)
    assert not transicion_valida(Estado.abierto, Estado.cerrado, Rol.jefe)


def test_cancelado_es_final_y_cerrado_solo_se_reabre():
    for hacia in Estado:
        assert not transicion_valida(Estado.cancelado, hacia, Rol.jefe)
    # Cerrado: lo único posible es reabrir a abierto, y solo para encargado o jefe.
    for hacia in Estado:
        esperado = hacia == Estado.abierto
        assert transicion_valida(Estado.cerrado, hacia, Rol.encargado) == esperado
        assert transicion_valida(Estado.cerrado, hacia, Rol.jefe) == esperado
        assert not transicion_valida(Estado.cerrado, hacia, Rol.asistente)
