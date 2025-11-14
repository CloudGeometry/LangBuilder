import { expect, test } from "@playwright/test";
import { awaitBootstrapTest } from "../../utils/await-bootstrap-test";

/**
 * Playwright test for "Publish to OpenWebUI" feature
 *
 * Prerequisites:
 * 1. LangBuilder backend running (make backend)
 * 2. LangBuilder frontend running (make frontend)
 * 3. OpenWebUI instance running on localhost:5839
 * 4. Valid OpenWebUI API key
 *
 * To run: npx playwright test publishToOpenWebUI.spec.ts
 */

test.describe("Publish to OpenWebUI Feature", () => {
  test.beforeEach(async ({ page }) => {
    await awaitBootstrapTest(page);
  });

  test(
    "should show publish button in toolbar",
    { tag: ["@release", "@workspace"] },
    async ({ page }) => {
      // Wait for blank flow button
      await page.waitForSelector('[data-testid="blank-flow"]', {
        timeout: 30000,
      });

      // Create a blank flow
      await page.getByTestId("blank-flow").click();

      // Wait for the flow editor to load
      await page.waitForSelector('[data-testid="fit_view"]', {
        timeout: 10000,
      });

      // Click the Share dropdown button
      await page.waitForSelector('[data-testid="publish-button"]', {
        timeout: 5000,
      });
      await page.getByTestId("publish-button").click();

      // Verify "Publish to OpenWebUI" menu item exists
      await page.waitForSelector('[data-testid="publish-to-openwebui-item"]', {
        timeout: 5000,
      });

      const publishMenuItem = await page.getByTestId("publish-to-openwebui-item");
      await expect(publishMenuItem).toBeVisible();

      const menuText = await publishMenuItem.textContent();
      expect(menuText).toContain("Publish to OpenWebUI");
    }
  );

  test(
    "should open publish modal when clicking publish button",
    { tag: ["@release", "@workspace"] },
    async ({ page }) => {
      // Create a blank flow
      await page.waitForSelector('[data-testid="blank-flow"]', {
        timeout: 30000,
      });
      await page.getByTestId("blank-flow").click();

      // Wait for flow editor
      await page.waitForSelector('[data-testid="fit_view"]', {
        timeout: 10000,
      });

      // Open Share dropdown
      await page.waitForSelector('[data-testid="publish-button"]', {
        timeout: 5000,
      });
      await page.getByTestId("publish-button").click();

      // Click "Publish to OpenWebUI"
      await page.waitForSelector('[data-testid="publish-to-openwebui-item"]', {
        timeout: 5000,
      });
      await page.getByTestId("publish-to-openwebui-item").click();

      // Wait for modal to appear
      await page.waitForTimeout(1000);

      // Check modal title
      const modalTitle = page.getByText("Publish to OpenWebUI");
      await expect(modalTitle).toBeVisible();

      // Check URL input exists
      const urlInput = page.locator('#openwebui-url');
      await expect(urlInput).toBeVisible();

      // Check API key input exists
      const apiKeyInput = page.locator('#api-key');
      await expect(apiKeyInput).toBeVisible();

      // Check default URL is pre-filled
      const urlValue = await urlInput.inputValue();
      expect(urlValue).toBe("http://localhost:5839");
    }
  );

  test(
    "should show validation error when API key is empty",
    { tag: ["@release", "@workspace"] },
    async ({ page }) => {
      // Create a blank flow
      await page.waitForSelector('[data-testid="blank-flow"]', {
        timeout: 30000,
      });
      await page.getByTestId("blank-flow").click();

      // Open publish modal
      await page.waitForSelector('[data-testid="publish-button"]', {
        timeout: 5000,
      });
      await page.getByTestId("publish-button").click();

      await page.waitForSelector('[data-testid="publish-to-openwebui-item"]', {
        timeout: 5000,
      });
      await page.getByTestId("publish-to-openwebui-item").click();

      await page.waitForTimeout(1000);

      // Try to publish without API key
      const publishButton = page.getByRole('button', { name: /Publish Flow/i });
      await publishButton.click();

      // Wait for error message
      await page.waitForTimeout(500);

      // Check error alert appears
      const errorAlert = page.getByText(/Please enter your OpenWebUI API key/i);
      await expect(errorAlert).toBeVisible();
    }
  );

  test.skip(
    "should publish flow successfully with valid credentials",
    { tag: ["@release", "@workspace", "@integration"] },
    async ({ page }) => {
      // SKIP BY DEFAULT - Requires real OpenWebUI instance and credentials
      // To enable: Remove test.skip and set environment variables

      const OPENWEBUI_URL = process.env.TEST_OPENWEBUI_URL || "http://localhost:5839";
      const OPENWEBUI_API_KEY = process.env.TEST_OPENWEBUI_API_KEY || "";

      if (!OPENWEBUI_API_KEY) {
        console.log("Skipping integration test - no API key provided");
        return;
      }

      // Create a flow with Chat Input/Output
      await page.waitForSelector('[data-testid="blank-flow"]', {
        timeout: 30000,
      });
      await page.getByTestId("blank-flow").click();

      // Add Chat Input
      await page.getByTestId("sidebar-search-input").click();
      await page.getByTestId("sidebar-search-input").fill("chat input");
      await page.waitForSelector('[data-testid="input_outputChat Input"]', {
        timeout: 2000,
      });
      await page
        .getByTestId("input_outputChat Input")
        .dragTo(page.locator('//*[@id="react-flow-id"]'), {
          targetPosition: { x: 100, y: 100 },
        });

      // Add Chat Output
      await page.getByTestId("sidebar-search-input").click();
      await page.getByTestId("sidebar-search-input").fill("chat output");
      await page.waitForSelector('[data-testid="input_outputChat Output"]', {
        timeout: 2000,
      });
      await page
        .getByTestId("input_outputChat Output")
        .hover()
        .then(async () => {
          await page.getByTestId("add-component-button-chat-output").click();
        });

      // Connect them
      await page
        .getByTestId("handle-chatinput-noshownode-chat message-source")
        .click();
      await page.getByTestId("handle-chatoutput-noshownode-inputs-target").click();

      // Save the flow
      await page.keyboard.press("Control+s");
      await page.waitForTimeout(1000);

      // Open publish modal
      await page.getByTestId("publish-button").click();
      await page.getByTestId("publish-to-openwebui-item").click();
      await page.waitForTimeout(1000);

      // Fill in credentials
      const urlInput = page.locator('#openwebui-url');
      await urlInput.fill(OPENWEBUI_URL);

      const apiKeyInput = page.locator('#api-key');
      await apiKeyInput.fill(OPENWEBUI_API_KEY);

      // Click Publish
      const publishButton = page.getByRole('button', { name: /Publish Flow/i });
      await publishButton.click();

      // Wait for success
      await page.waitForTimeout(5000);

      // Check for success message
      const successMessage = page.getByText(/Flow published successfully/i);
      await expect(successMessage).toBeVisible({ timeout: 10000 });

      // Check status badge appears
      await page.waitForTimeout(2000);
      const statusBadge = page.getByText(/Published \(/i);
      await expect(statusBadge).toBeVisible();
    }
  );
});
