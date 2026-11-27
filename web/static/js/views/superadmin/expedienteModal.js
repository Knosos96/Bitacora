import { esc } from "../../services/api.js";
import { $, abrirModal, badge, toast } from "../../components/ui.js";
import { abrirModalPurga } from "./purgaModal.js";
import { descargarCsv, fmtFecha, listaActividadHtml, tablaRegistrosDoc } from "./shared.js";

export async function verExpedienteCuenta(cuentaId, api, onDone = null) {
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
