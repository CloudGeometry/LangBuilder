const { chromium } = require('@playwright/test');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Navigate to the app
  await page.goto('http://localhost:3000');

  // Wait for the page to load
  await page.waitForTimeout(3000);

  // Take a screenshot of the homepage
  await page.screenshot({ path: 'screenshot-1-homepage.png', fullPage: true });
  console.log('Screenshot 1: Homepage');

  // Try to click blank flow
  try {
    await page.waitForSelector('[data-testid="blank-flow"]', { timeout: 5000 });
    await page.getByTestId('blank-flow').click();
    console.log('Clicked blank flow');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'screenshot-2-flow-loaded.png', fullPage: true });
    console.log('Screenshot 2: Flow loaded');
  } catch (e) {
    console.log('Could not find blank flow:', e.message);
  }

  // Try to click the publish button
  try {
    await page.waitForSelector('[data-testid="publish-button"]', { timeout: 5000 });
    await page.getByTestId('publish-button').click();
    console.log('Clicked publish button (dropdown)');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'screenshot-3-dropdown-open.png', fullPage: true });
    console.log('Screenshot 3: Dropdown open');
  } catch (e) {
    console.log('Could not find publish button:', e.message);
  }

  // Try to click "Publish to OpenWebUI"
  try {
    await page.waitForSelector('[data-testid="publish-to-openwebui-item"]', { timeout: 5000 });
    const menuItem = await page.getByTestId('publish-to-openwebui-item');
    console.log('Found publish-to-openwebui-item');

    await menuItem.click();
    console.log('Clicked "Publish to OpenWebUI" menu item');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'screenshot-4-after-click.png', fullPage: true });
    console.log('Screenshot 4: After clicking menu item');

    // Check if modal appeared
    const modalTitle = page.getByText('Publish to OpenWebUI');
    const isVisible = await modalTitle.isVisible().catch(() => false);
    console.log('Modal title visible:', isVisible);

    if (isVisible) {
      await page.screenshot({ path: 'screenshot-5-modal-open.png', fullPage: true });
      console.log('Screenshot 5: Modal open!');
    } else {
      console.log('❌ MODAL DID NOT OPEN');
      // Try to find what elements are on the page
      const bodyHTML = await page.evaluate(() => document.body.innerHTML);
      require('fs').writeFileSync('page-html.html', bodyHTML);
      console.log('Saved page HTML to page-html.html');
    }
  } catch (e) {
    console.log('Error during test:', e.message);
  }

  // Wait a bit before closing
  await page.waitForTimeout(5000);

  await browser.close();
})();
