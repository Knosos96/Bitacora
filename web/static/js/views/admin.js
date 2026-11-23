import { ErrorApi, TIPOS, esc } from "../services/api.js";
import {
  $,
  $$,
  abrirModal,
  badge,
  badgeActivo,
  campoClaveHtml,
  campoCorreoHtml,
  formModal,
  modalConfirmar,
  toast,
  validarClaveCriterios,
  validarCorreoCriterios,
} from "../components/ui.js";

export async function vistaAdmin(box, { api }) {
  if (!api.puedeAdmin) {
    box.innerHTML = `<div class="panel"><p class="alert-inline error">No tienes permisos para acceder a la sección de administración.</p></div>`;
    return;
  }

  const tabs = [];
  if (api.tienePermiso("gestionar_areas")) tabs.push({ key: "areas", label: "Áreas" });
  if (api.tienePermiso("gestionar_subtipos")) tabs.push({ key: "subtipos", label: "Subtipos" });
  if (api.tienePermiso("ver_usuarios", "crear_usuarios", "editar_usuarios")) tabs.push({ key: "usuarios", label: "Usuarios" });
  if (api.tienePermiso("gestionar_claves_api")) tabs.push({ key: "claves", label: "Claves API" });
  if (api.tienePermiso("gestionar_roles")) tabs.push({ key: "roles", label: "Roles" });

  box.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="section-title">Administración</h1>
        <p class="section-sub">Gestiona catálogos, usuarios, permisos y claves de integración.</p>
      </div>
    </div>
    <section class="panel">
      <div class="tabs" id="ad-tabs">
        ${tabs.map((t, i) => `<button type="button" class="btn ${i === 0 ? "active" : ""}" data-tab="${t.key}">${t.label}</button>`).join("")}
      </div>
      <div id="ad-body"></div>
    </section>`;

  let tab = tabs[0].key;
  const pintar = async () => {
    $$("#ad-tabs .btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
    const body = $("#ad-body");
    body.onclick = null;
    try {
      if (tab === "areas") await adminAreas(body, api);
      else if (tab === "subtipos") await adminSubtipos(body, api);
      else if (tab === "usuarios") await adminUsuarios(body, api);
      else if (tab === "claves") await adminClaves(body, api);
      else if (tab === "roles") await adminRoles(body, api);
    } catch (ex) {
      body.innerHTML = `<p class="alert-inline error">${esc(ex.message)}</p>`;
    }
  };

  $("#ad-tabs").onclick = (e) => {
    const b = e.target.closest("[data-tab]");
    if (!b) return;
    tab = b.dataset.tab;
    pintar();
  };

  await pintar();
}

/* ========================== ÁREAS ========================== */
async function adminAreas(body, api) {
  const areas = await api.areas(true);
  body.innerHTML = `
    <div class="filters-bar" style="justify-content:space-between;margin-bottom:0.85rem">
      <div class="row" style="flex:1;min-width:240px">
        <input id="area-buscar" placeholder="Filtrar área por nombre…" style="max-width:300px" />
        <select id="area-estado" style="width:auto;min-width:155px" aria-label="Estado del área">
          <option value="todas">Todas (${areas.length})</option>
          <option value="activas">Solo activas (${areas.filter((a) => a.activa).length})</option>
          <option value="inactivas">Solo inactivas (${areas.filter((a) => !a.activa).length})</option>
        </select>
        <span id="area-conteo" class="muted text-sm"></span>
      </div>
      <button type="button" class="btn primary" id="area-nueva">+ Nueva área</button>
    </div>
    <div class="table-wrap"><table class="data admin-table">
      <thead><tr><th>Área</th><th>Estado</th><th>Acciones</th></tr></thead>
      <tbody id="area-tbody"></tbody>
    </table></div>`;

  const pintarFilas = () => {
    const q = ($("#area-buscar")?.value || "").trim().toLowerCase();
    const est = $("#area-estado")?.value || "todas";
    const filtradas = areas.filter((a) => {
      if (est === "activas" && !a.activa) return false;
      if (est === "inactivas" && a.activa) return false;
      if (!q) return true;
      return a.nombre.toLowerCase().includes(q);
    });
    $("#area-conteo").textContent = `${filtradas.length} mostrada(s)`;
    $("#area-tbody").innerHTML = filtradas.length
      ? filtradas.map((a) => `<tr>
          <td><strong>${esc(a.nombre)}</strong></td>
          <td>${badgeActivo(a.activa)}</td>
          <td><div class="cell-actions">
            <button type="button" class="btn btn-sm" data-ren="${a.id}" data-nombre="${esc(a.nombre)}">Renombrar</button>
            <button type="button" class="btn btn-sm ${a.activa ? "ghost" : "ok"}" data-act="${a.id}" data-on="${a.activa ? "true" : "false"}">
              ${a.activa ? "Desactivar" : "Activar"}
            </button>
            <button type="button" class="btn danger btn-sm" data-del="${a.id}" data-nombre="${esc(a.nombre)}">Eliminar</button>
          </div></td>
        </tr>`).join("")
      : `<tr><td colspan="3"><div class="empty-state" style="border:0">No hay áreas que coincidan con el filtro.</div></td></tr>`;
  };

  $("#area-buscar").addEventListener("input", pintarFilas);
  $("#area-estado").addEventListener("change", pintarFilas);
  pintarFilas();

  $("#area-nueva").onclick = () => {
    formModal("Nueva área",
      `<label class="field">Nombre<input name="nombre" required maxlength="120" autofocus placeholder="Ej. Contabilidad" /></label>`,
      async (fd) => {
        await api.crearArea(fd.get("nombre").trim());
        toast("Área creada", "ok");
        await adminAreas(body, api);
      });
  };

  body.onclick = async (e) => {
    const ren = e.target.closest("[data-ren]");
    const act = e.target.closest("[data-act]");
    const del = e.target.closest("[data-del]");
    if (del) {
      const ok = await modalConfirmar({
        titulo: "Eliminar área",
        mensaje: `¿Estás seguro de eliminar permanentemente el área «${del.dataset.nombre}»? Los eventos asociados se conservarán sin área asignada.`,
        confirmarTexto: "Sí, eliminar",
        peligro: true,
      });
      if (!ok) return;
      try {
        await api.eliminarArea(del.dataset.del);
        toast("Área eliminada", "ok");
        await adminAreas(body, api);
      } catch (ex) {
        toast(ex.message, "error");
      }
      return;
    }
    if (ren) {
      formModal("Renombrar área",
        `<label class="field">Nombre<input name="nombre" required maxlength="120" value="${esc(ren.dataset.nombre)}" /></label>`,
        async (fd) => {
          await api.modificarArea(ren.dataset.ren, { nombre: fd.get("nombre").trim() });
          toast("Área actualizada", "ok");
          await adminAreas(body, api);
        });
      return;
    }
    if (act) {
      try {
        const activa = act.dataset.on !== "true";
        await api.modificarArea(act.dataset.act, { activa });
        toast(activa ? "Área activada" : "Área desactivada", "ok");
        await adminAreas(body, api);
      } catch (ex) {
        toast(ex.message, "error");
      }
    }
  };
}

/* ========================== SUBTIPOS ========================== */
async function adminSubtipos(body, api) {
  const lista = await api.subtipos(undefined, true);
  body.innerHTML = `
    <div class="filters-bar" style="justify-content:space-between;margin-bottom:0.85rem">
      <div class="row" style="flex:1;min-width:240px">
        <input id="sub-buscar" placeholder="Filtrar por subtipo…" style="max-width:250px" />
        <select id="sub-tipo" style="width:auto;min-width:155px" aria-label="Tipo de evento">
          <option value="">Todos los tipos</option>
          ${TIPOS.map((t) => `<option value="${t}">${t}</option>`).join("")}
        </select>
        <select id="sub-estado" style="width:auto;min-width:155px" aria-label="Estado del subtipo">
          <option value="todos">Todos (${lista.length})</option>
          <option value="activos">Solo activos (${lista.filter((s) => s.activo).length})</option>
          <option value="inactivos">Solo inactivos (${lista.filter((s) => !s.activo).length})</option>
        </select>
        <span id="sub-conteo" class="muted text-sm"></span>
      </div>
      <button type="button" class="btn primary" id="sub-nuevo">+ Nuevo subtipo</button>
    </div>
    <div class="table-wrap"><table class="data admin-table">
      <thead><tr><th>Tipo</th><th>Subtipo</th><th>Estado</th><th>Origen</th><th>Acciones</th></tr></thead>
      <tbody id="sub-tbody"></tbody>
    </table></div>`;

  const pintarFilas = () => {
    const q = ($("#sub-buscar")?.value || "").trim().toLowerCase();
    const tipoSel = $("#sub-tipo")?.value || "";
    const est = $("#sub-estado")?.value || "todos";
    const filtrados = lista.filter((s) => {
      if (tipoSel && s.tipo !== tipoSel) return false;
      if (est === "activos" && !s.activo) return false;
      if (est === "inactivos" && s.activo) return false;
      if (!q) return true;
      return s.nombre.toLowerCase().includes(q) || s.tipo.toLowerCase().includes(q);
    });
    $("#sub-conteo").textContent = `${filtrados.length} mostrado(s)`;
    $("#sub-tbody").innerHTML = filtrados.length
      ? filtrados.map((s) => `<tr>
          <td>${esc(s.tipo)}</td>
          <td><strong>${esc(s.nombre)}</strong></td>
          <td>${badgeActivo(s.activo)}</td>
          <td class="muted">${s.base ? "De fábrica" : "Personalizado"}</td>
          <td><div class="cell-actions">
            <button type="button" class="btn btn-sm ${s.activo ? "ghost" : "ok"}" data-tipo="${esc(s.tipo)}" data-nom="${esc(s.nombre)}" data-on="${s.activo ? "true" : "false"}">
              ${s.activo ? "Desactivar" : "Activar"}
            </button>
            <button type="button" class="btn danger btn-sm" data-del-tipo="${esc(s.tipo)}" data-del-nom="${esc(s.nombre)}">Eliminar</button>
          </div></td>
        </tr>`).join("")
      : `<tr><td colspan="5"><div class="empty-state" style="border:0">No hay subtipos que coincidan con el filtro.</div></td></tr>`;
  };

  $("#sub-buscar").addEventListener("input", pintarFilas);
  $("#sub-tipo").addEventListener("change", pintarFilas);
  $("#sub-estado").addEventListener("change", pintarFilas);
  pintarFilas();

  $("#sub-nuevo").onclick = () => {
    formModal("Nuevo subtipo", `
      <label class="field">Tipo
        <select name="tipo" required>
          ${TIPOS.map((t) => `<option value="${t}">${t}</option>`).join("")}
        </select>
      </label>
      <label class="field">Nombre (minúsculas, sin espacios)
        <input name="nombre" required pattern="[a-z0-9_]+" title="Solo minúsculas, números y _" placeholder="ej. capacitacion" />
      </label>`,
      async (fd) => {
        await api.crearSubtipo(fd.get("tipo"), fd.get("nombre").trim());
        toast("Subtipo creado", "ok");
        await adminSubtipos(body, api);
      });
  };

  body.onclick = async (e) => {
    const del = e.target.closest("[data-del-tipo]");
    const b = e.target.closest("[data-tipo]");
    if (del) {
      const ok = await modalConfirmar({
        titulo: "Eliminar subtipo",
        mensaje: `¿Estás seguro de eliminar permanentemente el subtipo «${del.dataset.delNom}» (${del.dataset.delTipo})?`,
        confirmarTexto: "Sí, eliminar",
        peligro: true,
      });
      if (!ok) return;
      try {
        await api.eliminarSubtipo(del.dataset.delTipo, del.dataset.delNom);
        toast("Subtipo eliminado", "ok");
        await adminSubtipos(body, api);
      } catch (ex) {
        toast(ex.message, "error");
      }
      return;
    }
    if (!b) return;
    try {
      const activo = b.dataset.on !== "true";
      await api.activarSubtipo(b.dataset.tipo, b.dataset.nom, activo);
      toast(activo ? "Subtipo activado" : "Subtipo desactivado", "ok");
      await adminSubtipos(body, api);
    } catch (ex) {
      toast(ex.message, "error");
    }
  };
}

/* ========================== USUARIOS ========================== */
function selectorRolPersonalizadoHtml(roles, seleccionadoId = "") {
  if (!roles.length) {
    return `
      <div id="box-rol-custom" class="custom-role-box hidden">
        <p class="alert-inline error" style="margin:0">
          Aún no hay roles personalizados activos. Crea uno primero en la pestaña <strong>Roles</strong>.
        </p>
      </div>`;
  }
  return `
    <div id="box-rol-custom" class="custom-role-box hidden">
      <label class="field">
        <span>Seleccionar rol personalizado</span>
        <select name="rol_custom_id">
          ${roles.map((r) => `<option value="${r.id}" ${seleccionadoId === r.id ? "selected" : ""}>${esc(r.nombre)}${r.descripcion ? " — " + esc(r.descripcion) : ""}</option>`).join("")}
        </select>
      </label>
    </div>`;
}

function enlazarSelectorRol(form) {
  const sel = form.querySelector('[name="rol_tipo"]');
  const box = form.querySelector("#box-rol-custom");
  if (!sel || !box) return;
  const actualizar = () => {
    box.classList.toggle("hidden", sel.value !== "otro");
  };
  sel.addEventListener("change", actualizar);
  actualizar();
}

async function adminUsuarios(body, api) {
  const [users, roles] = await Promise.all([api.usuarios(), api.roles(false)]);
  const yoId = api.usuario?.id;

  body.innerHTML = `
    <div class="filters-bar" style="justify-content:space-between;margin-bottom:0.85rem">
      <div class="row" style="flex:1;min-width:240px">
        <input id="usr-buscar" placeholder="Filtrar por nombre, correo o rol…" style="max-width:320px" />
        <select id="usr-estado" style="width:auto;min-width:145px" aria-label="Estado de usuario">
          <option value="todos">Todos (${users.length})</option>
          <option value="activos">Solo activos (${users.filter((u) => u.activo).length})</option>
          <option value="inactivos">Solo inactivos (${users.filter((u) => !u.activo).length})</option>
        </select>
        <span id="usr-conteo" class="muted text-sm"></span>
      </div>
      <button type="button" class="btn primary" id="usr-nuevo">+ Nuevo usuario</button>
    </div>
    <div class="table-wrap"><table class="data admin-table">
      <thead><tr><th>Nombre</th><th>Correo</th><th>Rol</th><th>Estado</th><th>Acciones</th></tr></thead>
      <tbody id="usr-tbody"></tbody>
    </table></div>`;

  const pintarFilas = () => {
    const q = ($("#usr-buscar")?.value || "").trim().toLowerCase();
    const est = $("#usr-estado")?.value || "todos";
    const filtrados = users.filter((u) => {
      if (est === "activos" && !u.activo) return false;
      if (est === "inactivos" && u.activo) return false;
      if (!q) return true;
      const rolTxt = (u.rol_custom_nombre || u.rol || "").toLowerCase();
      return (
        u.nombre.toLowerCase().includes(q) ||
        u.correo.toLowerCase().includes(q) ||
        rolTxt.includes(q)
      );
    });
    $("#usr-conteo").textContent = `${filtrados.length} mostrado(s)`;
    $("#usr-tbody").innerHTML = filtrados.length
      ? filtrados.map((u) => `<tr>
          <td><strong>${esc(u.nombre)}</strong></td>
          <td class="muted">${esc(u.correo)}</td>
          <td><span class="badge abierto">${esc(u.rol_custom_nombre || u.rol)}</span></td>
          <td>${badgeActivo(u.activo)}</td>
          <td><div class="cell-actions">
            <button type="button" class="btn btn-sm" data-rol="${u.id}" data-base="${esc(u.rol)}" data-custom="${u.rol_custom_id || ""}">Rol</button>
            <button type="button" class="btn btn-sm" data-clave="${u.id}">Clave</button>
            <button type="button" class="btn btn-sm ${u.activo ? "ghost" : "ok"}" data-act="${u.id}" data-on="${u.activo ? "true" : "false"}">
              ${u.activo ? "Desactivar" : "Activar"}
            </button>
            ${u.id !== yoId ? `<button type="button" class="btn danger btn-sm" data-del="${u.id}" data-nom="${esc(u.nombre)}">Eliminar</button>` : ""}
          </div></td>
        </tr>`).join("")
      : `<tr><td colspan="5"><div class="empty-state" style="border:0">No hay usuarios que coincidan con el filtro.</div></td></tr>`;
  };

  $("#usr-buscar").addEventListener("input", pintarFilas);
  $("#usr-estado").addEventListener("change", pintarFilas);
  pintarFilas();

  $("#usr-nuevo").onclick = () => {
    formModal("Nuevo usuario", `
      <label class="field">Nombre completo
        <input name="nombre" required maxlength="120" placeholder="Ej. Ana Pérez" />
      </label>
      ${campoCorreoHtml({ name: "correo", label: "Correo electrónico" })}
      <label class="field">Rol base
        <select name="rol_tipo" required>
          <option value="asistente">Asistente</option>
          <option value="encargado">Encargado</option>
          <option value="jefe">Jefe</option>
          <option value="otro">Otro rol (personalizado)…</option>
        </select>
      </label>
      ${selectorRolPersonalizadoHtml(roles)}
      ${campoClaveHtml({ name: "clave", label: "Contraseña inicial" })}`,
      async (fd) => {
        const nombre = fd.get("nombre").trim();
        const correo = fd.get("correo").trim();
        const clave = fd.get("clave");
        const rolTipo = fd.get("rol_tipo");

        validarCorreoCriterios(correo);
        validarClaveCriterios(clave);

        let rol = rolTipo;
        let rol_custom_id = null;
        if (rolTipo === "otro") {
          rol_custom_id = fd.get("rol_custom_id");
          if (!rol_custom_id) {
            throw new ErrorApi("Selecciona un rol personalizado o créalo primero en la pestaña Roles.");
          }
          rol = "asistente";
        }

        const creado = await api.crearUsuario({ nombre, correo, rol, clave, rol_custom_id });
        if (rol_custom_id && !creado.rol_custom_id) {
          await api.asignarRol(creado.id, rol_custom_id);
        }
        toast("Usuario creado", "ok");
        await adminUsuarios(body, api);
      },
      { onOpen: enlazarSelectorRol });
  };

  body.onclick = async (e) => {
    const rolBtn = e.target.closest("[data-rol]");
    const clave = e.target.closest("[data-clave]");
    const act = e.target.closest("[data-act]");
    const del = e.target.closest("[data-del]");

    if (del) {
      const ok = await modalConfirmar({
        titulo: "Eliminar usuario",
        mensaje: `¿Estás seguro de eliminar permanentemente a «${del.dataset.nom}»? Sus registros históricos se conservarán en la bitácora.`,
        confirmarTexto: "Sí, eliminar",
        peligro: true,
      });
      if (!ok) return;
      try {
        await api.eliminarUsuario(del.dataset.del);
        toast("Usuario eliminado", "ok");
        await adminUsuarios(body, api);
      } catch (ex) {
        toast(ex.message, "error");
      }
      return;
    }

    if (rolBtn) {
      const tieneCustom = Boolean(rolBtn.dataset.custom);
      const baseActual = rolBtn.dataset.base;
      formModal("Cambiar rol", `
        <label class="field">Rol base
          <select name="rol_tipo" required>
            <option value="asistente" ${!tieneCustom && baseActual === "asistente" ? "selected" : ""}>Asistente</option>
            <option value="encargado" ${!tieneCustom && baseActual === "encargado" ? "selected" : ""}>Encargado</option>
            <option value="jefe" ${!tieneCustom && baseActual === "jefe" ? "selected" : ""}>Jefe</option>
            <option value="otro" ${tieneCustom ? "selected" : ""}>Otro rol (personalizado)…</option>
          </select>
        </label>
        ${selectorRolPersonalizadoHtml(roles, rolBtn.dataset.custom)}
        <p class="muted text-sm" style="margin:0">Al elegir «Otro rol» se asigna el rol personalizado seleccionado; al elegir un rol base se quita el rol personalizado.</p>`,
        async (fd) => {
          const rolTipo = fd.get("rol_tipo");
          if (rolTipo === "otro") {
            const customId = fd.get("rol_custom_id");
            if (!customId) {
              throw new ErrorApi("Selecciona un rol personalizado activo.");
            }
            await api.asignarRol(rolBtn.dataset.rol, customId);
          } else {
            await api.asignarRol(rolBtn.dataset.rol, null);
            await api.modificarUsuario(rolBtn.dataset.rol, { rol: rolTipo });
          }
          toast("Rol actualizado", "ok");
          await adminUsuarios(body, api);
        },
        { onOpen: enlazarSelectorRol });
      return;
    }

    if (clave) {
      formModal("Restablecer contraseña",
        campoClaveHtml({ name: "clave", label: "Nueva contraseña" }),
        async (fd) => {
          const nuevaClave = fd.get("clave");
          validarClaveCriterios(nuevaClave);
          await api.modificarUsuario(clave.dataset.clave, { clave: nuevaClave });
          toast("Contraseña actualizada", "ok");
          await adminUsuarios(body, api);
        });
      return;
    }

    if (act) {
      try {
        const activo = act.dataset.on !== "true";
        await api.modificarUsuario(act.dataset.act, { activo });
        toast(activo ? "Usuario activado" : "Usuario desactivado", "ok");
        await adminUsuarios(body, api);
      } catch (ex) {
        toast(ex.message, "error");
      }
    }
  };
}

/* ========================== CLAVES API ========================== */
async function adminClaves(body, api) {
  const claves = await api.clavesApi();
  body.innerHTML = `
    <div class="filters-bar" style="justify-content:space-between;margin-bottom:0.85rem">
      <div class="row" style="flex:1;min-width:240px">
        <input id="api-buscar" placeholder="Filtrar por nombre o prefijo…" style="max-width:280px" />
        <select id="api-estado" style="width:auto;min-width:160px" aria-label="Estado de clave">
          <option value="todas">Todas (${claves.length})</option>
          <option value="activas">Solo activas (${claves.filter((k) => !k.revocada_en).length})</option>
          <option value="revocadas">Solo revocadas (${claves.filter((k) => k.revocada_en).length})</option>
        </select>
        <span id="api-conteo" class="muted text-sm"></span>
      </div>
      <button type="button" class="btn primary" id="api-nueva">+ Emitir clave</button>
    </div>
    <div class="table-wrap"><table class="data admin-table">
      <thead><tr><th>Nombre</th><th>Prefijo</th><th>Creada</th><th>Último uso</th><th>Usos</th><th>Estado</th><th>Acciones</th></tr></thead>
      <tbody id="api-tbody"></tbody>
    </table></div>`;

  const pintarFilas = () => {
    const q = ($("#api-buscar")?.value || "").trim().toLowerCase();
    const est = $("#api-estado")?.value || "todas";
    const filtradas = claves.filter((k) => {
      if (est === "activas" && k.revocada_en) return false;
      if (est === "revocadas" && !k.revocada_en) return false;
      if (!q) return true;
      return k.nombre.toLowerCase().includes(q) || (k.prefijo || "").toLowerCase().includes(q);
    });
    $("#api-conteo").textContent = `${filtradas.length} mostrada(s)`;
    $("#api-tbody").innerHTML = filtradas.length
      ? filtradas.map((k) => `<tr>
          <td><strong>${esc(k.nombre)}</strong></td>
          <td class="mono text-sm">${esc(k.prefijo)}…</td>
          <td class="cell-nowrap">${esc((k.creado_en || "").slice(0, 10))}</td>
          <td class="cell-nowrap muted">${esc((k.ultimo_uso || "nunca").toString().slice(0, 16).replace("T", " "))}</td>
          <td>${k.usos}</td>
          <td>${k.revocada_en ? badge("revocada") : badge("activo")}</td>
          <td><div class="cell-actions">
            ${!k.revocada_en ? `<button type="button" class="btn btn-sm" data-rev="${k.id}" data-nom="${esc(k.nombre)}">Revocar</button>` : ""}
            <button type="button" class="btn danger btn-sm" data-del="${k.id}" data-nom="${esc(k.nombre)}">Eliminar</button>
          </div></td>
        </tr>`).join("")
      : `<tr><td colspan="7"><div class="empty-state" style="border:0">No hay claves API que coincidan con el filtro.</div></td></tr>`;
  };

  $("#api-buscar").addEventListener("input", pintarFilas);
  $("#api-estado").addEventListener("change", pintarFilas);
  pintarFilas();

  $("#api-nueva").onclick = () => {
    formModal("Emitir clave API",
      `<label class="field">Nombre descriptivo<input name="nombre" required maxlength="120" placeholder="Ej. Integración reportes BI" /></label>
       <p class="muted text-sm" style="margin:0">Por seguridad, la clave completa se mostrará una única vez.</p>`,
      async (fd) => {
        const k = await api.crearClaveApi(fd.get("nombre").trim());
        await adminClaves(body, api);
        setTimeout(() => {
          abrirModal(`
            <div class="modal-header">
              <h2>Clave emitida correctamente</h2>
              <button type="button" class="btn ghost btn-sm" data-close-modal>Cerrar</button>
            </div>
            <p class="muted text-sm" style="margin:0 0 0.75rem">Cópiala ahora y envíala en el encabezado <code class="mono">X-API-Key</code>.</p>
            <div class="ficha-code" id="clave-valor">${esc(k.clave)}</div>
            <div class="row" style="justify-content:flex-end;margin-top:1rem">
              <button type="button" class="btn ghost" data-close-modal>Listo</button>
              <button type="button" class="btn primary" id="copiar-clave">Copiar clave</button>
            </div>`, { sm: true });
          $("#copiar-clave").onclick = async () => {
            try {
              await navigator.clipboard.writeText(k.clave);
              toast("Clave copiada al portapapeles", "ok");
            } catch {
              toast("Selecciona y copia la clave manualmente");
            }
          };
        }, 0);
      });
  };

  body.onclick = async (e) => {
    const del = e.target.closest("[data-del]");
    const b = e.target.closest("[data-rev]");
    if (del) {
      const ok = await modalConfirmar({
        titulo: "Eliminar clave API",
        mensaje: `¿Estás seguro de eliminar permanentemente la clave «${del.dataset.nom}» y su registro de usos?`,
        confirmarTexto: "Sí, eliminar",
        peligro: true,
      });
      if (!ok) return;
      try {
        await api.eliminarClaveApi(del.dataset.del);
        toast("Clave eliminada", "ok");
        await adminClaves(body, api);
      } catch (ex) {
        toast(ex.message, "error");
      }
      return;
    }
    if (!b) return;
    const ok = await modalConfirmar({
      titulo: "Revocar clave API",
      mensaje: `El programa externo que use la clave «${b.dataset.nom}» perderá el acceso de inmediato. ¿Deseas continuar?`,
      confirmarTexto: "Sí, revocar",
      peligro: true,
    });
    if (!ok) return;
    try {
      await api.revocarClaveApi(b.dataset.rev);
      toast("Clave revocada", "ok");
      await adminClaves(body, api);
    } catch (ex) {
      toast(ex.message, "error");
    }
  };
}

/* ========================== ROLES PERSONALIZADOS ========================== */
async function adminRoles(body, api) {
  const [roles, disponibles] = await Promise.all([api.roles(true), api.permisos()]);
  const checks = (seleccionados = []) => disponibles.map((p) => `
    <label class="check-row" style="align-items:flex-start">
      <input type="checkbox" name="permisos" value="${esc(p.codigo)}" ${seleccionados.includes(p.codigo) ? "checked" : ""} />
      <span><strong>${esc(p.codigo)}</strong> <span class="muted">— ${esc(p.descripcion)}</span></span>
    </label>`).join("");

  body.innerHTML = `
    <div class="filters-bar" style="justify-content:space-between;margin-bottom:0.85rem">
      <div class="row" style="flex:1;min-width:240px">
        <input id="rol-buscar" placeholder="Filtrar por nombre, descripción o permiso…" style="max-width:320px" />
        <select id="rol-estado" style="width:auto;min-width:155px" aria-label="Estado del rol">
          <option value="todos">Todos (${roles.length})</option>
          <option value="activos">Solo activos (${roles.filter((r) => r.activo).length})</option>
          <option value="inactivos">Solo inactivos (${roles.filter((r) => !r.activo).length})</option>
        </select>
        <span id="rol-conteo" class="muted text-sm"></span>
      </div>
      <button type="button" class="btn primary" id="rol-nuevo">+ Nuevo rol</button>
    </div>
    <div class="table-wrap"><table class="data admin-table">
      <thead><tr><th>Nombre</th><th>Descripción</th><th>Permisos</th><th>Estado</th><th>Acciones</th></tr></thead>
      <tbody id="rol-tbody"></tbody>
    </table></div>`;

  const pintarFilas = () => {
    const q = ($("#rol-buscar")?.value || "").trim().toLowerCase();
    const est = $("#rol-estado")?.value || "todos";
    const filtrados = roles.filter((r) => {
      if (est === "activos" && !r.activo) return false;
      if (est === "inactivos" && r.activo) return false;
      if (!q) return true;
      const perms = (r.permisos || []).join(" ").toLowerCase();
      return (
        r.nombre.toLowerCase().includes(q) ||
        (r.descripcion || "").toLowerCase().includes(q) ||
        perms.includes(q)
      );
    });
    $("#rol-conteo").textContent = `${filtrados.length} mostrado(s)`;
    $("#rol-tbody").innerHTML = filtrados.length
      ? filtrados.map((r) => `<tr>
          <td><strong>${esc(r.nombre)}</strong></td>
          <td class="muted">${esc(r.descripcion || "—")}</td>
          <td class="text-sm muted">${esc((r.permisos || []).join(", ") || "—")}</td>
          <td>${badgeActivo(r.activo)}</td>
          <td><div class="cell-actions">
            <button type="button" class="btn btn-sm" data-edit="${r.id}">Editar</button>
            <button type="button" class="btn btn-sm ${r.activo ? "ghost" : "ok"}" data-act="${r.id}" data-on="${r.activo ? "true" : "false"}">
              ${r.activo ? "Desactivar" : "Activar"}
            </button>
            <button type="button" class="btn danger btn-sm" data-del="${r.id}" data-nom="${esc(r.nombre)}">Eliminar</button>
          </div></td>
        </tr>`).join("")
      : `<tr><td colspan="5"><div class="empty-state" style="border:0">No hay roles personalizados que coincidan con el filtro.</div></td></tr>`;
  };

  $("#rol-buscar").addEventListener("input", pintarFilas);
  $("#rol-estado").addEventListener("change", pintarFilas);
  pintarFilas();

  $("#rol-nuevo").onclick = () => {
    formModal("Nuevo rol personalizado", `
      <label class="field">Nombre<input name="nombre" required maxlength="80" /></label>
      <label class="field">Descripción<input name="descripcion" maxlength="200" /></label>
      <fieldset class="permisos-box">
        <legend>Permisos</legend>
        <div class="stack" style="gap:0.55rem">${checks()}</div>
      </fieldset>`,
      async (fd) => {
        const permisos = fd.getAll("permisos");
        if (!permisos.length) throw new ErrorApi("Marca al menos un permiso.");
        await api.crearRol(fd.get("nombre").trim(), fd.get("descripcion").trim(), permisos);
        toast("Rol creado", "ok");
        await adminRoles(body, api);
      }, { sm: false });
  };

  body.onclick = async (e) => {
    const edit = e.target.closest("[data-edit]");
    const act = e.target.closest("[data-act]");
    const del = e.target.closest("[data-del]");
    if (del) {
      const ok = await modalConfirmar({
        titulo: "Eliminar rol personalizado",
        mensaje: `¿Estás seguro de eliminar permanentemente el rol «${del.dataset.nom}»? Los usuarios que lo tengan asignado volverán a su rol base.`,
        confirmarTexto: "Sí, eliminar",
        peligro: true,
      });
      if (!ok) return;
      try {
        await api.eliminarRol(del.dataset.del);
        toast("Rol eliminado", "ok");
        await adminRoles(body, api);
      } catch (ex) {
        toast(ex.message, "error");
      }
      return;
    }
    if (edit) {
      const rol = roles.find((r) => r.id === edit.dataset.edit);
      formModal(`Editar rol: ${rol.nombre}`, `
        <label class="field">Nombre<input name="nombre" required value="${esc(rol.nombre)}" /></label>
        <label class="field">Descripción<input name="descripcion" value="${esc(rol.descripcion || "")}" /></label>
        <fieldset class="permisos-box">
          <legend>Permisos</legend>
          <div class="stack" style="gap:0.55rem">${checks(rol.permisos || [])}</div>
        </fieldset>`,
        async (fd) => {
          const permisos = fd.getAll("permisos");
          if (!permisos.length) throw new ErrorApi("Marca al menos un permiso.");
          await api.editarRol(edit.dataset.edit, {
            nombre: fd.get("nombre").trim(),
            descripcion: fd.get("descripcion").trim(),
            permisos,
          });
          toast("Rol actualizado", "ok");
          await adminRoles(body, api);
        }, { sm: false });
      return;
    }
    if (act) {
      try {
        const activo = act.dataset.on !== "true";
        await api.editarRol(act.dataset.act, { activo });
        toast(activo ? "Rol activado" : "Rol desactivado", "ok");
        await adminRoles(body, api);
      } catch (ex) {
        toast(ex.message, "error");
      }
    }
  };
}
