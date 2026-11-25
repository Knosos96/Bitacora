"""Pruebas funcionales y de seguridad del módulo Superusuario e historial inmutable."""
from app.core.db import get_db
from app.core.enums import Rol
from app.core.security import hashear_clave
from app.models import Usuario
from tests.test_sprint1 import cliente, entrar  # noqa: F401
from tests.test_sprint2 import crear, equipo, manana  # noqa: F401


def _con_super(c):
    from app.main import app

    db = next(app.dependency_overrides[get_db]())
    db.add(Usuario(
        nombre="Super ZGROUP",
        correo="super@x.com",
        rol=Rol.superusuario,
        clave_hash=hashear_clave("SuperClave1"),
    ))
    db.commit()
    r = c.post("/api/v1/auth/login", json={"correo": "super@x.com", "clave": "SuperClave1"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_acceso_exclusivo_superusuario_y_proteccion_cuenta(equipo):
    c = equipo
    h_super = _con_super(c)
    jefe = entrar(c, "jefe@x.com")
    enca = entrar(c, "enca@x.com")
    asis = entrar(c, "asis@x.com")

    for h in (jefe, enca, asis):
        assert c.get("/api/v1/superadmin/resumen", headers=h).status_code == 409
        assert c.get("/api/v1/superadmin/cuentas", headers=h).status_code == 409
        assert c.get("/api/v1/superadmin/actividad", headers=h).status_code == 409

    assert c.get("/api/v1/superadmin/resumen", headers=h_super).status_code == 200

    # El jefe no ve al superusuario ni puede crear/modificar/eliminar superusuarios
    correos_jefe = [u["correo"] for u in c.get("/api/v1/usuarios", headers=jefe).json()]
    assert "super@x.com" not in correos_jefe
    assert c.post("/api/v1/usuarios", headers=jefe, json={
        "nombre": "Otro Super", "correo": "super2@x.com", "clave": "ClaveSegura1", "rol": "superusuario"
    }).status_code == 409

    super_id = c.get("/api/v1/auth/yo", headers=h_super).json()["id"]
    assert c.patch(f"/api/v1/usuarios/{super_id}", headers=jefe, json={"activo": False}).status_code == 409
    assert c.delete(f"/api/v1/usuarios/{super_id}", headers=jefe).status_code == 409


def test_historial_completo_preservado_tras_eliminar_cuenta(equipo):
    c = equipo
    h_super = _con_super(c)
    jefe = entrar(c, "jefe@x.com")

    # 1. El jefe crea una cuenta operativa de encargado
    creado = c.post("/api/v1/usuarios", headers=jefe, json={
        "nombre": "Operador Temporal",
        "correo": "operador@x.com",
        "clave": "ClaveSegura1",
        "rol": "encargado",
    })
    assert creado.status_code == 201
    op_id = creado.json()["id"]
    h_op = {"Authorization": f"Bearer {c.post('/api/v1/auth/login', json={'correo': 'operador@x.com', 'clave': 'ClaveSegura1'}).json()['token']}"}

    # 2. El operador registra una incidencia con referencia, nota, compromiso y exporta CSV
    inc = crear(
        c, h_op,
        tipo="incidencia",
        subtipo="falla",
        titulo="Caída enlace principal",
        descripcion="Sin acceso a red corporativa.",
        referencia="DOC-INC-2026-88",
    )
    folio = inc["folio"]
    assert c.post(f"/api/v1/eventos/{folio}/seguimientos", headers=h_op, json={"nota": "Revisando router."}).status_code == 201
    assert c.post(f"/api/v1/eventos/{folio}/compromisos", headers=h_op, json={
        "descripcion": "Validar con ISP", "fecha_limite": manana()
    }).status_code == 201
    assert c.get("/api/v1/eventos/exportar", headers=h_op).status_code == 200

    # 3. El jefe elimina permanentemente al operador
    assert c.delete(f"/api/v1/usuarios/{op_id}", headers=jefe).status_code == 204
    assert all(u["id"] != op_id for u in c.get("/api/v1/usuarios", headers=jefe).json())

    # 4. El superusuario conserva el historial completo de la cuenta eliminada
    cuentas = c.get("/api/v1/superadmin/cuentas", headers=h_super).json()
    cuenta_op = next(x for x in cuentas if x["id"] == op_id)
    assert cuenta_op["estado"] == "eliminada"
    assert cuenta_op["eliminado_por_nombre"] == "Jefa"
    assert cuenta_op["incidencias_creadas"] == 1
    assert cuenta_op["eventos_creados"] == 1
    assert cuenta_op["pendientes_abiertos"] == 1

    # Expediente completo de la cuenta eliminada
    exp = c.get(f"/api/v1/superadmin/cuentas/{op_id}", headers=h_super).json()
    assert len(exp["incidencias"]) == 1 and exp["incidencias"][0]["folio"] == folio
    assert exp["incidencias"][0]["autor_original_nombre"] == "Operador Temporal"
    assert exp["incidencias"][0]["autor_original_estado"] == "eliminada"
    assert len(exp["pendientes"]["eventos"]) == 1
    assert len(exp["exportaciones"]) == 1
    acciones = {a["accion"] for a in exp["actividades"]}
    assert {"login_exitoso", "incidencia_creada", "nota_agregada", "compromiso_creado", "csv_exportado"} <= acciones

    # Archivos y actividad global
    archivos = c.get("/api/v1/superadmin/archivos", headers=h_super).json()
    assert any(r["folio"] == folio and r["referencia"] == "DOC-INC-2026-88" for r in archivos["referencias"])
    assert any(x["actor_id"] == op_id for x in archivos["exportaciones"])

    act_global = c.get("/api/v1/superadmin/actividad", headers=h_super).json()
    assert any(a["accion"] == "usuario_eliminado" and "Operador Temporal" in (a["titulo"] or "") for a in act_global)

    # Exportaciones documentales CSV del superusuario
    for sec in ("cuentas", "registros", "actividad"):
        r_csv = c.get(f"/api/v1/superadmin/exportar?seccion={sec}", headers=h_super)
        assert r_csv.status_code == 200 and r_csv.content.startswith(b"\xef\xbb\xbf")


def test_eliminacion_logica_preserva_atribucion_sin_cascada(equipo):
    c = equipo
    h_super = _con_super(c)
    jefe = entrar(c, "jefe@x.com")

    # Área y operador que luego serán eliminados
    area_r = c.post("/api/v1/areas", headers=jefe, json={"nombre": "Redes Legado"})
    assert area_r.status_code == 201
    area_id = area_r.json()["id"]

    op_r = c.post("/api/v1/usuarios", headers=jefe, json={
        "nombre": "Ana Auditora",
        "correo": "ana@x.com",
        "clave": "ClaveSegura1",
        "rol": "encargado",
    })
    assert op_r.status_code == 201
    op_id = op_r.json()["id"]
    h_ana = {"Authorization": f"Bearer {c.post('/api/v1/auth/login', json={'correo': 'ana@x.com', 'clave': 'ClaveSegura1'}).json()['token']}"}

    inc = crear(
        c, h_ana,
        tipo="incidencia",
        subtipo="falla",
        titulo="Corte firewall perimetral",
        descripcion="Registro completo antes de eliminar cuenta y área.",
        area_id=area_id,
    )
    folio = inc["folio"]
    assert c.patch(f"/api/v1/eventos/{folio}", headers=h_ana, json={"titulo": "Corte firewall principal"}).status_code == 200
    assert c.post(f"/api/v1/eventos/{folio}/seguimientos", headers=h_ana, json={"nota": "Nota original de Ana."}).status_code == 201
    assert c.post(f"/api/v1/eventos/{folio}/compromisos", headers=h_ana, json={
        "descripcion": "Revisar reglas NAT", "fecha_limite": manana()
    }).status_code == 201

    # Jefe elimina el área y elimina la cuenta de Ana
    assert c.delete(f"/api/v1/areas/{area_id}", headers=jefe).status_code == 204
    assert c.delete(f"/api/v1/usuarios/{op_id}", headers=jefe).status_code == 204

    # La cuenta eliminada no puede iniciar sesión ni aparece en la lista operativa ni tiene token válido
    assert c.post("/api/v1/auth/login", json={"correo": "ana@x.com", "clave": "ClaveSegura1"}).status_code == 401
    assert c.get("/api/v1/auth/yo", headers=h_ana).status_code == 401
    assert all(u["id"] != op_id for u in c.get("/api/v1/usuarios", headers=jefe).json())

    # Superusuario ve la ficha documental intacta sin reasignar autor/nota/compromiso/auditoría/área
    det_r = c.get(f"/api/v1/superadmin/registros/{folio}", headers=h_super)
    assert det_r.status_code == 200, det_r.text
    det = det_r.json()
    assert det["registro"]["autor_original_nombre"] == "Ana Auditora"
    assert det["registro"]["autor_original_estado"] == "eliminada"
    assert det["registro"]["responsable_original_nombre"] == "Ana Auditora"
    assert det["registro"]["area_nombre"] == "Redes Legado"
    assert det["notas"][0]["autor_nombre"] == "Ana Auditora"
    assert det["notas"][0]["autor_estado"] == "eliminada"
    assert det["compromisos"][0]["responsable_nombre"] == "Ana Auditora"
    assert det["compromisos"][0]["responsable_estado"] == "eliminada"
    assert det["auditoria"][0]["usuario_nombre"] == "Ana Auditora"
    assert det["auditoria"][0]["usuario_estado"] == "eliminada"

    # Pendientes globales preservan al responsable original
    pend = c.get("/api/v1/superadmin/pendientes", headers=h_super).json()
    comp_p = next(x for x in pend["compromisos"] if x["evento_folio"] == folio)
    assert comp_p["responsable_nombre"] == "Ana Auditora"
    assert comp_p["responsable_estado"] == "eliminada"

    # Recrear una cuenta con el mismo correo funciona sin colisionar ni borrar el historial previo
    recreado = c.post("/api/v1/usuarios", headers=jefe, json={
        "nombre": "Ana Nueva",
        "correo": "ana@x.com",
        "clave": "ClaveSegura2",
        "rol": "asistente",
    })
    assert recreado.status_code == 201, recreado.text
    nuevo_id = recreado.json()["id"]
    assert nuevo_id != op_id

    cuentas = c.get("/api/v1/superadmin/cuentas", headers=h_super).json()
    viejas = [x for x in cuentas if x["id"] == op_id]
    nuevas = [x for x in cuentas if x["id"] == nuevo_id]
    assert viejas[0]["correo"] == "ana@x.com" and viejas[0]["estado"] == "eliminada"
    assert nuevas[0]["correo"] == "ana@x.com" and nuevas[0]["estado"] == "activa"
