"""Cliente de la API de Bitácora TI. Sin interfaz: se puede probar solo."""
import httpx


class ErrorApi(Exception):
    pass


class ClienteApi:
    def __init__(self, base_url: str, http: httpx.Client | None = None):
        # `http` permite inyectar un cliente (las pruebas usan el TestClient de FastAPI).
        self.http = http or httpx.Client(base_url=base_url.rstrip("/") + "/api/v1/", timeout=10)
        self.usuario: dict | None = None

    def _pedir(self, metodo: str, ruta: str, **kw):
        try:
            r = self.http.request(metodo, ruta.lstrip("/"), **kw)
        except httpx.HTTPError as e:
            raise ErrorApi(f"No se pudo conectar con el servidor: {e}") from e
        if r.status_code >= 400:
            try:
                d = r.json().get("detail", r.text)
            except ValueError:
                d = r.text
            if isinstance(d, list):  # error de validación 422
                d = "; ".join(x.get("msg", "") for x in d)
            if isinstance(d, dict):
                d = d.get("detalle", str(d))
            raise ErrorApi(str(d))
        return r.json()

    def login(self, correo: str, clave: str) -> dict:
        d = self._pedir("POST", "/auth/login", json={"correo": correo, "clave": clave})
        self.http.headers["Authorization"] = f"Bearer {d['token']}"
        self.usuario = d["usuario"]
        return self.usuario

    def areas(self) -> list[dict]:
        return self._pedir("GET", "/areas")

    def eventos(self, desde=None, hasta=None, tipos=None, page_size=200) -> dict:
        p = {"page_size": page_size}
        if desde:
            p["desde"] = desde
        if hasta:
            p["hasta"] = hasta
        if tipos:
            p["tipo"] = tipos
        return self._pedir("GET", "/eventos", params=p)

    def evento(self, folio: str) -> dict:
        return self._pedir("GET", f"/eventos/{folio}")

    def crear_evento(self, datos: dict) -> dict:
        return self._pedir("POST", "/eventos", json=datos)

    # --- Sprint 2 ---------------------------------------------------------
    def evento_completo(self, folio: str) -> dict:
        return self._pedir("GET", f"/eventos/{folio}", params={"incluir": "seguimientos,compromisos"})

    def modificar_evento(self, folio: str, datos: dict) -> dict:
        return self._pedir("PATCH", f"/eventos/{folio}", json=datos)

    def cambiar_estado(self, folio: str, estado: str, nota: str | None = None,
                       resolver_compromisos: str | None = None) -> dict:
        cuerpo = {"estado": estado, "nota": nota or None, "resolver_compromisos": resolver_compromisos}
        return self._pedir("POST", f"/eventos/{folio}/estado", json=cuerpo)

    def agregar_nota(self, folio: str, nota: str) -> dict:
        return self._pedir("POST", f"/eventos/{folio}/seguimientos", json={"nota": nota})

    def crear_compromiso(self, folio: str, descripcion: str, fecha_limite: str, responsable_id: str | None = None) -> dict:
        cuerpo = {"descripcion": descripcion, "fecha_limite": fecha_limite, "responsable_id": responsable_id}
        return self._pedir("POST", f"/eventos/{folio}/compromisos", json=cuerpo)

    def resolver_compromiso(self, compromiso_id: str, estado: str) -> dict:
        return self._pedir("PATCH", f"/compromisos/{compromiso_id}", json={"estado": estado})

    def pendientes(self, solo_mios: bool = False, solo_vencidos: bool = False) -> dict:
        return self._pedir("GET", "/pendientes", params={"solo_mios": solo_mios, "solo_vencidos": solo_vencidos})

    # --- Sprints 3 y 4 ----------------------------------------------------
    def buscar(self, **filtros) -> dict:
        """GET /eventos con q, desde, hasta, tipo, estado, seguimiento, vencidos, area_id, responsable_id..."""
        params = {k: v for k, v in filtros.items() if v not in (None, "", [])}
        return self._pedir("GET", "/eventos", params=params)

    def evento_con_auditoria(self, folio: str) -> dict:
        return self._pedir("GET", f"/eventos/{folio}", params={"incluir": "seguimientos,compromisos,auditoria"})

    def corregir_evento(self, folio: str, cambios: dict) -> dict:
        return self._pedir("PATCH", f"/eventos/{folio}", json=cambios)

    def tablero(self, desde: str | None = None, hasta: str | None = None) -> dict:
        params = {k: v for k, v in (("desde", desde), ("hasta", hasta)) if v}
        return self._pedir("GET", "/kpi", params=params)

    def lista_kpi(self, kid: str, desde: str | None = None, hasta: str | None = None, clave: str | None = None) -> dict:
        params = {k: v for k, v in (("desde", desde), ("hasta", hasta), ("clave", clave)) if v}
        return self._pedir("GET", f"/kpi/{kid}", params=params)
