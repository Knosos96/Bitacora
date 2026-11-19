import {
  ClienteApi, ErrorApi, TIPOS, ESTADOS, ESTADOS_SIGUIENTES, hoy, esc,
} from "./api.js";

const api = new ClienteApi();
const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.add("hidden"), 3200);
}

function badge(estado) {
  return `<span class="badge ${esc(estado)}">${esc(estado)}</span>`;
}

function nombre(ref) {
  return ref?.nombre || "—";
}

/* ---------- shell ---------- */
function mostrarLogin() {
  $("#vista-login").classList.remove("hidden");
  $("#vista-app").classList.add("hidden");
}

function mostrarApp() {
  $("#vista-login").classList.add("hidden");
  $("#vista-app").classList.remove("hidden");
  const u = api.usuario;
  $("#user-chip").textContent = `${u.nombre} · ${u.rol_custom_nombre || u.rol}`;
  $$(".solo-gestor").forEach((el) => el.classList.toggle("hidden", !api.esGestor));
  actualizarAviso();
  enrutar();
}

async function actualizarAviso() {
  const el = $("#aviso-vencidos");
  try {
    const r = await api.pendientes({ solo_vencidos: true });
    const n = r.compromisos.length;
    if (n) {
      el.textContent = `${n} compromiso(s) vencido(s) — clic para verlos`;
      el.classList.remove("hidden");
    } else el.classList.add("hidden");
  } catch {
    el.classList.add("hidden");
  }
}

$("#aviso-vencidos").addEventListener("click", () => {
  location.hash = "#/pendientes?vencidos=1";
});

$("#form-login").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const err = $("#login-error");
  err.hidden = true;
  try {
    await api.login(fd.get("correo"), fd.get("clave"));
    mostrarApp();
  } catch (ex) {
    err.textContent = ex.message;
    err.hidden = false;
  }
});

$("#btn-salir").addEventListener("click", () => {
  api.salir();
  location.hash = "#/";
  mostrarLogin();
});

/* ---------- modal ---------- */
function abrirModal(html) {
  const m = $("#modal");
  $("#modal-panel").innerHTML = html;
  m.classList.remove("hidden");
  document.body.style.overflow = "hidden";
}
function cerrarModal() {
  $("#modal").classList.add("hidden");
  $("#modal-panel").innerHTML = "";
  document.body.style.overflow = "";
}
$("#modal").addEventListener("click", (e) => {
  if (e.target.matches("[data-close-modal]")) cerrarModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") cerrarModal();
});

/* ---------- router ---------- */
window.addEventListener("hashchange", enrutar);

function ruta() {
  const raw = location.hash.replace(/^#/, "") || "/";
  const [path, qs] = raw.split("?");
  return { path: path || "/", params: new URLSearchParams(qs || "") };
}

async function enrutar() {
  if (!api.autenticado) {
    mostrarLogin();
    return;
  }
  const { path, params } = ruta();
  $$(".nav a").forEach((a) => {
    const href = a.getAttribute("href").replace(/^#/, "") || "/";
    a.classList.toggle("active", href === path || (href !== "/" && path.startsWith(href)));
  });
  const box = $("#contenido");
  box.innerHTML = `<p class="muted">Cargando…</p>`;
  try {
    if (path === "/" || path === "") await vistaHoy(box);
    else if (path === "/pendientes") await vistaPendientes(box, params);
    else if (path === "/busqueda") await vistaBusqueda(box, params);
    else if (path === "/tablero") await vistaTablero(box);
    else if (path === "/admin") await vistaAdmin(box);
    else if (path.startsWith("/evento/")) {
      await vistaHoy(box);
      await abrirDetalle(decodeURIComponent(path.slice("/evento/".length)));
    } else box.innerHTML = `<p>Ruta no encontrada.</p>`;
  } catch (ex) {
    box.innerHTML = `<p class="error">${esc(ex.message)}</p>`;
  }
  actualizarAviso();
}

/* ---------- Hoy ---------- */
async function vistaHoy(box) {
  const d = hoy();
  const [areas, eventos] = await Promise.all([
    api.areas(),
    api.eventos({ desde: d, hasta: d, page_size: 200 }),
  ]);
  box.innerHTML = `
    <div class="row spread" style="margin-bottom:1rem">
      <h1 class="section-title" style="margin:0">Hoy</h1>
      <span class="muted">${esc(eventos.meta.total)} evento(s)</span>
    </div>
    <div class="panel" style="margin-bottom:1rem">
      <h2>Nuevo evento</h2>
      <form id="form-alta" class="stack">
        <div class="grid-2">
          <label>Tipo
            <select name="tipo">${TIPOS.map((t) => `<option value="${t}">${t}</option>`).join("")}</select>
          </label>
          <label>Subtipo<select name="subtipo"><option value="">—</option></select></label>
          <label>Área
            <select name="area_id">
              <option value="">—</option>
              ${areas.map((a) => `<option value="${a.id}">${esc(a.nombre)}</option>`).join("")}
            </select>
          </label>
          <label>Solicitante<input name="solicitante_nombre" /></label>
        </div>
        <label>Título<input name="titulo" required maxlength="200" /></label>
        <label>Texto<textarea name="descripcion" required></textarea></label>
        <label class="row"><input type="checkbox" name="requiere_seguimiento" /> Requiere seguimiento</label>
        <div class="row"><button class="btn primary" type="submit">Guardar</button></div>
      </form>
    </div>
    <div class="panel">
      <div class="row spread">
        <h2 style="margin:0">Eventos de hoy</h2>
        <div class="row">
          <input type="date" id="filtro-desde" value="${d}" />
          <input type="date" id="filtro-hasta" value="${d}" />
          <select id="filtro-tipo">
            <option value="">todos</option>
            ${TIPOS.map((t) => `<option>${t}</option>`).join("")}
          </select>
          <button type="button" class="btn" id="btn-filtrar">Buscar</button>
          <button type="button" class="btn ghost" id="btn-hoy">Hoy</button>
        </div>
      </div>
      <div id="lista-hoy" style="margin-top:0.75rem"></div>
    </div>`;

  const pintar = (r) => {
    $("#lista-hoy").innerHTML = tablaEventos(r.data);
    box.querySelector(".muted") && (box.querySelector(".row.spread .muted").textContent = `${r.meta.total} evento(s)`);
  };
  pintar(eventos);
  await cargarSubtipos($("#form-alta [name=tipo]").value, $("#form-alta [name=subtipo]"));

  $("#form-alta [name=tipo]").addEventListener("change", async (e) => {
    await cargarSubtipos(e.target.value, $("#form-alta [name=subtipo]"));
  });
  $("#form-alta").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const ev = await api.crearEvento({
        tipo: fd.get("tipo"),
        subtipo: fd.get("subtipo") || null,
        titulo: fd.get("titulo").trim(),
        descripcion: fd.get("descripcion").trim(),
        area_id: fd.get("area_id") || null,
        solicitante_nombre: fd.get("solicitante_nombre").trim() || null,
        requiere_seguimiento: fd.get("requiere_seguimiento") === "on",
      });
      toast(`Guardado: ${ev.folio}`);
      e.target.reset();
      await cargarSubtipos(TIPOS[0], $("#form-alta [name=subtipo]"));
      const r = await api.eventos({ desde: hoy(), hasta: hoy(), page_size: 200 });
      pintar(r);
      actualizarAviso();
    } catch (ex) {
      toast(ex.message);
    }
  });
  const recargarFiltro = async () => {
    const params = {
      desde: $("#filtro-desde").value || undefined,
      hasta: $("#filtro-hasta").value || undefined,
      tipo: $("#filtro-tipo").value || undefined,
      page_size: 200,
    };
    pintar(await api.eventos(params));
  };
  $("#btn-filtrar").onclick = recargarFiltro;
  $("#btn-hoy").onclick = () => {
    $("#filtro-desde").value = hoy();
    $("#filtro-hasta").value = hoy();
    $("#filtro-tipo").value = "";
    recargarFiltro();
  };
}

function tablaEventos(filas, { fragmento = false } = {}) {
  if (!filas.length) return `<p class="muted">Sin eventos.</p>`;
  return `<div class="table-wrap"><table class="data">
    <thead><tr>
      <th>Folio</th><th>Fecha</th><th>Tipo</th><th>Título</th><th>Estado</th><th>Responsable</th>
      ${fragmento ? "<th>Coincidencia</th>" : ""}
    </tr></thead>
    <tbody>
      ${filas.map((e) => `<tr data-folio="${esc(e.folio)}">
        <td>${esc(e.folio)}</td>
        <td>${esc(e.fecha_hecho)}</td>
        <td>${esc(e.tipo)}${e.subtipo ? " / " + esc(e.subtipo) : ""}</td>
        <td>${esc(e.titulo)}</td>
        <td>${badge(e.estado)}</td>
        <td>${esc(nombre(e.responsable))}</td>
        ${fragmento ? `<td class="muted">${esc(e.fragmento || "")}</td>` : ""}
      </tr>`).join("")}
    </tbody></table></div>`;
}

document.addEventListener("click", (e) => {
  const tr = e.target.closest("tr[data-folio]");
  if (tr) abrirDetalle(tr.dataset.folio);
});

async function cargarSubtipos(tipo, select) {
  try {
    const lista = await api.subtipos(tipo);
    select.innerHTML = `<option value="">—</option>` + lista.map((s) =>
      `<option value="${esc(s.nombre)}">${esc(s.nombre)}</option>`).join("");
  } catch {
    select.innerHTML = `<option value="">—</option>`;
  }
}

/* ---------- Detalle ---------- */
async function abrirDetalle(folio) {
  let e;
  try {
    e = await api.evento(folio);
  } catch (ex) {
    toast(ex.message);
    return;
  }
  const siguientes = ESTADOS_SIGUIENTES[e.estado] || [];
  abrirModal(`
    <div class="row spread">
      <h2>${esc(e.folio)}</h2>
      <button type="button" class="btn ghost" data-close-modal>Cerrar</button>
    </div>
    <div class="ficha" id="ficha-texto"></div>
    <div class="row" style="margin:0.75rem 0">
      <select id="det-estado">
        <option value="">Cambiar estado…</option>
        ${siguientes.map((s) => `<option value="${s}">${s}</option>`).join("")}
      </select>
      <button type="button" class="btn" id="det-cambiar">Aplicar</button>
      <button type="button" class="btn" id="det-seg">${e.requiere_seguimiento ? "Quitar seguimiento" : "Activar seguimiento"}</button>
      <button type="button" class="btn" id="det-corregir">Corregir datos</button>
      <button type="button" class="btn ghost" id="det-auditoria">Auditoría</button>
    </div>
    <h3>Historial de notas</h3>
    <div class="notas" id="det-notas"></div>
    <form id="det-nota-form" class="row" style="margin:0.5rem 0 1rem">
      <input id="det-nota" placeholder="Nueva nota" style="flex:1" />
      <button class="btn primary" type="submit">Agregar</button>
    </form>
    <h3>Compromisos</h3>
    <div id="det-comps"></div>
    <form id="det-comp-form" class="row" style="margin-top:0.5rem">
      <input id="det-comp-desc" placeholder="Compromiso" style="flex:1" />
      <input type="date" id="det-comp-fecha" value="${hoy()}" />
      <button class="btn" type="submit">Agregar</button>
    </form>
  `);

  const pintarFicha = (ev) => {
    $("#ficha-texto").textContent = [
      `${ev.folio}  ·  ${ev.tipo}${ev.subtipo ? " / " + ev.subtipo : ""}`,
      `Fecha del hecho: ${ev.fecha_hecho}`,
      `Estado: ${ev.estado}${ev.prioridad ? "   Prioridad: " + ev.prioridad : ""}`,
      `Área: ${nombre(ev.area_origen)}   Solicitante: ${ev.solicitante || "—"}`,
      `Registró: ${ev.autor.nombre}   Responsable: ${nombre(ev.responsable)}`,
      `Referencia: ${ev.referencia || "—"}`,
      "",
      ev.titulo,
      "",
      ev.descripcion,
    ].join("\n");
    $("#det-notas").textContent = (ev.seguimientos || []).map((n) =>
      `[${(n.creado_en || "").slice(0, 16).replace("T", " ")}] ${n.autor.nombre}: ${n.nota}`
    ).join("\n") || "Sin notas.";
    const comps = ev.compromisos || [];
    $("#det-comps").innerHTML = comps.length
      ? `<div class="table-wrap"><table class="data">
          <thead><tr><th>Fecha</th><th>Compromiso</th><th>Resp.</th><th>Estado</th><th></th></tr></thead>
          <tbody>${comps.map((c) => `<tr>
            <td>${esc(c.fecha_limite)}</td>
            <td>${esc(c.descripcion)}</td>
            <td>${esc(c.responsable.nombre)}</td>
            <td>${c.vencido ? badge("VENCIDO") : badge(c.estado)}</td>
            <td>${c.estado === "pendiente" ? `
              <button type="button" class="btn" data-comp="${c.id}" data-acc="cumplido">Cumplir</button>
              <button type="button" class="btn danger" data-comp="${c.id}" data-acc="cancelado">Cancelar</button>` : ""}</td>
          </tr>`).join("")}</tbody></table></div>`
      : `<p class="muted">Sin compromisos.</p>`;
  };
  pintarFicha(e);

  const refrescar = async () => {
    e = await api.evento(folio);
    pintarFicha(e);
    const sig = ESTADOS_SIGUIENTES[e.estado] || [];
    $("#det-estado").innerHTML = `<option value="">Cambiar estado…</option>` +
      sig.map((s) => `<option value="${s}">${s}</option>`).join("");
    $("#det-seg").textContent = e.requiere_seguimiento ? "Quitar seguimiento" : "Activar seguimiento";
    actualizarAviso();
    enrutar();
  };

  $("#det-cambiar").onclick = async () => {
    const estado = $("#det-estado").value;
    if (!estado) return;
    const pide = e.estado === "cerrado"
      ? "Motivo de la reapertura (obligatorio):"
      : "Nota del cambio (obligatoria para en_espera / cierre con atajo):";
    const nota = prompt(pide) || "";
    try {
      try {
        await api.cambiarEstado(folio, estado, nota || null);
      } catch (ex) {
        if (/compromiso/i.test(ex.message) && /pendiente/i.test(ex.message)) {
          const op = confirm(`${ex.message}\n\nAceptar = marcarlos cumplidos · Cancelar = cancelarlos`);
          await api.cambiarEstado(folio, estado, nota || null, op ? "cumplir" : "cancelar");
        } else throw ex;
      }
      await refrescar();
      toast("Estado actualizado");
    } catch (ex) {
      toast(ex.message);
    }
  };

  $("#det-seg").onclick = async () => {
    try {
      await api.modificarEvento(folio, { requiere_seguimiento: !e.requiere_seguimiento });
      await refrescar();
    } catch (ex) { toast(ex.message); }
  };

  $("#det-auditoria").onclick = () => {
    const filas = e.auditoria || [];
    if (!filas.length) return toast("Este evento no tiene correcciones.");
    alert(filas.map((a) =>
      `[${(a.creado_en || "").slice(0, 16).replace("T", " ")}] ${a.usuario.nombre}: ${a.campo} «${a.valor_anterior || "—"}» → «${a.valor_nuevo || "—"}»`
    ).join("\n"));
  };

  $("#det-corregir").onclick = () => {
    const campos = [
      ["titulo", "Título", e.titulo],
      ["descripcion", "Descripción", e.descripcion],
      ["referencia", "Referencia", e.referencia || ""],
      ["solicitante_nombre", "Solicitante", e.solicitante || ""],
      ["fecha_hecho", "Fecha del hecho", e.fecha_hecho],
      ["subtipo", "Subtipo", e.subtipo || ""],
    ];
    abrirModal(`
      <div class="row spread"><h2>Corregir ${esc(folio)}</h2>
        <button type="button" class="btn ghost" id="corr-volver">Volver</button></div>
      <form id="form-corregir" class="stack">
        ${campos.map(([k, lab, val]) =>
          `<label>${lab}<input name="${k}" value="${esc(val)}" /></label>`).join("")}
        <p class="muted">El autor corrige el mismo día; después, encargado o jefe.</p>
        <button class="btn primary" type="submit">Guardar</button>
      </form>`);
    $("#corr-volver").onclick = () => abrirDetalle(folio);
    $("#form-corregir").onsubmit = async (ev) => {
      ev.preventDefault();
      const fd = new FormData(ev.target);
      const cambios = {};
      const antes = {
        titulo: e.titulo, descripcion: e.descripcion, referencia: e.referencia || "",
        solicitante_nombre: e.solicitante || "", fecha_hecho: e.fecha_hecho, subtipo: e.subtipo || "",
      };
      for (const k of Object.keys(antes)) {
        const nuevo = String(fd.get(k) || "").trim();
        if (nuevo !== String(antes[k] || "")) cambios[k] = nuevo || null;
      }
      if (!Object.keys(cambios).length) return abrirDetalle(folio);
      try {
        await api.modificarEvento(folio, cambios);
        toast("Corregido");
        await abrirDetalle(folio);
      } catch (ex) { toast(ex.message); }
    };
  };

  $("#det-nota-form").onsubmit = async (ev) => {
    ev.preventDefault();
    const nota = $("#det-nota").value.trim();
    if (!nota) return;
    try {
      await api.agregarNota(folio, nota);
      $("#det-nota").value = "";
      await refrescar();
    } catch (ex) { toast(ex.message); }
  };

  $("#det-comp-form").onsubmit = async (ev) => {
    ev.preventDefault();
    const desc = $("#det-comp-desc").value.trim();
    if (!desc) return;
    try {
      await api.crearCompromiso(folio, desc, $("#det-comp-fecha").value);
      $("#det-comp-desc").value = "";
      await refrescar();
    } catch (ex) { toast(ex.message); }
  };

  $("#det-comps").onclick = async (ev) => {
    const btn = ev.target.closest("[data-comp]");
    if (!btn) return;
    try {
      await api.resolverCompromiso(btn.dataset.comp, btn.dataset.acc);
      await refrescar();
    } catch (ex) { toast(ex.message); }
  };
}

/* ---------- Pendientes ---------- */
async function vistaPendientes(box, params) {
  const soloVencidos = params.get("vencidos") === "1";
  box.innerHTML = `
    <h1 class="section-title">Pendientes</h1>
    <div class="panel">
      <label class="row"><input type="checkbox" id="pen-venc" ${soloVencidos ? "checked" : ""} /> Solo vencidos</label>
      <div id="pen-ev" style="margin-top:0.75rem"></div>
      <h3 style="margin-top:1rem">Compromisos pendientes</h3>
      <div id="pen-co"></div>
    </div>`;
  const cargar = async () => {
    const r = await api.pendientes({ solo_vencidos: $("#pen-venc").checked });
    $("#pen-ev").innerHTML = `<h3>Eventos con seguimiento</h3>` + tablaEventos(r.eventos);
    $("#pen-co").innerHTML = r.compromisos.length
      ? `<div class="table-wrap"><table class="data">
          <thead><tr><th>Fecha</th><th>Evento</th><th>Compromiso</th><th>Resp.</th><th></th></tr></thead>
          <tbody>${r.compromisos.map((c) => `<tr data-folio="${esc(c.evento_folio)}">
            <td>${esc(c.fecha_limite)}</td><td>${esc(c.evento_folio)}</td>
            <td>${esc(c.descripcion)}</td><td>${esc(c.responsable.nombre)}</td>
            <td>${c.vencido ? badge("VENCIDO") : ""}</td>
          </tr>`).join("")}</tbody></table></div>`
      : `<p class="muted">Sin compromisos pendientes.</p>`;
  };
  $("#pen-venc").onchange = cargar;
  await cargar();
}

/* ---------- Búsqueda ---------- */
async function vistaBusqueda(box) {
  box.innerHTML = `
    <h1 class="section-title">Búsqueda</h1>
    <div class="panel stack">
      <div class="row">
        <input id="bq-q" placeholder="Texto o folio" style="flex:1;min-width:180px" />
        <select id="bq-tipo"><option value="">tipo</option>${TIPOS.map((t) => `<option>${t}</option>`).join("")}</select>
        <select id="bq-estado"><option value="">estado</option>${ESTADOS.map((t) => `<option>${t}</option>`).join("")}</select>
        <select id="bq-seg"><option value="">seguimiento</option><option value="con">con</option><option value="sin">sin</option></select>
        <label class="row"><input type="checkbox" id="bq-venc" /> Vencidos</label>
        <button type="button" class="btn primary" id="bq-btn">Buscar</button>
        ${api.esGestor ? `<button type="button" class="btn" id="bq-csv">Exportar CSV</button>` : ""}
      </div>
      <div class="row">
        <label>Desde <input type="date" id="bq-desde" /></label>
        <label>Hasta <input type="date" id="bq-hasta" /></label>
        <span class="muted">Sin fechas y con filtros se busca en todo el histórico.</span>
        <span id="bq-total" class="muted" style="margin-left:auto"></span>
      </div>
      <div id="bq-res"></div>
    </div>`;

  const filtros = () => ({
    q: $("#bq-q").value.trim() || undefined,
    desde: $("#bq-desde").value || undefined,
    hasta: $("#bq-hasta").value || undefined,
    tipo: $("#bq-tipo").value || undefined,
    estado: $("#bq-estado").value || undefined,
    seguimiento: $("#bq-seg").value || undefined,
    vencidos: $("#bq-venc").checked || undefined,
    page_size: 200,
  });

  const buscar = async () => {
    try {
      const r = await api.eventos(filtros());
      $("#bq-res").innerHTML = tablaEventos(r.data, { fragmento: true });
      const n = r.meta.total;
      $("#bq-total").textContent = `${n} resultado(s)` + (n > 200 ? " — mostrando 200" : "");
    } catch (ex) { toast(ex.message); }
  };
  $("#bq-btn").onclick = buscar;
  $("#bq-q").addEventListener("keydown", (e) => { if (e.key === "Enter") buscar(); });
  if ($("#bq-csv")) {
    $("#bq-csv").onclick = async () => {
      try {
        const blob = await api.exportarCsv(filtros());
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "bitacora.csv";
        a.click();
        URL.revokeObjectURL(a.href);
        toast("CSV descargado");
      } catch (ex) { toast(ex.message); }
    };
  }
}

/* ---------- Tablero ---------- */
function detalleKpi(i) {
  const d = i.detalle || {};
  if (i.id === "K1") return Object.entries(d.por_tipo || {}).map(([t, n]) => `${t} ${n}`).join(", ");
  if (i.id === "K2") return `con ${d.con_seguimiento} · info ${d.informativos}`;
  if (i.id === "K5") return `${d.cerrados} cerrados`;
  if (i.id === "K7") return `${d.cumplidos_a_tiempo} de ${d.total} a tiempo`;
  if (i.id === "K9") return (d.por_responsable || []).map((p) => `${p.nombre} ${p.abiertos}`).join(", ");
  if (i.id === "K10") return (d.top || []).map((a) => `${a.nombre} ${a.total}`).join(", ");
  if (i.id === "K11" && d.folio) return `${d.folio} — ${d.titulo}`;
  return "";
}

async function vistaTablero(box) {
  if (!api.esGestor) {
    box.innerHTML = `<p class="error">El tablero es para encargado y jefe.</p>`;
    return;
  }
  box.innerHTML = `
    <h1 class="section-title">Tablero</h1>
    <div class="panel">
      <div class="row">
        <input type="date" id="tb-desde" />
        <input type="date" id="tb-hasta" />
        <button type="button" class="btn" id="tb-semana">Esta semana</button>
        <button type="button" class="btn" id="tb-hoy">Hoy</button>
        <button type="button" class="btn" id="tb-mes">Este mes</button>
        <button type="button" class="btn primary" id="tb-aplicar">Aplicar</button>
        <span id="tb-info" class="muted" style="margin-left:auto"></span>
      </div>
      <p class="muted" style="margin:0.75rem 0">K3, K4, K8, K9 y K11 son del momento y no dependen del rango.</p>
      <div class="kpi-grid" id="tb-grid"></div>
    </div>`;

  let rango = [null, null];
  const cargar = async () => {
    const desde = $("#tb-desde").value || undefined;
    const hasta = $("#tb-hasta").value || undefined;
    const r = await api.tablero(desde, hasta);
    rango = [r.desde, r.hasta];
    $("#tb-info").textContent = `Rango ${r.desde} a ${r.hasta}`;
    $("#tb-grid").innerHTML = r.indicadores.map((i) => {
      const valor = i.valor == null ? "sin datos" : `${i.valor}${i.unidad ? " " + i.unidad : ""}`;
      return `<article class="kpi-card" data-kid="${i.id}">
        <div class="id">${i.id}</div>
        <div>${esc(i.nombre)}</div>
        <div class="val">${esc(valor)}</div>
        <div class="det">${esc(detalleKpi(i))}</div>
      </article>`;
    }).join("");
  };
  $("#tb-semana").onclick = () => { $("#tb-desde").value = ""; $("#tb-hasta").value = ""; cargar(); };
  $("#tb-hoy").onclick = () => { $("#tb-desde").value = hoy(); $("#tb-hasta").value = hoy(); cargar(); };
  $("#tb-mes").onclick = () => {
    const d = new Date();
    $("#tb-desde").value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
    $("#tb-hasta").value = hoy();
    cargar();
  };
  $("#tb-aplicar").onclick = cargar;
  $("#tb-grid").onclick = async (e) => {
    const card = e.target.closest("[data-kid]");
    if (!card) return;
    try {
      const r = await api.listaKpi(card.dataset.kid, rango[0], rango[1]);
      abrirModal(`
        <div class="row spread"><h2>${esc(card.dataset.kid)} — ${esc(r.nombre)}</h2>
          <button type="button" class="btn ghost" data-close-modal>Cerrar</button></div>
        ${(!r.eventos.length && !r.compromisos.length)
          ? `<p class="muted">${esc(r.texto_vacio || "Sin resultados")}</p>`
          : tablaEventos(r.eventos) + (r.compromisos.length ? `
            <h3 style="margin-top:1rem">Compromisos</h3>
            <div class="table-wrap"><table class="data">
              <thead><tr><th>Evento</th><th>Compromiso</th><th>Estado</th><th>Fecha</th></tr></thead>
              <tbody>${r.compromisos.map((c) => `<tr data-folio="${esc(c.evento_folio)}">
                <td>${esc(c.evento_folio)}</td><td>${esc(c.descripcion)}</td>
                <td>${c.vencido ? badge("VENCIDO") : badge(c.estado)}</td>
                <td>${esc(c.fecha_limite)}</td></tr>`).join("")}
              </tbody></table></div>` : "")}`);
    } catch (ex) { toast(ex.message); }
  };
  await cargar();
}

/* ---------- Administración ---------- */
function formModal(titulo, camposHtml, onSubmit) {
  abrirModal(`
    <div class="row spread">
      <h2>${esc(titulo)}</h2>
      <button type="button" class="btn ghost" data-close-modal>Cerrar</button>
    </div>
    <form id="admin-form" class="stack" style="margin-top:0.75rem">
      ${camposHtml}
      <p id="admin-form-error" class="error" hidden></p>
      <div class="row">
        <button type="submit" class="btn primary">Guardar</button>
        <button type="button" class="btn ghost" data-close-modal>Cancelar</button>
      </div>
    </form>`);
  $("#admin-form").onsubmit = async (e) => {
    e.preventDefault();
    const err = $("#admin-form-error");
    err.hidden = true;
    const btn = e.target.querySelector('[type="submit"]');
    btn.disabled = true;
    try {
      const fd = new FormData(e.target);
      cerrarModal();
      await onSubmit(fd);
    } catch (ex) {
      // Reabrir con el error si falló tras cerrar no aplica; mostrar toast.
      toast(ex.message);
      btn.disabled = false;
    }
  };
}

async function vistaAdmin(box) {
  if (!api.esGestor) {
    box.innerHTML = `<p class="error">Solo encargado y jefe.</p>`;
    return;
  }
  const tabs = ["Áreas", "Subtipos"];
  if (api.esJefe) tabs.push("Usuarios", "Claves API", "Roles");
  box.innerHTML = `
    <h1 class="section-title">Administración</h1>
    <div class="panel">
      <div class="tabs" id="ad-tabs">${tabs.map((t, i) =>
        `<button type="button" class="btn ${i === 0 ? "active" : ""}" data-tab="${i}">${t}</button>`).join("")}</div>
      <div id="ad-body"></div>
    </div>`;

  let tab = 0;
  const pintar = async () => {
    $$("#ad-tabs .btn").forEach((b) => b.classList.toggle("active", Number(b.dataset.tab) === tab));
    const body = $("#ad-body");
    try {
      if (tab === 0) await adminAreas(body);
      else if (tab === 1) await adminSubtipos(body);
      else if (tab === 2) await adminUsuarios(body);
      else if (tab === 3) await adminClaves(body);
      else if (tab === 4) await adminRoles(body);
    } catch (ex) {
      body.innerHTML = `<p class="error">${esc(ex.message)}</p>`;
    }
  };
  $("#ad-tabs").onclick = (e) => {
    const b = e.target.closest("[data-tab]");
    if (!b) return;
    tab = Number(b.dataset.tab);
    pintar();
  };
  await pintar();
}

async function adminAreas(body) {
  const areas = await api.areas(true);
  body.innerHTML = `
    <div class="row" style="margin-bottom:0.75rem">
      <button type="button" class="btn primary" id="area-nueva">Agregar…</button>
    </div>
    <div class="table-wrap"><table class="data admin-table">
      <thead><tr><th>Área</th><th>Activa</th><th></th></tr></thead>
      <tbody>${areas.map((a) => `<tr>
        <td>${esc(a.nombre)}</td><td>${a.activa ? "sí" : "no"}</td>
        <td class="row">
          <button type="button" class="btn" data-ren="${a.id}" data-nombre="${esc(a.nombre)}">Renombrar</button>
          <button type="button" class="btn" data-act="${a.id}" data-on="${a.activa ? "true" : "false"}">
            ${a.activa ? "Desactivar" : "Activar"}
          </button>
        </td></tr>`).join("")}</tbody></table></div>`;

  $("#area-nueva").onclick = () => {
    formModal("Nueva área",
      `<label>Nombre<input name="nombre" required maxlength="120" autofocus /></label>`,
      async (fd) => {
        await api.crearArea(fd.get("nombre").trim());
        toast("Área creada");
        await adminAreas(body);
      });
  };
  body.onclick = async (e) => {
    e.stopPropagation();
    const ren = e.target.closest("[data-ren]");
    const act = e.target.closest("[data-act]");
    if (ren) {
      formModal("Renombrar área",
        `<label>Nombre<input name="nombre" required maxlength="120" value="${ren.dataset.nombre}" /></label>`,
        async (fd) => {
          await api.modificarArea(ren.dataset.ren, { nombre: fd.get("nombre").trim() });
          toast("Área actualizada");
          await adminAreas(body);
        });
      return;
    }
    if (act) {
      try {
        const activa = act.dataset.on !== "true";
        await api.modificarArea(act.dataset.act, { activa });
        toast(activa ? "Área activada" : "Área desactivada");
        await adminAreas(body);
      } catch (ex) { toast(ex.message); }
    }
  };
}

async function adminSubtipos(body) {
  const lista = await api.subtipos(undefined, true);
  body.innerHTML = `
    <div class="row" style="margin-bottom:0.75rem">
      <button type="button" class="btn primary" id="sub-nuevo">Agregar…</button>
    </div>
    <div class="table-wrap"><table class="data admin-table">
      <thead><tr><th>Tipo</th><th>Subtipo</th><th>Activo</th><th>Origen</th><th></th></tr></thead>
      <tbody>${lista.map((s) => `<tr>
        <td>${esc(s.tipo)}</td><td>${esc(s.nombre)}</td>
        <td>${s.activo ? "sí" : "no"}</td><td>${s.base ? "de fábrica" : "agregado"}</td>
        <td><button type="button" class="btn" data-tipo="${esc(s.tipo)}" data-nom="${esc(s.nombre)}" data-on="${s.activo ? "true" : "false"}">
          ${s.activo ? "Desactivar" : "Activar"}
        </button></td>
      </tr>`).join("")}</tbody></table></div>`;

  $("#sub-nuevo").onclick = () => {
    formModal("Nuevo subtipo", `
      <label>Tipo
        <select name="tipo" required>
          ${TIPOS.map((t) => `<option value="${t}">${t}</option>`).join("")}
        </select>
      </label>
      <label>Nombre (minúsculas, sin espacios)
        <input name="nombre" required pattern="[a-z0-9_]+" title="solo minúsculas, números y _" />
      </label>`,
      async (fd) => {
        await api.crearSubtipo(fd.get("tipo"), fd.get("nombre").trim());
        toast("Subtipo creado");
        await adminSubtipos(body);
      });
  };
  body.onclick = async (e) => {
    e.stopPropagation();
    const b = e.target.closest("[data-tipo]");
    if (!b) return;
    try {
      const activo = b.dataset.on !== "true";
      await api.activarSubtipo(b.dataset.tipo, b.dataset.nom, activo);
      toast(activo ? "Subtipo activado" : "Subtipo desactivado");
      await adminSubtipos(body);
    } catch (ex) { toast(ex.message); }
  };
}

async function adminUsuarios(body) {
  const [users, roles] = await Promise.all([api.usuarios(), api.roles(false)]);
  body.innerHTML = `
    <div class="row" style="margin-bottom:0.75rem">
      <button type="button" class="btn primary" id="usr-nuevo">Agregar…</button>
    </div>
    <div class="table-wrap"><table class="data admin-table">
      <thead><tr><th>Nombre</th><th>Correo</th><th>Rol</th><th>Activo</th><th></th></tr></thead>
      <tbody>${users.map((u) => `<tr>
        <td>${esc(u.nombre)}</td><td>${esc(u.correo)}</td>
        <td>${esc(u.rol_custom_nombre || u.rol)}</td><td>${u.activo ? "sí" : "no"}</td>
        <td class="row">
          <button type="button" class="btn" data-rol="${u.id}" data-base="${esc(u.rol)}" data-custom="${u.rol_custom_id || ""}">Rol…</button>
          <button type="button" class="btn" data-clave="${u.id}">Clave…</button>
          <button type="button" class="btn" data-act="${u.id}" data-on="${u.activo ? "true" : "false"}">
            ${u.activo ? "Desactivar" : "Activar"}
          </button>
        </td></tr>`).join("")}</tbody></table></div>`;

  $("#usr-nuevo").onclick = () => {
    formModal("Nuevo usuario", `
      <label>Nombre<input name="nombre" required maxlength="120" /></label>
      <label>Correo<input name="correo" type="email" required /></label>
      <label>Rol base
        <select name="rol" required>
          <option value="asistente">asistente</option>
          <option value="encargado">encargado</option>
          <option value="jefe">jefe</option>
        </select>
      </label>
      <label>Clave (mín. 8)<input name="clave" type="password" required minlength="8" /></label>`,
      async (fd) => {
        await api.crearUsuario({
          nombre: fd.get("nombre").trim(),
          correo: fd.get("correo").trim(),
          rol: fd.get("rol"),
          clave: fd.get("clave"),
        });
        toast("Usuario creado");
        await adminUsuarios(body);
      });
  };

  body.onclick = async (e) => {
    e.stopPropagation();
    const rolBtn = e.target.closest("[data-rol]");
    const clave = e.target.closest("[data-clave]");
    const act = e.target.closest("[data-act]");

    if (rolBtn) {
      const customOpts = roles.map((r) =>
        `<option value="custom:${r.id}" ${rolBtn.dataset.custom === r.id ? "selected" : ""}>${esc(r.nombre)} (personalizado)</option>`
      ).join("");
      formModal("Cambiar rol", `
        <label>Rol
          <select name="rol_sel" required>
            <option value="base:asistente" ${rolBtn.dataset.base === "asistente" && !rolBtn.dataset.custom ? "selected" : ""}>asistente</option>
            <option value="base:encargado" ${rolBtn.dataset.base === "encargado" && !rolBtn.dataset.custom ? "selected" : ""}>encargado</option>
            <option value="base:jefe" ${rolBtn.dataset.base === "jefe" && !rolBtn.dataset.custom ? "selected" : ""}>jefe</option>
            ${customOpts}
          </select>
        </label>
        <p class="muted">Los roles personalizados se asignan además del rol base; al elegir uno base se quita el personalizado.</p>`,
        async (fd) => {
          const sel = fd.get("rol_sel");
          if (sel.startsWith("custom:")) {
            await api.asignarRol(rolBtn.dataset.rol, sel.slice(7));
          } else {
            await api.asignarRol(rolBtn.dataset.rol, null);
            await api.modificarUsuario(rolBtn.dataset.rol, { rol: sel.slice(5) });
          }
          toast("Rol actualizado");
          await adminUsuarios(body);
        });
      return;
    }

    if (clave) {
      formModal("Restablecer clave",
        `<label>Nueva clave (mín. 8)<input name="clave" type="password" required minlength="8" /></label>`,
        async (fd) => {
          await api.modificarUsuario(clave.dataset.clave, { clave: fd.get("clave") });
          toast("Clave actualizada");
          await adminUsuarios(body);
        });
      return;
    }

    if (act) {
      try {
        const activo = act.dataset.on !== "true";
        await api.modificarUsuario(act.dataset.act, { activo });
        toast(activo ? "Usuario activado" : "Usuario desactivado");
        await adminUsuarios(body);
      } catch (ex) { toast(ex.message); }
    }
  };
}

async function adminClaves(body) {
  const claves = await api.clavesApi();
  body.innerHTML = `
    <div class="row" style="margin-bottom:0.75rem">
      <button type="button" class="btn primary" id="api-nueva">Emitir clave…</button>
    </div>
    <div class="table-wrap"><table class="data admin-table">
      <thead><tr><th>Nombre</th><th>Prefijo</th><th>Creada</th><th>Último uso</th><th>Usos</th><th>Estado</th><th></th></tr></thead>
      <tbody>${claves.length ? claves.map((k) => `<tr>
        <td>${esc(k.nombre)}</td><td>${esc(k.prefijo)}…</td>
        <td>${esc((k.creado_en || "").slice(0, 10))}</td>
        <td>${esc((k.ultimo_uso || "nunca").toString().slice(0, 16).replace("T", " "))}</td>
        <td>${k.usos}</td><td>${k.revocada_en ? "revocada" : "activa"}</td>
        <td>${!k.revocada_en ? `<button type="button" class="btn danger" data-rev="${k.id}">Revocar</button>` : ""}</td>
      </tr>`).join("") : `<tr><td colspan="7" class="muted">No hay claves. Emite una para el programa externo.</td></tr>`}</tbody></table></div>`;

  $("#api-nueva").onclick = () => {
    formModal("Emitir clave API",
      `<label>Nombre<input name="nombre" required maxlength="120" placeholder="ej. integración reportes" /></label>
       <p class="muted">La clave en claro se muestra una sola vez.</p>`,
      async (fd) => {
        const k = await api.crearClaveApi(fd.get("nombre").trim());
        await adminClaves(body);
        abrirModal(`
          <div class="row spread"><h2>Clave emitida</h2>
            <button type="button" class="btn ghost" data-close-modal>Cerrar</button></div>
          <p>Cópiala ahora. Encabezado: <code>X-API-Key</code></p>
          <div class="ficha" id="clave-valor">${esc(k.clave)}</div>
          <div class="row" style="margin-top:0.75rem">
            <button type="button" class="btn primary" id="copiar-clave">Copiar</button>
            <button type="button" class="btn ghost" data-close-modal>Listo</button>
          </div>`);
        $("#copiar-clave").onclick = async () => {
          try {
            await navigator.clipboard.writeText(k.clave);
            toast("Clave copiada");
          } catch {
            toast("Selecciona y copia manualmente");
          }
        };
      });
  };
  body.onclick = async (e) => {
    e.stopPropagation();
    const b = e.target.closest("[data-rev]");
    if (!b) return;
    if (!confirm("El programa que use esta clave perderá el acceso. ¿Continuar?")) return;
    try {
      await api.revocarClaveApi(b.dataset.rev);
      toast("Clave revocada");
      await adminClaves(body);
    } catch (ex) { toast(ex.message); }
  };
}

async function adminRoles(body) {
  const [roles, disponibles] = await Promise.all([api.roles(true), api.permisos()]);
  const checks = (seleccionados = []) => disponibles.map((p) => `
    <label class="row" style="justify-content:flex-start">
      <input type="checkbox" name="permisos" value="${esc(p.codigo)}" ${seleccionados.includes(p.codigo) ? "checked" : ""} />
      <span><strong>${esc(p.codigo)}</strong> — ${esc(p.descripcion)}</span>
    </label>`).join("");

  body.innerHTML = `
    <div class="row" style="margin-bottom:0.75rem">
      <button type="button" class="btn primary" id="rol-nuevo">Nuevo rol…</button>
    </div>
    <div class="table-wrap"><table class="data admin-table">
      <thead><tr><th>Nombre</th><th>Descripción</th><th>Permisos</th><th>Activo</th><th></th></tr></thead>
      <tbody>${roles.length ? roles.map((r) => `<tr>
        <td>${esc(r.nombre)}</td><td>${esc(r.descripcion)}</td>
        <td class="muted">${esc((r.permisos || []).join(", ") || "—")}</td>
        <td>${r.activo ? "sí" : "no"}</td>
        <td class="row">
          <button type="button" class="btn" data-edit="${r.id}">Editar…</button>
          <button type="button" class="btn" data-act="${r.id}" data-on="${r.activo ? "true" : "false"}">
            ${r.activo ? "Desactivar" : "Activar"}
          </button>
        </td></tr>`).join("") : `<tr><td colspan="5" class="muted">Sin roles personalizados.</td></tr>`}</tbody></table></div>`;

  $("#rol-nuevo").onclick = () => {
    formModal("Nuevo rol", `
      <label>Nombre<input name="nombre" required maxlength="80" /></label>
      <label>Descripción<input name="descripcion" maxlength="200" /></label>
      <fieldset style="border:1px solid var(--line);border-radius:10px;padding:0.75rem">
        <legend>Permisos</legend>
        <div class="stack">${checks()}</div>
      </fieldset>`,
      async (fd) => {
        const permisos = fd.getAll("permisos");
        if (!permisos.length) throw new ErrorApi("Marca al menos un permiso");
        await api.crearRol(fd.get("nombre").trim(), fd.get("descripcion").trim(), permisos);
        toast("Rol creado");
        await adminRoles(body);
      });
  };

  body.onclick = async (e) => {
    e.stopPropagation();
    const edit = e.target.closest("[data-edit]");
    const act = e.target.closest("[data-act]");
    if (edit) {
      const rol = roles.find((r) => r.id === edit.dataset.edit);
      formModal(`Editar: ${rol.nombre}`, `
        <label>Nombre<input name="nombre" required value="${esc(rol.nombre)}" /></label>
        <label>Descripción<input name="descripcion" value="${esc(rol.descripcion || "")}" /></label>
        <fieldset style="border:1px solid var(--line);border-radius:10px;padding:0.75rem">
          <legend>Permisos</legend>
          <div class="stack">${checks(rol.permisos || [])}</div>
        </fieldset>`,
        async (fd) => {
          const permisos = fd.getAll("permisos");
          if (!permisos.length) throw new ErrorApi("Marca al menos un permiso");
          await api.editarRol(edit.dataset.edit, {
            nombre: fd.get("nombre").trim(),
            descripcion: fd.get("descripcion").trim(),
            permisos,
          });
          toast("Rol actualizado");
          await adminRoles(body);
        });
      return;
    }
    if (act) {
      try {
        const activo = act.dataset.on !== "true";
        await api.editarRol(act.dataset.act, { activo });
        toast(activo ? "Rol activado" : "Rol desactivado");
        await adminRoles(body);
      } catch (ex) { toast(ex.message); }
    }
  };
}

/* ---------- boot ---------- */
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
