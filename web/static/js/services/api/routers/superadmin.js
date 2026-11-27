export const superadminRouter = {
  superResumen() {
    return this._pedir("GET", "/superadmin/resumen");
  },

  superCuentas(params = {}) {
    return this._pedir("GET", "/superadmin/cuentas", { params });
  },

  superExpediente(id) {
    return this._pedir("GET", `/superadmin/cuentas/${id}`);
  },

  superPurgaResumen(id) {
    return this._pedir("GET", `/superadmin/cuentas/${id}/purga`);
  },

  superPurgarCuenta(id, datos) {
    return this._pedir("POST", `/superadmin/cuentas/${id}/purga`, { json: datos });
  },

  superRestablecerCredenciales(id, datos) {
    return this._pedir("POST", `/superadmin/cuentas/${id}/credenciales`, { json: datos });
  },

  superRegistros(params = {}) {
    return this._pedir("GET", "/superadmin/registros", { params });
  },

  superRegistroDetalle(folio) {
    return this._pedir("GET", `/superadmin/registros/${encodeURIComponent(folio)}`);
  },

  superPendientes(params = {}) {
    return this._pedir("GET", "/superadmin/pendientes", { params });
  },

  superArchivos() {
    return this._pedir("GET", "/superadmin/archivos");
  },

  superActividad(params = {}) {
    return this._pedir("GET", "/superadmin/actividad", { params });
  },

  async superExportarCsv(params = {}) {
    const r = await this._pedir("GET", "/superadmin/exportar", { params, raw: true });
    return r.blob();
  },
};
