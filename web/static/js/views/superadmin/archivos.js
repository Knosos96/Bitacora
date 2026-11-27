import { esc } from "../../services/api.js";
import { bannerSuper, etiquetaCuenta, fmtBytes, fmtFecha, listaActividadHtml } from "./shared.js";

export async function renderArchivos(box, api) {
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
