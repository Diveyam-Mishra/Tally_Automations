const { chromium } = require('playwright');
const path = require('path');

(async () => {
  console.log('🚀 Opening Chrome for one-time login...');
  const browser = await chromium.launch({
    channel: 'chrome',
    headless: false,
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('📍 Navigating to FieldAssist...');
  await page.goto('https://dms-hsfpl.fieldassist.io/');

  console.log('\n======================================================');
  console.log('👉 Please LOG IN manually in the opened Chrome window.');
  console.log('👉 Once you reach the dashboard (/home), wait 3 seconds.');
  console.log('👉 The script will automatically save your session!');
  console.log('======================================================\n');

  try {
    // Wait until URL contains /home (up to 5 minutes)
    await page.waitForURL('**/home**', { timeout: 300000 });
    await page.waitForTimeout(3000);

    const storagePath = path.join(__dirname, 'auth.json');
    await context.storageState({ path: storagePath });

    console.log(`\n🎉 Session & tokens saved successfully to:\n${storagePath}`);
    console.log('You can now run: node run_invoice.js\n');
  } catch (err) {
    console.error('Login timed out or was closed:', err.message);
  } finally {
    await browser.close();
  }
})();
