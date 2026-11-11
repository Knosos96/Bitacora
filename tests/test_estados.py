"""La máquina de estados no toca la base: se prueba sola."""
from app.enums import Estado, Rol
from app.estados import transicion_valida


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


def test_cerrado_y_cancelado_son_finales():
    for desde in (Estado.cerrado, Estado.cancelado):
        for hacia in Estado:
            assert not transicion_valida(desde, hacia, Rol.jefe)
