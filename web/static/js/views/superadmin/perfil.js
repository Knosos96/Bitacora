import { ErrorApi, esc } from "../../services/api.js";
import {
  $,
  campoClaveHtml,
  campoClaveSimpleHtml,
  campoCorreoHtml,
  enlazarCriterios,
  iniciales,
  toast,
  validarClaveCriterios,
  validarCorreoCriterios,
} from "../../components/ui.js";
import { bannerSuper } from "./shared.js";

export async function renderPerfil(box, api, ctx) {
  const u = await api.yo().catch(() => api.usuario);
  box.innerHTML = `
    ${bannerSuper({
      titulo: "Mi perfil · Superusuario",
      subtitulo: "Actualiza tu nombre, correo electrónico o contraseña de acceso con verificación de identidad.",
    })}

    <div class="super-profile-grid">
      <section class="panel">
        <div class="profile-card-head">
          <span class="profile-avatar-lg">${esc(iniciales(u.nombre))}</span>
          <div>
            <h2 style="margin:0">${esc(u.nombre)}</h2>
            <div class="muted text-sm">${esc(u.correo)}</div>
          </div>
        </div>

        <div class="profile-meta-list">
          <div class="meta-item">
            <div class="meta-label">Rol del sistema</div>
            <div class="meta-val"><span class="badge abierto">${esc(u.rol)}</span></div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Estado de la cuenta</div>
            <div class="meta-val"><span class="badge activo">activa</span></div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Seguridad de sesiones</div>
            <div class="meta-val text-sm muted" style="font-weight:400">
              Al cambiar tu contraseña, cualquier sesión abierta en otros dispositivos caducará automáticamente y tu historial quedará registrado en la bitácora.
            </div>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <h2>Editar credenciales y datos de acceso</h2>
        </div>

        <form id="form-super-perfil" class="stack">
          <label class="field">
            <span>Nombre completo</span>
            <input name="nombre" required maxlength="120" value="${esc(u.nombre)}" />
          </label>

          ${campoCorreoHtml({ name: "correo", label: "Correo electrónico", value: u.correo })}

          ${campoClaveHtml({
            name: "clave_nueva",
            label: "Nueva contraseña (opcional: déjalo vacío si no deseas cambiarla)",
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
            name: "clave_actual",
            label: "Contraseña actual (obligatoria para guardar cambios)",
            placeholder: "Ingresa tu contraseña actual",
            required: true,
            autocomplete: "current-password",
          })}

          <p id="sp-perfil-error" class="alert-inline error" hidden></p>

          <div class="row" style="justify-content:flex-end">
            <button type="submit" class="btn primary">Guardar cambios</button>
          </div>
        </form>
      </section>
    </div>`;

  enlazarCriterios(box);

  $("#form-super-perfil").onsubmit = async (e) => {
    e.preventDefault();
    const err = $("#sp-perfil-error");
    err.hidden = true;
    const btn = e.target.querySelector('[type="submit"]');
    const fd = new FormData(e.target);

    const nombre = String(fd.get("nombre") || "").trim();
    const correo = String(fd.get("correo") || "").trim().toLowerCase();
    const claveNueva = String(fd.get("clave_nueva") || "");
    const claveConfirmar = String(fd.get("clave_confirmar") || "");
    const claveActual = String(fd.get("clave_actual") || "");

    try {
      if (!nombre) throw new ErrorApi("El nombre no puede estar vacío.");
      validarCorreoCriterios(correo);

      if (claveNueva || claveConfirmar) {
        validarClaveCriterios(claveNueva);
        if (claveNueva !== claveConfirmar) {
          throw new ErrorApi("La nueva contraseña y su confirmación no coinciden.");
        }
      }

      const payload = { clave_actual: claveActual };
      if (nombre !== u.nombre) payload.nombre = nombre;
      if (correo !== u.correo) payload.correo = correo;
      if (claveNueva) payload.clave_nueva = claveNueva;

      if (!payload.nombre && !payload.correo && !payload.clave_nueva) {
        throw new ErrorApi("No realizaste cambios respecto a tus datos actuales.");
      }

      btn.disabled = true;
      await api.actualizarPerfil(payload);
      ctx?.refrescarUsuario?.();
      toast("Perfil actualizado correctamente", "ok");
      await renderPerfil(box, api, ctx);
    } catch (ex) {
      err.textContent = ex.message;
      err.hidden = false;
      btn.disabled = false;
    }
  };
}
