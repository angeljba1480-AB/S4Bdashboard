import { expect, test } from "@playwright/test";

/**
 * Pruebas reales del gate de contraseña del reporte, en un navegador de verdad.
 * La contraseña la fija playwright.config.ts (REPORT_PASSWORD=e2e-pass-123).
 */
const PASSWORD = "e2e-pass-123";

test("sin sesión, la raíz redirige a /login", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByRole("heading", { name: "Tablero Financiero" })).toBeVisible();
  await expect(page.getByText("Acceso restringido")).toBeVisible();
});

test("contraseña incorrecta muestra error y no entra", async ({ page }) => {
  await page.goto("/login");
  await page.getByPlaceholder("Contraseña de acceso").fill("incorrecta");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByText("Contraseña incorrecta")).toBeVisible();
  await expect(page).toHaveURL(/\/login/);
});

test("contraseña correcta entra al tablero", async ({ page }) => {
  await page.goto("/login");
  await page.getByPlaceholder("Contraseña de acceso").fill(PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
  // Ya en el tablero: elementos que solo existen autenticado.
  await expect(page.getByText("Reporte de solo lectura")).toBeVisible();
  await expect(page.getByRole("button", { name: "Salir" })).toBeVisible();
  await expect(page).not.toHaveURL(/\/login/);
});

test("cerrar sesión regresa al gate", async ({ page }) => {
  await page.goto("/login");
  await page.getByPlaceholder("Contraseña de acceso").fill(PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("button", { name: "Salir" })).toBeVisible();
  await page.getByRole("button", { name: "Salir" }).click();
  // El logout borra la cookie y redirige al gate.
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByRole("heading", { name: "Tablero Financiero" })).toBeVisible();
});
