import { esc } from "../../services/api.js";
import { bannerSuper, listaActividadHtml } from "./shared.js";

export async function renderResumen(box, api) {
  const [r, cuentas, actividad] = await Promise.all([
    api.superResumen(),
    api.superCuentas(),
    api.superActividad({ limit: 15 }),
  ]);

  box.innerHTML = `
    ${bannerSuper({
      titulo: "Portal de Superusuario · Auditoría y Documentación",
      subtitulo: "Trazabilidad completa de todas las cuentas (activas, inactivas y eliminadas), incidencias, pendientes, archivos y actividad.",
      exportSeccion: "actividad",
    })}

    <div class="stats-strip">
      <div class="stat-card accent">
        <div class="stat-label">Cuentas históricas</div>
        <div class="stat-value">${r.cuentas_total}</div>
        <div class="muted text-sm">${r.cuentas_activas} activas · ${r.cuentas_inactivas} inactivas · ${r.cuentas_eliminadas} eliminadas</div>
      </div>
      <div class="stat-card warn">
        <div class="stat-label">Incidencias totales</div>
        <div class="stat-value">${r.incidencias_total}</div>
        <div class="muted text-sm">De ${r.eventos_total} registros en bitácora</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Pendientes globales</div>
        <div class="stat-value">${r.pendientes_eventos}</div>
        <div class="muted text-sm">${r.pendientes_compromisos} compromiso(s) · ${r.compromisos_vencidos} vencido(s)</div>
      </div>
      <div class="stat-card ok">
        <div class="stat-label">Archivos y actividad</div>
        <div class="stat-value">${r.archivos_total}</div>
        <div class="muted text-sm">${r.actividades_total} evento(s) en bitácora</div>
      </div>
    </div>

    <section class="panel">
      <div class="panel-header">
        <h2>Cuentas registradas y eliminadas (${cuentas.length})</h2>
        <a href="#/super/cuentas" class="btn soft btn-sm">Ver todas las cuentas</a>
      </div>
      <div class="table-wrap"><table class="data admin-table">
        <thead><tr><th>Cuenta</th><th>Rol</th><th>Estado</th><th>Incidencias</th><th>Registros</th><th>Pendientes</th><th>Expediente</th></tr></thead>
        <tbody>${cuentas.slice(0, 8).map((c) => `<tr>
          <td><strong>${esc(c.nombre)}</strong><div class="muted text-sm">${esc(c.correo)}</div></td>
          <td>${esc(c.rol_custom_nombre || c.rol)}</td>
          <td><span class="badge ${esc(c.estado)}">${esc(c.estado)}</span></td>
          <td>${c.incidencias_creadas}</td>
          <td>${c.eventos_creados}</td>
          <td>${c.pendientes_abiertos}</td>
          <td><div class="cell-actions">
            <button type="button" class="btn soft btn-sm" data-expediente="${c.id}">Ver expediente</button>
            <button type="button" class="btn danger btn-sm" data-purgar="${c.id}">Eliminar datos</button>
          </div></td>
        </tr>`).join("")}</tbody>
      </table></div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <h2>Última actividad del sistema</h2>
        <a href="#/super/actividad" class="btn soft btn-sm">Ver bitácora completa</a>
      </div>
      ${listaActividadHtml(actividad)}
    </section>`;
}
