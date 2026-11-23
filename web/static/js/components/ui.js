import { ErrorApi, esc } from "../services/api.js";

export const $ = (sel, el = document) => el.querySelector(sel);
export const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

const ICON_EYE = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
const ICON_EYE_OFF = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;

export function toast(msg, tipo = "info") {
  const t = $("#toast");
  t.textContent = msg;
  t.className = `toast ${tipo === "ok" ? "ok" : tipo === "error" ? "error" : ""}`.trim();
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.add("hidden"), 3400);
}

export function badge(estado) {
  const etiqueta = String(estado || "").replaceAll("_", " ");
  return `<span class="badge ${esc(estado)}">${esc(etiqueta)}</span>`;
}

export function badgeActivo(activo) {
  return activo
    ? `<span class="badge activo">activo</span>`
    : `<span class="badge inactivo">inactivo</span>`;
}

export function nombre(ref) {
  return ref?.nombre || "—";
}

export function iniciales(texto = "") {
  const partes = String(texto).trim().split(/\s+/).filter(Boolean);
  if (!partes.length) return "TI";
  return (partes[0][0] + (partes[1]?.[0] || "")).toUpperCase();
}

/* ---------- Campos de correo y contraseña con criterios y mostrar/ocultar ---------- */
export function reglasCorreo(valor = "") {
  const v = String(valor);
  return {
    formato: /^[^\s@]+@[^\s@]+$/.test(v),
    dominio: /^[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}$/.test(v),
    sinEspacios: v.length > 0 && !/\s/.test(v),
  };
}

export function reglasClave(valor = "") {
  const v = String(valor);
  return {
    longitud: v.length >= 8,
    letra: /[a-zA-Z]/.test(v),
    numero: /\d/.test(v),
    sinEspacios: v.length > 0 && !/\s/.test(v),
  };
}

export function validarCorreoCriterios(correo) {
  const r = reglasCorreo(correo);
  if (!r.formato || !r.dominio || !r.sinEspacios) {
    throw new ErrorApi("El correo debe tener un formato válido (ej. usuario@dominio.com) y no contener espacios.");
  }
}

export function validarClaveCriterios(clave) {
  const r = reglasClave(clave);
  if (!r.longitud || !r.letra || !r.numero || !r.sinEspacios) {
    throw new ErrorApi("La contraseña debe tener al menos 8 caracteres, incluir letras y números, y no tener espacios.");
  }
}

export function campoCorreoHtml({
  name = "correo",
  label = "Correo electrónico",
  placeholder = "usuario@dominio.com",
} = {}) {
  return `
    <div class="field" data-email-check>
      <span>${esc(label)}</span>
      <input name="${esc(name)}" type="email" required placeholder="${esc(placeholder)}" autocomplete="off" />
      <ul class="criteria-list">
        <li class="criteria-item" data-crit="formato"><span class="crit-dot">✓</span>Incluye usuario y símbolo @</li>
        <li class="criteria-item" data-crit="dominio"><span class="crit-dot">✓</span>Dominio válido (ej. @empresa.com)</li>
        <li class="criteria-item" data-crit="sinEspacios"><span class="crit-dot">✓</span>Sin espacios en blanco</li>
      </ul>
    </div>`;
}

export function campoClaveHtml({
  name = "clave",
  label = "Contraseña",
  placeholder = "Mínimo 8 caracteres (letras y números)",
} = {}) {
  return `
    <div class="field" data-pass-check>
      <span>${esc(label)}</span>
      <div class="password-wrap">
        <input name="${esc(name)}" type="password" required minlength="8" placeholder="${esc(placeholder)}" autocomplete="new-password" />
        <button type="button" class="btn-eye" data-toggle-pass aria-label="Mostrar u ocultar contraseña" title="Mostrar u ocultar contraseña">
          ${ICON_EYE}
        </button>
      </div>
      <ul class="criteria-list">
        <li class="criteria-item" data-crit="longitud"><span class="crit-dot">✓</span>Mínimo 8 caracteres</li>
        <li class="criteria-item" data-crit="letra"><span class="crit-dot">✓</span>Contiene al menos una letra (a-z, A-Z)</li>
        <li class="criteria-item" data-crit="numero"><span class="crit-dot">✓</span>Contiene al menos un número (0-9)</li>
        <li class="criteria-item" data-crit="sinEspacios"><span class="crit-dot">✓</span>Sin espacios en blanco</li>
      </ul>
    </div>`;
}

function enlazarCriterios(contenedor) {
  $$("[data-email-check]", contenedor).forEach((box) => {
    const input = box.querySelector("input");
    const actualizar = () => {
      const estado = reglasCorreo(input.value);
      for (const [clave, ok] of Object.entries(estado)) {
        box.querySelector(`[data-crit="${clave}"]`)?.classList.toggle("is-valid", ok);
      }
    };
    input.addEventListener("input", actualizar);
    actualizar();
  });

  $$("[data-pass-check]", contenedor).forEach((box) => {
    const input = box.querySelector("input");
    const actualizar = () => {
      const estado = reglasClave(input.value);
      for (const [clave, ok] of Object.entries(estado)) {
        box.querySelector(`[data-crit="${clave}"]`)?.classList.toggle("is-valid", ok);
      }
    };
    input.addEventListener("input", actualizar);
    actualizar();
  });
}

// Delegación global para botones mostrar/ocultar contraseña (login y modales)
document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-toggle-pass]");
  if (!btn) return;
  const input = btn.closest(".password-wrap")?.querySelector("input");
  if (!input) return;
  const mostrar = input.type === "password";
  input.type = mostrar ? "text" : "password";
  btn.innerHTML = mostrar ? ICON_EYE_OFF : ICON_EYE;
  btn.setAttribute("aria-pressed", String(mostrar));
});

export function abrirModal(html, { sm = false } = {}) {
  const m = $("#modal");
  const panel = $("#modal-panel");
  panel.classList.toggle("modal-sm", sm);
  panel.innerHTML = html;
  m.classList.remove("hidden");
  document.body.style.overflow = "hidden";
  enlazarCriterios(panel);
}

export function cerrarModal() {
  $("#modal").classList.add("hidden");
  const panel = $("#modal-panel");
  panel.classList.remove("modal-sm");
  panel.innerHTML = "";
  document.body.style.overflow = "";
}

export function formModal(titulo, camposHtml, onSubmit, { submitTexto = "Guardar", sm = true, onOpen = null } = {}) {
  abrirModal(`
    <div class="modal-header">
      <h2>${esc(titulo)}</h2>
      <button type="button" class="btn ghost btn-sm" data-close-modal>Cerrar</button>
    </div>
    <form id="modal-form" class="stack">
      ${camposHtml}
      <p id="modal-form-error" class="alert-inline error" hidden></p>
      <div class="row" style="justify-content:flex-end;margin-top:0.25rem">
        <button type="button" class="btn ghost" data-close-modal>Cancelar</button>
        <button type="submit" class="btn primary">${esc(submitTexto)}</button>
      </div>
    </form>`, { sm });

  if (onOpen) onOpen($("#modal-form"));

  $("#modal-form").onsubmit = async (e) => {
    e.preventDefault();
    const err = $("#modal-form-error");
    err.hidden = true;
    const btn = e.target.querySelector('[type="submit"]');
    btn.disabled = true;
    try {
      const fd = new FormData(e.target);
      await onSubmit(fd);
      cerrarModal();
    } catch (ex) {
      err.textContent = ex.message;
      err.hidden = false;
      btn.disabled = false;
    }
  };
}

export function modalConfirmar({
  titulo,
  mensaje,
  confirmarTexto = "Confirmar",
  cancelarTexto = "Cancelar",
  peligro = false,
}) {
  return new Promise((resolve) => {
    abrirModal(`
      <div class="modal-header">
        <h2>${esc(titulo)}</h2>
        <button type="button" class="btn ghost btn-sm" id="mc-close">Cerrar</button>
      </div>
      <p style="margin:0 0 1.25rem;color:var(--ink-secondary)">${esc(mensaje)}</p>
      <div class="row" style="justify-content:flex-end">
        <button type="button" class="btn ghost" id="mc-cancel">${esc(cancelarTexto)}</button>
        <button type="button" class="btn ${peligro ? "danger" : "primary"}" id="mc-ok">${esc(confirmarTexto)}</button>
      </div>`, { sm: true });
    const cerrar = (val) => { cerrarModal(); resolve(val); };
    $("#mc-close").onclick = () => cerrar(false);
    $("#mc-cancel").onclick = () => cerrar(false);
    $("#mc-ok").onclick = () => cerrar(true);
  });
}

export function tablaEventos(filas, { fragmento = false, vacio = "No hay eventos para mostrar." } = {}) {
  if (!filas.length) return `<div class="empty-state">${esc(vacio)}</div>`;
  return `<div class="table-wrap"><table class="data">
    <thead><tr>
      <th>Folio</th>
      <th>Fecha</th>
      <th>Tipo</th>
      <th>Título</th>
      <th>Estado</th>
      <th>Responsable</th>
      ${fragmento ? "<th>Coincidencia</th>" : ""}
    </tr></thead>
    <tbody>
      ${filas.map((e) => `<tr data-folio="${esc(e.folio)}">
        <td class="folio-cell">${esc(e.folio)}</td>
        <td class="cell-nowrap">${esc(e.fecha_hecho)}</td>
        <td class="cell-nowrap">${esc(e.tipo)}${e.subtipo ? ` <span class="muted">/ ${esc(e.subtipo)}</span>` : ""}</td>
        <td><strong>${esc(e.titulo)}</strong></td>
        <td>${badge(e.estado)}</td>
        <td class="cell-nowrap">${esc(nombre(e.responsable))}</td>
        ${fragmento ? `<td class="muted text-sm">${esc(e.fragmento || "")}</td>` : ""}
      </tr>`).join("")}
    </tbody></table></div>`;
}

export async function cargarSubtipos(api, tipo, select) {
  try {
    const lista = await api.subtipos(tipo);
    select.innerHTML = `<option value="">—</option>` + lista.map((s) =>
      `<option value="${esc(s.nombre)}">${esc(s.nombre)}</option>`
    ).join("");
  } catch {
    select.innerHTML = `<option value="">—</option>`;
  }
}
