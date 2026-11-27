export const eventosRouter = {
  eventos(params = {}) {
    return this._pedir("GET", "/eventos", { params });
  },

  crearEvento(datos) {
    return this._pedir("POST", "/eventos", { json: datos });
  },

  evento(folio, incluir = "seguimientos,compromisos,auditoria") {
    return this._pedir("GET", `/eventos/${encodeURIComponent(folio)}`, { params: { incluir } });
  },

  modificarEvento(folio, datos) {
    return this._pedir("PATCH", `/eventos/${encodeURIComponent(folio)}`, { json: datos });
  },

  cambiarEstado(folio, estado, nota = null, resolver_compromisos = null) {
    return this._pedir("POST", `/eventos/${encodeURIComponent(folio)}/estado`, {
      json: { estado, nota, resolver_compromisos },
    });
  },

  agregarNota(folio, nota) {
    return this._pedir("POST", `/eventos/${encodeURIComponent(folio)}/seguimientos`, { json: { nota } });
  },

  crearCompromiso(folio, descripcion, fecha_limite, responsable_id = null) {
    return this._pedir("POST", `/eventos/${encodeURIComponent(folio)}/compromisos`, {
      json: { descripcion, fecha_limite, responsable_id },
    });
  },

  resolverCompromiso(id, estado) {
    return this._pedir("PATCH", `/compromisos/${id}`, { json: { estado } });
  },

  pendientes({ solo_mios = false, solo_vencidos = false } = {}) {
    return this._pedir("GET", "/pendientes", { params: { solo_mios, solo_vencidos } });
  },

  async exportarCsv(params = {}) {
    const r = await this._pedir("GET", "/eventos/exportar", { params, raw: true });
    return r.blob();
  },

  tablero(desde, hasta) {
    return this._pedir("GET", "/kpi", { params: { desde, hasta } });
  },

  listaKpi(kid, desde, hasta, clave) {
    return this._pedir("GET", `/kpi/${kid}`, { params: { desde, hasta, clave } });
  },
};
