const TOKEN_KEY = "bitacora_token";
const USER_KEY = "bitacora_user";

export class ErrorApi extends Error {
  constructor(message) {
    super(message);
    this.name = "ErrorApi";
  }
}

export class ClienteApi {
  constructor(base = "/api/v1") {
    this.base = base.replace(/\/$/, "");
    this.token = localStorage.getItem(TOKEN_KEY);
    this.usuario = JSON.parse(localStorage.getItem(USER_KEY) || "null");
  }

  get autenticado() {
    return Boolean(this.token && this.usuario);
  }

  tienePermiso(...codigos) {
    if (!this.usuario) return false;
    const perms = this.usuario.permisos;
    if (Array.isArray(perms) && perms.length) {
      return codigos.some((c) => perms.includes(c));
    }
    return ["encargado", "jefe"].includes(this.usuario.rol);
  }

  get puedeVerTablero() {
    return this.tienePermiso("ver_kpi");
  }

  get puedeAdmin() {
    return this.tienePermiso(
      "gestionar_areas",
      "gestionar_subtipos",
      "ver_usuarios",
      "crear_usuarios",
      "editar_usuarios",
      "gestionar_claves_api",
      "gestionar_roles"
    );
  }

  get puedeExportar() {
    return this.tienePermiso("exportar_csv");
  }

  get esGestor() {
    return this.puedeVerTablero || this.puedeAdmin;
  }

  get esJefe() {
    return this.usuario?.rol === "jefe" || this.tienePermiso("gestionar_roles", "gestionar_claves_api");
  }

  get esSuperusuario() {
    return this.usuario?.rol === "superusuario";
  }

  _guardarSesion(token, usuario) {
    this.token = token;
    this.usuario = usuario;
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(usuario));
  }

  salir() {
    this.token = null;
    this.usuario = null;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  async _pedir(metodo, ruta, { json, params, raw } = {}) {
    const url = new URL(this.base + ruta, window.location.origin);
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        if (v === undefined || v === null || v === "" || v === false) continue;
        if (Array.isArray(v)) v.forEach((x) => url.searchParams.append(k, x));
        else url.searchParams.set(k, v);
      }
    }
    const headers = {};
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    if (json !== undefined) headers["Content-Type"] = "application/json";
    let r;
    try {
      r = await fetch(url, {
        method: metodo,
        headers,
        body: json !== undefined ? JSON.stringify(json) : undefined,
      });
    } catch (e) {
      throw new ErrorApi(`No se pudo conectar con el servidor: ${e.message}`);
    }
    if (r.status >= 400) {
      let d;
      try {
        const body = await r.json();
        d = body.detail ?? body;
      } catch {
        d = await r.text();
      }
      if (Array.isArray(d)) d = d.map((x) => x.msg || JSON.stringify(x)).join("; ");
      if (d && typeof d === "object") d = d.detalle || d.codigo || JSON.stringify(d);
      throw new ErrorApi(String(d));
    }
    if (raw) return r;
    if (r.status === 204) return null;
    return r.json();
  }

  async login(correo, clave) {
    const d = await this._pedir("POST", "/auth/login", { json: { correo, clave } });
    this._guardarSesion(d.token, d.usuario);
    return d.usuario;
  }

  yo() { return this._pedir("GET", "/auth/yo"); }

  async actualizarPerfil(datos) {
    const d = await this._pedir("PATCH", "/auth/perfil", { json: datos });
    this._guardarSesion(d.token, d.usuario);
    return d.usuario;
  }
  areas(incluir_inactivas = false) {
    return this._pedir("GET", "/areas", { params: { incluir_inactivas } });
  }
  crearArea(nombre) { return this._pedir("POST", "/areas", { json: { nombre } }); }
  modificarArea(id, cambios) { return this._pedir("PATCH", `/areas/${id}`, { json: cambios }); }
  eliminarArea(id) { return this._pedir("DELETE", `/areas/${id}`); }

  eventos(params = {}) { return this._pedir("GET", "/eventos", { params }); }
  crearEvento(datos) { return this._pedir("POST", "/eventos", { json: datos }); }
  evento(folio, incluir = "seguimientos,compromisos,auditoria") {
    return this._pedir("GET", `/eventos/${encodeURIComponent(folio)}`, { params: { incluir } });
  }
  modificarEvento(folio, datos) {
    return this._pedir("PATCH", `/eventos/${encodeURIComponent(folio)}`, { json: datos });
  }
  cambiarEstado(folio, estado, nota = null, resolver_compromisos = null) {
    return this._pedir("POST", `/eventos/${encodeURIComponent(folio)}/estado`, {
      json: { estado, nota, resolver_compromisos },
    });
  }
  agregarNota(folio, nota) {
    return this._pedir("POST", `/eventos/${encodeURIComponent(folio)}/seguimientos`, { json: { nota } });
  }
  crearCompromiso(folio, descripcion, fecha_limite, responsable_id = null) {
    return this._pedir("POST", `/eventos/${encodeURIComponent(folio)}/compromisos`, {
      json: { descripcion, fecha_limite, responsable_id },
    });
  }
  resolverCompromiso(id, estado) {
    return this._pedir("PATCH", `/compromisos/${id}`, { json: { estado } });
  }
  pendientes({ solo_mios = false, solo_vencidos = false } = {}) {
    return this._pedir("GET", "/pendientes", { params: { solo_mios, solo_vencidos } });
  }
  async exportarCsv(params = {}) {
    const r = await this._pedir("GET", "/eventos/exportar", { params, raw: true });
    return r.blob();
  }
  tablero(desde, hasta) {
    return this._pedir("GET", "/kpi", { params: { desde, hasta } });
  }
  listaKpi(kid, desde, hasta, clave) {
    return this._pedir("GET", `/kpi/${kid}`, { params: { desde, hasta, clave } });
  }
  subtipos(tipo, incluir_inactivos = false) {
    return this._pedir("GET", "/subtipos", { params: { tipo, incluir_inactivos } });
  }
  crearSubtipo(tipo, nombre) {
    return this._pedir("POST", "/subtipos", { json: { tipo, nombre } });
  }
  activarSubtipo(tipo, nombre, activo) {
    return this._pedir("PATCH", `/subtipos/${tipo}/${encodeURIComponent(nombre)}`, { json: { activo } });
  }
  eliminarSubtipo(tipo, nombre) {
    return this._pedir("DELETE", `/subtipos/${tipo}/${encodeURIComponent(nombre)}`);
  }
  usuarios() { return this._pedir("GET", "/usuarios"); }
  crearUsuario(datos) { return this._pedir("POST", "/usuarios", { json: datos }); }
  modificarUsuario(id, cambios) { return this._pedir("PATCH", `/usuarios/${id}`, { json: cambios }); }
  eliminarUsuario(id) { return this._pedir("DELETE", `/usuarios/${id}`); }
  clavesApi() { return this._pedir("GET", "/claves-api"); }
  crearClaveApi(nombre) { return this._pedir("POST", "/claves-api", { json: { nombre } }); }
  revocarClaveApi(id) { return this._pedir("DELETE", `/claves-api/${id}`); }
  eliminarClaveApi(id) { return this._pedir("DELETE", `/claves-api/${id}/permanente`); }
  roles(incluir_inactivos = false) {
    return this._pedir("GET", "/roles", { params: { incluir_inactivos } });
  }
  permisos() { return this._pedir("GET", "/roles/permisos"); }
  crearRol(nombre, descripcion, permisos) {
    return this._pedir("POST", "/roles", { json: { nombre, descripcion, permisos } });
  }
  editarRol(id, cambios) { return this._pedir("PATCH", `/roles/${id}`, { json: cambios }); }
  eliminarRol(id) { return this._pedir("DELETE", `/roles/${id}`); }
  asignarRol(usuario_id, rol_id = null) {
    const params = { usuario_id };
    if (rol_id) params.rol_id = rol_id;
    return this._pedir("POST", "/roles/asignar", { params });
  }

  /* --- Portal Superusuario --- */
  superResumen() { return this._pedir("GET", "/superadmin/resumen"); }
  superCuentas(params = {}) { return this._pedir("GET", "/superadmin/cuentas", { params }); }
  superExpediente(id) { return this._pedir("GET", `/superadmin/cuentas/${id}`); }
  superPurgaResumen(id) { return this._pedir("GET", `/superadmin/cuentas/${id}/purga`); }
  superPurgarCuenta(id, datos) { return this._pedir("POST", `/superadmin/cuentas/${id}/purga`, { json: datos }); }
  superRestablecerCredenciales(id, datos) { return this._pedir("POST", `/superadmin/cuentas/${id}/credenciales`, { json: datos }); }
  superRegistros(params = {}) { return this._pedir("GET", "/superadmin/registros", { params }); }
  superRegistroDetalle(folio) { return this._pedir("GET", `/superadmin/registros/${encodeURIComponent(folio)}`); }
  superPendientes(params = {}) { return this._pedir("GET", "/superadmin/pendientes", { params }); }
  superArchivos() { return this._pedir("GET", "/superadmin/archivos"); }
  superActividad(params = {}) { return this._pedir("GET", "/superadmin/actividad", { params }); }
  async superExportarCsv(params = {}) {
    const r = await this._pedir("GET", "/superadmin/exportar", { params, raw: true });
    return r.blob();
  }
}

export const TIPOS = ["solicitud", "incidencia", "tarea", "visita", "otro"];
export const ESTADOS = ["informativo", "abierto", "en_proceso", "en_espera", "resuelto", "cerrado", "cancelado"];
export const ESTADOS_SIGUIENTES = {
  abierto: ["en_proceso", "en_espera", "resuelto", "cancelado"],
  en_proceso: ["en_espera", "resuelto", "cerrado", "cancelado"],
  en_espera: ["en_proceso", "resuelto", "cerrado", "cancelado"],
  resuelto: ["en_proceso", "cerrado"],
  cerrado: ["abierto"],
  informativo: [],
  cancelado: [],
};

export function hoy() {
  return new Date().toISOString().slice(0, 10);
}

export function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

