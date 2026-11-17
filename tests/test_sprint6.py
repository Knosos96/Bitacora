import csv
import io

from tests.test_sprint1 import cliente, entrar  # noqa: F401
from tests.test_sprint2 import crear, equipo, manana  # noqa: F401


def cerrar(c, asis, enca, folio):
    c.post(f"/api/v1/eventos/{folio}/estado", headers=asis, json={"estado": "resuelto"})
    r = c.post(f"/api/v1/eventos/{folio}/estado", headers=enca, json={"estado": "cerrado"})
    assert r.status_code == 200 and r.json()["cerrado_en"]


# ---------------------------------------------------------------- CU-10 reabrir
def test_reabrir_solo_gestores_con_motivo(equipo):
    c = equipo
    asis, enca = entrar(c, "asis@x.com"), entrar(c, "enca@x.com")
    folio = crear(c, asis)["folio"]
    cerrar(c, asis, enca, folio)

    r = c.post(f"/api/v1/eventos/{folio}/estado", headers=asis, json={"estado": "abierto", "nota": "Volvió a fallar"})
    assert r.status_code == 409 and r.json()["detail"]["codigo"] == "sin_permiso"
    assert c.post(f"/api/v1/eventos/{folio}/estado", headers=enca, json={"estado": "abierto"}).status_code == 422  # sin motivo

    r = c.post(f"/api/v1/eventos/{folio}/estado", headers=enca, json={"estado": "abierto", "nota": "Volvió a fallar"})
    assert r.status_code == 200 and r.json()["estado"] == "abierto" and r.json()["cerrado_en"] is None
    # Vuelve al stock abierto y se puede cerrar otra vez.
    assert c.get("/api/v1/kpi", headers=enca).json()["indicadores"][2]["valor"] == 1  # K3
    cerrar(c, asis, enca, folio)


def test_cancelado_no_se_reabre_y_cerrado_no_va_a_otros_estados(equipo):
    c = equipo
    asis, enca = entrar(c, "asis@x.com"), entrar(c, "enca@x.com")
    f1, f2 = crear(c, asis)["folio"], crear(c, asis)["folio"]
    assert c.post(f"/api/v1/eventos/{f1}/estado", headers=enca, json={"estado": "cancelado"}).status_code == 200
    r = c.post(f"/api/v1/eventos/{f1}/estado", headers=enca, json={"estado": "abierto", "nota": "x"})
    assert r.status_code == 409 and r.json()["detail"]["codigo"] == "evento_cerrado"
    cerrar(c, asis, enca, f2)
    r = c.post(f"/api/v1/eventos/{f2}/estado", headers=enca, json={"estado": "en_proceso", "nota": "x"})
    assert r.status_code == 409 and r.json()["detail"]["codigo"] == "evento_cerrado"


def test_nota_en_cerrado_solo_gestores_y_no_reabre(equipo):
    c = equipo
    asis, enca = entrar(c, "asis@x.com"), entrar(c, "enca@x.com")
    folio = crear(c, asis)["folio"]
    cerrar(c, asis, enca, folio)
    assert c.post(f"/api/v1/eventos/{folio}/seguimientos", headers=asis, json={"nota": "x"}).status_code == 409
    assert c.post(f"/api/v1/eventos/{folio}/seguimientos", headers=enca, json={"nota": "Aclaración"}).status_code == 201
    assert c.get(f"/api/v1/eventos/{folio}", headers=enca).json()["estado"] == "cerrado"


# ---------------------------------------------------------------- CU-22 exportar
def leer_csv(respuesta):
    texto = respuesta.content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(texto)))


def test_exportar_csv_con_filtros_y_acentos(equipo):
    c = equipo
    asis, enca = entrar(c, "asis@x.com"), entrar(c, "enca@x.com")
    crear(c, asis, titulo="Préstamo de cámara", descripcion="Se prestó, con coma y \"comillas\".")
    crear(c, asis, tipo="visita", subtipo=None, requiere_seguimiento=False, titulo="Visita")

    r = c.get("/api/v1/eventos/exportar", headers=enca)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"] and r.headers["content-disposition"].endswith('.csv"')
    assert r.content.startswith(b"\xef\xbb\xbf")  # BOM para Excel
    filas = leer_csv(r)
    assert len(filas) == 2 and filas[0]["folio"].startswith("BIT-")
    assert {f["titulo"] for f in filas} == {"Préstamo de cámara", "Visita"}
    prestamo = next(f for f in filas if f["tipo"] == "solicitud")
    assert prestamo["descripcion"] == 'Se prestó, con coma y "comillas".'
    assert prestamo["requiere_seguimiento"] == "sí" and prestamo["autor"] == "Asis"

    solo = leer_csv(c.get("/api/v1/eventos/exportar", headers=enca, params={"tipo": "visita"}))
    assert [f["titulo"] for f in solo] == ["Visita"]
    texto = leer_csv(c.get("/api/v1/eventos/exportar", headers=enca, params={"q": "camara"}))
    assert [f["titulo"] for f in texto] == ["Préstamo de cámara"]


def test_exportar_solo_gestores_y_neutraliza_formulas(equipo):
    c = equipo
    asis, enca = entrar(c, "asis@x.com"), entrar(c, "enca@x.com")
    crear(c, asis, titulo='=HYPERLINK("http://malo")', descripcion="+cmd")
    assert c.get("/api/v1/eventos/exportar", headers=asis).status_code == 409
    fila = leer_csv(c.get("/api/v1/eventos/exportar", headers=enca))[0]
    assert fila["titulo"].startswith("'=") and fila["descripcion"] == "'+cmd"


# ---------------------------------------------------------------- CU-16 usuarios
def uid(c, h, correo):
    return next(u["id"] for u in c.get("/api/v1/usuarios", headers=h).json() if u["correo"] == correo)


def test_jefe_administra_usuarios(equipo):
    c = equipo
    jefe, enca = entrar(c, "jefe@x.com"), entrar(c, "enca@x.com")
    asis_id = uid(c, jefe, "asis@x.com")

    assert c.patch(f"/api/v1/usuarios/{asis_id}", headers=enca, json={"rol": "jefe"}).status_code == 409
    r = c.patch(f"/api/v1/usuarios/{asis_id}", headers=jefe, json={"nombre": "Asistente Uno", "rol": "encargado"})
    assert r.status_code == 200 and r.json()["nombre"] == "Asistente Uno" and r.json()["rol"] == "encargado"

    # Restablecer la clave.
    c.patch(f"/api/v1/usuarios/{asis_id}", headers=jefe, json={"clave": "otraClave123"})
    assert c.post("/api/v1/auth/login", json={"correo": "asis@x.com", "clave": "clave12345"}).status_code == 401
    assert c.post("/api/v1/auth/login", json={"correo": "asis@x.com", "clave": "otraClave123"}).status_code == 200

    # Desactivar: no entra más, pero su nombre queda en el historial.
    folio = crear(c, entrar_con(c, "asis@x.com", "otraClave123"))["folio"]
    assert c.patch(f"/api/v1/usuarios/{asis_id}", headers=jefe, json={"activo": False}).status_code == 200
    assert c.post("/api/v1/auth/login", json={"correo": "asis@x.com", "clave": "otraClave123"}).status_code == 401
    assert c.get(f"/api/v1/eventos/{folio}", headers=jefe).json()["autor"]["nombre"] == "Asistente Uno"
    # Un usuario inactivo no puede ser responsable.
    nuevo = crear(c, jefe, titulo="Otro")["folio"]
    r = c.patch(f"/api/v1/eventos/{nuevo}", headers=jefe, json={"responsable_id": asis_id})
    assert r.status_code == 400


def entrar_con(c, correo, clave):
    r = c.post("/api/v1/auth/login", json={"correo": correo, "clave": clave})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_no_se_queda_sin_jefe(equipo):
    c = equipo
    jefe = entrar(c, "jefe@x.com")
    jefe_id = uid(c, jefe, "jefe@x.com")
    r = c.patch(f"/api/v1/usuarios/{jefe_id}", headers=jefe, json={"activo": False})
    assert r.status_code == 409
    r = c.patch(f"/api/v1/usuarios/{jefe_id}", headers=jefe, json={"rol": "asistente"})
    assert r.status_code == 409 and r.json()["detail"]["codigo"] == "ultimo_jefe"


# ---------------------------------------------------------------- CU-17 áreas y subtipos
def test_areas_se_desactivan_sin_tocar_eventos(equipo):
    c = equipo
    enca, asis = entrar(c, "enca@x.com"), entrar(c, "asis@x.com")
    assert c.post("/api/v1/areas", headers=enca, json={"nombre": "Operaciones"}).status_code in (200, 201)
    area = next(a for a in c.get("/api/v1/areas", headers=asis).json() if a["nombre"] == "Contabilidad")
    ev = crear(c, asis, area_id=area["id"])

    assert c.patch(f"/api/v1/areas/{area['id']}", headers=asis, json={"activa": False}).status_code == 409
    r = c.patch(f"/api/v1/areas/{area['id']}", headers=enca, json={"activa": False})
    assert r.status_code == 200 and r.json()["activa"] is False

    assert area["id"] not in [a["id"] for a in c.get("/api/v1/areas", headers=asis).json()]
    assert area["id"] in [a["id"] for a in c.get("/api/v1/areas?incluir_inactivas=true", headers=enca).json()]
    assert area["id"] not in [a["id"] for a in c.get("/api/v1/areas?incluir_inactivas=true", headers=asis).json()]
    # El evento anterior conserva su área.
    assert c.get(f"/api/v1/eventos/{ev['folio']}", headers=asis).json()["area_origen"]["nombre"] == area["nombre"]
    # Pero no se puede registrar uno nuevo con ella.
    nuevo = {"tipo": "otro", "titulo": "x", "descripcion": "y", "area_id": area["id"]}
    assert c.post("/api/v1/eventos", headers=asis, json=nuevo).status_code == 400
    # Renombrar sin duplicar.
    otra = c.get("/api/v1/areas", headers=asis).json()[0]
    assert c.patch(f"/api/v1/areas/{otra['id']}", headers=enca, json={"nombre": area["nombre"]}).status_code == 400


def test_subtipos_catalogo(equipo):
    c = equipo
    enca, asis = entrar(c, "enca@x.com"), entrar(c, "asis@x.com")
    nuevo = {"tipo": "otro", "titulo": "Taller", "descripcion": "x", "subtipo": "capacitacion"}
    assert c.post("/api/v1/eventos", headers=asis, json=nuevo).status_code == 422  # todavía no existe

    assert c.post("/api/v1/subtipos", headers=asis, json={"tipo": "otro", "nombre": "capacitacion"}).status_code == 409
    assert c.post("/api/v1/subtipos", headers=enca, json={"tipo": "otro", "nombre": "Capacitación!"}).status_code == 422
    assert c.post("/api/v1/subtipos", headers=enca, json={"tipo": "otro", "nombre": "capacitacion"}).status_code == 201
    assert c.post("/api/v1/subtipos", headers=enca, json={"tipo": "otro", "nombre": "capacitacion"}).status_code == 400
    assert c.post("/api/v1/eventos", headers=asis, json=nuevo).status_code == 201

    # Desactivar uno de fábrica: ya no se acepta, pero el catálogo lo sigue mostrando a quien administra.
    assert c.patch("/api/v1/subtipos/otro/aviso", headers=enca, json={"activo": False}).status_code == 200
    lo_mismo = {"tipo": "otro", "titulo": "Aviso", "descripcion": "x", "subtipo": "aviso"}
    assert c.post("/api/v1/eventos", headers=asis, json=lo_mismo).status_code == 422
    vigentes = [s["nombre"] for s in c.get("/api/v1/subtipos?tipo=otro", headers=asis).json()]
    assert "aviso" not in vigentes and "capacitacion" in vigentes
    todos = {s["nombre"]: s for s in c.get("/api/v1/subtipos?tipo=otro&incluir_inactivos=true", headers=enca).json()}
    assert todos["aviso"]["activo"] is False and todos["aviso"]["base"] is True and todos["capacitacion"]["base"] is False
    assert c.patch("/api/v1/subtipos/otro/inexistente", headers=enca, json={"activo": False}).status_code == 404
    # Reactivar.
    assert c.post("/api/v1/subtipos", headers=enca, json={"tipo": "otro", "nombre": "aviso"}).status_code == 201
    assert c.post("/api/v1/eventos", headers=asis, json=lo_mismo).status_code == 201
