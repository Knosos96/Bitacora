export const TOKEN_KEY = "bitacora_token";
export const USER_KEY = "bitacora_user";

export class ErrorApi extends Error {
  constructor(message) {
    super(message);
    this.name = "ErrorApi";
  }
}

export const PERMISOS_ADMIN = [
  "gestionar_areas",
  "gestionar_subtipos",
  "ver_usuarios",
  "crear_usuarios",
  "editar_usuarios",
  "gestionar_claves_api",
  "gestionar_roles",
];

export const TIPOS = ["solicitud", "incidencia", "tarea", "visita", "otro"];

export const ESTADOS = [
  "informativo",
  "abierto",
  "en_proceso",
  "en_espera",
  "resuelto",
  "cerrado",
  "cancelado",
];

export const ESTADOS_SIGUIENTES = {
  abierto: ["en_proceso", "en_espera", "resuelto", "cancelado"],
  en_proceso: ["en_espera", "resuelto", "cerrado", "cancelado"],
  en_espera: ["en_proceso", "resuelto", "cerrado", "cancelado"],
  resuelto: ["en_proceso", "cerrado"],
  cerrado: ["abierto"],
  informativo: [],
  cancelado: [],
};
