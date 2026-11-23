"""Pruebas funcionales y no funcionales (seguridad, validación, encabezados, rendimiento y concurrencia)."""
import time

from app.core.rate_limit import login_ip_limiter, login_limiter
from tests.test_sprint1 import cliente, entrar  # noqa: F401
from tests.test_sprint2 import crear, equipo, manana  # noqa: F401


# ---------------------------------------------------------------- Funcional: roles personalizados y eliminación
def test_rol_personalizado_aplica_permisos_en_login_y_endpoints(equipo):
    c = equipo
    jefe = entrar(c, "jefe@x.com")

    rol = c.post(
        "/api/v1/roles",
        headers=jefe,
        json={"nombre": "Analista KPI", "descripcion": "Ve tablero y gestiona áreas", "permisos": ["ver_kpi", "gestionar_areas"]},
    )
    assert rol.status_code == 201, rol.text
    rol_id = rol.json()["id"]

    u = c.post(
        "/api/v1/usuarios",
        headers=jefe,
        json={
            "nombre": "Analista",
            "correo": "analista@x.com",
            "clave": "ClaveSegura1",
            "rol": "asistente",
            "rol_custom_id": rol_id,
        },
    )
    assert u.status_code == 201, u.text
    assert u.json()["rol_custom_nombre"] == "Analista KPI"
    assert set(u.json()["permisos"]) == {"ver_kpi", "gestionar_areas"}

    login_res = c.post("/api/v1/auth/login", json={"correo": "analista@x.com", "clave": "ClaveSegura1"})
    assert login_res.status_code == 200
    datos = login_res.json()
    assert datos["usuario"]["rol_custom_nombre"] == "Analista KPI"
    assert set(datos["usuario"]["permisos"]) == {"ver_kpi", "gestionar_areas"}

    h_ana = {"Authorization": f"Bearer {datos['token']}"}
    yo = c.get("/api/v1/auth/yo", headers=h_ana)
    assert yo.status_code == 200 and yo.json()["rol_custom_nombre"] == "Analista KPI"

    # Tiene ver_kpi y gestionar_areas, pero NO crear_usuarios ni crear_eventos
    assert c.get("/api/v1/kpi", headers=h_ana).status_code == 200
    assert c.post("/api/v1/areas", headers=h_ana, json={"nombre": "Redes"}).status_code == 201
    assert c.post("/api/v1/usuarios", headers=h_ana, json={
        "nombre": "Otro", "correo": "otro@x.com", "clave": "ClaveSegura1", "rol": "asistente"
    }).status_code == 409
    assert c.post("/api/v1/eventos", headers=h_ana, json={
        "tipo": "otro", "titulo": "x", "descripcion": "y"
    }).status_code == 409


def test_eliminacion_en_administracion_preserva_integridad(equipo):
    c = equipo
    jefe = entrar(c, "jefe@x.com")
    asis = entrar(c, "asis@x.com")

    # Área asociada a un evento
    area = c.post("/api/v1/areas", headers=jefe, json={"nombre": "Temporal"}).json()
    ev = crear(c, asis, area_id=area["id"])
    assert c.delete(f"/api/v1/areas/{area['id']}", headers=jefe).status_code == 204
    assert c.get(f"/api/v1/eventos/{ev['folio']}", headers=jefe).json()["area_origen"] is None

    # Subtipo personalizado y de fábrica
    assert c.post("/api/v1/subtipos", headers=jefe, json={"tipo": "otro", "nombre": "auditoria_ti"}).status_code == 201
    assert c.delete("/api/v1/subtipos/otro/auditoria_ti", headers=jefe).status_code == 204
    assert c.delete("/api/v1/subtipos/otro/aviso", headers=jefe).status_code == 204
    nombres_otro = [s["nombre"] for s in c.get("/api/v1/subtipos?tipo=otro&incluir_inactivos=true", headers=jefe).json()]
    assert "auditoria_ti" not in nombres_otro and "aviso" not in nombres_otro

    # Clave API permanente
    clave = c.post("/api/v1/claves-api", headers=jefe, json={"nombre": "TempKey"}).json()
    assert c.delete(f"/api/v1/claves-api/{clave['id']}/permanente", headers=jefe).status_code == 204
    assert c.get("/api/v1/claves-api", headers=jefe).json() == []

    # Usuario (no puede eliminarse a sí mismo, sí a otro preservando eventos)
    jefe_id = c.get("/api/v1/auth/yo", headers=jefe).json()["id"]
    assert c.delete(f"/api/v1/usuarios/{jefe_id}", headers=jefe).status_code == 409
    asis_id = c.get("/api/v1/auth/yo", headers=asis).json()["id"]
    assert c.delete(f"/api/v1/usuarios/{asis_id}", headers=jefe).status_code == 204
    assert c.get(f"/api/v1/eventos/{ev['folio']}", headers=jefe).status_code == 200


# ---------------------------------------------------------------- Funcional: validación de entradas
def test_rechaza_cadenas_solo_espacios_y_claves_debiles(equipo):
    c = equipo
    jefe = entrar(c, "jefe@x.com")

    assert c.post("/api/v1/areas", headers=jefe, json={"nombre": "   "}).status_code == 422
    assert c.post("/api/v1/eventos", headers=jefe, json={
        "tipo": "otro", "titulo": "   ", "descripcion": "valido"
    }).status_code == 422
    assert c.post("/api/v1/eventos", headers=jefe, json={
        "tipo": "otro", "titulo": "valido", "descripcion": "   "
    }).status_code == 422

    # Contraseña sin números / sin letras / con espacios
    for mala in ("sololetras", "12345678", "Clave 123"):
        r = c.post("/api/v1/usuarios", headers=jefe, json={
            "nombre": "Test", "correo": "test@x.com", "clave": mala, "rol": "asistente"
        })
        assert r.status_code == 422, f"Aceptó clave débil: {mala}"


# ---------------------------------------------------------------- No funcional: Seguridad
def test_cabeceras_de_seguridad_y_recursos_web(cliente):
    c = cliente
    for ruta in ("/", "/static/css/app.css", "/static/js/app.js", "/static/img/logo-zgroup.png", "/api/v1/salud"):
        r = c.get(ruta)
        assert r.status_code == 200, f"Fallo en {ruta}: {r.status_code}"
        assert r.headers.get("x-content-type-options") == "nosniff"
        assert r.headers.get("x-frame-options") == "DENY"
        assert r.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert "frame-ancestors 'none'" in (r.headers.get("content-security-policy") or "")

    r_login = c.post("/api/v1/auth/login", json={"correo": "jefe@x.com", "clave": "clave12345"})
    assert r_login.headers.get("cache-control") == "no-store"


def test_jwt_malformado_y_revocacion_al_cambiar_clave(equipo):
    import jwt as pyjwt
    from app.core.config import settings

    c = equipo
    jefe = entrar(c, "jefe@x.com")
    asis = entrar(c, "asis@x.com")
    asis_id = c.get("/api/v1/auth/yo", headers=asis).json()["id"]

    # Token firmado con sub no-UUID debe responder 401 (no 500)
    malo = pyjwt.encode({"sub": "no-es-uuid"}, settings.secret_key, algorithm="HS256")
    assert c.get("/api/v1/auth/yo", headers={"Authorization": f"Bearer {malo}"}).status_code == 401

    # Cambiar contraseña invalida tokens emitidos anteriormente
    assert c.get("/api/v1/auth/yo", headers=asis).status_code == 200
    assert c.patch(f"/api/v1/usuarios/{asis_id}", headers=jefe, json={"clave": "NuevaClave1"}).status_code == 200
    assert c.get("/api/v1/auth/yo", headers=asis).status_code == 401


def test_rate_limit_en_login(cliente):
    c = cliente
    login_limiter._eventos.clear()
    login_ip_limiter._eventos.clear()

    for _ in range(10):
        r = c.post("/api/v1/auth/login", json={"correo": "fuerza@x.com", "clave": "mala"})
        assert r.status_code == 401

    bloqueado = c.post("/api/v1/auth/login", json={"correo": "fuerza@x.com", "clave": "mala"})
    assert bloqueado.status_code == 429
    assert "retry-after" in bloqueado.headers

    login_limiter._eventos.clear()
    login_ip_limiter._eventos.clear()


def test_limites_busqueda_y_csv_injection(equipo):
    c = equipo
    jefe = entrar(c, "jefe@x.com")
    assert c.get("/api/v1/eventos", headers=jefe, params={"q": "a" * 201}).status_code == 422
    assert c.get("/api/v1/eventos", headers=jefe, params={"page_size": 201}).status_code == 422

    crear(c, jefe, titulo=" =CMD()", descripcion=" +SUM(1,2)")
    r = c.get("/api/v1/eventos/exportar", headers=jefe)
    assert r.status_code == 200
    cuerpo = r.content.decode("utf-8-sig")
    assert "'=CMD()" in cuerpo or "' =CMD()" in cuerpo


# ---------------------------------------------------------------- No funcional: Rendimiento / folios únicos
def test_rendimiento_y_unicidad_folios(equipo):
    c = equipo
    jefe = entrar(c, "jefe@x.com")
    t0 = time.perf_counter()
    folios = set()
    for i in range(15):
        r = c.post(
            "/api/v1/eventos",
            headers=jefe,
            json={"tipo": "tarea", "titulo": f"Tarea carga {i}", "descripcion": "Prueba rendimiento"},
        )
        assert r.status_code == 201
        folios.add(r.json()["folio"])
    duracion = time.perf_counter() - t0
    assert len(folios) == 15
    assert duracion < 5.0
