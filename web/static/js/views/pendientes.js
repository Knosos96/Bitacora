import { esc } from "../services/api.js";
import { $, badge, tablaEventos } from "../components/ui.js";

export async function vistaPendientes(box, params, { api }) {
  const soloVencidos = params.get("vencidos") === "1";

  box.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="section-title">Pendientes</h1>
        <p class="section-sub">Eventos abiertos con seguimiento y compromisos activos.</p>
      </div>
      <label class="check-row" style="background:var(--surface);border:1px solid var(--line);padding:0.5rem 0.9rem;border-radius:999px">
        <input type="checkbox" id="pen-venc" ${soloVencidos ? "checked" : ""} />
        <span>Mostrar solo vencidos</span>
      </label>
    </div>

    <div class="stats-strip" id="pen-stats"></div>

    <section class="panel">
      <div class="panel-header">
        <h2>Eventos con seguimiento abierto</h2>
      </div>
      <div id="pen-ev"></div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <h2>Compromisos pendientes</h2>
      </div>
      <div id="pen-co"></div>
    </section>`;

  const cargar = async () => {
    const r = await api.pendientes({ solo_vencidos: $("#pen-venc").checked });
    const vencidosCount = r.compromisos.filter((c) => c.vencido).length;

    $("#pen-stats").innerHTML = `
      <div class="stat-card accent">
        <div class="stat-label">Eventos abiertos</div>
        <div class="stat-value">${r.eventos.length}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Compromisos pendientes</div>
        <div class="stat-value">${r.compromisos.length}</div>
      </div>
      <div class="stat-card ${vencidosCount ? "warn" : "ok"}">
        <div class="stat-label">Compromisos vencidos</div>
        <div class="stat-value">${vencidosCount}</div>
      </div>`;

    $("#pen-ev").innerHTML = tablaEventos(r.eventos, { vacio: "No hay eventos abiertos en esta vista." });
    $("#pen-co").innerHTML = r.compromisos.length
      ? `<div class="table-wrap"><table class="data">
          <thead><tr><th>Fecha límite</th><th>Evento</th><th>Compromiso</th><th>Responsable</th><th>Estado</th></tr></thead>
          <tbody>${r.compromisos.map((c) => `<tr data-folio="${esc(c.evento_folio)}">
            <td class="cell-nowrap">${esc(c.fecha_limite)}</td>
            <td class="folio-cell">${esc(c.evento_folio)}</td>
            <td><strong>${esc(c.descripcion)}</strong></td>
            <td class="cell-nowrap">${esc(c.responsable.nombre)}</td>
            <td>${c.vencido ? badge("VENCIDO") : badge("pendiente")}</td>
          </tr>`).join("")}</tbody></table></div>`
      : `<div class="empty-state">No hay compromisos pendientes.</div>`;
  };

  $("#pen-venc").onchange = cargar;
  await cargar();
}

