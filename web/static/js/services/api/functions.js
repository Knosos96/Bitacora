import { ErrorApi, PERMISOS_ADMIN, TOKEN_KEY, USER_KEY } from "./models.js";

export class ClienteHttp {
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
    return this.tienePermiso(...PERMISOS_ADMIN);
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
}

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
