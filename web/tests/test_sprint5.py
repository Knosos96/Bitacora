from datetime import timedelta

from app.db import get_db
from app.models import UsoClaveApi
from app.services.eventos import hoy_en_zona
from tests.test_sprint1 import cliente, entrar  # noqa: F401
from tests.test_sprint2 import crear, equipo  # noqa: F401

CAMPOS_10_1 = {"id", "folio", "tipo", "subtipo", "titulo", "descripcion", "referencia", "fecha_hecho", "estado",
               "requiere_seguimiento", "prioridad", "area_origen", "solicitante", "autor", "responsable",
               "creado_en", "cerrado_en"}


def hoy():
    return str(hoy_en_zona())


def emitir(c, nombre="integración"):
    jefe = entrar(c, "jefe@x.com")
    r = c.post("/api/v1/claves-api", headers=jefe, json={"nombre": nombre})
    assert r.status_code == 201, r.text
    return r.json(), jefe


def test_solo_el_jefe_emite_y_la_clave_se_ve_una_vez(equipo):
    c = equipo
    assert c.post("/api/v1/claves-api", headers=entrar(c, "enca@x.com"), json={"nombre": "x"}).status_code == 409
    assert c.post("/api/v1/claves-api", headers=entrar(c, "asis@x.com"), json={"nombre": "x"}).status_code == 409
    creada, jefe = emitir(c)
    assert creada["clave"].startswith("bti_") and len(creada["clave"]) > 30
    lista = c.get("/api/v1/claves-api", headers=jefe).json()
    assert len(lista) == 1 and "clave" not in lista[0] and "hash" not in lista[0]
    assert lista[0]["prefijo"] == creada["clave"][:8]


def test_consulta_con_clave_y_sin_clave(equipo):
    c = equipo
    asis = entrar(c, "asis@x.com")
    crear(c, asis, titulo="Una solicitud")
    crear(c, asis, tipo="visita", subtipo=None, requiere_seguimiento=False, titulo="Visita")
    clave = emitir(c)[0]["clave"]
    k = {"X-API-Key": clave}

    r = c.get("/api/v1/eventos", headers=k, params={"desde": hoy(), "hasta": hoy(), "tipo": "solicitud"})
    assert r.status_code == 200
    assert [e["titulo"] for e in r.json()["data"]] == ["Una solicitud"]
    assert CAMPOS_10_1 <= set(r.json()["data"][0])
    assert r.json()["meta"] == {"page": 1, "page_size": 50, "total": 1}

    # Sin tipo equivale a todos; sin resultados es 200 con lista vacía.
    assert c.get("/api/v1/eventos", headers=k, params={"desde": hoy(), "hasta": hoy()}).json()["meta"]["total"] == 2
    ayer = str(hoy_en_zona() - timedelta(days=30))
    vacio = c.get("/api/v1/eventos", headers=k, params={"desde": ayer, "hasta": ayer})
    assert vacio.status_code == 200 and vacio.json()["data"] == []

    # Ni clave ni sesión: 401.
    assert c.get("/api/v1/eventos", params={"desde": hoy(), "hasta": hoy()}).status_code == 401
    assert c.get("/api/v1/eventos", headers={"X-API-Key": "bti_inventada"}, params={"desde": hoy(), "hasta": hoy()}).status_code == 401


def test_errores_de_rango_con_clave(equipo):
    c = equipo
    k = {"X-API-Key": emitir(c)[0]["clave"]}
    base = "/api/v1/eventos"
    assert c.get(base, headers=k).status_code == 400  # sin desde/hasta
    assert c.get(base, headers=k, params={"desde": hoy()}).status_code == 400
    assert c.get(base, headers=k, params={"desde": "2026-02-01", "hasta": "2026-01-01"}).status_code == 400
    assert c.get(base, headers=k, params={"desde": "2025-01-01", "hasta": "2026-06-01"}).status_code == 400  # > 366 días
    # Incluso buscando por texto, el tope se respeta.
    assert c.get(base, headers=k, params={"desde": "2024-01-01", "hasta": "2026-06-01", "q": "algo"}).status_code == 400
    # Filtros internos no disponibles para clave.
    assert c.get(base, headers=k, params={"desde": hoy(), "hasta": hoy(), "vencidos": True}).status_code == 400


def test_ficha_y_resumen_por_api(equipo):
    c = equipo
    asis = entrar(c, "asis@x.com")
    e = crear(c, asis)
    c.post(f"/api/v1/eventos/{e['folio']}/seguimientos", headers=asis, json={"nota": "Una nota"})
    k = {"X-API-Key": emitir(c)[0]["clave"]}

    ficha = c.get(f"/api/v1/eventos/{e['folio']}", headers=k)
    assert ficha.status_code == 200 and ficha.json()["folio"] == e["folio"]
    por_uuid = c.get(f"/api/v1/eventos/{e['id']}", headers=k, params={"incluir": "seguimientos,compromisos"}).json()
    assert [n["nota"] for n in por_uuid["seguimientos"]] == ["Una nota"] and por_uuid["compromisos"] == []
    assert c.get(f"/api/v1/eventos/{e['folio']}", headers=k, params={"incluir": "auditoria"}).status_code == 400
    assert c.get("/api/v1/eventos/BIT-2026-99999", headers=k).status_code == 404

    r = c.get("/api/v1/eventos/resumen", headers=k, params={"desde": hoy(), "hasta": hoy()}).json()
    assert r["total"] == 1 and r["por_tipo"] == {"solicitud": 1, "incidencia": 0, "tarea": 0, "visita": 0, "otro": 0}
    solo = c.get("/api/v1/eventos/resumen", headers=k, params={"desde": hoy(), "hasta": hoy(), "tipo": "visita"}).json()
    assert solo["total"] == 0


def test_la_clave_no_puede_escribir_ni_ver_lo_interno(equipo):
    c = equipo
    k = {"X-API-Key": emitir(c)[0]["clave"]}
    nuevo = {"tipo": "otro", "titulo": "x", "descripcion": "y"}
    assert c.post("/api/v1/eventos", headers=k, json=nuevo).status_code == 401
    assert c.get("/api/v1/kpi", headers=k).status_code == 401
    assert c.get("/api/v1/pendientes", headers=k).status_code == 401
    assert c.get("/api/v1/usuarios", headers=k).status_code == 401
    assert c.get("/api/v1/claves-api", headers=k).status_code == 401
    assert c.get("/api/v1/eventos/exportar", headers=k).status_code == 401


def test_revocar_corta_el_acceso_y_el_uso_queda_registrado(equipo):
    from app.main import app

    c = equipo
    creada, jefe = emitir(c)
    k = {"X-API-Key": creada["clave"]}
    for _ in range(2):
        assert c.get("/api/v1/eventos", headers=k, params={"desde": hoy(), "hasta": hoy()}).status_code == 200

    r = c.delete(f"/api/v1/claves-api/{creada['id']}", headers=jefe)
    assert r.status_code == 200 and r.json()["revocada_en"] and r.json()["usos"] == 2 and r.json()["ultimo_uso"]
    assert c.get("/api/v1/eventos", headers=k, params={"desde": hoy(), "hasta": hoy()}).status_code == 401

    db = next(app.dependency_overrides[get_db]())
    usos = db.query(UsoClaveApi).all()
    assert len(usos) == 2 and all(u.ruta == "/api/v1/eventos" and u.metodo == "GET" for u in usos)
    assert not hasattr(UsoClaveApi, "cuerpo")  # no se guarda el cuerpo


def test_contrato_openapi(equipo):
    """El contrato de la sección 10.5: la especificación publicada y la respuesta real coinciden."""
    c = equipo
    spec = c.get("/api/v1/openapi.json").json()
    rutas = spec["paths"]
    for ruta in ("/api/v1/eventos", "/api/v1/eventos/{folio}", "/api/v1/eventos/resumen"):
        assert "get" in rutas[ruta]
    params = {p["name"] for p in rutas["/api/v1/eventos"]["get"]["parameters"]}
    assert {"desde", "hasta", "tipo", "estado", "q", "area_id", "page", "page_size"} <= params
    assert {"incluir"} <= {p["name"] for p in rutas["/api/v1/eventos/{folio}"]["get"]["parameters"]}

    esquema = spec["components"]["schemas"]["EventoOut"]["properties"]
    assert CAMPOS_10_1 <= set(esquema)
    assert set(spec["components"]["schemas"]["Tipo"]["enum"]) == {"solicitud", "incidencia", "tarea", "visita", "otro"}

    asis = entrar(c, "asis@x.com")
    crear(c, asis)
    k = {"X-API-Key": emitir(c)[0]["clave"]}
    dato = c.get("/api/v1/eventos", headers=k, params={"desde": hoy(), "hasta": hoy()}).json()["data"][0]
    assert CAMPOS_10_1 <= set(dato)
