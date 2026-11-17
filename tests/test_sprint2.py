from datetime import timedelta

import pytest

from app.db import get_db
from app.enums import Rol
from app.models import Seguimiento, Usuario
from app.routers.eventos import hoy_en_zona
from app.security import hashear_clave
from tests.test_sprint1 import cliente, entrar  # noqa: F401


@pytest.fixture()
def equipo(cliente):  # noqa: F811
    """Agrega un encargado a la base de la fixture del sprint 1."""
    from app.main import app

    db = next(app.dependency_overrides[get_db]())
    db.add(Usuario(nombre="Enca", correo="enca@x.com", rol=Rol.encargado, clave_hash=hashear_clave("clave12345")))
    db.commit()
    return cliente


def crear(c, h, **extra):
    datos = {"tipo": "solicitud", "subtipo": "desarrollo", "titulo": "Reporte de ventas",
             "descripcion": "Operaciones pide un reporte.", "requiere_seguimiento": True, **extra}
    r = c.post("/api/v1/eventos", headers=h, json=datos)
    assert r.status_code == 201, r.text
    return r.json()


def manana():
    return (hoy_en_zona() + timedelta(days=1)).isoformat()


def test_criterio_de_listo_sprint2(equipo):
    """Abierta → en proceso, dos notas, un compromiso con fecha y no se cierra con él pendiente."""
    c = equipo
    asis, enca = entrar(c, "asis@x.com"), entrar(c, "enca@x.com")
    ev = crear(c, asis)
    folio = ev["folio"]
    assert ev["estado"] == "abierto"

    r = c.post(f"/api/v1/eventos/{folio}/estado", headers=asis, json={"estado": "en_proceso"})
    assert r.status_code == 200 and r.json()["estado"] == "en_proceso"

    assert c.post(f"/api/v1/eventos/{folio}/seguimientos", headers=asis, json={"nota": "Hablé con Operaciones."}).status_code == 201
    assert c.post(f"/api/v1/eventos/{folio}/seguimientos", headers=asis, json={"nota": "Falta el formato."}).status_code == 201

    r = c.post(f"/api/v1/eventos/{folio}/compromisos", headers=asis,
               json={"descripcion": "Entregar el reporte", "fecha_limite": manana()})
    assert r.status_code == 201 and r.json()["estado"] == "pendiente" and r.json()["vencido"] is False
    compromiso_id = r.json()["id"]

    c.post(f"/api/v1/eventos/{folio}/estado", headers=asis, json={"estado": "resuelto"})

    # Cerrar con el compromiso pendiente se rechaza, con código estable.
    r = c.post(f"/api/v1/eventos/{folio}/estado", headers=enca, json={"estado": "cerrado"})
    assert r.status_code == 409 and r.json()["detail"]["codigo"] == "compromisos_pendientes"

    # Cumplido el compromiso, cierra.
    assert c.patch(f"/api/v1/compromisos/{compromiso_id}", headers=asis, json={"estado": "cumplido"}).status_code == 200
    r = c.post(f"/api/v1/eventos/{folio}/estado", headers=enca, json={"estado": "cerrado"})
    assert r.status_code == 200 and r.json()["estado"] == "cerrado" and r.json()["cerrado_en"]

    det = c.get(f"/api/v1/eventos/{folio}?incluir=seguimientos,compromisos", headers=asis).json()
    assert len(det["compromisos"]) == 1
    textos = [n["nota"] for n in det["seguimientos"]]
    assert "Hablé con Operaciones." in textos and "Falta el formato." in textos
    assert any("abierto → en_proceso" in t for t in textos)  # nota automática del cambio de estado


def test_cerrar_resolviendo_los_compromisos(equipo):
    c = equipo
    asis, enca = entrar(c, "asis@x.com"), entrar(c, "enca@x.com")
    folio = crear(c, asis)["folio"]
    c.post(f"/api/v1/eventos/{folio}/compromisos", headers=asis, json={"descripcion": "x", "fecha_limite": manana()})
    c.post(f"/api/v1/eventos/{folio}/estado", headers=asis, json={"estado": "resuelto"})
    r = c.post(f"/api/v1/eventos/{folio}/estado", headers=enca, json={"estado": "cerrado", "resolver_compromisos": "cumplir"})
    assert r.status_code == 200
    comp = c.get(f"/api/v1/eventos/{folio}/compromisos", headers=enca).json()
    assert comp[0]["estado"] == "cumplido" and comp[0]["cumplido_en"]


def test_activar_y_quitar_seguimiento(equipo):
    c = equipo
    asis, enca = entrar(c, "asis@x.com"), entrar(c, "enca@x.com")
    ev = crear(c, asis, requiere_seguimiento=False)
    assert ev["estado"] == "informativo"
    folio = ev["folio"]

    r = c.patch(f"/api/v1/eventos/{folio}", headers=asis, json={"requiere_seguimiento": True})
    assert r.status_code == 200 and r.json()["estado"] == "abierto" and r.json()["responsable"]["nombre"] == "Asis"

    # El asistente no puede quitarlo; el encargado sí, si no hay compromisos pendientes.
    assert c.patch(f"/api/v1/eventos/{folio}", headers=asis, json={"requiere_seguimiento": False}).status_code == 409
    c.post(f"/api/v1/eventos/{folio}/compromisos", headers=asis, json={"descripcion": "x", "fecha_limite": manana()})
    r = c.patch(f"/api/v1/eventos/{folio}", headers=enca, json={"requiere_seguimiento": False})
    assert r.status_code == 409 and r.json()["detail"]["codigo"] == "compromisos_pendientes"


def test_estado_sin_seguimiento_y_transicion_invalida(equipo):
    c = equipo
    asis = entrar(c, "asis@x.com")
    info = crear(c, asis, requiere_seguimiento=False)
    r = c.post(f"/api/v1/eventos/{info['folio']}/estado", headers=asis, json={"estado": "en_proceso"})
    assert r.status_code == 409 and r.json()["detail"]["codigo"] == "sin_seguimiento"

    ev = crear(c, asis)
    r = c.post(f"/api/v1/eventos/{ev['folio']}/estado", headers=asis, json={"estado": "cerrado"})
    assert r.status_code == 409 and r.json()["detail"]["codigo"] in ("transicion_invalida", "sin_permiso")


def test_en_espera_exige_nota(equipo):
    c = equipo
    asis = entrar(c, "asis@x.com")
    folio = crear(c, asis)["folio"]
    assert c.post(f"/api/v1/eventos/{folio}/estado", headers=asis, json={"estado": "en_espera"}).status_code == 422
    r = c.post(f"/api/v1/eventos/{folio}/estado", headers=asis,
               json={"estado": "en_espera", "nota": "Esperando al proveedor."})
    assert r.status_code == 200 and r.json()["estado"] == "en_espera"


def test_asistente_no_cancela_ni_cierra_ajenos(equipo):
    c = equipo
    jefe, asis = entrar(c, "jefe@x.com"), entrar(c, "asis@x.com")
    folio = crear(c, jefe)["folio"]  # autor y responsable: la jefa
    r = c.post(f"/api/v1/eventos/{folio}/estado", headers=asis, json={"estado": "en_proceso"})
    assert r.status_code == 409 and r.json()["detail"]["codigo"] == "sin_permiso"


def test_cierre_con_atajo_exige_nota(equipo):
    c = equipo
    asis, enca = entrar(c, "asis@x.com"), entrar(c, "enca@x.com")
    folio = crear(c, asis)["folio"]
    c.post(f"/api/v1/eventos/{folio}/estado", headers=asis, json={"estado": "en_proceso"})
    assert c.post(f"/api/v1/eventos/{folio}/estado", headers=enca, json={"estado": "cerrado"}).status_code == 422
    r = c.post(f"/api/v1/eventos/{folio}/estado", headers=enca, json={"estado": "cerrado", "nota": "Ya no aplica."})
    assert r.status_code == 200


def test_compromiso_requiere_seguimiento_y_fecha_futura(equipo):
    c = equipo
    asis = entrar(c, "asis@x.com")
    info = crear(c, asis, requiere_seguimiento=False)
    r = c.post(f"/api/v1/eventos/{info['folio']}/compromisos", headers=asis, json={"descripcion": "x", "fecha_limite": manana()})
    assert r.status_code == 409 and r.json()["detail"]["codigo"] == "sin_seguimiento"
    ev = crear(c, asis)
    ayer = (hoy_en_zona() - timedelta(days=1)).isoformat()
    assert c.post(f"/api/v1/eventos/{ev['folio']}/compromisos", headers=asis, json={"descripcion": "x", "fecha_limite": ayer}).status_code == 400


def test_notas_inmutables(equipo):
    from app.main import app

    c = equipo
    asis = entrar(c, "asis@x.com")
    folio = crear(c, asis)["folio"]
    c.post(f"/api/v1/eventos/{folio}/seguimientos", headers=asis, json={"nota": "Primera"})
    db = next(app.dependency_overrides[get_db]())
    nota = db.query(Seguimiento).first()
    nota.nota = "Cambiada"
    with pytest.raises(ValueError):
        db.commit()
    db.rollback()
    db.delete(db.query(Seguimiento).first())
    with pytest.raises(ValueError):
        db.commit()


def test_pendientes_por_rol(equipo):
    c = equipo
    asis, enca = entrar(c, "asis@x.com"), entrar(c, "enca@x.com")
    mio = crear(c, asis)["folio"]
    ajeno = crear(c, enca, titulo="Del encargado")["folio"]
    crear(c, asis, requiere_seguimiento=False, titulo="Informativo")
    c.post(f"/api/v1/eventos/{mio}/compromisos", headers=asis, json={"descripcion": "a", "fecha_limite": manana()})
    c.post(f"/api/v1/eventos/{ajeno}/compromisos", headers=enca, json={"descripcion": "b", "fecha_limite": manana()})

    p_asis = c.get("/api/v1/pendientes", headers=asis).json()
    assert [e["folio"] for e in p_asis["eventos"]] == [mio]
    assert len(p_asis["compromisos"]) == 1

    p_enca = c.get("/api/v1/pendientes", headers=enca).json()
    assert {e["folio"] for e in p_enca["eventos"]} == {mio, ajeno}  # el informativo no entra
    assert len(p_enca["compromisos"]) == 2
    assert c.get("/api/v1/pendientes?solo_vencidos=true", headers=enca).json()["compromisos"] == []


def test_asignar_responsable_solo_gestores(equipo):
    c = equipo
    asis, enca = entrar(c, "asis@x.com"), entrar(c, "enca@x.com")
    folio = crear(c, asis)["folio"]
    quien = c.get("/api/v1/usuarios", headers=enca).json()
    id_enca = next(u["id"] for u in quien if u["correo"] == "enca@x.com")
    assert c.patch(f"/api/v1/eventos/{folio}", headers=asis, json={"responsable_id": id_enca}).status_code == 409
    r = c.patch(f"/api/v1/eventos/{folio}", headers=enca, json={"responsable_id": id_enca, "prioridad": "alta"})
    assert r.status_code == 200 and r.json()["responsable"]["nombre"] == "Enca" and r.json()["prioridad"] == "alta"
