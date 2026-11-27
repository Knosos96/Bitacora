import { ClienteApi, esc } from "./services/api.js";
import { $, $$, cerrarModal, iniciales } from "./components/ui.js";
import { vistaHoy } from "./views/hoy.js";
import { abrirDetalle } from "./views/detalle.js";
import { vistaPendientes } from "./views/pendientes.js";
import { vistaBusqueda } from "./views/busqueda.js";
import { vistaTablero } from "./views/tablero.js";
import { vistaAdmin } from "./views/admin.js";
import { vistaSuperadmin } from "./views/superadmin.js";

const api = new ClienteApi();

/* ---------- Menú móvil ---------- */
function cerrarMenuMovil() {
  const drawer = $("#mobile-drawer");
  const btn = $("#btn-menu");
  if (!drawer || !btn) return;
  drawer.classList.add("hidden");
  btn.setAttribute("aria-expanded", "false");
}

$("#btn-menu")?.addEventListener("click", () => {
  const drawer = $("#mobile-drawer");
  const abierto = !drawer.classList.contains("hidden");
  drawer.classList.toggle("hidden", abierto);
  $("#btn-menu").setAttribute("aria-expanded", String(!abierto));
});

/* ---------- Shell y sesión ---------- */
function mostrarLogin() {
  cerrarMenuMovil();
  document.body.classList.remove("mode-superadmin");
  $("#vista-login").classList.remove("hidden");
  $("#vista-app").classList.add("hidden");
}

function sincronizarCabeceraUsuario() {
  const u = api.usuario;
  if (!u) return;
  const etiqueta = `${u.nombre} · ${u.rol_custom_nombre || u.rol}`;
  const ini = iniciales(u.nombre);
  $("#user-chip").textContent = etiqueta;
  $("#user-avatar").textContent = ini;
  $("#user-chip-mobile").textContent = etiqueta;
  $("#user-avatar-mobile").textContent = ini;
}

function mostrarApp() {
  $("#vista-login").classList.add("hidden");
  $("#vista-app").classList.remove("hidden");
  const esSuper = api.esSuperusuario;

  document.body.classList.toggle("mode-superadmin", esSuper);
  $("#super-mode-pill")?.classList.toggle("hidden", !esSuper);
  $("#brand-title").textContent = esSuper ? "Superusuario" : "Bitácora TI";
  $("#footer-label").textContent = esSuper
    ? "ZGROUP · Portal Documental y de Auditoría (Superusuario)"
    : "Bitácora TI · Gestión operativa";

  sincronizarCabeceraUsuario();

  $$(".solo-operativo").forEach((el) => el.classList.toggle("hidden", esSuper));
  $$(".solo-super").forEach((el) => el.classList.toggle("hidden", !esSuper));

  if (!esSuper) {
    $$(".solo-gestor").forEach((el) => el.classList.toggle("hidden", !api.esGestor));
    $$(".solo-tablero").forEach((el) => el.classList.toggle("hidden", !api.puedeVerTablero));
    $$(".solo-admin").forEach((el) => el.classList.toggle("hidden", !api.puedeAdmin));
    actualizarAviso();
  } else {
    $("#aviso-vencidos").classList.add("hidden");
    if (!location.hash.startsWith("#/super")) {
      location.hash = "#/super/resumen";
    }
  }
  enrutar();
}

async function actualizarAviso() {
  if (api.esSuperusuario) return;
  const el = $("#aviso-vencidos");
  try {
    const r = await api.pendientes({ solo_vencidos: true });
    const n = r.compromisos.length;
    if (n) {
      el.textContent = `Tienes ${n} compromiso(s) vencido(s) — haz clic aquí para revisarlos`;
      el.classList.remove("hidden");
    } else {
      el.classList.add("hidden");
    }
  } catch {
    el.classList.add("hidden");
  }
}

$("#aviso-vencidos").addEventListener("click", () => {
  location.hash = "#/pendientes?vencidos=1";
});

$("#aviso-vencidos").addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    location.hash = "#/pendientes?vencidos=1";
  }
});

$("#form-login").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const err = $("#login-error");
  const btn = e.target.querySelector('[type="submit"]');
  err.hidden = true;
  btn.disabled = true;
  try {
    await api.login(fd.get("correo"), fd.get("clave"));
    mostrarApp();
  } catch (ex) {
    err.textContent = ex.message;
    err.hidden = false;
  } finally {
    btn.disabled = false;
  }
});

const cerrarSesion = () => {
  api.salir();
  location.hash = "#/";
  mostrarLogin();
};

$("#btn-salir").addEventListener("click", cerrarSesion);
$("#btn-salir-mobile").addEventListener("click", cerrarSesion);

/* ---------- Eventos de modal y tabla ---------- */
$("#modal").addEventListener("click", (e) => {
  if (e.target.matches("[data-close-modal]")) cerrarModal();
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    cerrarModal();
    cerrarMenuMovil();
  }
});

document.addEventListener("click", (e) => {
  const tr = e.target.closest("tr[data-folio]");
  if (tr && !api.esSuperusuario) abrirDetalle(tr.dataset.folio, ctx);
});

/* ---------- Enrutador hash ---------- */
const refrescarFondo = async () => {
  const { path } = ruta();
  if (path.startsWith("/evento/")) {
    await vistaHoy($("#contenido"), ctx);
    return;
  }
  await enrutar();
};

const ctx = {
  api,
  actualizarAviso,
  enrutar: refrescarFondo,
  refrescarUsuario: sincronizarCabeceraUsuario,
};

window.addEventListener("hashchange", enrutar);

function ruta() {
  const raw = location.hash.replace(/^#/, "") || "/";
  const [path, qs] = raw.split("?");
  return { path: path || "/", params: new URLSearchParams(qs || "") };
}

async function enrutar() {
  cerrarMenuMovil();
  if (!api.autenticado) {
    mostrarLogin();
    return;
  }
  const { path, params } = ruta();
  $$("[data-nav]").forEach((a) => {
    const href = a.getAttribute("href").replace(/^#/, "") || "/";
    a.classList.toggle("active", href === path || (href !== "/" && path.startsWith(href)));
  });

  const box = $("#contenido");
  box.innerHTML = `<div class="panel"><p class="muted" style="margin:0">Cargando vista…</p></div>`;
  try {
    if (api.esSuperusuario) {
      const rutaSuper = path.startsWith("/super") ? path : "/super/resumen";
      await vistaSuperadmin(box, rutaSuper, ctx);
    } else if (path === "/" || path === "") await vistaHoy(box, ctx);
    else if (path === "/pendientes") await vistaPendientes(box, params, ctx);
    else if (path === "/busqueda") await vistaBusqueda(box, params, ctx);
    else if (path === "/tablero") await vistaTablero(box, ctx);
    else if (path === "/admin") await vistaAdmin(box, ctx);
    else if (path.startsWith("/evento/")) {
      await vistaHoy(box, ctx);
      await abrirDetalle(decodeURIComponent(path.slice("/evento/".length)), ctx);
    } else {
      box.innerHTML = `<div class="panel"><p class="muted" style="margin:0">Ruta no encontrada.</p></div>`;
    }
  } catch (ex) {
    box.innerHTML = `<div class="panel"><p class="alert-inline error">${esc(ex.message)}</p></div>`;
  }
  actualizarAviso();
}

/* ---------- Arranque ---------- */
(async function boot() {
  if (api.autenticado) {
    try {
      api.usuario = await api.yo();
      localStorage.setItem("bitacora_user", JSON.stringify(api.usuario));
      mostrarApp();
      return;
    } catch {
      api.salir();
    }
  }
  mostrarLogin();
})();
