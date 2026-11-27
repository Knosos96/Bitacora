import { esc } from "../../services/api.js";
import { $, abrirModal, cerrarModal, toast } from "../../components/ui.js";

export async function abrirModalPurga(cuentaId, api, onDone = null) {
  let info;
  try {
    info = await api.superPurgaResumen(cuentaId);
  } catch (ex) {
    toast(ex.message, "error");
    return;
  }

  abrirModal(`
    <div class="modal-header">
      <div>
        <div class="row" style="gap:0.5rem;margin-bottom:0.25rem">
          <span class="badge ${esc(info.estado)}">${esc(info.estado)}</span>
          <span class="badge">${esc(info.rol)}</span>
        </div>
        <h2>Eliminar información de la base de datos</h2>
        <p class="muted text-sm" style="margin:0.15rem 0 0">${esc(info.nombre)} · ${esc(info.correo)}</p>
      </div>
      <button type="button" class="btn ghost btn-sm" data-close-modal>Cerrar</button>
    </div>

    <p class="alert-inline error" style="margin-bottom:0.9rem">
      Esta acción elimina permanentemente de PostgreSQL los registros seleccionados. No se puede deshacer.
    </p>

    <form id="form-purga" class="stack">
      <div class="row spread">
        <strong>Selecciona qué información deseas eliminar:</strong>
        <button type="button" class="btn soft btn-sm" id="purga-marcar-todo">Seleccionar todo</button>
      </div>

      <fieldset class="permisos-box">
        <legend>Datos asociados a la cuenta</legend>
        <div class="stack" style="gap:0.55rem">
          <label class="check-row">
            <input type="checkbox" name="eliminar_eventos_creados" />
            <span><strong>Eventos e incidencias creadas (${info.eventos_creados})</strong> <span class="muted">— incluye notas, compromisos y auditoría propios de esos eventos</span></span>
          </label>
          <label class="check-row">
            <input type="checkbox" name="eliminar_notas" />
            <span><strong>Notas de seguimiento en otros eventos (${info.notas_en_otros_eventos})</strong></span>
          </label>
          <label class="check-row">
            <input type="checkbox" name="eliminar_compromisos" />
            <span><strong>Compromisos asignados en otros eventos (${info.compromisos_en_otros_eventos})</strong></span>
          </label>
          <label class="check-row">
            <input type="checkbox" name="eliminar_auditorias" />
            <span><strong>Correcciones de auditoría realizadas (${info.auditorias_en_otros_eventos})</strong></span>
          </label>
          <label class="check-row">
            <input type="checkbox" name="eliminar_claves_api" />
            <span><strong>Claves API emitidas y su historial de usos (${info.claves_api})</strong></span>
          </label>
          <label class="check-row">
            <input type="checkbox" name="eliminar_actividades" />
            <span><strong>Bitácora cronológica de actividad (${info.actividades})</strong></span>
          </label>
        </div>
      </fieldset>

      <div class="meta-item" style="border-color:var(--danger-border);background:var(--danger-soft)">
        <label class="check-row" style="align-items:flex-start">
          <input type="checkbox" name="eliminar_cuenta" ${info.es_protegida ? "disabled" : ""} />
          <span>
            <strong style="color:var(--danger)">Eliminar también la cuenta completa de la base de datos</strong>
            <div class="muted text-sm" style="font-weight:400">
              ${info.es_protegida
                ? "Cuenta protegida (Superusuario actual o último Jefe activo): solo puedes depurar sus registros de prueba, no la cuenta."
                : "Borra definitivamente la cuenta y su expediente histórico junto con todas sus dependencias."}
            </div>
          </span>
        </label>
      </div>

      <p id="purga-error" class="alert-inline error" hidden></p>

      <div id="purga-confirm-box" class="panel hidden" style="border-color:var(--danger-border);background:var(--danger-soft);margin:0;padding:0.85rem">
        <p style="margin:0 0 0.65rem;font-weight:600;color:var(--danger)">
          ¿Confirmas que deseas eliminar permanentemente la información marcada de «${esc(info.nombre)}»?
        </p>
        <div class="row" style="justify-content:flex-end">
          <button type="button" class="btn ghost btn-sm" id="purga-volver">Cancelar</button>
          <button type="button" class="btn danger btn-sm" id="purga-confirmar-ok">Sí, eliminar permanentemente</button>
        </div>
      </div>

      <div class="row" id="purga-actions" style="justify-content:flex-end">
        <button type="button" class="btn ghost" data-close-modal>Cancelar</button>
        <button type="submit" class="btn danger">Eliminar información seleccionada</button>
      </div>
    </form>
  `, { sm: false });

  const form = $("#form-purga");
  const checksDatos = [...form.querySelectorAll('input[type="checkbox"]:not([name="eliminar_cuenta"])')];
  const checkCuenta = form.querySelector('input[name="eliminar_cuenta"]');

  checkCuenta?.addEventListener("change", () => {
    if (checkCuenta.checked) {
      checksDatos.forEach((ch) => { ch.checked = true; });
    }
  });

  $("#purga-marcar-todo").onclick = () => {
    const habilitar = !checksDatos.every((ch) => ch.checked);
    checksDatos.forEach((ch) => { ch.checked = habilitar; });
    if (checkCuenta && !checkCuenta.disabled) checkCuenta.checked = habilitar;
  };

  let payloadPendiente = null;

  form.onsubmit = (e) => {
    e.preventDefault();
    const err = $("#purga-error");
    err.hidden = true;
    const fd = new FormData(form);
    const payload = {
      eliminar_eventos_creados: fd.get("eliminar_eventos_creados") === "on",
      eliminar_notas: fd.get("eliminar_notas") === "on",
      eliminar_compromisos: fd.get("eliminar_compromisos") === "on",
      eliminar_auditorias: fd.get("eliminar_auditorias") === "on",
      eliminar_claves_api: fd.get("eliminar_claves_api") === "on",
      eliminar_actividades: fd.get("eliminar_actividades") === "on",
      eliminar_cuenta: fd.get("eliminar_cuenta") === "on",
    };

    if (!Object.values(payload).some(Boolean)) {
      err.textContent = "Marca al menos una categoría de información para eliminar.";
      err.hidden = false;
      return;
    }
    payloadPendiente = payload;
    $("#purga-confirm-box").classList.remove("hidden");
    $("#purga-actions").classList.add("hidden");
  };

  $("#purga-volver").onclick = () => {
    payloadPendiente = null;
    $("#purga-confirm-box").classList.add("hidden");
    $("#purga-actions").classList.remove("hidden");
  };

  $("#purga-confirmar-ok").onclick = async () => {
    if (!payloadPendiente) return;
    const btn = $("#purga-confirmar-ok");
    const err = $("#purga-error");
    btn.disabled = true;
    err.hidden = true;
    try {
      const r = await api.superPurgarCuenta(cuentaId, payloadPendiente);
      cerrarModal();
      const resumen = [
        r.eventos_eliminados ? `${r.eventos_eliminados} evento(s)` : null,
        r.notas_eliminadas ? `${r.notas_eliminadas} nota(s)` : null,
        r.compromisos_eliminados ? `${r.compromisos_eliminados} compromiso(s)` : null,
        r.auditorias_eliminadas ? `${r.auditorias_eliminadas} auditoría(s)` : null,
        r.claves_api_eliminadas ? `${r.claves_api_eliminadas} clave(s)` : null,
        r.actividades_eliminadas ? `${r.actividades_eliminadas} movimiento(s)` : null,
        r.cuenta_eliminada ? "cuenta eliminada" : null,
      ].filter(Boolean).join(", ");
      toast(`Información eliminada: ${resumen || "completado"}`, "ok");
      if (onDone) await onDone();
    } catch (ex) {
      err.textContent = ex.message;
      err.hidden = false;
      btn.disabled = false;
    }
  };
}
