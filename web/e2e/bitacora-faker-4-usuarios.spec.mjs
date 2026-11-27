import fs from "node:fs";
import { test, expect } from "@playwright/test";
import { fakerES as faker } from "@faker-js/faker";
import {
  generarActividadUsuarioFalso,
  generarCatalogosFalsos,
  generarCuatroUsuariosFalsos,
} from "./helpers/fakerData.mjs";

const JEFE_CORREO = process.env.JEFE_CORREO || "jefe@correo.com";
const JEFE_CLAVE = process.env.JEFE_CLAVE || "claveSegura123";
const SUPER_CORREO = process.env.SUPER_CORREO || "superusuario@zgroup.com";
const SUPER_CLAVE = process.env.SUPER_CLAVE || "SuperSegura123";

async function iniciarSesion(page, correo, clave) {
  await page.goto("/");
  await expect(page.locator("#vista-login")).toBeVisible();
  await page.locator('#form-login input[name="correo"]').fill(correo);
  await page.locator('#form-login input[name="clave"]').fill(clave);
  await page.locator('#form-login button[type="submit"]').click();
  await expect(page.locator("#vista-app")).toBeVisible();
}

async function cerrarSesion(page) {
  await page.locator("#btn-salir").click();
  await expect(page.locator("#vista-login")).toBeVisible();
}

async function aceptarConfirmacionModal(page) {
  await expect(page.locator("#mc-ok")).toBeVisible();
  await page.locator("#mc-ok").click();
  await expect(page.locator("#modal")).toHaveClass(/hidden/);
}

test.describe("Pruebas E2E completas con Playwright + Faker.js (4 usuarios aleatorios)", () => {
  test("Flujo integral de 4 usuarios falsos, administración, superusuario y preservación histórica", async ({ page }) => {
    const catalogos = generarCatalogosFalsos();
    const usuarios = generarCuatroUsuariosFalsos(catalogos.rolNombre);
    const actividadesPorUsuario = new Map();

    /* =====================================================================
       FASE 1: JEFE CREA CATÁLOGOS ALEATORIOS Y LOS 4 USUARIOS FALSOS
       ===================================================================== */
    await iniciarSesion(page, JEFE_CORREO, JEFE_CLAVE);
    await page.locator('#main-nav a[href="#/admin"]').click();
    await expect(page.locator("#ad-tabs")).toBeVisible();

    // 1.1 Áreas: crear, filtrar, renombrar, desactivar/activar
    await page.locator('#ad-tabs [data-tab="areas"]').click();
    await page.locator("#area-nueva").click();
    await page.locator('#modal-form input[name="nombre"]').fill(catalogos.areaNombre);
    await page.locator('#modal-form button[type="submit"]').click();
    await expect(page.locator("#area-tbody")).toContainText(catalogos.areaNombre);

    await page.locator("#area-buscar").fill(catalogos.areaNombre);
    await expect(page.locator("#area-tbody tr")).toHaveCount(1);
    await page.locator('#area-tbody [data-ren]').first().click();
    await page.locator('#modal-form input[name="nombre"]').fill(catalogos.areaRenombrada);
    await page.locator('#modal-form button[type="submit"]').click();
    await page.locator("#area-buscar").fill(catalogos.areaRenombrada);
    await expect(page.locator("#area-tbody")).toContainText(catalogos.areaRenombrada);

    await page.locator('#area-tbody [data-act]').first().click(); // desactivar
    await page.locator("#area-buscar").fill(catalogos.areaRenombrada);
    await expect(page.locator("#area-tbody")).toContainText("inactivo");
    await page.locator('#area-tbody [data-act]').first().click(); // reactivar
    await page.locator("#area-buscar").fill(catalogos.areaRenombrada);
    await expect(page.locator("#area-tbody")).toContainText("activo");

    // 1.2 Subtipos: crear, filtrar, desactivar/activar
    await page.locator('#ad-tabs [data-tab="subtipos"]').click();
    await page.locator("#sub-nuevo").click();
    await page.locator('#modal-form select[name="tipo"]').selectOption(catalogos.subtipoTipo);
    await page.locator('#modal-form input[name="nombre"]').fill(catalogos.subtipoNombre);
    await page.locator('#modal-form button[type="submit"]').click();
    await page.locator("#sub-buscar").fill(catalogos.subtipoNombre);
    await expect(page.locator("#sub-tbody")).toContainText(catalogos.subtipoNombre);
    await page.locator('#sub-tbody [data-tipo]').first().click();
    await page.locator("#sub-buscar").fill(catalogos.subtipoNombre);
    await expect(page.locator("#sub-tbody")).toContainText("inactivo");
    await page.locator('#sub-tbody [data-tipo]').first().click();
    await page.locator("#sub-buscar").fill(catalogos.subtipoNombre);
    await expect(page.locator("#sub-tbody")).toContainText("activo");

    // 1.3 Roles personalizados: crear con permisos aleatorios/completos y filtrar
    await page.locator('#ad-tabs [data-tab="roles"]').click();
    await page.locator("#rol-nuevo").click();
    await page.locator('#modal-form input[name="nombre"]').fill(catalogos.rolNombre);
    await page.locator('#modal-form input[name="descripcion"]').fill(catalogos.rolDescripcion);
    for (const perm of catalogos.rolPermisos) {
      await page.locator(`#modal-form input[name="permisos"][value="${perm}"]`).check();
    }
    await page.locator('#modal-form button[type="submit"]').click();
    await page.locator("#rol-buscar").fill(catalogos.rolNombre);
    await expect(page.locator("#rol-tbody")).toContainText(catalogos.rolNombre);

    // 1.4 Claves API: emitir clave temporal, revocar y eliminar otra
    await page.locator('#ad-tabs [data-tab="claves"]').click();
    await page.locator("#api-nueva").click();
    await page.locator('#modal-form input[name="nombre"]').fill(catalogos.claveApiDescartarNombre);
    await page.locator('#modal-form button[type="submit"]').click();
    await expect(page.locator("#clave-valor")).toContainText("bti_");
    await page.locator('#modal-panel [data-close-modal]').first().click();
    await expect(page.locator("#modal")).toHaveClass(/hidden/);

    await page.locator("#api-buscar").fill(catalogos.claveApiDescartarNombre);
    await expect(page.locator("#api-tbody tr")).toHaveCount(1);
    await page.locator('#api-tbody [data-rev]').first().click();
    await aceptarConfirmacionModal(page);
    await expect(page.locator("#api-tbody")).toContainText("revocada");
    await page.locator("#api-buscar").fill(catalogos.claveApiDescartarNombre);
    await page.locator('#api-tbody [data-del]').first().click();
    await aceptarConfirmacionModal(page);
    await expect(page.locator("#api-tbody")).not.toContainText(catalogos.claveApiDescartarNombre);

    // 1.5 Usuarios: crear los 4 usuarios falsos con Faker (probando validación en vivo y ojito)
    await page.locator('#ad-tabs [data-tab="usuarios"]').click();
    for (const u of usuarios) {
      await page.locator("#usr-nuevo").click();
      await page.locator('#modal-form input[name="nombre"]').fill(u.nombre);
      await page.locator('#modal-form input[name="correo"]').fill(u.correo);
      await expect(page.locator('#modal-form [data-email-check] [data-crit="dominio"]')).toHaveClass(/is-valid/);

      await page.locator('#modal-form select[name="rol_tipo"]').selectOption(u.rolTipo);
      if (u.rolTipo === "otro") {
        await expect(page.locator("#box-rol-custom")).toBeVisible();
        const option = page.locator('#modal-form select[name="rol_custom_id"] option', { hasText: catalogos.rolNombre });
        const val = await option.getAttribute("value");
        await page.locator('#modal-form select[name="rol_custom_id"]').selectOption(val);
      }

      const passInput = page.locator('#modal-form input[name="clave"]');
      await passInput.fill(u.clave);
      await expect(page.locator('#modal-form [data-pass-check] [data-crit="longitud"]')).toHaveClass(/is-valid/);
      await page.locator('#modal-form [data-toggle-pass]').click();
      await expect(passInput).toHaveAttribute("type", "text");
      await page.locator('#modal-form [data-toggle-pass]').click();
      await expect(passInput).toHaveAttribute("type", "password");

      await page.locator('#modal-form button[type="submit"]').click();
      await expect(page.locator("#usr-tbody")).toContainText(u.correo);
    }

    // Probar cambio de contraseña desde admin sobre U3 antes de que entre
    const u3 = usuarios[2];
    await page.locator("#usr-buscar").fill(u3.correo);
    await expect(page.locator("#usr-tbody tr")).toHaveCount(1);
    await page.locator('#usr-tbody [data-clave]').first().click();
    await page.locator('#modal-form input[name="clave"]').fill(u3.claveNueva);
    await page.locator('#modal-form button[type="submit"]').click();
    u3.clave = u3.claveNueva;

    await cerrarSesion(page);

    /* =====================================================================
       FASE 2: CADA UNO DE LOS 4 USUARIOS FALSOS RELLENA Y USA TODA LA WEB
       ===================================================================== */
    for (const u of usuarios) {
      const data = generarActividadUsuarioFalso(u, catalogos.areaRenombrada);
      await iniciarSesion(page, u.correo, u.clave);
      await expect(page.locator("#user-chip")).toContainText(u.nombre);

      // 2.1 Hoy (#/): crear evento principal (con área Faker y seguimiento) + evento informativo
      await expect(page.locator("#form-alta")).toBeVisible();
      await page.locator('#form-alta select[name="tipo"]').selectOption(data.eventoPrincipal.tipo);
      if (data.eventoPrincipal.tipo === catalogos.subtipoTipo) {
        const subOpt = page.locator('#form-alta select[name="subtipo"] option', { hasText: catalogos.subtipoNombre });
        await expect(subOpt).toBeAttached();
        await page.locator('#form-alta select[name="subtipo"]').selectOption(catalogos.subtipoNombre);
      }
      const areaOpt = page.locator('#form-alta select[name="area_id"] option', { hasText: catalogos.areaRenombrada });
      const areaVal = await areaOpt.getAttribute("value");
      await page.locator('#form-alta select[name="area_id"]').selectOption(areaVal);
      await page.locator('#form-alta input[name="solicitante_nombre"]').fill(data.eventoPrincipal.solicitante);
      await page.locator('#form-alta input[name="titulo"]').fill(data.eventoPrincipal.titulo);
      await page.locator('#form-alta textarea[name="descripcion"]').fill(data.eventoPrincipal.descripcion);
      await page.locator('#form-alta input[name="requiere_seguimiento"]').check();
      await page.locator('#form-alta button[type="submit"]').click();
      await expect(page.locator("#lista-hoy")).toContainText(data.eventoPrincipal.titulo);

      const filaPrincipal = page.locator("#lista-hoy tr[data-folio]", { hasText: data.eventoPrincipal.titulo }).first();
      const folioPrincipal = await filaPrincipal.getAttribute("data-folio");
      expect(folioPrincipal).toMatch(/^BIT-\d{4}-\d{5}$/);
      data.folioPrincipal = folioPrincipal;

      // Segundo registro aleatorio rápido
      await page.locator('#form-alta select[name="tipo"]').selectOption(data.eventoInformativo.tipo);
      await page.locator('#form-alta input[name="solicitante_nombre"]').fill(data.eventoInformativo.solicitante);
      await page.locator('#form-alta input[name="titulo"]').fill(data.eventoInformativo.titulo);
      await page.locator('#form-alta textarea[name="descripcion"]').fill(data.eventoInformativo.descripcion);
      await page.locator('#form-alta button[type="submit"]').click();
      await expect(page.locator("#lista-hoy")).toContainText(data.eventoInformativo.titulo);

      // Filtrar en Hoy por tipo y restablecer con botón Hoy
      await page.locator("#filtro-tipo").selectOption(data.eventoPrincipal.tipo);
      await page.locator("#btn-filtrar").click();
      await expect(page.locator("#lista-hoy")).toContainText(folioPrincipal);
      await page.locator("#btn-hoy").click();

      // 2.2 Detalle del evento: nota, compromiso, corregir datos (auditoría), cambiar estado y cumplir compromiso
      await page.locator(`#lista-hoy tr[data-folio="${folioPrincipal}"]`).click();
      await expect(page.locator("#modal")).not.toHaveClass(/hidden/);

      // Agregar nota aleatoria
      await page.locator("#det-nota").fill(data.eventoPrincipal.notaSeguimiento);
      await page.locator('#det-nota-form button[type="submit"]').click();
      await expect(page.locator(".notas-list")).toContainText(data.eventoPrincipal.notaSeguimiento);

      // Agregar compromiso aleatorio
      await page.locator("#det-comp-desc").fill(data.eventoPrincipal.compromisoDesc);
      await page.locator("#det-comp-fecha").fill(data.eventoPrincipal.compromisoFecha);
      await page.locator('#det-comp-form button[type="submit"]').click();
      await expect(page.locator("#det-comps")).toContainText(data.eventoPrincipal.compromisoDesc);

      // Corregir datos (genera registro de Auditoría)
      await page.locator("#det-corregir").click();
      await page.locator('#form-corregir input[name="titulo"]').fill(data.eventoPrincipal.tituloCorregido);
      await page.locator('#form-corregir input[name="referencia"]').fill(data.eventoPrincipal.referenciaNueva);
      await page.locator('#form-corregir button[type="submit"]').click();
      await expect(page.locator("#modal")).toContainText(data.eventoPrincipal.tituloCorregido);

      // Ver modal de Auditoría
      await page.locator("#det-auditoria").click();
      await expect(page.locator("#modal")).toContainText("Auditoría de cambios");
      await expect(page.locator("#modal")).toContainText("titulo");
      await page.locator("#aud-volver").click();

      // Cambiar estado -> en_proceso
      await page.locator("#det-estado").selectOption("en_proceso");
      await page.locator("#det-cambiar").click();
      await page.locator('#form-estado textarea[name="nota"]').fill(data.eventoPrincipal.notaCambioEstado);
      await page.locator('#form-estado button[type="submit"]').click();
      await expect(page.locator("#modal")).toContainText("en proceso");

      // Para U1 y U2 cumplimos el compromiso desde el detalle; para U4 dejamos el compromiso pendiente para auditarlo en Superusuario
      if (u.rolTipo !== "otro") {
        await page.locator('#det-comps [data-acc="cumplido"]').first().click();
        await expect(page.locator("#det-comps")).toContainText("cumplido");
      }

      await page.locator('#modal-panel [data-close-modal]').first().click();
      await expect(page.locator("#modal")).toHaveClass(/hidden/);

      // 2.3 Pendientes (#/pendientes)
      await page.locator('#main-nav a[href="#/pendientes"]').click();
      await expect(page.locator("#pen-ev")).toContainText(folioPrincipal);
      await page.locator("#pen-venc").check();
      await page.locator("#pen-venc").uncheck();

      // 2.4 Búsqueda histórica (#/busqueda) y descarga CSV si tiene permiso
      await page.locator('#main-nav a[href="#/busqueda"]').click();
      await page.locator("#bq-q").fill(folioPrincipal);
      await page.locator("#bq-btn").click();
      await expect(page.locator("#bq-res")).toContainText(folioPrincipal);

      if (u.puedeCsv) {
        const downloadPromise = page.waitForEvent("download");
        await page.locator("#bq-csv").click();
        const dl = await downloadPromise;
        expect(dl.suggestedFilename()).toBe("bitacora.csv");
      } else {
        await expect(page.locator("#bq-csv")).toHaveCount(0);
      }

      // 2.5 Tablero KPI (#/tablero) para quienes tienen permiso ver_kpi
      if (u.puedeTablero) {
        await page.locator('#main-nav a[href="#/tablero"]').click();
        await expect(page.locator("#tb-grid .kpi-card")).toHaveCount(12);
        await page.locator("#tb-hoy").click();
        await page.locator('#tb-grid [data-kid="K1"]').click();
        await expect(page.locator("#modal")).toContainText("K1 —");
        await page.locator('#modal-panel [data-close-modal]').first().click();
      } else {
        await expect(page.locator('#main-nav a[href="#/tablero"]')).toBeHidden();
      }

      // 2.6 Mi perfil (#/perfil): para U1 probamos cambiar su propio correo y contraseña desde la web
      if (u.alias === "U1 Encargado") {
        const nuevoCorreoU1 = `upd.${u.correo}`;
        await page.locator('#main-nav a[href="#/perfil"]').click();
        await expect(page.locator("#form-perfil-cuenta")).toBeVisible();
        await page.locator('#form-perfil-cuenta input[name="correo"]').fill(nuevoCorreoU1);
        await page.locator('#form-perfil-cuenta input[name="clave_nueva"]').fill(u.claveNueva);
        await page.locator('#form-perfil-cuenta input[name="clave_confirmar"]').fill(u.claveNueva);
        await page.locator('#form-perfil-cuenta input[name="clave_actual"]').fill(u.clave);
        await page.locator('#form-perfil-cuenta button[type="submit"]').click();
        await expect(page.locator("#contenido")).toContainText(nuevoCorreoU1);
        u.correo = nuevoCorreoU1;
        u.clave = u.claveNueva;
      }

      actividadesPorUsuario.set(u.correo, data);
      await cerrarSesion(page);
    }

    /* =====================================================================
       FASE 3: JEFE ELIMINA EL ÁREA Y ELIMINA A DOS USUARIOS FALSOS (SIN CASCADA)
       ===================================================================== */
    await iniciarSesion(page, JEFE_CORREO, JEFE_CLAVE);
    await page.locator('#main-nav a[href="#/admin"]').click();

    // Eliminar área Faker (debe preservar area_nombre en Superusuario)
    await page.locator('#ad-tabs [data-tab="areas"]').click();
    await page.locator("#area-buscar").fill(catalogos.areaRenombrada);
    await page.locator('#area-tbody [data-del]').first().click();
    await aceptarConfirmacionModal(page);
    await expect(page.locator("#area-tbody")).not.toContainText(catalogos.areaRenombrada);

    // Eliminar U3 y U4 desde Administración -> Usuarios
    await page.locator('#ad-tabs [data-tab="usuarios"]').click();
    for (const uElim of usuarios.filter((x) => x.eliminarAlFinal)) {
      await page.locator("#usr-buscar").fill(uElim.correo);
      await expect(page.locator("#usr-tbody tr")).toHaveCount(1);
      await page.locator('#usr-tbody [data-del]').first().click();
      await aceptarConfirmacionModal(page);
      await expect(page.locator("#usr-tbody")).not.toContainText(uElim.correo);
      await page.locator("#usr-buscar").fill(uElim.correo);
      await expect(page.locator("#usr-tbody")).toContainText("No hay usuarios que coincidan");
    }
    await cerrarSesion(page);

    // Verificar que un usuario eliminado ya no puede iniciar sesión
    const u4 = usuarios[3];
    await page.goto("/");
    await page.locator('#form-login input[name="correo"]').fill(u4.correo);
    await page.locator('#form-login input[name="clave"]').fill(u4.clave);
    await page.locator('#form-login button[type="submit"]').click();
    await expect(page.locator("#login-error")).toBeVisible();

    /* =====================================================================
       FASE 4: PORTAL SUPERUSUARIO VERIFICA TODO EL HISTORIAL Y "MI PERFIL"
       ===================================================================== */
    await iniciarSesion(page, SUPER_CORREO, SUPER_CLAVE);
    await expect(page.locator("body")).toHaveClass(/mode-superadmin/);
    await expect(page.locator("#contenido")).toContainText("Portal de Superusuario");

    // 4.1 Cuentas: ver cuentas activas y eliminadas y abrir expediente de U4 eliminado
    await page.locator('#main-nav a[href="#/super/cuentas"]').click();
    await page.locator("#sc-q").fill(u4.correo);
    await page.locator("#sc-est").selectOption("eliminada");
    await expect(page.locator("#sc-tbody")).toContainText(u4.nombre);

    await page.locator(`#sc-tbody [data-expediente]`).first().click();
    const actU4 = actividadesPorUsuario.get(u4.correo);
    await expect(page.locator("#modal")).toContainText(actU4.folioPrincipal);
    await expect(page.locator("#modal")).toContainText("eliminada");

    // Verificar en modo impresión (@media print) que SOLO se imprime el expediente del modal y NO la tabla de fondo
    await page.emulateMedia({ media: "print" });
    await expect(page.locator("#modal-panel")).toBeVisible();
    await expect(page.locator("#vista-app")).toBeHidden();
    await page.emulateMedia({ media: "screen" });

    // Verificar CSV individual del expediente (solo este usuario, nunca otros usuarios)
    const expDownloadPromise = page.waitForEvent("download");
    await page.locator("#exp-csv").click();
    const expDl = await expDownloadPromise;
    expect(expDl.suggestedFilename()).toContain("expediente-");
    const expCsvTxt = fs.readFileSync(await expDl.path(), "utf8");
    expect(expCsvTxt).toContain("EXPEDIENTE INDIVIDUAL DE CUENTA");
    expect(expCsvTxt).toContain(u4.correo);
    expect(expCsvTxt).toContain(actU4.folioPrincipal);
    expect(expCsvTxt).not.toContain(usuarios[0].correo);

    await page.locator('#modal-panel [data-close-modal]').first().click();

    // 4.2 Incidencias y Registros: ficha documental preserva autor, nota, compromiso, auditoría y área eliminada
    await page.locator('#main-nav a[href="#/super/registros"]').click();
    await page.locator("#sr-q").fill(actU4.folioPrincipal);
    await page.locator("#sr-btn").click();
    await page.locator(`#sr-res [data-super-folio="${actU4.folioPrincipal}"]`).click();

    await expect(page.locator("#modal")).toContainText(u4.nombre);
    await expect(page.locator("#modal")).toContainText(catalogos.areaRenombrada);
    await expect(page.locator("#modal")).toContainText(actU4.eventoPrincipal.notaSeguimiento);
    await expect(page.locator("#modal")).toContainText(actU4.eventoPrincipal.compromisoDesc);
    await expect(page.locator("#modal")).toContainText("Auditoría de cambios");
    await page.locator('#modal-panel [data-close-modal]').first().click();

    // 4.3 Pendientes, Archivos y Actividad
    await page.locator('#main-nav a[href="#/super/pendientes"]').click();
    await expect(page.locator("#sp-co")).toContainText(actU4.eventoPrincipal.compromisoDesc);

    await page.locator('#main-nav a[href="#/super/archivos"]').click();
    await expect(page.locator("#contenido")).toContainText(actU4.eventoPrincipal.referenciaNueva);

    await page.locator('#main-nav a[href="#/super/actividad"]').click();
    await page.locator("#sa-q").fill(u4.nombre);
    await page.locator("#sa-btn").click();
    await expect(page.locator("#sa-lista")).toContainText(u4.nombre);

    // 4.4 Mi perfil: cambiar nombre con Faker verificando clave actual y restaurar el original
    const nombreTemporalSuper = `Auditor ${faker.person.lastName()}`;
    await page.locator('#main-nav a[href="#/super/perfil"]').click();
    await expect(page.locator("#form-perfil-cuenta")).toBeVisible();
    await page.locator('#form-perfil-cuenta input[name="nombre"]').fill(nombreTemporalSuper);
    await page.locator('#form-perfil-cuenta input[name="clave_actual"]').fill(SUPER_CLAVE);
    await page.locator('#form-perfil-cuenta button[type="submit"]').click();
    await expect(page.locator("#user-chip")).toContainText(nombreTemporalSuper);

    await page.locator('#form-perfil-cuenta input[name="nombre"]').fill("Superusuario ZGROUP");
    await page.locator('#form-perfil-cuenta input[name="clave_actual"]').fill(SUPER_CLAVE);
    await page.locator('#form-perfil-cuenta button[type="submit"]').click();
    await expect(page.locator("#user-chip")).toContainText("Superusuario ZGROUP");

    // 4.5 Restablecer credenciales desde Superusuario sobre U1 y luego depurar las 4 cuentas de prueba
    const u1 = usuarios[0];
    const correoSuperReset = `sup.${u1.correo}`;
    await page.locator('#main-nav a[href="#/super/cuentas"]').click();
    await page.locator("#sc-q").fill(u1.correo);
    await expect(page.locator("#sc-tbody")).toContainText(u1.correo);
    await page.locator("#sc-tbody [data-credenciales]").first().click();
    await expect(page.locator("#form-super-credenciales")).toBeVisible();
    await page.locator('#form-super-credenciales input[name="correo"]').fill(correoSuperReset);
    await page.locator('#form-super-credenciales input[name="clave_nueva"]').fill(u1.clave);
    await page.locator('#form-super-credenciales input[name="clave_confirmar"]').fill(u1.clave);
    await page.locator('#form-super-credenciales input[name="clave_actual_super"]').fill(SUPER_CLAVE);
    await page.locator('#form-super-credenciales button[type="submit"]').click();
    await expect(page.locator("#modal")).toHaveClass(/hidden/);
    await page.locator("#sc-q").fill(correoSuperReset);
    await expect(page.locator("#sc-tbody")).toContainText(correoSuperReset);
    u1.correo = correoSuperReset;

    // 4.6 Eliminar información seleccionada permanentemente (purga parcial en U3 y purga completa de los 4 usuarios de prueba)
    await page.locator("#sc-q").fill(u3.correo);
    await expect(page.locator("#sc-tbody")).toContainText(u3.nombre);
    await page.locator("#sc-tbody [data-purgar]").first().click();
    await expect(page.locator("#form-purga")).toBeVisible();
    await page.locator('#form-purga input[name="eliminar_actividades"]').check();
    await page.locator('#form-purga button[type="submit"]').click();
    await expect(page.locator("#purga-confirm-box")).toBeVisible();
    await page.locator("#purga-confirmar-ok").click();
    await expect(page.locator("#modal")).toHaveClass(/hidden/);

    // Purga permanente completa de los 4 usuarios falsos de prueba para dejar PostgreSQL limpio
    for (const uFalso of usuarios) {
      await page.locator("#sc-q").fill(uFalso.correo);
      await expect(page.locator("#sc-tbody")).toContainText(uFalso.correo);
      await page.locator("#sc-tbody [data-purgar]").first().click();
      await expect(page.locator("#form-purga")).toBeVisible();
      await page.locator('#form-purga input[name="eliminar_cuenta"]').check();
      await page.locator('#form-purga button[type="submit"]').click();
      await expect(page.locator("#purga-confirm-box")).toBeVisible();
      await page.locator("#purga-confirmar-ok").click();
      await expect(page.locator("#modal")).toHaveClass(/hidden/);
      await page.locator("#sc-q").fill(uFalso.correo);
      await expect(page.locator("#sc-tbody")).toContainText("Sin cuentas que coincidan");
    }
    await cerrarSesion(page);

    /* =====================================================================
       FASE 5: LIMPIEZA DE CATÁLOGOS DE PRUEBA (MANTENIENDO HISTORIAL EN SUPER)
       ===================================================================== */
    await iniciarSesion(page, JEFE_CORREO, JEFE_CLAVE);
    await page.locator('#main-nav a[href="#/admin"]').click();

    await page.locator('#ad-tabs [data-tab="subtipos"]').click();
    await page.locator("#sub-buscar").fill(catalogos.subtipoNombre);
    await page.locator('#sub-tbody [data-del-tipo]').first().click();
    await aceptarConfirmacionModal(page);
    await expect(page.locator("#sub-tbody")).not.toContainText(catalogos.subtipoNombre);

    await page.locator('#ad-tabs [data-tab="roles"]').click();
    await page.locator("#rol-buscar").fill(catalogos.rolNombre);
    await page.locator('#rol-tbody [data-del]').first().click();
    await aceptarConfirmacionModal(page);
    await expect(page.locator("#rol-tbody")).not.toContainText(catalogos.rolNombre);
  });
});
