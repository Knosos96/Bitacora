import { ESTADOS, TIPOS, esc } from "../../services/api.js";
import { $, toast } from "../../components/ui.js";
import { bannerSuper, tablaRegistrosDoc } from "./shared.js";

export async function renderRegistros(box, api) {
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
