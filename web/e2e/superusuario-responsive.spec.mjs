import { test, expect } from "@playwright/test";

const SUPER_CORREO = process.env.SUPER_CORREO || "superusuario@zgroup.com";
const SUPER_CLAVE = process.env.SUPER_CLAVE || "SuperSegura123";

const PANTALLAS_LAPTOP_PC = [
  { nombre: "PC Full HD 1920x1080", width: 1920, height: 1080, modoMovil: false },
  { nombre: "Laptop/Mac 1440x900", width: 1440, height: 900, modoMovil: false },
  { nombre: "Laptop estándar 1366x768", width: 1366, height: 768, modoMovil: false },
  { nombre: "Laptop compacta 1280x720", width: 1280, height: 720, modoMovil: false },
  { nombre: "Laptop pequeña / Split 1024x768", width: 1024, height: 768, modoMovil: false },
  { nombre: "Tablet / Ventana reducida 800x900", width: 800, height: 900, modoMovil: true },
];

test("Portal Superusuario es responsivo sin desbordamiento en pantallas de laptop y PC", async ({ page }) => {
  await page.goto("/");
  await page.locator('#form-login input[name="correo"]').fill(SUPER_CORREO);
  await page.locator('#form-login input[name="clave"]').fill(SUPER_CLAVE);
  await page.locator('#form-login button[type="submit"]').click();
  await expect(page.locator("#vista-app")).toBeVisible();
  await expect(page.locator("#contenido")).toContainText("Portal de Superusuario");

  for (const vp of PANTALLAS_LAPTOP_PC) {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.waitForTimeout(100);

    const medidas = await page.evaluate(() => {
      const docOverflow = document.documentElement.scrollWidth - window.innerWidth;
      const topbar = document.querySelector(".topbar-inner");
      const brand = document.querySelector(".brand-block");
      const nav = document.querySelector("#main-nav");
      const actions = document.querySelector(".topbar-actions");
      const navLinks = [...document.querySelectorAll("#main-nav a:not(.hidden)")];

      return {
        innerWidth: window.innerWidth,
        docOverflow,
        topbarRect: topbar?.getBoundingClientRect().toJSON(),
        brandRect: brand?.getBoundingClientRect().toJSON(),
        navRect: nav?.getBoundingClientRect().toJSON(),
        actionsRect: actions?.getBoundingClientRect().toJSON(),
        navScrollOverflow: nav ? nav.scrollWidth - nav.clientWidth : 0,
        linksWrapped: navLinks.some((a) => a.getBoundingClientRect().height > 40),
      };
    });

    expect(medidas.docOverflow, `${vp.nombre}: sin scroll horizontal global`).toBeLessThanOrEqual(1);

    if (!vp.modoMovil) {
      await expect(page.locator("#main-nav")).toBeVisible();
      expect(medidas.actionsRect.right, `${vp.nombre}: botones dentro del viewport`).toBeLessThanOrEqual(vp.width + 1);
      expect(medidas.navRect.right, `${vp.nombre}: nav dentro del viewport`).toBeLessThanOrEqual(vp.width + 1);
      expect(medidas.navScrollOverflow, `${vp.nombre}: todos los enlaces caben sin scroll oculto`).toBeLessThanOrEqual(1);
      expect(medidas.linksWrapped, `${vp.nombre}: links de menú en una sola línea limpia`).toBe(false);
    } else {
      await expect(page.locator("#btn-menu")).toBeVisible();
      await expect(page.locator("#main-nav")).toBeHidden();
    }
  }
});
