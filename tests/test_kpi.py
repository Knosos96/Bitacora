from datetime import timedelta

from app.routers.eventos import hoy_en_zona
from tests.test_sprint1 import cliente, entrar  # noqa: F401
from tests.test_sprint2 import crear, equipo, manana  # noqa: F401


def kpis(c, h, **params):
    r = c.get("/api/v1/kpi", headers=h, params=params)
    assert r.status_code == 200, r.text
    return {i["id"]: i for i in r.json()["indicadores"]}


def test_asistente_no_ve_el_tablero(equipo):
    c = equipo
    asis = entrar(c, "asis@x.com")
    assert c.get("/api/v1/kpi", headers=asis).status_code == 403
    assert c.get("/api/v1/kpi/K3", headers=asis).status_code == 403


def test_semana_de_prueba_criterio_de_listo_sprint4(equipo):
    """K1 suma el total, K5 no incluye informativos y K8 lista el compromiso cuya fecha ya pasó."""
    c = equipo
    asis, enca = entrar(c, "asis@x.com"), entrar(c, "enca@x.com")
    areas = c.get("/api/v1/areas", headers=asis).json()
    conta = areas[0]["id"]

    s1 = crear(c, asis, tipo="solicitud", area_id=conta)          # con seguimiento
    crear(c, asis, tipo="visita", subtipo=None, requiere_seguimiento=False, titulo="Visita")  # informativo
    crear(c, asis, tipo="incidencia", subtipo=None, titulo="Servidor caído")
    crear(c, asis, tipo="tarea", subtipo=None, requiere_seguimiento=False, titulo="Script")

    # Se cierra la solicitud con su compromiso cumplido.
    folio = s1["folio"]
    comp = c.post(f"/api/v1/eventos/{folio}/compromisos", headers=asis,
                  json={"descripcion": "Entregar", "fecha_limite": manana()}).json()
    c.patch(f"/api/v1/compromisos/{comp['id']}", headers=asis, json={"estado": "cumplido"})
    c.post(f"/api/v1/eventos/{folio}/estado", headers=asis, json={"estado": "resuelto"})
    c.post(f"/api/v1/eventos/{folio}/estado", headers=enca, json={"estado": "cerrado"})

    # El rango llega hasta mañana para que el compromiso (vence mañana) entre en K7.
    k = kpis(c, enca, desde=str(hoy_en_zona()), hasta=manana())
    assert k["K1"]["valor"] == 4 and sum(k["K1"]["detalle"]["por_tipo"].values()) == 4
    assert k["K1"]["detalle"]["por_tipo"]["incidencia"] == 1 and k["K12"]["valor"] == 1
    assert k["K2"]["detalle"] == {"con_seguimiento": 2, "informativos": 2}
    assert k["K3"]["valor"] == 1  # solo la incidencia: la solicitud se cerró, los informativos no cuentan
    assert k["K4"]["valor"] == 0
    assert k["K5"]["detalle"]["cerrados"] == 1 and "visita" not in k["K5"]["detalle"]["por_tipo"]
    assert k["K6"]["valor"] == 1
    assert k["K7"]["valor"] == 100.0 and k["K7"]["detalle"] == {"cumplidos_a_tiempo": 1, "total": 1}
    assert k["K9"]["detalle"]["por_responsable"][0]["nombre"] == "Asis"
    assert k["K10"]["valor"] == 1 and k["K10"]["detalle"]["top"][0]["total"] == 1
    assert k["K11"]["valor"] == 0 and k["K11"]["detalle"]["titulo"] == "Servidor caído"

    # Cada indicador abre su lista.
    lista = c.get("/api/v1/kpi/K1", headers=enca, params={"desde": str(hoy_en_zona()), "hasta": str(hoy_en_zona())}).json()
    assert len(lista["eventos"]) == 4
    solo_inc = c.get("/api/v1/kpi/K1", headers=enca, params={"clave": "incidencia"}).json()
    assert [e["tipo"] for e in solo_inc["eventos"]] == ["incidencia"]
    assert [e["folio"] for e in c.get("/api/v1/kpi/K5", headers=enca).json()["eventos"]] == [folio]


def test_k8_lista_el_compromiso_vencido_y_responde_en_vacio(equipo):
    from app.main import app
    from app.db import get_db
    from app.models import Compromiso

    c = equipo
    asis, enca = entrar(c, "asis@x.com"), entrar(c, "enca@x.com")

    vacio = c.get("/api/v1/kpi/K8", headers=enca).json()
    assert vacio["compromisos"] == [] and vacio["texto_vacio"] == "No hay compromisos vencidos"
    assert kpis(c, enca)["K8"]["valor"] == 0

    folio = crear(c, asis)["folio"]
    c.post(f"/api/v1/eventos/{folio}/compromisos", headers=asis, json={"descripcion": "Entregar", "fecha_limite": manana()})
    db = next(app.dependency_overrides[get_db]())
    db.query(Compromiso).update({"fecha_limite": hoy_en_zona() - timedelta(days=2)})  # se le "pasó" la fecha
    db.commit()

    assert kpis(c, enca)["K8"]["valor"] == 1
    lista = c.get("/api/v1/kpi/K8", headers=enca).json()
    assert len(lista["compromisos"]) == 1 and lista["compromisos"][0]["vencido"] is True
    assert lista["compromisos"][0]["evento_folio"] == folio
    # Y los filtros de la Sprint 3 y Pendientes lo ven igual.
    assert c.get("/api/v1/eventos?vencidos=true", headers=enca).json()["meta"]["total"] == 1
    assert len(c.get("/api/v1/pendientes?solo_vencidos=true", headers=enca).json()["compromisos"]) == 1


def test_k7_incumplido_y_cancelado_no_cuenta(equipo):
    from app.main import app
    from app.db import get_db
    from app.models import Compromiso

    c = equipo
    asis, enca = entrar(c, "asis@x.com"), entrar(c, "enca@x.com")
    folio = crear(c, asis)["folio"]
    ids = [c.post(f"/api/v1/eventos/{folio}/compromisos", headers=asis,
                  json={"descripcion": f"c{i}", "fecha_limite": manana()}).json()["id"] for i in range(3)]
    c.patch(f"/api/v1/compromisos/{ids[0]}", headers=asis, json={"estado": "cumplido"})
    c.patch(f"/api/v1/compromisos/{ids[1]}", headers=asis, json={"estado": "cancelado"})
    db = next(app.dependency_overrides[get_db]())
    db.query(Compromiso).update({"fecha_limite": hoy_en_zona()})
    db.commit()
    k = kpis(c, enca, desde=str(hoy_en_zona()), hasta=str(hoy_en_zona()))
    # 1 cumplido a tiempo, 1 pendiente, 1 cancelado (fuera del denominador) → 1/2
    assert k["K7"]["detalle"] == {"cumplidos_a_tiempo": 1, "total": 2} and k["K7"]["valor"] == 50.0
    assert len(c.get("/api/v1/kpi/K7", headers=enca, params={"clave": "fuera"}).json()["compromisos"]) == 1


def test_rango_por_defecto_es_la_semana_y_validaciones(equipo):
    c = equipo
    enca = entrar(c, "enca@x.com")
    r = c.get("/api/v1/kpi", headers=enca).json()
    d, h = r["desde"], r["hasta"]
    from datetime import date
    assert date.fromisoformat(d).weekday() == 0 and date.fromisoformat(h).weekday() == 6
    assert c.get("/api/v1/kpi", headers=enca, params={"desde": "2026-02-02", "hasta": "2026-01-01"}).status_code == 400
    assert c.get("/api/v1/kpi/K99", headers=enca).status_code == 404


def test_k3_k4_k8_k9_k11_dependen_del_rango(equipo):
    from app.main import app
    from app.db import get_db
    from app.models import Compromiso

    c = equipo
    asis, enca = entrar(c, "asis@x.com"), entrar(c, "enca@x.com")
    hoy = hoy_en_zona()

    # Evento 1: abierto con seguimiento
    ev1 = crear(c, asis, tipo="solicitud", titulo="Abierto hoy", requiere_seguimiento=True)
    # Evento 2: resuelto hoy
    ev2 = crear(c, asis, tipo="tarea", subtipo="mantenimiento", titulo="Resuelto hoy", requiere_seguimiento=True)
    c.post(f"/api/v1/eventos/{ev2['folio']}/estado", headers=asis, json={"estado": "en_proceso"})
    c.post(f"/api/v1/eventos/{ev2['folio']}/estado", headers=asis, json={"estado": "resuelto"})

    # Compromiso vencido hoy (fecha_limite = ayer)
    c.post(f"/api/v1/eventos/{ev1['folio']}/compromisos", headers=asis, json={"descripcion": "Vencido", "fecha_limite": manana()})
    db = next(app.dependency_overrides[get_db]())
    ayer = hoy - timedelta(days=1)
    db.query(Compromiso).update({"fecha_limite": ayer})
    db.commit()

    # Rango que incluye hoy y ayer:
    k_incluye = kpis(c, enca, desde=str(ayer), hasta=str(hoy))
    assert k_incluye["K3"]["valor"] >= 1
    assert k_incluye["K4"]["valor"] >= 1
    assert k_incluye["K8"]["valor"] >= 1
    assert k_incluye["K9"]["valor"] >= 1
    assert k_incluye["K11"]["valor"] is not None

    # Las listas de K3, K4, K8, K9, K11 responden con los datos del rango
    assert len(c.get("/api/v1/kpi/K3", headers=enca, params={"desde": str(ayer), "hasta": str(hoy)}).json()["eventos"]) >= 1
    assert len(c.get("/api/v1/kpi/K4", headers=enca, params={"desde": str(ayer), "hasta": str(hoy)}).json()["eventos"]) >= 1
    assert len(c.get("/api/v1/kpi/K8", headers=enca, params={"desde": str(ayer), "hasta": str(hoy)}).json()["compromisos"]) >= 1
    assert len(c.get("/api/v1/kpi/K9", headers=enca, params={"desde": str(ayer), "hasta": str(hoy)}).json()["eventos"]) >= 1
    assert len(c.get("/api/v1/kpi/K11", headers=enca, params={"desde": str(ayer), "hasta": str(hoy)}).json()["eventos"]) >= 1

    # Rango pasado ajeno (hace un mes):
    pasado_desde = str(hoy - timedelta(days=60))
    pasado_hasta = str(hoy - timedelta(days=50))
    k_vacio = kpis(c, enca, desde=pasado_desde, hasta=pasado_hasta)
    assert k_vacio["K3"]["valor"] == 0
    assert k_vacio["K4"]["valor"] == 0
    assert k_vacio["K8"]["valor"] == 0
    assert k_vacio["K9"]["valor"] == 0
    assert k_vacio["K11"]["valor"] is None

    assert len(c.get("/api/v1/kpi/K3", headers=enca, params={"desde": pasado_desde, "hasta": pasado_hasta}).json()["eventos"]) == 0
    assert len(c.get("/api/v1/kpi/K4", headers=enca, params={"desde": pasado_desde, "hasta": pasado_hasta}).json()["eventos"]) == 0
    assert len(c.get("/api/v1/kpi/K8", headers=enca, params={"desde": pasado_desde, "hasta": pasado_hasta}).json()["compromisos"]) == 0
    assert len(c.get("/api/v1/kpi/K9", headers=enca, params={"desde": pasado_desde, "hasta": pasado_hasta}).json()["eventos"]) == 0
    assert len(c.get("/api/v1/kpi/K11", headers=enca, params={"desde": pasado_desde, "hasta": pasado_hasta}).json()["eventos"]) == 0
