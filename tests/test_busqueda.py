from app.busqueda import fragmento, normalizar, terminos
from tests.test_sprint1 import cliente, entrar  # noqa: F401
from tests.test_sprint2 import crear, equipo, manana  # noqa: F401


def test_normalizar_y_raices():
    assert normalizar("Préstamo de CÁMARA") == "prestamo de camara"
    assert terminos("licencias") == terminos("licencia")
    assert terminos("computadores") == terminos("computador")
    assert terminos("préstamo multímetro") == ["prestamo", "multimetro"]


def test_fragmento_indica_el_campo():
    class E:  # lo mínimo que usa fragmento()
        titulo, descripcion = "Préstamo de multímetro", "Se prestó a Operaciones."
        solicitante_nombre = referencia = None
    assert fragmento("multimetro", E, [], []).startswith("título:")


def test_busca_sin_acentos_y_con_plurales(equipo):
    c = equipo
    h = entrar(c, "asis@x.com")
    crear(c, h, tipo="visita", subtipo=None, titulo="Préstamo de multímetro", requiere_seguimiento=False,
          descripcion="Se prestó el multímetro a Operaciones.")
    crear(c, h, titulo="Licencia de Office", descripcion="Renovar licencias del área.")
    r = c.get("/api/v1/eventos?q=prestamo", headers=h).json()
    assert r["meta"]["total"] == 1 and "multímetro" in r["data"][0]["titulo"]
    assert r["data"][0]["fragmento"]
    assert c.get("/api/v1/eventos?q=licencias", headers=h).json()["meta"]["total"] == 1
    assert c.get("/api/v1/eventos?q=MULTIMETROS", headers=h).json()["meta"]["total"] == 1


def test_varias_palabras_todas_deben_aparecer(equipo):
    c = equipo
    h = entrar(c, "asis@x.com")
    crear(c, h, titulo="Reporte de ventas", descripcion="Para Contabilidad.")
    assert c.get("/api/v1/eventos?q=reporte contabilidad", headers=h).json()["meta"]["total"] == 1
    assert c.get("/api/v1/eventos?q=reporte inventario", headers=h).json()["meta"]["total"] == 0


def test_busca_en_notas_y_compromisos_pero_no_en_notas_automaticas(equipo):
    c = equipo
    h = entrar(c, "asis@x.com")
    folio = crear(c, h)["folio"]
    c.post(f"/api/v1/eventos/{folio}/seguimientos", headers=h, json={"nota": "Habló el proveedor Zeta."})
    c.post(f"/api/v1/eventos/{folio}/compromisos", headers=h, json={"descripcion": "Enviar cotización", "fecha_limite": manana()})
    assert c.get("/api/v1/eventos?q=zeta", headers=h).json()["meta"]["total"] == 1
    assert c.get("/api/v1/eventos?q=cotizacion", headers=h).json()["meta"]["total"] == 1
    c.post(f"/api/v1/eventos/{folio}/estado", headers=h, json={"estado": "en_proceso"})
    assert c.get("/api/v1/eventos?q=en_proceso", headers=h).json()["meta"]["total"] == 0  # nota automática no cuenta


def test_folio_abre_ese_evento(equipo):
    c = equipo
    h = entrar(c, "asis@x.com")
    folio = crear(c, h)["folio"]
    r = c.get(f"/api/v1/eventos?q={folio.lower()}", headers=h).json()
    assert [e["folio"] for e in r["data"]] == [folio]


def test_filtros_combinados_y_vencidos(equipo):
    c = equipo
    h = entrar(c, "asis@x.com")
    a = crear(c, h, titulo="Uno")
    crear(c, h, titulo="Dos", requiere_seguimiento=False)
    assert c.get("/api/v1/eventos?seguimiento=sin", headers=h).json()["meta"]["total"] == 1
    assert c.get("/api/v1/eventos?estado=abierto", headers=h).json()["meta"]["total"] == 1
    assert c.get("/api/v1/eventos?q=uno&tipo=solicitud", headers=h).json()["meta"]["total"] == 1
    assert c.get("/api/v1/eventos?q=uno&tipo=visita", headers=h).json()["meta"]["total"] == 0
    assert c.get("/api/v1/eventos?vencidos=true", headers=h).json()["meta"]["total"] == 0
    assert a["estado"] == "abierto"


def test_correccion_de_cabecera_con_auditoria(equipo):
    c = equipo
    asis, enca = entrar(c, "asis@x.com"), entrar(c, "enca@x.com")
    folio = crear(c, asis)["folio"]
    # El autor corrige el mismo día.
    r = c.patch(f"/api/v1/eventos/{folio}", headers=asis, json={"titulo": "Reporte de ventas Q4", "referencia": "TKT-9"})
    assert r.status_code == 200 and r.json()["titulo"] == "Reporte de ventas Q4" and r.json()["referencia"] == "TKT-9"
    # La búsqueda ve el cambio.
    assert c.get("/api/v1/eventos?q=TKT-9", headers=asis).json()["meta"]["total"] == 1
    # Otro asistente-autor ajeno no puede; el encargado sí.
    ajeno = crear(c, enca, titulo="Del encargado")["folio"]
    r = c.patch(f"/api/v1/eventos/{ajeno}", headers=asis, json={"titulo": "Cambio ajeno"})
    assert r.status_code == 409 and r.json()["detail"]["codigo"] == "sin_permiso"
    assert c.patch(f"/api/v1/eventos/{folio}", headers=enca, json={"descripcion": "Nueva descripción"}).status_code == 200
    det = c.get(f"/api/v1/eventos/{folio}?incluir=auditoria", headers=asis).json()
    campos = [(a["campo"], a["valor_anterior"], a["valor_nuevo"]) for a in det["auditoria"]]
    assert ("titulo", "Reporte de ventas", "Reporte de ventas Q4") in campos
    assert any(x[0] == "descripcion" for x in campos)
    assert det["auditoria"][0]["usuario"]["nombre"] == "Asis"


def test_correccion_valida_subtipo_y_fecha(equipo):
    c = equipo
    enca = entrar(c, "enca@x.com")
    folio = crear(c, enca)["folio"]
    assert c.patch(f"/api/v1/eventos/{folio}", headers=enca, json={"subtipo": "no_existe"}).status_code == 400
    assert c.patch(f"/api/v1/eventos/{folio}", headers=enca, json={"fecha_hecho": "2999-01-01"}).status_code == 400
    r = c.patch(f"/api/v1/eventos/{folio}", headers=enca, json={"subtipo": None})
    assert r.status_code == 200 and r.json()["subtipo"] is None


def test_condicion_busqueda_postgresql_tsvector():
    from sqlalchemy import select
    from sqlalchemy.dialects import postgresql
    from app.busqueda import condicion_busqueda
    from app.models import Evento

    conds = condicion_busqueda("servidor base datos", dialect_name="postgresql")
    assert len(conds) == 1
    sql = str(select(Evento).where(*conds).compile(dialect=postgresql.dialect()))
    assert "plainto_tsquery('spanish'" in sql
    assert "evento.busqueda @@" in sql
