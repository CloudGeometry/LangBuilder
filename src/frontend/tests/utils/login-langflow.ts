import type { Page } from "playwright/test";

export const loginLangBuilder = async (page: Page) => {
  await page.goto("/");
  await page.getByPlaceholder("Username").fill("langbuilder");
  await page.getByPlaceholder("Password").fill("langbuilder");
  await page.getByRole("button", { name: "Sign In" }).click();
};
