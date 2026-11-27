export const adminRouter = {
  areas(incluir_inactivas = false) {
    return this._pedir("GET", "/areas", { params: { incluir_inactivas } });
  },

  crearArea(nombre) {
    return this._pedir("POST", "/areas", { json: { nombre } });
  },

  modificarArea(id, cambios) {
    return this._pedir("PATCH", `/areas/${id}`, { json: cambios });
  },

  eliminarArea(id) {
    return this._pedir("DELETE", `/areas/${id}`);
  },

  subtipos(tipo, incluir_inactivos = false) {
    return this._pedir("GET", "/subtipos", { params: { tipo, incluir_inactivos } });
  },

  crearSubtipo(tipo, nombre) {
    return this._pedir("POST", "/subtipos", { json: { tipo, nombre } });
  },

  activarSubtipo(tipo, nombre, activo) {
    return this._pedir("PATCH", `/subtipos/${tipo}/${encodeURIComponent(nombre)}`, { json: { activo } });
  },

  eliminarSubtipo(tipo, nombre) {
    return this._pedir("DELETE", `/subtipos/${tipo}/${encodeURIComponent(nombre)}`);
  },

  usuarios() {
    return this._pedir("GET", "/usuarios");
  },

  crearUsuario(datos) {
    return this._pedir("POST", "/usuarios", { json: datos });
  },

  modificarUsuario(id, cambios) {
    return this._pedir("PATCH", `/usuarios/${id}`, { json: cambios });
  },

  eliminarUsuario(id) {
    return this._pedir("DELETE", `/usuarios/${id}`);
  },

  clavesApi() {
    return this._pedir("GET", "/claves-api");
  },

  crearClaveApi(nombre) {
    return this._pedir("POST", "/claves-api", { json: { nombre } });
  },

  revocarClaveApi(id) {
    return this._pedir("DELETE", `/claves-api/${id}`);
  },

  eliminarClaveApi(id) {
    return this._pedir("DELETE", `/claves-api/${id}/permanente`);
  },

  roles(incluir_inactivos = false) {
    return this._pedir("GET", "/roles", { params: { incluir_inactivos } });
  },

  permisos() {
    return this._pedir("GET", "/roles/permisos");
  },

  crearRol(nombre, descripcion, permisos) {
    return this._pedir("POST", "/roles", { json: { nombre, descripcion, permisos } });
  },

  editarRol(id, cambios) {
    return this._pedir("PATCH", `/roles/${id}`, { json: cambios });
  },

  eliminarRol(id) {
    return this._pedir("DELETE", `/roles/${id}`);
  },

  asignarRol(usuario_id, rol_id = null) {
    const params = { usuario_id };
    if (rol_id) params.rol_id = rol_id;
    return this._pedir("POST", "/roles/asignar", { params });
  },
};
