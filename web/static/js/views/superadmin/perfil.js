import { renderPerfilContenido } from "../perfil.js";
import { bannerSuper } from "./shared.js";

export async function renderPerfil(box, api, ctx) {
  const headerHtml = bannerSuper({
    titulo: "Mi perfil · Superusuario",
    subtitulo: "Actualiza tu nombre, correo electrónico o contraseña de acceso con verificación de identidad.",
  });
  await renderPerfilContenido(box, api, ctx, headerHtml, () => renderPerfil(box, api, ctx));
}
