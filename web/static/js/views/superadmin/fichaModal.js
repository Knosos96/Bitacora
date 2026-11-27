import { esc } from "../../services/api.js";
import { $, abrirModal, badge, toast } from "../../components/ui.js";
import { etiquetaCuenta, fmtFecha } from "./shared.js";

export async function verFichaDocumental(folio, api) {
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
