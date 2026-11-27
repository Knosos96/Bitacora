import { esc } from "../../services/api.js";
import { $, toast } from "../../components/ui.js";
import { bannerSuper, listaActividadHtml } from "./shared.js";

export async function renderActividad(box, api) {
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
