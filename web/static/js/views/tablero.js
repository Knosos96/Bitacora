import { esc, hoy } from "../services/api.js";
import { $, abrirModal, badge, tablaEventos, toast } from "../components/ui.js";

const STOCK_IDS = new Set(["K3", "K4", "K8", "K9", "K11"]);

function detalleKpi(i) {
  const d = i.detalle || {};
  if (i.id === "K1") return Object.entries(d.por_tipo || {}).map(([t, n]) => `${t}: ${n}`).join(" · ");
  if (i.id === "K2") return `Con seguimiento: ${d.con_seguimiento} · Informativos: ${d.informativos}`;
  if (i.id === "K5") return `${d.cerrados} evento(s) cerrado(s)`;
  if (i.id === "K7") return `${d.cumplidos_a_tiempo} de ${d.total} cumplidos a tiempo`;
  if (i.id === "K9") return (d.por_responsable || []).map((p) => `${p.nombre}: ${p.abiertos}`).join(" · ");
  if (i.id === "K10") return (d.top || []).map((a) => `${a.nombre}: ${a.total}`).join(" · ");
  if (i.id === "K11" && d.folio) return `${d.folio} — ${d.titulo}`;
  return "";
}

export async function vistaTablero(box, { api }) {
  if (!api.puedeVerTablero) {
    box.innerHTML = `<div class="panel"><p class="alert-inline error">El tablero KPI está disponible únicamente para encargado, jefe o roles autorizados.</p></div>`;
    return;
  }

  box.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="section-title">Tablero de indicadores</h1>
        <p class="section-sub">Indicadores K1 a K12. Haz clic en cualquier tarjeta para ver el desglose.</p>
      </div>
      <span id="tb-info" class="count-pill">Semana actual</span>
    </div>

    <section class="panel stack">
      <div class="filters-bar" style="justify-content:space-between">
        <div class="row">
          <input type="date" id="tb-desde" aria-label="Desde" />
          <input type="date" id="tb-hasta" aria-label="Hasta" />
          <button type="button" class="btn primary" id="tb-aplicar">Aplicar</button>
        </div>
        <div class="row">
          <button type="button" class="btn soft btn-sm" id="tb-semana">Esta semana</button>
          <button type="button" class="btn soft btn-sm" id="tb-hoy">Hoy</button>
          <button type="button" class="btn soft btn-sm" id="tb-mes">Este mes</button>
        </div>
      </div>

      <p class="muted text-sm" style="margin:0">
        Nota: <strong>K3, K4, K8, K9 y K11</strong> reflejan el estado actual del momento y no dependen del rango seleccionado.
      </p>

      <div class="kpi-grid" id="tb-grid"></div>
    </section>`;

  let rango = [null, null];
  const cargar = async () => {
    try {
      const desde = $("#tb-desde").value || undefined;
      const hasta = $("#tb-hasta").value || undefined;
      const r = await api.tablero(desde, hasta);
      rango = [r.desde, r.hasta];
      $("#tb-info").textContent = `${r.desde} → ${r.hasta}`;
      $("#tb-grid").innerHTML = r.indicadores.map((i) => {
        const valor = i.valor == null ? "Sin datos" : `${i.valor}${i.unidad ? " " + i.unidad : ""}`;
        const clase = i.id === "K8" && i.valor > 0
          ? "kpi-alert"
          : STOCK_IDS.has(i.id)
            ? "kpi-stock"
            : "";
        return `<article class="kpi-card ${clase}" data-kid="${i.id}">
          <div class="kpi-top">
            <span class="id">${i.id}</span>
            <span class="muted text-sm">${STOCK_IDS.has(i.id) ? "En vivo" : "Rango"}</span>
          </div>
          <div class="kpi-name">${esc(i.nombre)}</div>
          <div class="val">${esc(valor)}</div>
          <div class="det">${esc(detalleKpi(i) || "Clic para ver detalle")}</div>
        </article>`;
      }).join("");
    } catch (ex) {
      toast(ex.message, "error");
    }
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
        <div class="modal-header">
          <h2>${esc(card.dataset.kid)} — ${esc(r.nombre)}</h2>
          <button type="button" class="btn ghost btn-sm" data-close-modal>Cerrar</button>
        </div>
        ${(!r.eventos.length && !r.compromisos.length)
          ? `<div class="empty-state">${esc(r.texto_vacio || "Sin resultados para este indicador.")}</div>`
          : (r.eventos.length ? tablaEventos(r.eventos) : "") + (r.compromisos.length ? `
            <div class="modal-section">
              <h3>Compromisos</h3>
              <div class="table-wrap"><table class="data">
                <thead><tr><th>Evento</th><th>Compromiso</th><th>Estado</th><th>Fecha límite</th></tr></thead>
                <tbody>${r.compromisos.map((c) => `<tr data-folio="${esc(c.evento_folio)}">
                  <td class="folio-cell">${esc(c.evento_folio)}</td>
                  <td><strong>${esc(c.descripcion)}</strong></td>
                  <td>${c.vencido ? badge("VENCIDO") : badge(c.estado)}</td>
                  <td class="cell-nowrap">${esc(c.fecha_limite)}</td>
                </tr>`).join("")}</tbody></table></div>
            </div>` : "")}`);
    } catch (ex) {
      toast(ex.message, "error");
    }
  };

  await cargar();
}

