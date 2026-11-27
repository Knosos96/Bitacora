import { ESTADOS, ErrorApi, TIPOS, esc } from "../services/api.js";
import {
  $,
  abrirModal,
  badge,
  campoClaveHtml,
  campoClaveSimpleHtml,
  campoCorreoHtml,
  cerrarModal,
  enlazarCriterios,
  iniciales,
  toast,
  validarClaveCriterios,
  validarCorreoCriterios,
} from "../components/ui.js";

function fmtFecha(iso) {
  if (!iso) return "—";
  return String(iso).slice(0, 16).replace("T", " ");
}

function fmtBytes(bytes) {
  const n = Number(bytes || 0);
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
}

function etiquetaCuenta(nombre, estado) {
  if (!nombre) return `<span class="muted">—</span>`;
  if (estado === "eliminada") {
    return `${esc(nombre)} <span class="badge eliminada">eliminada</span>`;
  }
  if (estado === "inactiva") {
    return `${esc(nombre)} <span class="badge inactiva">inactiva</span>`;
  }
  return esc(nombre);
}

async function descargarCsv(api, params, nombreArchivo) {
  try {
    const blob = await api.superExportarCsv(params);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = nombreArchivo;
    a.click();
    URL.revokeObjectURL(a.href);
    toast("Dossier CSV descargado", "ok");
  } catch (ex) {
    toast(ex.message, "error");
  }
}

function bannerSuper({ titulo, subtitulo, exportSeccion, cuentaId = null }) {
  return `
    <div class="super-banner">
      <div>
        <h1>${esc(titulo)}</h1>
        <p>${esc(subtitulo)}</p>
      </div>
      <div class="row">
        ${exportSeccion ? `<button type="button" class="btn btn-sm" id="sup-export-csv" data-sec="${esc(exportSeccion)}" data-cid="${esc(cuentaId || "")}">Exportar CSV</button>` : ""}
        <button type="button" class="btn btn-sm" id="sup-print">Imprimir / PDF</button>
      </div>
    </div>`;
}

function tablaRegistrosDoc(filas, vacio = "Sin registros históricos para mostrar.") {
  if (!filas.length) return `<div class="empty-state">${esc(vacio)}</div>`;
  return `<div class="table-wrap"><table class="data">
    <thead><tr>
      <th>Folio</th>
      <th>Fecha</th>
      <th>Tipo</th>
      <th>Título</th>
      <th>Estado</th>
      <th>Autor original</th>
      <th>Responsable</th>
      <th>Notas / Comp.</th>
    </tr></thead>
    <tbody>
      ${filas.map((r) => `<tr data-super-folio="${esc(r.folio)}" style="cursor:pointer">
        <td class="folio-cell">${esc(r.folio)}</td>
        <td class="cell-nowrap">${esc(r.fecha_hecho)}</td>
        <td class="cell-nowrap"><span class="badge ${esc(r.tipo)}">${esc(r.tipo)}</span>${r.subtipo ? ` <span class="muted text-sm">/ ${esc(r.subtipo)}</span>` : ""}</td>
        <td><strong>${esc(r.titulo)}</strong></td>
        <td>${badge(r.estado)}</td>
        <td>${etiquetaCuenta(r.autor_original_nombre, r.autor_original_estado)}</td>
        <td>${etiquetaCuenta(r.responsable_original_nombre, r.responsable_original_estado)}</td>
        <td class="cell-nowrap muted text-sm">${r.notas_count} / ${r.compromisos_count}</td>
      </tr>`).join("")}
    </tbody>
  </table></div>`;
}

function listaActividadHtml(filas, vacio = "No hay actividad registrada.") {
  if (!filas.length) return `<div class="empty-state">${esc(vacio)}</div>`;
  return `<div class="timeline-list">
    ${filas.map((a) => `
      <div class="timeline-item">
        <div class="timeline-time">${esc(fmtFecha(a.creado_en))}</div>
        <div class="timeline-body">
          <h4>
            <span class="badge">${esc(a.accion.replaceAll("_", " "))}</span>
            ${a.folio ? `<span class="folio-cell" style="margin-left:0.35rem">${esc(a.folio)}</span>` : ""}
            ${a.titulo ? ` — ${esc(a.titulo)}` : ""}
          </h4>
          <div class="timeline-meta">
            Actor: <strong>${esc(a.actor_nombre)}</strong> (${esc(a.actor_correo)}) · Rol: ${esc(a.actor_rol)} · Entidad: ${esc(a.entidad)}
          </div>
          ${a.detalle ? `<p class="timeline-detail">${esc(a.detalle)}</p>` : ""}
        </div>
      </div>`).join("")}
  </div>`;
}

async function verFichaDocumental(folio, api) {
  let det;
  try {
    det = await api.superRegistroDetalle(folio);
  } catch (ex) {
    toast(ex.message, "error");
    return;
  }
  const e = det.registro;
  const notas = det.notas || [];
  const compromisos = det.compromisos || [];
  const auditoria = det.auditoria || [];
  const autorOrig = etiquetaCuenta(e.autor_original_nombre, e.autor_original_estado);
  const respOrig = etiquetaCuenta(e.responsable_original_nombre, e.responsable_original_estado);

  abrirModal(`
    <div class="modal-header">
      <div>
        <div class="row" style="gap:0.5rem;margin-bottom:0.25rem">
          <span class="folio-cell" style="font-size:1rem">${esc(e.folio)}</span>
          ${badge(e.estado)}
          <span class="badge ${esc(e.tipo)}">${esc(e.tipo)}</span>
        </div>
        <h2>${esc(e.titulo)}</h2>
      </div>
      <div class="row">
        <button type="button" class="btn soft btn-sm" id="doc-ficha-print">Imprimir ficha</button>
        <button type="button" class="btn ghost btn-sm" data-close-modal>Cerrar</button>
      </div>
    </div>

    <div class="detail-meta-grid">
      <div class="meta-item">
        <div class="meta-label">Autor original</div>
        <div class="meta-val">${autorOrig}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Responsable</div>
        <div class="meta-val">${respOrig}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Fecha del hecho</div>
        <div class="meta-val">${esc(e.fecha_hecho)}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Área / Solicitante</div>
        <div class="meta-val">${esc(e.area_nombre || "—")} · ${esc(e.solicitante || "—")}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Creado / Cerrado</div>
        <div class="meta-val">${esc(fmtFecha(e.creado_en))} / ${esc(fmtFecha(e.cerrado_en))}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Referencia</div>
        <div class="meta-val">${esc(e.referencia || "—")}</div>
      </div>
    </div>

    <div class="ficha-body">
      <h3>Descripción documental</h3>
      <p>${esc(e.descripcion)}</p>
    </div>

    <div class="modal-section">
      <h3>Notas de seguimiento (${notas.length})</h3>
      <div class="notas-list">
        ${notas.length ? notas.map((n) => `
          <div class="nota-item">
            <div class="nota-head">
              <strong>${etiquetaCuenta(n.autor_nombre, n.autor_estado)}</strong>
              <span>${esc(fmtFecha(n.creado_en))}</span>
            </div>
            <p class="nota-text">${esc(n.nota)}</p>
          </div>`).join("") : `<div class="empty-state">Sin notas registradas.</div>`}
      </div>
    </div>

    <div class="modal-section">
      <h3>Compromisos (${compromisos.length})</h3>
      ${compromisos.length ? `<div class="table-wrap"><table class="data">
        <thead><tr><th>Fecha límite</th><th>Descripción</th><th>Responsable</th><th>Estado</th></tr></thead>
        <tbody>${compromisos.map((c) => `<tr>
          <td class="cell-nowrap">${esc(c.fecha_limite)}</td>
          <td>${esc(c.descripcion)}</td>
          <td>${etiquetaCuenta(c.responsable_nombre, c.responsable_estado)}</td>
          <td>${c.vencido ? badge("VENCIDO") : badge(c.estado)}</td>
        </tr>`).join("")}</tbody></table></div>` : `<div class="empty-state">Sin compromisos.</div>`}
    </div>

    <div class="modal-section">
      <h3>Auditoría de cambios (${auditoria.length})</h3>
      ${auditoria.length ? `<div class="table-wrap"><table class="data">
        <thead><tr><th>Fecha</th><th>Usuario</th><th>Campo</th><th>Antes</th><th>Después</th></tr></thead>
        <tbody>${auditoria.map((a) => `<tr>
          <td class="cell-nowrap">${esc(fmtFecha(a.creado_en))}</td>
          <td>${etiquetaCuenta(a.usuario_nombre, a.usuario_estado)}</td>
          <td><strong>${esc(a.campo)}</strong></td>
          <td class="muted">${esc(a.valor_anterior || "—")}</td>
          <td>${esc(a.valor_nuevo || "—")}</td>
        </tr>`).join("")}</tbody></table></div>` : `<div class="empty-state">Sin correcciones de cabecera.</div>`}
    </div>
  `);
  $("#doc-ficha-print").onclick = () => window.print();
}

async function abrirModalPurga(cuentaId, api, onDone = null) {
  let info;
  try {
    info = await api.superPurgaResumen(cuentaId);
  } catch (ex) {
    toast(ex.message, "error");
    return;
  }

  abrirModal(`
    <div class="modal-header">
      <div>
        <div class="row" style="gap:0.5rem;margin-bottom:0.25rem">
          <span class="badge ${esc(info.estado)}">${esc(info.estado)}</span>
          <span class="badge">${esc(info.rol)}</span>
        </div>
        <h2>Eliminar información de la base de datos</h2>
        <p class="muted text-sm" style="margin:0.15rem 0 0">${esc(info.nombre)} · ${esc(info.correo)}</p>
      </div>
      <button type="button" class="btn ghost btn-sm" data-close-modal>Cerrar</button>
    </div>

    <p class="alert-inline error" style="margin-bottom:0.9rem">
      Esta acción elimina permanentemente de PostgreSQL los registros seleccionados. No se puede deshacer.
    </p>

    <form id="form-purga" class="stack">
      <div class="row spread">
        <strong>Selecciona qué información deseas eliminar:</strong>
        <button type="button" class="btn soft btn-sm" id="purga-marcar-todo">Seleccionar todo</button>
      </div>

      <fieldset class="permisos-box">
        <legend>Datos asociados a la cuenta</legend>
        <div class="stack" style="gap:0.55rem">
          <label class="check-row">
            <input type="checkbox" name="eliminar_eventos_creados" />
            <span><strong>Eventos e incidencias creadas (${info.eventos_creados})</strong> <span class="muted">— incluye notas, compromisos y auditoría propios de esos eventos</span></span>
          </label>
          <label class="check-row">
            <input type="checkbox" name="eliminar_notas" />
            <span><strong>Notas de seguimiento en otros eventos (${info.notas_en_otros_eventos})</strong></span>
          </label>
          <label class="check-row">
            <input type="checkbox" name="eliminar_compromisos" />
            <span><strong>Compromisos asignados en otros eventos (${info.compromisos_en_otros_eventos})</strong></span>
          </label>
          <label class="check-row">
            <input type="checkbox" name="eliminar_auditorias" />
            <span><strong>Correcciones de auditoría realizadas (${info.auditorias_en_otros_eventos})</strong></span>
          </label>
          <label class="check-row">
            <input type="checkbox" name="eliminar_claves_api" />
            <span><strong>Claves API emitidas y su historial de usos (${info.claves_api})</strong></span>
          </label>
          <label class="check-row">
            <input type="checkbox" name="eliminar_actividades" />
            <span><strong>Bitácora cronológica de actividad (${info.actividades})</strong></span>
          </label>
        </div>
      </fieldset>

      <div class="meta-item" style="border-color:var(--danger-border);background:var(--danger-soft)">
        <label class="check-row" style="align-items:flex-start">
          <input type="checkbox" name="eliminar_cuenta" ${info.es_protegida ? "disabled" : ""} />
          <span>
            <strong style="color:var(--danger)">Eliminar también la cuenta completa de la base de datos</strong>
            <div class="muted text-sm" style="font-weight:400">
              ${info.es_protegida
                ? "Cuenta protegida (Superusuario actual o último Jefe activo): solo puedes depurar sus registros de prueba, no la cuenta."
                : "Borra definitivamente la cuenta y su expediente histórico junto con todas sus dependencias."}
            </div>
          </span>
        </label>
      </div>

      <p id="purga-error" class="alert-inline error" hidden></p>

      <div id="purga-confirm-box" class="panel hidden" style="border-color:var(--danger-border);background:var(--danger-soft);margin:0;padding:0.85rem">
        <p style="margin:0 0 0.65rem;font-weight:600;color:var(--danger)">
          ¿Confirmas que deseas eliminar permanentemente la información marcada de «${esc(info.nombre)}»?
        </p>
        <div class="row" style="justify-content:flex-end">
          <button type="button" class="btn ghost btn-sm" id="purga-volver">Cancelar</button>
          <button type="button" class="btn danger btn-sm" id="purga-confirmar-ok">Sí, eliminar permanentemente</button>
        </div>
      </div>

      <div class="row" id="purga-actions" style="justify-content:flex-end">
        <button type="button" class="btn ghost" data-close-modal>Cancelar</button>
        <button type="submit" class="btn danger">Eliminar información seleccionada</button>
      </div>
    </form>
  `, { sm: false });

  const form = $("#form-purga");
  const checksDatos = [...form.querySelectorAll('input[type="checkbox"]:not([name="eliminar_cuenta"])')];
  const checkCuenta = form.querySelector('input[name="eliminar_cuenta"]');

  checkCuenta?.addEventListener("change", () => {
    if (checkCuenta.checked) {
      checksDatos.forEach((ch) => { ch.checked = true; });
    }
  });

  $("#purga-marcar-todo").onclick = () => {
    const habilitar = !checksDatos.every((ch) => ch.checked);
    checksDatos.forEach((ch) => { ch.checked = habilitar; });
    if (checkCuenta && !checkCuenta.disabled) checkCuenta.checked = habilitar;
  };

  let payloadPendiente = null;

  form.onsubmit = (e) => {
    e.preventDefault();
    const err = $("#purga-error");
    err.hidden = true;
    const fd = new FormData(form);
    const payload = {
      eliminar_eventos_creados: fd.get("eliminar_eventos_creados") === "on",
      eliminar_notas: fd.get("eliminar_notas") === "on",
      eliminar_compromisos: fd.get("eliminar_compromisos") === "on",
      eliminar_auditorias: fd.get("eliminar_auditorias") === "on",
      eliminar_claves_api: fd.get("eliminar_claves_api") === "on",
      eliminar_actividades: fd.get("eliminar_actividades") === "on",
      eliminar_cuenta: fd.get("eliminar_cuenta") === "on",
    };

    if (!Object.values(payload).some(Boolean)) {
      err.textContent = "Marca al menos una categoría de información para eliminar.";
      err.hidden = false;
      return;
    }
    payloadPendiente = payload;
    $("#purga-confirm-box").classList.remove("hidden");
    $("#purga-actions").classList.add("hidden");
  };

  $("#purga-volver").onclick = () => {
    payloadPendiente = null;
    $("#purga-confirm-box").classList.add("hidden");
    $("#purga-actions").classList.remove("hidden");
  };

  $("#purga-confirmar-ok").onclick = async () => {
    if (!payloadPendiente) return;
    const btn = $("#purga-confirmar-ok");
    const err = $("#purga-error");
    btn.disabled = true;
    err.hidden = true;
    try {
      const r = await api.superPurgarCuenta(cuentaId, payloadPendiente);
      cerrarModal();
      const resumen = [
        r.eventos_eliminados ? `${r.eventos_eliminados} evento(s)` : null,
        r.notas_eliminadas ? `${r.notas_eliminadas} nota(s)` : null,
        r.compromisos_eliminados ? `${r.compromisos_eliminados} compromiso(s)` : null,
        r.auditorias_eliminadas ? `${r.auditorias_eliminadas} auditoría(s)` : null,
        r.claves_api_eliminadas ? `${r.claves_api_eliminadas} clave(s)` : null,
        r.actividades_eliminadas ? `${r.actividades_eliminadas} movimiento(s)` : null,
        r.cuenta_eliminada ? "cuenta eliminada" : null,
      ].filter(Boolean).join(", ");
      toast(`Información eliminada: ${resumen || "completado"}`, "ok");
      if (onDone) await onDone();
    } catch (ex) {
      err.textContent = ex.message;
      err.hidden = false;
      btn.disabled = false;
    }
  };
}

async function verExpedienteCuenta(cuentaId, api, onDone = null) {
  let exp;
  try {
    exp = await api.superExpediente(cuentaId);
  } catch (ex) {
    toast(ex.message, "error");
    return;
  }
  const c = exp.cuenta;
  abrirModal(`
    <div class="modal-header">
      <div>
        <div class="row" style="gap:0.5rem;margin-bottom:0.25rem">
          <span class="badge ${esc(c.estado)}">${esc(c.estado)}</span>
          <span class="badge">${esc(c.rol_custom_nombre || c.rol)}</span>
        </div>
        <h2>Expediente documental: ${esc(c.nombre)}</h2>
        <p class="muted text-sm" style="margin:0.15rem 0 0">${esc(c.correo)}</p>
      </div>
      <div class="row">
        <button type="button" class="btn danger btn-sm" id="exp-purgar">Eliminar datos</button>
        <button type="button" class="btn soft btn-sm" id="exp-csv">Exportar CSV</button>
        <button type="button" class="btn soft btn-sm" id="exp-print">Imprimir</button>
        <button type="button" class="btn ghost btn-sm" data-close-modal>Cerrar</button>
      </div>
    </div>

    <div class="detail-meta-grid">
      <div class="meta-item">
        <div class="meta-label">Fecha de creación</div>
        <div class="meta-val">${esc(fmtFecha(c.creado_en))}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Estado de cuenta</div>
        <div class="meta-val">${esc(c.estado)}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Incidencias / Registros</div>
        <div class="meta-val">${exp.incidencias.length} / ${exp.registros.length}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Pendientes / Actividad</div>
        <div class="meta-val">${exp.pendientes.eventos.length + exp.pendientes.compromisos.length} / ${exp.actividades.length}</div>
      </div>
      ${c.eliminado_en ? `
      <div class="meta-item" style="grid-column:1 / -1;border-color:var(--danger-border);background:var(--danger-soft)">
        <div class="meta-label" style="color:var(--danger)">Cuenta eliminada</div>
        <div class="meta-val">El ${esc(fmtFecha(c.eliminado_en))} por ${esc(c.eliminado_por_nombre || "—")} (${esc(c.eliminado_por_correo || "—")})</div>
      </div>` : ""}
    </div>

    <div class="doc-section">
      <h3>Incidencias registradas (${exp.incidencias.length})</h3>
      ${tablaRegistrosDoc(exp.incidencias, "Esta cuenta no registra incidencias.")}
    </div>

    <div class="doc-section">
      <h3>Pendientes actuales (${exp.pendientes.eventos.length} eventos · ${exp.pendientes.compromisos.length} compromisos)</h3>
      ${tablaRegistrosDoc(exp.pendientes.eventos, "Sin eventos abiertos.")}
      ${exp.pendientes.compromisos.length ? `
        <div class="table-wrap" style="margin-top:0.65rem"><table class="data">
          <thead><tr><th>Fecha límite</th><th>Folio</th><th>Compromiso</th><th>Estado</th></tr></thead>
          <tbody>${exp.pendientes.compromisos.map((cp) => `<tr>
            <td class="cell-nowrap">${esc(cp.fecha_limite)}</td>
            <td class="folio-cell">${esc(cp.evento_folio)}</td>
            <td>${esc(cp.descripcion)}</td>
            <td>${cp.vencido ? badge("VENCIDO") : badge("pendiente")}</td>
          </tr>`).join("")}</tbody></table></div>` : ""}
    </div>

    <div class="doc-section">
      <h3>Todos los registros de la cuenta (${exp.registros.length})</h3>
      ${tablaRegistrosDoc(exp.registros, "Sin registros asociados.")}
    </div>

    <div class="doc-section">
      <h3>Archivos y exportaciones realizadas (${exp.exportaciones.length})</h3>
      ${listaActividadHtml(exp.exportaciones, "No realizó exportaciones CSV.")}
    </div>

    <div class="doc-section">
      <h3>Bitácora cronológica de actividad (${exp.actividades.length})</h3>
      ${listaActividadHtml(exp.actividades, "Sin eventos de actividad registrados.")}
    </div>
  `);

  $("#exp-purgar").onclick = () => abrirModalPurga(c.id, api, onDone);
  $("#exp-csv").onclick = () => descargarCsv(
    api,
    { seccion: "expediente", cuenta_id: c.id },
    `expediente-${c.correo.replace(/[^a-z0-9]/gi, "_")}.csv`,
  );
  $("#exp-print").onclick = () => window.print();
}

/* ========================== VISTAS DEL PORTAL ========================== */

export async function vistaSuperadmin(box, path, ctx) {
  const { api } = ctx;
  if (!api.esSuperusuario) {
    box.innerHTML = `<div class="panel"><p class="alert-inline error">Acceso restringido al rol de Superusuario.</p></div>`;
    return;
  }

  const sub = path.replace(/^\/super\/?/, "") || "resumen";
  if (sub === "resumen") await renderResumen(box, api);
  else if (sub === "cuentas") await renderCuentas(box, api);
  else if (sub === "registros") await renderRegistros(box, api);
  else if (sub === "pendientes") await renderPendientes(box, api);
  else if (sub === "archivos") await renderArchivos(box, api);
  else if (sub === "actividad") await renderActividad(box, api);
  else if (sub === "perfil") await renderPerfil(box, api, ctx);
  else await renderResumen(box, api);

  box.onclick = async (e) => {
    const trFolio = e.target.closest("[data-super-folio]");
    if (trFolio) {
      await verFichaDocumental(trFolio.dataset.superFolio, api);
      return;
    }
    const btnExp = e.target.closest("[data-expediente]");
    if (btnExp) {
      await verExpedienteCuenta(btnExp.dataset.expediente, api, () => ctx.enrutar?.());
      return;
    }
    const btnPurga = e.target.closest("[data-purgar]");
    if (btnPurga) {
      await abrirModalPurga(btnPurga.dataset.purgar, api, () => ctx.enrutar?.());
      return;
    }
    if (e.target.id === "sup-print") {
      window.print();
      return;
    }
    if (e.target.id === "sup-export-csv") {
      const sec = e.target.dataset.sec || "actividad";
      const cid = e.target.dataset.cid || undefined;
      await descargarCsv(api, { seccion: sec, cuenta_id: cid }, `dossier-${sec}.csv`);
    }
  };
}

async function renderResumen(box, api) {
  const [r, cuentas, actividad] = await Promise.all([
    api.superResumen(),
    api.superCuentas(),
    api.superActividad({ limit: 15 }),
  ]);

  box.innerHTML = `
    ${bannerSuper({
      titulo: "Portal de Superusuario · Auditoría y Documentación",
      subtitulo: "Trazabilidad completa de todas las cuentas (activas, inactivas y eliminadas), incidencias, pendientes, archivos y actividad.",
      exportSeccion: "actividad",
    })}

    <div class="stats-strip">
      <div class="stat-card accent">
        <div class="stat-label">Cuentas históricas</div>
        <div class="stat-value">${r.cuentas_total}</div>
        <div class="muted text-sm">${r.cuentas_activas} activas · ${r.cuentas_inactivas} inactivas · ${r.cuentas_eliminadas} eliminadas</div>
      </div>
      <div class="stat-card warn">
        <div class="stat-label">Incidencias totales</div>
        <div class="stat-value">${r.incidencias_total}</div>
        <div class="muted text-sm">De ${r.eventos_total} registros en bitácora</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Pendientes globales</div>
        <div class="stat-value">${r.pendientes_eventos}</div>
        <div class="muted text-sm">${r.pendientes_compromisos} compromiso(s) · ${r.compromisos_vencidos} vencido(s)</div>
      </div>
      <div class="stat-card ok">
        <div class="stat-label">Archivos y actividad</div>
        <div class="stat-value">${r.archivos_total}</div>
        <div class="muted text-sm">${r.actividades_total} evento(s) en bitácora</div>
      </div>
    </div>

    <section class="panel">
      <div class="panel-header">
        <h2>Cuentas registradas y eliminadas (${cuentas.length})</h2>
        <a href="#/super/cuentas" class="btn soft btn-sm">Ver todas las cuentas</a>
      </div>
      <div class="table-wrap"><table class="data admin-table">
        <thead><tr><th>Cuenta</th><th>Rol</th><th>Estado</th><th>Incidencias</th><th>Registros</th><th>Pendientes</th><th>Expediente</th></tr></thead>
        <tbody>${cuentas.slice(0, 8).map((c) => `<tr>
          <td><strong>${esc(c.nombre)}</strong><div class="muted text-sm">${esc(c.correo)}</div></td>
          <td>${esc(c.rol_custom_nombre || c.rol)}</td>
          <td><span class="badge ${esc(c.estado)}">${esc(c.estado)}</span></td>
          <td>${c.incidencias_creadas}</td>
          <td>${c.eventos_creados}</td>
          <td>${c.pendientes_abiertos}</td>
          <td><div class="cell-actions">
            <button type="button" class="btn soft btn-sm" data-expediente="${c.id}">Ver expediente</button>
            <button type="button" class="btn danger btn-sm" data-purgar="${c.id}">Eliminar datos</button>
          </div></td>
        </tr>`).join("")}</tbody>
      </table></div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <h2>Última actividad del sistema</h2>
        <a href="#/super/actividad" class="btn soft btn-sm">Ver bitácora completa</a>
      </div>
      ${listaActividadHtml(actividad)}
    </section>`;
}

async function renderCuentas(box, api) {
  const cuentas = await api.superCuentas();
  box.innerHTML = `
    ${bannerSuper({
      titulo: "Historial de Cuentas",
      subtitulo: "Consulta todas las cuentas creadas históricamente, incluso aquellas eliminadas por administración.",
      exportSeccion: "cuentas",
    })}
    <section class="panel stack">
      <div class="filters-bar" style="justify-content:space-between">
        <div class="row" style="flex:1;min-width:240px">
          <input id="sc-q" placeholder="Buscar por nombre, correo o rol…" style="max-width:320px" />
          <select id="sc-est" style="width:auto;min-width:170px">
            <option value="">Todas (${cuentas.length})</option>
            <option value="activa">Activas (${cuentas.filter((c) => c.estado === "activa").length})</option>
            <option value="inactiva">Inactivas (${cuentas.filter((c) => c.estado === "inactiva").length})</option>
            <option value="eliminada">Eliminadas (${cuentas.filter((c) => c.estado === "eliminada").length})</option>
          </select>
          <span id="sc-count" class="muted text-sm"></span>
        </div>
      </div>
      <div class="table-wrap"><table class="data admin-table">
        <thead><tr>
          <th>Nombre y correo</th>
          <th>Rol</th>
          <th>Estado</th>
          <th>Creada / Eliminada</th>
          <th>Incidencias</th>
          <th>Registros</th>
          <th>Pendientes</th>
          <th>Actividad</th>
          <th>Documentación</th>
        </tr></thead>
        <tbody id="sc-tbody"></tbody>
      </table></div>
    </section>`;

  const pintar = () => {
    const q = ($("#sc-q").value || "").trim().toLowerCase();
    const est = $("#sc-est").value;
    const fil = cuentas.filter((c) => {
      if (est && c.estado !== est) return false;
      if (!q) return true;
      return c.nombre.toLowerCase().includes(q) || c.correo.toLowerCase().includes(q) ||
        c.rol.toLowerCase().includes(q) || (c.rol_custom_nombre || "").toLowerCase().includes(q);
    });
    $("#sc-count").textContent = `${fil.length} cuenta(s)`;
    $("#sc-tbody").innerHTML = fil.length
      ? fil.map((c) => `<tr>
          <td><strong>${esc(c.nombre)}</strong><div class="muted text-sm">${esc(c.correo)}</div></td>
          <td>${esc(c.rol_custom_nombre || c.rol)}</td>
          <td><span class="badge ${esc(c.estado)}">${esc(c.estado)}</span></td>
          <td class="text-sm">
            <div>Creada: ${esc(fmtFecha(c.creado_en))}</div>
            ${c.eliminado_en ? `<div style="color:var(--danger)">Eliminada: ${esc(fmtFecha(c.eliminado_en))} (${esc(c.eliminado_por_nombre || "—")})</div>` : ""}
          </td>
          <td>${c.incidencias_creadas}</td>
          <td>${c.eventos_creados}</td>
          <td>${c.pendientes_abiertos}</td>
          <td>${c.actividades_count}</td>
          <td><div class="cell-actions">
            <button type="button" class="btn soft btn-sm" data-expediente="${c.id}">Ver expediente</button>
            <button type="button" class="btn danger btn-sm" data-purgar="${c.id}">Eliminar datos</button>
          </div></td>
        </tr>`).join("")
      : `<tr><td colspan="9"><div class="empty-state" style="border:0">Sin cuentas que coincidan.</div></td></tr>`;
  };

  $("#sc-q").addEventListener("input", pintar);
  $("#sc-est").addEventListener("change", pintar);
  pintar();
}

async function renderRegistros(box, api) {
  const [cuentas, iniciales] = await Promise.all([api.superCuentas(), api.superRegistros()]);
  box.innerHTML = `
    ${bannerSuper({
      titulo: "Incidencias y Registros Históricos",
      subtitulo: "Todos los eventos e incidencias conservando el autor y responsable originales.",
      exportSeccion: "registros",
    })}
    <section class="panel stack">
      <div class="filters-bar">
        <input id="sr-q" class="grow" placeholder="Buscar por folio, título, descripción o usuario…" />
        <select id="sr-cuenta" style="min-width:210px">
          <option value="">Todas las cuentas</option>
          ${cuentas.map((c) => `<option value="${c.id}">${esc(c.nombre)} (${esc(c.estado)})</option>`).join("")}
        </select>
        <select id="sr-tipo">
          <option value="">Todos los tipos</option>
          ${TIPOS.map((t) => `<option value="${t}">${t}</option>`).join("")}
        </select>
        <select id="sr-estado">
          <option value="">Todos los estados</option>
          ${ESTADOS.map((s) => `<option value="${s}">${s.replaceAll("_", " ")}</option>`).join("")}
        </select>
        <button type="button" class="btn primary" id="sr-btn">Filtrar</button>
      </div>
      <div class="row spread">
        <span class="muted text-sm">Haz clic en cualquier fila para abrir su ficha documental imprimible.</span>
        <span id="sr-total" class="count-pill">${iniciales.length} registro(s)</span>
      </div>
      <div id="sr-res">${tablaRegistrosDoc(iniciales)}</div>
    </section>`;

  const filtrar = async () => {
    try {
      const cid = $("#sr-cuenta").value || undefined;
      const btnExp = $("#sup-export-csv");
      if (btnExp) btnExp.dataset.cid = cid || "";
      const filas = await api.superRegistros({
        q: $("#sr-q").value.trim() || undefined,
        cuenta_id: cid,
        tipo: $("#sr-tipo").value || undefined,
        estado: $("#sr-estado").value || undefined,
      });
      $("#sr-total").textContent = `${filas.length} registro(s)`;
      $("#sr-res").innerHTML = tablaRegistrosDoc(filas);
    } catch (ex) {
      toast(ex.message, "error");
    }
  };
  $("#sr-btn").onclick = filtrar;
  $("#sr-cuenta").addEventListener("change", filtrar);
  $("#sr-q").addEventListener("keydown", (e) => { if (e.key === "Enter") filtrar(); });
}

async function renderPendientes(box, api) {
  const [cuentas, data] = await Promise.all([api.superCuentas(), api.superPendientes()]);
  box.innerHTML = `
    ${bannerSuper({
      titulo: "Pendientes Globales",
      subtitulo: "Seguimiento de eventos abiertos y compromisos pendientes en todas las cuentas.",
    })}
    <section class="panel stack">
      <div class="filters-bar" style="justify-content:space-between">
        <select id="sp-cuenta" style="min-width:240px">
          <option value="">Todas las cuentas</option>
          ${cuentas.map((c) => `<option value="${c.id}">${esc(c.nombre)} (${esc(c.estado)})</option>`).join("")}
        </select>
        <span id="sp-info" class="count-pill">${data.eventos.length} evento(s) · ${data.compromisos.length} compromiso(s)</span>
      </div>
      <h3>Eventos abiertos con seguimiento</h3>
      <div id="sp-ev">${tablaRegistrosDoc(data.eventos, "No hay eventos pendientes.")}</div>
      <h3>Compromisos pendientes</h3>
      <div id="sp-co"></div>
    </section>`;

  const pintarComps = (comps) => {
    $("#sp-co").innerHTML = comps.length
      ? `<div class="table-wrap"><table class="data">
          <thead><tr><th>Fecha límite</th><th>Folio</th><th>Evento</th><th>Compromiso</th><th>Responsable</th><th>Estado</th></tr></thead>
          <tbody>${comps.map((c) => `<tr data-super-folio="${esc(c.evento_folio)}" style="cursor:pointer">
            <td class="cell-nowrap">${esc(c.fecha_limite)}</td>
            <td class="folio-cell">${esc(c.evento_folio)}</td>
            <td>${esc(c.evento_titulo)}</td>
            <td><strong>${esc(c.descripcion)}</strong></td>
            <td>${etiquetaCuenta(c.responsable_nombre, c.responsable_estado)}</td>
            <td>${c.vencido ? badge("VENCIDO") : badge("pendiente")}</td>
          </tr>`).join("")}</tbody></table></div>`
      : `<div class="empty-state">No hay compromisos pendientes.</div>`;
  };
  pintarComps(data.compromisos);

  $("#sp-cuenta").onchange = async () => {
    const cid = $("#sp-cuenta").value || undefined;
    const d = await api.superPendientes({ cuenta_id: cid });
    $("#sp-info").textContent = `${d.eventos.length} evento(s) · ${d.compromisos.length} compromiso(s)`;
    $("#sp-ev").innerHTML = tablaRegistrosDoc(d.eventos, "No hay eventos pendientes para esta cuenta.");
    pintarComps(d.compromisos);
  };
}

async function renderArchivos(box, api) {
  const data = await api.superArchivos();
  box.innerHTML = `
    ${bannerSuper({
      titulo: "Archivos, Exportaciones y Respaldos",
      subtitulo: "Inventario documental de archivos exportados, respaldos en disco y referencias de eventos.",
    })}

    <section class="panel">
      <div class="panel-header">
        <h2>Exportaciones CSV registradas (${data.exportaciones.length})</h2>
      </div>
      ${listaActividadHtml(data.exportaciones, "Aún no se han registrado exportaciones CSV.")}
    </section>

    <section class="panel">
      <div class="panel-header">
        <h2>Respaldos de base de datos (${data.respaldos.length})</h2>
      </div>
      ${data.respaldos.length ? `<div class="table-wrap"><table class="data">
        <thead><tr><th>Archivo</th><th>Tamaño</th><th>Última modificación</th></tr></thead>
        <tbody>${data.respaldos.map((f) => `<tr>
          <td class="mono text-sm"><strong>${esc(f.nombre)}</strong></td>
          <td class="cell-nowrap">${esc(fmtBytes(f.tamano_bytes))}</td>
          <td class="cell-nowrap muted">${esc(fmtFecha(f.modificado_en))}</td>
        </tr>`).join("")}</tbody></table></div>` : `<div class="empty-state">No hay archivos de respaldo en la carpeta respaldos/.</div>`}
    </section>

    <section class="panel">
      <div class="panel-header">
        <h2>Referencias / documentos adjuntos en eventos (${data.referencias.length})</h2>
      </div>
      ${data.referencias.length ? `<div class="table-wrap"><table class="data">
        <thead><tr><th>Folio</th><th>Fecha</th><th>Tipo</th><th>Título</th><th>Referencia</th><th>Autor original</th></tr></thead>
        <tbody>${data.referencias.map((r) => `<tr data-super-folio="${esc(r.folio)}" style="cursor:pointer">
          <td class="folio-cell">${esc(r.folio)}</td>
          <td class="cell-nowrap">${esc(r.fecha_hecho)}</td>
          <td><span class="badge ${esc(r.tipo)}">${esc(r.tipo)}</span></td>
          <td><strong>${esc(r.titulo)}</strong></td>
          <td class="mono text-sm">${esc(r.referencia)}</td>
          <td>${etiquetaCuenta(r.autor_nombre, r.autor_estado)}</td>
        </tr>`).join("")}</tbody></table></div>` : `<div class="empty-state">No hay eventos con referencia documental registrada.</div>`}
    </section>`;
}

async function renderActividad(box, api) {
  const [cuentas, acts] = await Promise.all([api.superCuentas(), api.superActividad({ limit: 250 })]);
  box.innerHTML = `
    ${bannerSuper({
      titulo: "Bitácora Cronológica de Actividad",
      subtitulo: "Registro inmutable de inicios de sesión, altas, ediciones, eliminaciones y seguimiento operativo.",
      exportSeccion: "actividad",
    })}
    <section class="panel stack">
      <div class="filters-bar">
        <input id="sa-q" class="grow" placeholder="Buscar por acción, folio, usuario o detalle…" />
        <select id="sa-cuenta" style="min-width:210px">
          <option value="">Todas las cuentas</option>
          ${cuentas.map((c) => `<option value="${c.id}">${esc(c.nombre)} (${esc(c.estado)})</option>`).join("")}
        </select>
        <select id="sa-entidad">
          <option value="">Todas las entidades</option>
          <option value="evento">Eventos / Incidencias</option>
          <option value="usuario">Cuentas de usuario</option>
          <option value="compromiso">Compromisos</option>
          <option value="archivo">Archivos / Exportaciones</option>
          <option value="sesion">Sesiones</option>
          <option value="area">Áreas</option>
          <option value="clave_api">Claves API</option>
        </select>
        <input type="date" id="sa-desde" aria-label="Desde" />
        <input type="date" id="sa-hasta" aria-label="Hasta" />
        <button type="button" class="btn primary" id="sa-btn">Filtrar</button>
      </div>
      <div class="row spread">
        <span class="muted text-sm">Mostrando hasta 250 registros más recientes por consulta.</span>
        <span id="sa-total" class="count-pill">${acts.length} movimiento(s)</span>
      </div>
      <div id="sa-lista">${listaActividadHtml(acts)}</div>
    </section>`;

  const filtrar = async () => {
    try {
      const cid = $("#sa-cuenta").value || undefined;
      const btnExp = $("#sup-export-csv");
      if (btnExp) btnExp.dataset.cid = cid || "";
      const filas = await api.superActividad({
        q: $("#sa-q").value.trim() || undefined,
        cuenta_id: cid,
        entidad: $("#sa-entidad").value || undefined,
        desde: $("#sa-desde").value || undefined,
        hasta: $("#sa-hasta").value || undefined,
        limit: 500,
      });
      $("#sa-total").textContent = `${filas.length} movimiento(s)`;
      $("#sa-lista").innerHTML = listaActividadHtml(filas);
    } catch (ex) {
      toast(ex.message, "error");
    }
  };
  $("#sa-btn").onclick = filtrar;
  $("#sa-cuenta").addEventListener("change", filtrar);
  $("#sa-q").addEventListener("keydown", (e) => { if (e.key === "Enter") filtrar(); });
}

async function renderPerfil(box, api, ctx) {
  const u = await api.yo().catch(() => api.usuario);
  box.innerHTML = `
    ${bannerSuper({
      titulo: "Mi perfil · Superusuario",
      subtitulo: "Actualiza tu nombre, correo electrónico o contraseña de acceso con verificación de identidad.",
    })}

    <div class="super-profile-grid">
      <section class="panel">
        <div class="profile-card-head">
          <span class="profile-avatar-lg">${esc(iniciales(u.nombre))}</span>
          <div>
            <h2 style="margin:0">${esc(u.nombre)}</h2>
            <div class="muted text-sm">${esc(u.correo)}</div>
          </div>
        </div>

        <div class="profile-meta-list">
          <div class="meta-item">
            <div class="meta-label">Rol del sistema</div>
            <div class="meta-val"><span class="badge abierto">${esc(u.rol)}</span></div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Estado de la cuenta</div>
            <div class="meta-val"><span class="badge activo">activa</span></div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Seguridad de sesiones</div>
            <div class="meta-val text-sm muted" style="font-weight:400">
              Al cambiar tu contraseña, cualquier sesión abierta en otros dispositivos caducará automáticamente y tu historial quedará registrado en la bitácora.
            </div>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <h2>Editar credenciales y datos de acceso</h2>
        </div>

        <form id="form-super-perfil" class="stack">
          <label class="field">
            <span>Nombre completo</span>
            <input name="nombre" required maxlength="120" value="${esc(u.nombre)}" />
          </label>

          ${campoCorreoHtml({ name: "correo", label: "Correo electrónico", value: u.correo })}

          ${campoClaveHtml({
            name: "clave_nueva",
            label: "Nueva contraseña (opcional: déjalo vacío si no deseas cambiarla)",
            placeholder: "Mínimo 8 caracteres (letras y números)",
            required: false,
          })}

          ${campoClaveSimpleHtml({
            name: "clave_confirmar",
            label: "Confirmar nueva contraseña",
            placeholder: "Repite la nueva contraseña",
            required: false,
            autocomplete: "new-password",
          })}

          ${campoClaveSimpleHtml({
            name: "clave_actual",
            label: "Contraseña actual (obligatoria para guardar cambios)",
            placeholder: "Ingresa tu contraseña actual",
            required: true,
            autocomplete: "current-password",
          })}

          <p id="sp-perfil-error" class="alert-inline error" hidden></p>

          <div class="row" style="justify-content:flex-end">
            <button type="submit" class="btn primary">Guardar cambios</button>
          </div>
        </form>
      </section>
    </div>`;

  enlazarCriterios(box);

  $("#form-super-perfil").onsubmit = async (e) => {
    e.preventDefault();
    const err = $("#sp-perfil-error");
    err.hidden = true;
    const btn = e.target.querySelector('[type="submit"]');
    const fd = new FormData(e.target);

    const nombre = String(fd.get("nombre") || "").trim();
    const correo = String(fd.get("correo") || "").trim().toLowerCase();
    const claveNueva = String(fd.get("clave_nueva") || "");
    const claveConfirmar = String(fd.get("clave_confirmar") || "");
    const claveActual = String(fd.get("clave_actual") || "");

    try {
      if (!nombre) throw new ErrorApi("El nombre no puede estar vacío.");
      validarCorreoCriterios(correo);

      if (claveNueva || claveConfirmar) {
        validarClaveCriterios(claveNueva);
        if (claveNueva !== claveConfirmar) {
          throw new ErrorApi("La nueva contraseña y su confirmación no coinciden.");
        }
      }

      const payload = { clave_actual: claveActual };
      if (nombre !== u.nombre) payload.nombre = nombre;
      if (correo !== u.correo) payload.correo = correo;
      if (claveNueva) payload.clave_nueva = claveNueva;

      if (!payload.nombre && !payload.correo && !payload.clave_nueva) {
        throw new ErrorApi("No realizaste cambios respecto a tus datos actuales.");
      }

      btn.disabled = true;
      await api.actualizarPerfil(payload);
      ctx?.refrescarUsuario?.();
      toast("Perfil actualizado correctamente", "ok");
      await renderPerfil(box, api, ctx);
    } catch (ex) {
      err.textContent = ex.message;
      err.hidden = false;
      btn.disabled = false;
    }
  };
}
