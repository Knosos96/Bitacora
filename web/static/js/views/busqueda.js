import { ESTADOS, TIPOS } from "../services/api.js";
import { $, tablaEventos, toast } from "../components/ui.js";

export async function vistaBusqueda(box, _params, { api }) {
  box.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="section-title">Búsqueda histórica</h1>
        <p class="section-sub">Encuentra eventos por texto, folio, tipo, estado o rango de fechas.</p>
      </div>
      ${api.puedeExportar ? `<button type="button" class="btn soft" id="bq-csv">Exportar CSV</button>` : ""}
    </div>

    <section class="panel stack">
      <div class="filters-bar">
        <input id="bq-q" class="grow" placeholder="Buscar por palabra clave, solicitante, nota o folio (ej. BIT-2026-00001)…" />
        <select id="bq-tipo" aria-label="Tipo">
          <option value="">Todos los tipos</option>
          ${TIPOS.map((t) => `<option value="${t}">${t}</option>`).join("")}
        </select>
        <select id="bq-estado" aria-label="Estado">
          <option value="">Todos los estados</option>
          ${ESTADOS.map((t) => `<option value="${t}">${t.replaceAll("_", " ")}</option>`).join("")}
        </select>
        <select id="bq-seg" aria-label="Seguimiento">
          <option value="">Seguimiento: todos</option>
          <option value="con">Con seguimiento</option>
          <option value="sin">Sin seguimiento</option>
        </select>
      </div>

      <div class="filters-bar" style="justify-content:space-between">
        <div class="row">
          <label class="field" style="min-width:150px">Desde
            <input type="date" id="bq-desde" />
          </label>
          <label class="field" style="min-width:150px">Hasta
            <input type="date" id="bq-hasta" />
          </label>
          <label class="check-row" style="margin-top:1.2rem">
            <input type="checkbox" id="bq-venc" />
            <span>Solo con vencidos</span>
          </label>
        </div>
        <div class="row">
          <button type="button" class="btn ghost" id="bq-limpiar">Limpiar</button>
          <button type="button" class="btn primary" id="bq-btn">Buscar</button>
        </div>
      </div>

      <div class="row spread">
        <span class="muted text-sm">Sin fechas y con filtros se busca en todo el histórico.</span>
        <span id="bq-total" class="count-pill hidden"></span>
      </div>

      <div id="bq-res">
        <div class="empty-state">Aplica filtros o escribe un término y presiona <strong>Buscar</strong>.</div>
      </div>
    </section>`;

  const filtros = () => ({
    q: $("#bq-q").value.trim() || undefined,
    desde: $("#bq-desde").value || undefined,
    hasta: $("#bq-hasta").value || undefined,
    tipo: $("#bq-tipo").value || undefined,
    estado: $("#bq-estado").value || undefined,
    seguimiento: $("#bq-seg").value || undefined,
    vencidos: $("#bq-venc").checked || undefined,
    page_size: 200,
  });

  const buscar = async () => {
    try {
      const r = await api.eventos(filtros());
      $("#bq-res").innerHTML = tablaEventos(r.data, {
        fragmento: true,
        vacio: "No se encontraron coincidencias para los filtros seleccionados.",
      });
      const n = r.meta.total;
      const badgeEl = $("#bq-total");
      badgeEl.textContent = `${n} resultado(s)` + (n > 200 ? " (mostrando 200)" : "");
      badgeEl.classList.remove("hidden");
    } catch (ex) {
      toast(ex.message, "error");
    }
  };

  $("#bq-btn").onclick = buscar;
  $("#bq-limpiar").onclick = () => {
    $("#bq-q").value = "";
    $("#bq-desde").value = "";
    $("#bq-hasta").value = "";
    $("#bq-tipo").value = "";
    $("#bq-estado").value = "";
    $("#bq-seg").value = "";
    $("#bq-venc").checked = false;
    $("#bq-total").classList.add("hidden");
    $("#bq-res").innerHTML = `<div class="empty-state">Filtros limpiados. Presiona <strong>Buscar</strong> para consultar.</div>`;
  };
  $("#bq-q").addEventListener("keydown", (e) => { if (e.key === "Enter") buscar(); });

  if ($("#bq-csv")) {
    $("#bq-csv").onclick = async () => {
      try {
        const blob = await api.exportarCsv(filtros());
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "bitacora.csv";
        a.click();
        URL.revokeObjectURL(a.href);
        toast("Archivo CSV descargado", "ok");
      } catch (ex) {
        toast(ex.message, "error");
      }
    };
  }
}

