"""Prueba el cliente del escritorio contra la API real, sin abrir ventanas."""
import pytest
from starlette.testclient import TestClient

from app.main import app
from desktop.api_client import ClienteApi, ErrorApi
from tests.test_sprint1 import cliente  # noqa: F401  (reutiliza la fixture de la base)


def test_flujo_cliente(cliente):  # noqa: F811
    api = ClienteApi("", http=TestClient(app, base_url="http://test/api/v1"))

    with pytest.raises(ErrorApi):
        api.login("asis@x.com", "mala")
    assert api.login("asis@x.com", "clave12345")["rol"] == "asistente"

    e = api.crear_evento({"tipo": "otro", "subtipo": "prestamo", "titulo": "Préstamo", "descripcion": "Fluke"})
    assert e["folio"].startswith("BIT-")
    assert api.eventos()["meta"]["total"] == 1
    assert api.evento(e["folio"])["titulo"] == "Préstamo"
    assert api.areas()[0]["nombre"] == "Contabilidad"
    with pytest.raises(ErrorApi):
        api.crear_evento({"tipo": "visita", "subtipo": "prestamo", "titulo": "x", "descripcion": "y"})


def test_flujo_cliente_sprint2(cliente):  # noqa: F811
    from datetime import timedelta

    from app.routers.eventos import hoy_en_zona

    api = ClienteApi("", http=TestClient(app, base_url="http://test/api/v1"))
    api.login("asis@x.com", "clave12345")
    e = api.crear_evento({"tipo": "solicitud", "titulo": "Reporte", "descripcion": "x", "requiere_seguimiento": True})
    assert api.cambiar_estado(e["folio"], "en_proceso")["estado"] == "en_proceso"
    api.agregar_nota(e["folio"], "Avance")
    c = api.crear_compromiso(e["folio"], "Entregar", (hoy_en_zona() + timedelta(days=1)).isoformat())
    assert api.pendientes()["compromisos"][0]["id"] == c["id"]
    assert api.resolver_compromiso(c["id"], "cumplido")["estado"] == "cumplido"
    det = api.evento_completo(e["folio"])
    assert len(det["seguimientos"]) >= 3 and len(det["compromisos"]) == 1
    with pytest.raises(ErrorApi):
        api.cambiar_estado(e["folio"], "cerrado")  # el asistente no cierra


def test_flujo_cliente_sprints_3_y_4(cliente):  # noqa: F811
    from tests.test_sprint2 import Usuario, Rol, hashear_clave, get_db  # noqa: F401

    db = next(app.dependency_overrides[get_db]())
    db.add(Usuario(nombre="Enca", correo="enca@x.com", rol=Rol.encargado, clave_hash=hashear_clave("clave12345")))
    db.commit()

    api = ClienteApi("", http=TestClient(app, base_url="http://test/api/v1"))
    api.login("asis@x.com", "clave12345")
    e = api.crear_evento({"tipo": "incidencia", "titulo": "Impresora sin tóner", "descripcion": "Piso 2", "requiere_seguimiento": True})
    r = api.buscar(q="impresora toner")
    assert r["meta"]["total"] == 1 and r["data"][0]["fragmento"]
    api.corregir_evento(e["folio"], {"titulo": "Impresora sin tóner (piso 2)"})
    assert len(api.evento_con_auditoria(e["folio"])["auditoria"]) == 1
    with pytest.raises(ErrorApi):
        api.tablero()  # el asistente no ve el tablero

    jefe = ClienteApi("", http=TestClient(app, base_url="http://test/api/v1"))
    jefe.login("enca@x.com", "clave12345")
    t = jefe.tablero()
    assert [i["id"] for i in t["indicadores"]] == [f"K{n}" for n in range(1, 13)]
    assert jefe.lista_kpi("K8")["texto_vacio"] == "No hay compromisos vencidos"
