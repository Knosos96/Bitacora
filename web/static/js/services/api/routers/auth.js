export const authRouter = {
  async login(correo, clave) {
    const d = await this._pedir("POST", "/auth/login", { json: { correo, clave } });
    this._guardarSesion(d.token, d.usuario);
    return d.usuario;
  },

  yo() {
    return this._pedir("GET", "/auth/yo");
  },

  async actualizarPerfil(datos) {
    const d = await this._pedir("PATCH", "/auth/perfil", { json: datos });
    this._guardarSesion(d.token, d.usuario);
    return d.usuario;
  },
};
