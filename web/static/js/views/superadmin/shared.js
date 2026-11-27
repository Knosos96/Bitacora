import { esc } from "../../services/api.js";
import { badge, toast } from "../../components/ui.js";

export function fmtFecha(iso) {
  if (!iso) return "—";
  return String(iso).slice(0, 16).replace("T", " ");
}

export function fmtBytes(bytes) {
  const n = Number(bytes || 0);
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
}

export function etiquetaCuenta(nombre, estado) {
  if (!nombre) return `<span class="muted">—</span>`;
  if (estado === "eliminada") {
    return `${esc(nombre)} <span class="badge eliminada">eliminada</span>`;
  }
  if (estado === "inactiva") {
    return `${esc(nombre)} <span class="badge inactiva">inactiva</span>`;
  }
  return esc(nombre);
}

export async function descargarCsv(api, params, nombreArchivo) {
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

export function bannerSuper({ titulo, subtitulo, exportSeccion, cuentaId = null }) {
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

export function tablaRegistrosDoc(filas, vacio = "Sin registros históricos para mostrar.") {
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

export function listaActividadHtml(filas, vacio = "No hay actividad registrada.") {
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
