import { ErrorApi, esc } from "../../services/api.js";
import {
  $,
  abrirModal,
  campoClaveHtml,
  campoClaveSimpleHtml,
  campoCorreoHtml,
  cerrarModal,
  enlazarCriterios,
  toast,
  validarClaveCriterios,
  validarCorreoCriterios,
} from "../../components/ui.js";

export async function abrirModalCredenciales(cuentaId, api, onDone = null, cuentaPrevia = null) {
  let c = cuentaPrevia;
  if (!c) {
    try {
      const lista = await api.superCuentas();
      c = lista.find((x) => x.id === cuentaId);
    } catch (ex) {
      toast(ex.message, "error");
      return;
    }
  }
  if (!c) {
    toast("Cuenta no encontrada", "error");
    return;
  }

  abrirModal(`
    <div class="modal-header">
      <div>
        <div class="row" style="gap:0.5rem;margin-bottom:0.25rem">
          <span class="badge ${esc(c.estado)}">${esc(c.estado)}</span>
          <span class="badge">${esc(c.rol_custom_nombre || c.rol)}</span>
        </div>
        <h2>Restablecer credenciales — ${esc(c.nombre)}</h2>
        <p class="muted text-sm" style="margin:0.15rem 0 0">${esc(c.correo)}</p>
      </div>
      <button type="button" class="btn ghost btn-sm" data-close-modal>Cerrar</button>
    </div>

    <p class="alert-inline" style="background:var(--accent-soft);border:1px solid var(--accent-border);color:var(--accent);margin-bottom:0.9rem">
      Si el usuario olvidó su clave o requiere cambio administrativo, asigna un nuevo correo y/o contraseña. Las sesiones previas de esa cuenta caducarán automáticamente.
    </p>

    <form id="form-super-credenciales" class="stack">
      ${campoCorreoHtml({ name: "correo", label: "Correo electrónico", value: c.correo })}

      ${campoClaveHtml({
        name: "clave_nueva",
        label: "Nueva contraseña (opcional: déjalo vacío si solo cambias el correo)",
        placeholder: "Mínimo 8 caracteres (letras y números)",
        required: false,
      })}

      ${campoClaveSimpleHtml({
        name: "clave_confirmar",
        label: "Confirmar nueva contraseña",
        placeholder: "Repite la nueva contraseña",
        required: false,
        autocomplete: "new-password",
      })}

      ${campoClaveSimpleHtml({
        name: "clave_actual_super",
        label: "Tu contraseña actual de Superusuario (autorización obligatoria)",
        placeholder: "Ingresa tu contraseña de Superusuario",
        required: true,
        autocomplete: "current-password",
      })}

      <p id="sc-cred-error" class="alert-inline error" hidden></p>

      <div class="row" style="justify-content:flex-end">
        <button type="button" class="btn ghost" data-close-modal>Cancelar</button>
        <button type="submit" class="btn primary">Guardar credenciales</button>
      </div>
    </form>
  `, { sm: true });

  const form = $("#form-super-credenciales");
  enlazarCriterios(form);

  form.onsubmit = async (e) => {
    e.preventDefault();
    const err = $("#sc-cred-error");
    err.hidden = true;
    const btn = form.querySelector('[type="submit"]');
    const fd = new FormData(form);

    const correo = String(fd.get("correo") || "").trim().toLowerCase();
    const claveNueva = String(fd.get("clave_nueva") || "");
    const claveConfirmar = String(fd.get("clave_confirmar") || "");
    const claveActualSuper = String(fd.get("clave_actual_super") || "");

    try {
      validarCorreoCriterios(correo);
      if (claveNueva || claveConfirmar) {
        validarClaveCriterios(claveNueva);
        if (claveNueva !== claveConfirmar) {
          throw new ErrorApi("La nueva contraseña y su confirmación no coinciden.");
        }
      }

      const payload = { clave_actual_super: claveActualSuper };
      if (correo !== c.correo) payload.correo = correo;
      if (claveNueva) payload.clave_nueva = claveNueva;

      if (!payload.correo && !payload.clave_nueva) {
        throw new ErrorApi("Cambia el correo o ingresa una nueva contraseña.");
      }

      btn.disabled = true;
      await api.superRestablecerCredenciales(c.id, payload);
      cerrarModal();
      toast(`Credenciales actualizadas para ${c.nombre}`, "ok");
      if (onDone) await onDone();
    } catch (ex) {
      err.textContent = ex.message;
      err.hidden = false;
      btn.disabled = false;
    }
  };
}
