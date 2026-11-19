import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.enums import Rol
from app.main import app
from app.models import Area, Usuario
from app.security import hashear_clave


@pytest.fixture()
def cliente():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Sesion = sessionmaker(bind=engine, expire_on_commit=False)

    def _db():
        db = Sesion()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    with Sesion() as db:
        db.add_all(
            [
                Usuario(nombre="Jefa", correo="jefe@x.com", rol=Rol.jefe, clave_hash=hashear_clave("clave12345")),
                Usuario(nombre="Asis", correo="asis@x.com", rol=Rol.asistente, clave_hash=hashear_clave("clave12345")),
                Area(nombre="Contabilidad"),
            ]
        )
        db.commit()
    yield TestClient(app)
    app.dependency_overrides.clear()


def entrar(c, correo):
    r = c.post("/api/v1/auth/login", json={"correo": correo, "clave": "clave12345"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_login_incorrecto(cliente):
    r = cliente.post("/api/v1/auth/login", json={"correo": "jefe@x.com", "clave": "mala"})
    assert r.status_code == 401


def test_sin_token(cliente):
    assert cliente.get("/api/v1/eventos").status_code == 401


def test_criterio_de_listo_sprint1(cliente):
    h = entrar(cliente, "asis@x.com")
    area = cliente.get("/api/v1/areas", headers=h).json()[0]["id"]

    solicitud = cliente.post("/api/v1/eventos", headers=h, json={
        "tipo": "solicitud", "subtipo": "informacion",
        "titulo": "Inventario de licencias", "descripcion": "Contabilidad pide el listado.",
        "area_id": area, "solicitante_nombre": "Ana Pérez", "requiere_seguimiento": True})
    visita = cliente.post("/api/v1/eventos", headers=h, json={
        "tipo": "visita", "titulo": "Visita del jefe de operaciones", "descripcion": "Revisó el área."})
    prestamo = cliente.post("/api/v1/eventos", headers=h, json={
        "tipo": "otro", "subtipo": "prestamo",
        "titulo": "Préstamo de multímetro", "descripcion": "Juan Díaz retiró el Fluke."})

    assert [r.status_code for r in (solicitud, visita, prestamo)] == [201, 201, 201]
    assert solicitud.json()["estado"] == "abierto"
    assert solicitud.json()["responsable"]["nombre"] == "Asis"
    assert visita.json()["estado"] == "informativo"
    assert prestamo.json()["estado"] == "informativo"
    assert prestamo.json()["prioridad"] is None

    folios = {r.json()["folio"] for r in (solicitud, visita, prestamo)}
    assert len(folios) == 3 and all(f.startswith("BIT-") and len(f) == 14 for f in folios)

    hoy = cliente.get("/api/v1/eventos", headers=h).json()
    assert hoy["meta"]["total"] == 3

    solo_visitas = cliente.get("/api/v1/eventos?tipo=visita", headers=h).json()
    assert solo_visitas["meta"]["total"] == 1

    por_folio = cliente.get(f"/api/v1/eventos/{solicitud.json()['folio']}", headers=h)
    por_uuid = cliente.get(f"/api/v1/eventos/{solicitud.json()['id']}", headers=h)
    assert por_folio.json()["id"] == por_uuid.json()["id"]


def test_subtipo_invalido(cliente):
    h = entrar(cliente, "asis@x.com")
    r = cliente.post("/api/v1/eventos", headers=h, json={
        "tipo": "visita", "subtipo": "prestamo", "titulo": "x", "descripcion": "y"})
    assert r.status_code == 422


def test_asistente_no_crea_usuarios_ni_areas(cliente):
    h = entrar(cliente, "asis@x.com")
    assert cliente.post("/api/v1/areas", headers=h, json={"nombre": "Nueva"}).status_code == 409
    assert cliente.post("/api/v1/usuarios", headers=h, json={
        "nombre": "N", "correo": "n@x.com", "clave": "clave12345", "rol": "asistente"}).status_code == 409


def test_jefe_crea_usuario(cliente):
    h = entrar(cliente, "jefe@x.com")
    r = cliente.post("/api/v1/usuarios", headers=h, json={
        "nombre": "Nuevo", "correo": "Nuevo@x.com", "clave": "clave12345", "rol": "encargado"})
    assert r.status_code == 201 and r.json()["correo"] == "nuevo@x.com"


def test_fecha_futura_rechazada(cliente):
    h = entrar(cliente, "asis@x.com")
    r = cliente.post("/api/v1/eventos", headers=h, json={
        "tipo": "otro", "titulo": "x", "descripcion": "y", "fecha_hecho": "2999-01-01"})
    assert r.status_code == 400
