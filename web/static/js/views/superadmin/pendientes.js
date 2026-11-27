import { esc } from "../../services/api.js";
import { $, badge } from "../../components/ui.js";
import { bannerSuper, etiquetaCuenta, tablaRegistrosDoc } from "./shared.js";

export async function renderPendientes(box, api) {
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
