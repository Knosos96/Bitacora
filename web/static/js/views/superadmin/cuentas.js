import { esc } from "../../services/api.js";
import { $ } from "../../components/ui.js";
import { bannerSuper, fmtFecha } from "./shared.js";

export async function renderCuentas(box, api) {
  const cuentas = await api.superCuentas();
  box.innerHTML = `
    ${bannerSuper({
      titulo: "Historial de Cuentas",
      subtitulo: "Consulta todas las cuentas creadas históricamente, incluso aquellas eliminadas por administración.",
      exportSeccion: "cuentas",
    })}
    <section class="panel stack">
      <div class="filters-bar" style="justify-content:space-between">
        <div class="row" style="flex:1;min-width:240px">
          <input id="sc-q" placeholder="Buscar por nombre, correo o rol…" style="max-width:320px" />
          <select id="sc-est" style="width:auto;min-width:170px">
            <option value="">Todas (${cuentas.length})</option>
            <option value="activa">Activas (${cuentas.filter((c) => c.estado === "activa").length})</option>
            <option value="inactiva">Inactivas (${cuentas.filter((c) => c.estado === "inactiva").length})</option>
            <option value="eliminada">Eliminadas (${cuentas.filter((c) => c.estado === "eliminada").length})</option>
          </select>
          <span id="sc-count" class="muted text-sm"></span>
        </div>
      </div>
      <div class="table-wrap"><table class="data admin-table">
        <thead><tr>
          <th>Nombre y correo</th>
          <th>Rol</th>
          <th>Estado</th>
          <th>Creada / Eliminada</th>
          <th>Incidencias</th>
          <th>Registros</th>
          <th>Pendientes</th>
          <th>Actividad</th>
          <th>Documentación</th>
        </tr></thead>
        <tbody id="sc-tbody"></tbody>
      </table></div>
    </section>`;

  const pintar = () => {
    const q = ($("#sc-q").value || "").trim().toLowerCase();
    const est = $("#sc-est").value;
    const fil = cuentas.filter((c) => {
      if (est && c.estado !== est) return false;
      if (!q) return true;
      return c.nombre.toLowerCase().includes(q) || c.correo.toLowerCase().includes(q) ||
        c.rol.toLowerCase().includes(q) || (c.rol_custom_nombre || "").toLowerCase().includes(q);
    });
    $("#sc-count").textContent = `${fil.length} cuenta(s)`;
    $("#sc-tbody").innerHTML = fil.length
      ? fil.map((c) => `<tr>
          <td><strong>${esc(c.nombre)}</strong><div class="muted text-sm">${esc(c.correo)}</div></td>
          <td>${esc(c.rol_custom_nombre || c.rol)}</td>
          <td><span class="badge ${esc(c.estado)}">${esc(c.estado)}</span></td>
          <td class="text-sm">
            <div>Creada: ${esc(fmtFecha(c.creado_en))}</div>
            ${c.eliminado_en ? `<div style="color:var(--danger)">Eliminada: ${esc(fmtFecha(c.eliminado_en))} (${esc(c.eliminado_por_nombre || "—")})</div>` : ""}
          </td>
          <td>${c.incidencias_creadas}</td>
          <td>${c.eventos_creados}</td>
          <td>${c.pendientes_abiertos}</td>
          <td>${c.actividades_count}</td>
          <td><div class="cell-actions">
            <button type="button" class="btn soft btn-sm" data-expediente="${c.id}">Ver expediente</button>
            <button type="button" class="btn danger btn-sm" data-purgar="${c.id}">Eliminar datos</button>
          </div></td>
        </tr>`).join("")
      : `<tr><td colspan="9"><div class="empty-state" style="border:0">Sin cuentas que coincidan.</div></td></tr>`;
  };

  $("#sc-q").addEventListener("input", pintar);
  $("#sc-est").addEventListener("change", pintar);
  pintar();
}
