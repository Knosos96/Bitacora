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
