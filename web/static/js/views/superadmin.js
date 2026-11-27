import { renderActividad } from "./superadmin/actividad.js";
import { renderArchivos } from "./superadmin/archivos.js";
import { renderCuentas } from "./superadmin/cuentas.js";
import { verExpedienteCuenta } from "./superadmin/expedienteModal.js";
import { verFichaDocumental } from "./superadmin/fichaModal.js";
import { renderPendientes } from "./superadmin/pendientes.js";
import { renderPerfil } from "./superadmin/perfil.js";
import { abrirModalPurga } from "./superadmin/purgaModal.js";
import { renderRegistros } from "./superadmin/registros.js";
import { renderResumen } from "./superadmin/resumen.js";
import { descargarCsv } from "./superadmin/shared.js";

const VISTAS_SUPER = {
  resumen: renderResumen,
  cuentas: renderCuentas,
  registros: renderRegistros,
  pendientes: renderPendientes,
  archivos: renderArchivos,
  actividad: renderActividad,
  perfil: renderPerfil,
};

export async function vistaSuperadmin(box, path, ctx) {
  const { api } = ctx;
  if (!api.esSuperusuario) {
    box.innerHTML = `<div class="panel"><p class="alert-inline error">Acceso restringido al rol de Superusuario.</p></div>`;
    return;
  }

  const sub = path.replace(/^\/super\/?/, "") || "resumen";
  const render = VISTAS_SUPER[sub] || renderResumen;
  await render(box, api, ctx);

  box.onclick = async (e) => {
    const trFolio = e.target.closest("[data-super-folio]");
    if (trFolio) {
      await verFichaDocumental(trFolio.dataset.superFolio, api);
      return;
    }
    const btnExp = e.target.closest("[data-expediente]");
    if (btnExp) {
      await verExpedienteCuenta(btnExp.dataset.expediente, api, () => ctx.enrutar?.());
      return;
    }
    const btnPurga = e.target.closest("[data-purgar]");
    if (btnPurga) {
      await abrirModalPurga(btnPurga.dataset.purgar, api, () => ctx.enrutar?.());
      return;
    }
    if (e.target.id === "sup-print") {
      window.print();
      return;
    }
    if (e.target.id === "sup-export-csv") {
      const sec = e.target.dataset.sec || "actividad";
      const cid = e.target.dataset.cid || undefined;
      await descargarCsv(api, { seccion: sec, cuenta_id: cid }, `dossier-${sec}.csv`);
    }
  };
}
