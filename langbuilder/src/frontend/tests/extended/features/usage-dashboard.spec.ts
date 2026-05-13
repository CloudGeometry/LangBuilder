import { test, expect } from "../../fixtures";

const MOCK_USAGE_RESPONSE = {
  summary: {
    total_cost_usd: 1.234,
    total_invocations: 100,
    avg_cost_per_invocation_usd: 0.01234,
    active_flow_count: 5,
    date_range: { from: null, to: null },
    currency: "USD",
    data_source: "langwatch",
    cached: false,
    cache_age_seconds: null,
    truncated: false,
  },
  flows: [
    {
      flow_id: "flow-1",
      flow_name: "Test Flow",
      total_cost_usd: 0.5,
      invocation_count: 50,
      avg_cost_per_invocation_usd: 0.01,
      owner_user_id: "user-1",
      owner_username: "testuser",
    },
  ],
};

test.describe(
  "Usage Dashboard",
  { tag: ["@release", "@workspace"] },
  () => {
    test(
      "loading skeleton appears within 200ms of navigation to usage page",
      { tag: ["@release"] },
      async ({ page }) => {
        // Mock API to be slow so we can observe the skeleton
        await page.route("**/api/v1/usage/**", async (route) => {
          await new Promise<void>((resolve) => setTimeout(resolve, 2000));
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(MOCK_USAGE_RESPONSE),
          });
        });

        await page.goto("/");

        // Wait for the app to load before measuring
        await page.waitForLoadState("domcontentloaded");

        const start = Date.now();
        // Navigate to the usage page directly
        await page.goto("/usage");

        // The skeleton should appear very quickly (synchronously on mount when isLoading=true)
        await page.waitForSelector('[data-testid="usage-loading-skeleton"]', {
          timeout: 1000,
        });
        const elapsed = Date.now() - start;

        await expect(
          page.locator('[data-testid="usage-loading-skeleton"]'),
        ).toBeVisible();
        expect(elapsed).toBeLessThan(200);
      },
    );

    test(
      "usage summary cards display after data loads successfully",
      { tag: ["@release"] },
      async ({ page }) => {
        // Mock API to respond immediately with data
        await page.route("**/api/v1/usage/**", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(MOCK_USAGE_RESPONSE),
          });
        });

        await page.goto("/usage");

        // Loading skeleton should disappear once data is available
        await expect(
          page.locator('[data-testid="usage-loading-skeleton"]'),
        ).not.toBeVisible({ timeout: 5000 });

        // The main dashboard should be visible
        await expect(
          page.locator('[data-testid="usage-dashboard"]'),
        ).toBeVisible({ timeout: 5000 });

        // Summary cards should render
        await expect(
          page.locator('[data-testid="usage-summary-cards"]'),
        ).toBeVisible({ timeout: 5000 });
      },
    );

    test(
      "date range picker updates the displayed range on preset selection",
      { tag: ["@release"] },
      async ({ page }) => {
        let requestCount = 0;
        const capturedUrls: string[] = [];

        await page.route("**/api/v1/usage/**", async (route) => {
          requestCount++;
          capturedUrls.push(route.request().url());
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(MOCK_USAGE_RESPONSE),
          });
        });

        await page.goto("/usage");

        // Wait for dashboard to be visible
        await expect(
          page.locator('[data-testid="usage-dashboard"]'),
        ).toBeVisible({ timeout: 5000 });

        const initialRequestCount = requestCount;

        // Open the date range picker
        await page.click('[data-testid="date-range-picker-trigger"]');

        // Click a preset
        await page.click('[data-testid="preset-last-7-days"]');

        // The trigger button text should update to reflect the selected range
        await expect(
          page.locator('[data-testid="date-range-picker-trigger"]'),
        ).not.toHaveText("All time", { timeout: 3000 });

        // A new API request should be triggered (after debounce)
        await page.waitForTimeout(600); // debounce is 500ms
        expect(requestCount).toBeGreaterThan(initialRequestCount);

        // New request should include date parameters
        const latestUrl = capturedUrls[capturedUrls.length - 1];
        expect(latestUrl).toContain("from_date");
        expect(latestUrl).toContain("to_date");
      },
    );

    test(
      "error state shows when LangWatch API key is not configured (503 KEY_NOT_CONFIGURED)",
      { tag: ["@release"] },
      async ({ page }) => {
        await page.route("**/api/v1/usage/**", async (route) => {
          await route.fulfill({
            status: 503,
            contentType: "application/json",
            body: JSON.stringify({ detail: { code: "KEY_NOT_CONFIGURED" } }),
          });
        });

        await page.goto("/usage");
        (page as any).allowFlowErrors?.();

        // After retries are exhausted, the error state should be visible
        await expect(
          page.locator('[data-testid="usage-error-state"]'),
        ).toBeVisible({ timeout: 30000 });

        // The heading should say "Failed to load usage data"
        await expect(
          page.getByText(/failed to load usage data/i),
        ).toBeVisible({ timeout: 5000 });
      },
    );

    test(
      "error state shows for generic API failure",
      { tag: ["@release"] },
      async ({ page }) => {
        await page.route("**/api/v1/usage/**", async (route) => {
          await route.fulfill({
            status: 500,
            contentType: "application/json",
            body: JSON.stringify({ detail: "Internal Server Error" }),
          });
        });

        // Allow expected flow errors so fixture doesn't fail the test
        await page.goto("/usage");
        (page as any).allowFlowErrors?.();

        // Wait for error state (after retries)
        await expect(
          page.locator('[data-testid="usage-error-state"]'),
        ).toBeVisible({ timeout: 30000 });

        await expect(
          page.getByText(/failed to load usage data/i),
        ).toBeVisible({ timeout: 5000 });
      },
    );
  },
);
