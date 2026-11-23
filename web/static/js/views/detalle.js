import { ESTADOS_SIGUIENTES, esc, hoy } from "../services/api.js";
import { $, abrirModal, badge, nombre, toast } from "../components/ui.js";

export async function abrirDetalle(folio, { api, actualizarAviso, enrutar }) {
  let e;
  try {
    e = await api.evento(folio);
  } catch (ex) {
    toast(ex.message, "error");
    return;
  }

  const renderizar = () => {
    const siguientes = ESTADOS_SIGUIENTES[e.estado] || [];
    const notas = e.seguimientos || [];
    const comps = e.compromisos || [];

    abrirModal(`
      <div class="modal-header">
        <div>
          <div class="row" style="gap:0.5rem;margin-bottom:0.25rem">
            <span class="folio-cell" style="font-size:1rem">${esc(e.folio)}</span>
            ${badge(e.estado)}
            ${e.prioridad ? `<span class="badge">${esc(e.prioridad)}</span>` : ""}
          </div>
          <h2>${esc(e.titulo)}</h2>
        </div>
        <button type="button" class="btn ghost btn-sm" data-close-modal>Cerrar</button>
      </div>

      <div class="detail-meta-grid">
        <div class="meta-item">
          <div class="meta-label">Tipo</div>
          <div class="meta-val">${esc(e.tipo)}${e.subtipo ? ` / ${esc(e.subtipo)}` : ""}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">Fecha del hecho</div>
          <div class="meta-val">${esc(e.fecha_hecho)}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">Área de origen</div>
          <div class="meta-val">${esc(nombre(e.area_origen))}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">Solicitante</div>
          <div class="meta-val">${esc(e.solicitante || "—")}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">Registrado por</div>
          <div class="meta-val">${esc(e.autor.nombre)}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">Responsable</div>
          <div class="meta-val">${esc(nombre(e.responsable))}</div>
        </div>
        ${e.referencia ? `<div class="meta-item">
          <div class="meta-label">Referencia</div>
          <div class="meta-val">${esc(e.referencia)}</div>
        </div>` : ""}
      </div>

      <div class="ficha-body">
        <h3>Descripción</h3>
        <p>${esc(e.descripcion)}</p>
      </div>

      <div class="action-toolbar">
        <select id="det-estado" aria-label="Nuevo estado">
          <option value="">Cambiar estado…</option>
          ${siguientes.map((s) => `<option value="${s}">${s.replaceAll("_", " ")}</option>`).join("")}
        </select>
        <button type="button" class="btn soft" id="det-cambiar">Aplicar estado</button>
        <button type="button" class="btn" id="det-seg">${e.requiere_seguimiento ? "Quitar seguimiento" : "Activar seguimiento"}</button>
        <button type="button" class="btn" id="det-corregir">Corregir datos</button>
        <button type="button" class="btn ghost" id="det-auditoria">Auditoría (${(e.auditoria || []).length})</button>
      </div>

      <div class="modal-section">
        <h3>Historial de notas (${notas.length})</h3>
        <div class="notas-list">
          ${notas.length ? notas.map((n) => `
            <div class="nota-item">
              <div class="nota-head">
                <strong>${esc(n.autor.nombre)}</strong>
                <span>${esc((n.creado_en || "").slice(0, 16).replace("T", " "))}</span>
              </div>
              <p class="nota-text">${esc(n.nota)}</p>
            </div>`).join("") : `<div class="empty-state">Aún no hay notas registradas.</div>`}
        </div>
        <form id="det-nota-form" class="row" style="margin-top:0.65rem">
          <input id="det-nota" placeholder="Escribe una nueva nota de seguimiento…" style="flex:1;min-width:200px" />
          <button class="btn primary" type="submit">Agregar nota</button>
        </form>
      </div>

      <div class="modal-section">
        <h3>Compromisos (${comps.length})</h3>
        <div id="det-comps">
          ${comps.length ? `<div class="table-wrap"><table class="data">
            <thead><tr><th>Fecha límite</th><th>Compromiso</th><th>Resp.</th><th>Estado</th><th>Acciones</th></tr></thead>
            <tbody>${comps.map((c) => `<tr>
              <td class="cell-nowrap">${esc(c.fecha_limite)}</td>
              <td>${esc(c.descripcion)}</td>
              <td class="cell-nowrap">${esc(c.responsable.nombre)}</td>
              <td>${c.vencido ? badge("VENCIDO") : badge(c.estado)}</td>
              <td><div class="cell-actions">${c.estado === "pendiente" ? `
                <button type="button" class="btn ok btn-sm" data-comp="${c.id}" data-acc="cumplido">Cumplir</button>
                <button type="button" class="btn danger btn-sm" data-comp="${c.id}" data-acc="cancelado">Cancelar</button>` : "—"}</div></td>
            </tr>`).join("")}</tbody></table></div>` : `<div class="empty-state">Sin compromisos asociados.</div>`}
        </div>
        <form id="det-comp-form" class="row" style="margin-top:0.65rem">
          <input id="det-comp-desc" placeholder="Descripción del compromiso…" style="flex:1;min-width:200px" />
          <input type="date" id="det-comp-fecha" value="${hoy()}" style="width:auto" aria-label="Fecha límite" />
          <button class="btn soft" type="submit">Agregar compromiso</button>
        </form>
      </div>
    `);

    const refrescar = async () => {
      e = await api.evento(folio);
      renderizar();
      actualizarAviso();
      enrutar();
    };

    const abrirModalEstado = (estadoDestino) => {
      const esReapertura = e.estado === "cerrado" && estadoDestino === "abierto";
      const exigeNota = esReapertura || estadoDestino === "en_espera" ||
        (estadoDestino === "cerrado" && ["en_proceso", "en_espera"].includes(e.estado));
      abrirModal(`
        <div class="modal-header">
          <h2>Cambiar estado a «${esc(estadoDestino.replaceAll("_", " "))}»</h2>
          <button type="button" class="btn ghost btn-sm" id="est-volver">Volver</button>
        </div>
        <form id="form-estado" class="stack">
          <label class="field">
            <span>${esReapertura ? "Motivo de la reapertura (obligatorio)" : exigeNota ? "Nota del cambio (obligatoria)" : "Nota del cambio (opcional)"}</span>
            <textarea name="nota" ${exigeNota ? "required" : ""} placeholder="Describe el motivo o detalle del cambio…"></textarea>
          </label>
          <div id="est-comps-box" class="stack hidden">
            <p class="alert-inline error" id="est-comps-msg"></p>
            <label class="field">
              <span>¿Cómo deseas resolver los compromisos pendientes?</span>
              <select name="resolver_compromisos">
                <option value="cumplir">Marcarlos como cumplidos</option>
                <option value="cancelar">Marcarlos como cancelados</option>
              </select>
            </label>
          </div>
          <p id="est-error" class="alert-inline error" hidden></p>
          <div class="row" style="justify-content:flex-end">
            <button type="button" class="btn ghost" id="est-cancel">Cancelar</button>
            <button type="submit" class="btn primary">Confirmar cambio</button>
          </div>
        </form>`, { sm: true });

      $("#est-volver").onclick = renderizar;
      $("#est-cancel").onclick = renderizar;
      let requiereResolver = false;

      $("#form-estado").onsubmit = async (ev) => {
        ev.preventDefault();
        const fd = new FormData(ev.target);
        const nota = String(fd.get("nota") || "").trim() || null;
        const resolver = requiereResolver ? fd.get("resolver_compromisos") : null;
        const err = $("#est-error");
        err.hidden = true;
        try {
          await api.cambiarEstado(folio, estadoDestino, nota, resolver);
          toast("Estado actualizado", "ok");
          await refrescar();
        } catch (ex) {
          if (!requiereResolver && /compromiso/i.test(ex.message) && /pendiente/i.test(ex.message)) {
            requiereResolver = true;
            $("#est-comps-msg").textContent = ex.message;
            $("#est-comps-box").classList.remove("hidden");
          } else {
            err.textContent = ex.message;
            err.hidden = false;
          }
        }
      };
    };

    $("#det-cambiar").onclick = () => {
      const estado = $("#det-estado").value;
      if (!estado) {
        toast("Selecciona un estado para aplicar.");
        return;
      }
      abrirModalEstado(estado);
    };

    $("#det-seg").onclick = async () => {
      try {
        await api.modificarEvento(folio, { requiere_seguimiento: !e.requiere_seguimiento });
        toast(e.requiere_seguimiento ? "Seguimiento desactivado" : "Seguimiento activado", "ok");
        await refrescar();
      } catch (ex) {
        toast(ex.message, "error");
      }
    };

    $("#det-auditoria").onclick = () => {
      const filas = e.auditoria || [];
      abrirModal(`
        <div class="modal-header">
          <h2>Auditoría de cambios — ${esc(folio)}</h2>
          <button type="button" class="btn ghost btn-sm" id="aud-volver">Volver</button>
        </div>
        ${filas.length ? `<div class="table-wrap"><table class="data">
          <thead><tr><th>Fecha</th><th>Usuario</th><th>Campo</th><th>Antes</th><th>Después</th></tr></thead>
          <tbody>${filas.map((a) => `<tr>
            <td class="cell-nowrap">${esc((a.creado_en || "").slice(0, 16).replace("T", " "))}</td>
            <td class="cell-nowrap">${esc(a.usuario.nombre)}</td>
            <td><strong>${esc(a.campo)}</strong></td>
            <td class="muted">${esc(a.valor_anterior || "—")}</td>
            <td>${esc(a.valor_nuevo || "—")}</td>
          </tr>`).join("")}</tbody></table></div>` : `<div class="empty-state">Este evento no tiene correcciones registradas.</div>`}
      `);
      $("#aud-volver").onclick = renderizar;
    };

    $("#det-corregir").onclick = () => {
      abrirModal(`
        <div class="modal-header">
          <h2>Corregir datos — ${esc(folio)}</h2>
          <button type="button" class="btn ghost btn-sm" id="corr-volver">Volver</button>
        </div>
        <form id="form-corregir" class="stack">
          <label class="field">Título
            <input name="titulo" value="${esc(e.titulo)}" required maxlength="200" />
          </label>
          <label class="field">Descripción
            <textarea name="descripcion" required>${esc(e.descripcion)}</textarea>
          </label>
          <div class="grid-2">
            <label class="field">Referencia
              <input name="referencia" value="${esc(e.referencia || "")}" />
            </label>
            <label class="field">Solicitante
              <input name="solicitante_nombre" value="${esc(e.solicitante || "")}" />
            </label>
            <label class="field">Fecha del hecho
              <input type="date" name="fecha_hecho" value="${esc(e.fecha_hecho)}" required />
            </label>
            <label class="field">Subtipo
              <input name="subtipo" value="${esc(e.subtipo || "")}" />
            </label>
          </div>
          <p class="muted text-sm" style="margin:0">El autor puede corregir el mismo día; después, solo encargado o jefe.</p>
          <p id="corr-error" class="alert-inline error" hidden></p>
          <div class="row" style="justify-content:flex-end">
            <button type="button" class="btn ghost" id="corr-cancel">Cancelar</button>
            <button class="btn primary" type="submit">Guardar cambios</button>
          </div>
        </form>`);
      $("#corr-volver").onclick = renderizar;
      $("#corr-cancel").onclick = renderizar;
      $("#form-corregir").onsubmit = async (ev) => {
        ev.preventDefault();
        const fd = new FormData(ev.target);
        const cambios = {};
        const antes = {
          titulo: e.titulo,
          descripcion: e.descripcion,
          referencia: e.referencia || "",
          solicitante_nombre: e.solicitante || "",
          fecha_hecho: e.fecha_hecho,
          subtipo: e.subtipo || "",
        };
        for (const k of Object.keys(antes)) {
          const nuevo = String(fd.get(k) || "").trim();
          if (nuevo !== String(antes[k] || "")) cambios[k] = nuevo || null;
        }
        if (!Object.keys(cambios).length) return renderizar();
        try {
          await api.modificarEvento(folio, cambios);
          toast("Datos corregidos", "ok");
          await refrescar();
        } catch (ex) {
          const err = $("#corr-error");
          err.textContent = ex.message;
          err.hidden = false;
        }
      };
    };

    $("#det-nota-form").onsubmit = async (ev) => {
      ev.preventDefault();
      const texto = $("#det-nota").value.trim();
      if (!texto) return;
      try {
        await api.agregarNota(folio, texto);
        toast("Nota agregada", "ok");
        await refrescar();
      } catch (ex) {
        toast(ex.message, "error");
      }
    };

    $("#det-comp-form").onsubmit = async (ev) => {
      ev.preventDefault();
      const desc = $("#det-comp-desc").value.trim();
      if (!desc) return;
      try {
        await api.crearCompromiso(folio, desc, $("#det-comp-fecha").value);
        toast("Compromiso registrado", "ok");
        await refrescar();
      } catch (ex) {
        toast(ex.message, "error");
      }
    };

    $("#det-comps").onclick = async (ev) => {
      const btn = ev.target.closest("[data-comp]");
      if (!btn) return;
      try {
        await api.resolverCompromiso(btn.dataset.comp, btn.dataset.acc);
        toast("Compromiso actualizado", "ok");
        await refrescar();
      } catch (ex) {
        toast(ex.message, "error");
      }
    };
  };

  renderizar();
}

