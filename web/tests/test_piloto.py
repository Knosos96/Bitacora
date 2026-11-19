"""Ensayo automático de la semana piloto (sección 13 del diseño).

Reproduce lunes a viernes con los mismos hechos y comprueba lo que la tabla pide recuperar.
La semana termina hoy: el viernes es hoy y el lunes, cuatro días atrás (un hecho no puede ser del futuro).
"""
from datetime import timedelta

from app.services.eventos import hoy_en_zona
from tests.test_sprint1 import cliente, entrar  # noqa: F401
from tests.test_sprint2 import crear, equipo  # noqa: F401


def test_semana_piloto(equipo):
    c = equipo
    asis, enca, jefe = entrar(c, "asis@x.com"), entrar(c, "enca@x.com"), entrar(c, "jefe@x.com")
    viernes = hoy_en_zona()
    lunes, martes, miercoles, jueves = (viernes - timedelta(days=n) for n in (4, 3, 2, 1))
    conta = next(a for a in c.get("/api/v1/areas", headers=asis).json() if a["nombre"] == "Contabilidad")
    k = {"X-API-Key": c.post("/api/v1/claves-api", headers=jefe, json={"nombre": "programa externo"}).json()["clave"]}

    # LUNES — solicitud de otra área, con seguimiento y compromiso al viernes.
    sol = crear(c, asis, tipo="solicitud", subtipo="desarrollo", titulo="Reporte de cartera vencida",
                descripcion="Contabilidad pide un reporte de cartera por cliente.", area_id=conta["id"],
                solicitante_nombre="Laura Pérez", fecha_hecho=str(lunes))
    comp = c.post(f"/api/v1/eventos/{sol['folio']}/compromisos", headers=asis,
                  json={"descripcion": "Entregar el reporte", "fecha_limite": str(viernes)}).json()
    tablero = {i["id"]: i for i in c.get("/api/v1/kpi", headers=enca).json()["indicadores"]}
    assert tablero["K3"]["valor"] == 1  # aparece en K3
    pend = c.get("/api/v1/pendientes", headers=enca).json()
    assert [e["folio"] for e in pend["eventos"]] == [sol["folio"]]  # y en Pendientes
    assert [x["id"] for x in pend["compromisos"]] == [comp["id"]]

    # LUNES — préstamo de una herramienta, sin seguimiento.
    crear(c, asis, tipo="otro", subtipo="prestamo", requiere_seguimiento=False, fecha_hecho=str(lunes),
          titulo="Préstamo de multímetro Fluke", descripcion="Se prestó el multímetro a Mantenimiento.")
    r = c.get("/api/v1/eventos", headers=asis, params={"q": "multimetro"}).json()
    assert r["meta"]["total"] == 1 and r["data"][0]["requiere_seguimiento"] is False  # la búsqueda lo encuentra
    k3 = c.get("/api/v1/kpi/K3", headers=enca).json()["eventos"]
    assert "Préstamo de multímetro Fluke" not in [e["titulo"] for e in k3]  # no aparece en K3

    # MARTES — visita de un jefe de área.
    crear(c, asis, tipo="visita", subtipo="presencial", requiere_seguimiento=False, fecha_hecho=str(martes),
          titulo="Visita del jefe de Operaciones", descripcion="Vino a ver el avance del tablero.")
    por_pantalla = c.get("/api/v1/eventos", headers=asis, params={"tipo": "visita", "desde": str(martes), "hasta": str(martes)})
    por_api = c.get("/api/v1/eventos", headers=k, params={"tipo": "visita", "desde": str(martes), "hasta": str(martes)})
    for r in (por_pantalla, por_api):
        assert [e["titulo"] for e in r.json()["data"]] == ["Visita del jefe de Operaciones"]

    # MIÉRCOLES — incidencia del ambiente de pruebas, en espera de un proveedor.
    inc = crear(c, asis, tipo="incidencia", subtipo="falla", fecha_hecho=str(miercoles),
                titulo="Ambiente de pruebas caído", descripcion="No levanta la base del ambiente de pruebas.")
    sin_nota = c.post(f"/api/v1/eventos/{inc['folio']}/estado", headers=asis, json={"estado": "en_espera"})
    assert sin_nota.status_code == 422  # en espera exige decir de quién
    c.post(f"/api/v1/eventos/{inc['folio']}/estado", headers=asis,
           json={"estado": "en_espera", "nota": "Esperando respuesta del proveedor de hosting."})
    ficha = c.get(f"/api/v1/eventos/{inc['folio']}?incluir=seguimientos", headers=asis).json()
    assert ficha["estado"] == "en_espera"
    assert any("proveedor de hosting" in n["nota"] for n in ficha["seguimientos"])

    # JUEVES — tarea interna, asignada a un asistente.
    tarea = crear(c, enca, tipo="tarea", subtipo="interna", fecha_hecho=str(jueves),
                  titulo="Script de respaldo nocturno", descripcion="Automatizar el respaldo de la base.")
    asis_id = next(u["id"] for u in c.get("/api/v1/usuarios", headers=enca).json() if u["correo"] == "asis@x.com")
    assert c.patch(f"/api/v1/eventos/{tarea['folio']}", headers=enca, json={"responsable_id": asis_id}).status_code == 200
    c.post(f"/api/v1/eventos/{tarea['folio']}/compromisos", headers=enca,
           json={"descripcion": "Probar el script en pruebas", "fecha_limite": str(viernes), "responsable_id": asis_id})
    k9 = {i["id"]: i for i in c.get("/api/v1/kpi", headers=enca).json()["indicadores"]}["K9"]
    asis_carga = next(p for p in k9["detalle"]["por_responsable"] if p["nombre"] == "Asis")
    assert asis_carga["abiertos"] == 3  # solicitud, incidencia y tarea
    suyos = c.get("/api/v1/pendientes", headers=asis).json()
    assert len(suyos["eventos"]) == 3

    # VIERNES — se cumple el compromiso del lunes y el encargado cierra.
    assert c.patch(f"/api/v1/compromisos/{comp['id']}", headers=asis, json={"estado": "cumplido"}).status_code == 200
    c.post(f"/api/v1/eventos/{sol['folio']}/estado", headers=asis, json={"estado": "resuelto"})
    assert c.post(f"/api/v1/eventos/{sol['folio']}/estado", headers=enca, json={"estado": "cerrado"}).status_code == 200
    rango = {"desde": str(lunes), "hasta": str(viernes)}
    tablero = {i["id"]: i for i in c.get("/api/v1/kpi", headers=enca, params=rango).json()["indicadores"]}
    # K7: de los dos compromisos con fecha el viernes, el del lunes se cumplió a tiempo y el del jueves sigue abierto.
    assert tablero["K7"]["detalle"] == {"cumplidos_a_tiempo": 1, "total": 2}
    assert tablero["K5"]["detalle"]["cerrados"] == 1 and "solicitud" in tablero["K5"]["detalle"]["por_tipo"]
    assert tablero["K1"]["valor"] == 5 and tablero["K12"]["valor"] == 1

    # VIERNES — consulta del programa externo, lunes a viernes, tipo solicitud.
    api = c.get("/api/v1/eventos", headers=k, params={**rango, "tipo": "solicitud"}).json()
    assert [e["folio"] for e in api["data"]] == [sol["folio"]]

    # CIERRE DE SEMANA — el encargado responde solo con la bitácora.
    pidio_conta = c.get("/api/v1/eventos", headers=enca, params={"area_id": conta["id"], **rango}).json()
    assert [e["titulo"] for e in pidio_conta["data"]] == ["Reporte de cartera vencida"]
    abiertos = c.get("/api/v1/pendientes", headers=enca).json()["compromisos"]
    assert [x["descripcion"] for x in abiertos] == ["Probar el script en pruebas"]
    export = c.get("/api/v1/eventos/exportar", headers=enca, params=rango)
    assert export.status_code == 200 and export.content.decode("utf-8-sig").count("BIT-") == 5
