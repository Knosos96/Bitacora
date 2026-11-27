import { ClienteHttp, esc, hoy } from "./api/functions.js";
import { ESTADOS, ESTADOS_SIGUIENTES, ErrorApi, TIPOS } from "./api/models.js";
import { adminRouter } from "./api/routers/admin.js";
import { authRouter } from "./api/routers/auth.js";
import { eventosRouter } from "./api/routers/eventos.js";
import { superadminRouter } from "./api/routers/superadmin.js";

export class ClienteApi extends ClienteHttp {}

Object.assign(
  ClienteApi.prototype,
  authRouter,
  eventosRouter,
  adminRouter,
  superadminRouter,
);

export { ESTADOS, ESTADOS_SIGUIENTES, ErrorApi, TIPOS, esc, hoy };
