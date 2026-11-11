const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function fetchDateRange(startDateStr, endDateStr, limit = 500) {
  const authPath = path.join(__dirname, 'auth.json');
  if (!fs.existsSync(authPath)) {
    console.error('❌ auth.json not found!');
    process.exit(1);
  }

  // Parse start and end date DD-MM-YYYY
  const [sDay, sMonth, sYear] = startDateStr.split('-').map(Number);
  const [eDay, eMonth, eYear] = endDateStr.split('-').map(Number);

  const startDt = new Date(Date.UTC(sYear, sMonth - 1, sDay));
  const endDt = new Date(Date.UTC(eYear, eMonth - 1, eDay));

  const dateList = [];
  let curr = new Date(startDt);
  while (curr <= endDt) {
    const d = String(curr.getUTCDate()).padStart(2, '0');
    const m = String(curr.getUTCMonth() + 1).padStart(2, '0');
    const y = curr.getUTCFullYear();
    dateList.push(`${d}-${m}-${y}`);
    curr.setUTCDate(curr.getUTCDate() + 1);
  }

  console.log(`\n=============================================================`);
  console.log(`📦 BATCH FETCHER: 11-Oct to 28-Oct (${dateList.length} days)`);
  console.log(`=============================================================\n`);

  const invoicesDir = path.join(__dirname, 'invoices');
  if (!fs.existsSync(invoicesDir)) fs.mkdirSync(invoicesDir, { recursive: true });

  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext({
    storageState: authPath,
    viewport: { width: 1366, height: 768 },
  });
  const page = await context.newPage();

  console.log('🔑 Authenticating session...');
  await page.goto('https://dms-hsfpl.fieldassist.io/home');
  await page.waitForTimeout(4000);

  for (let dIdx = 0; dIdx < dateList.length; dIdx++) {
    const targetDateStr = dateList[dIdx];
    const outputFile = path.join(invoicesDir, `invoices_${targetDateStr}.json`);

    // If file already exists and has invoices, skip fetching!
    if (fs.existsSync(outputFile)) {
      try {
        const existing = JSON.parse(fs.readFileSync(outputFile, 'utf-8'));
        if (Array.isArray(existing) && existing.length > 0) {
          console.log(`[${dIdx + 1}/${dateList.length}] ⏭️  ${targetDateStr} already fetched (${existing.length} invoices). Skipping.`);
          continue;
        }
      } catch (e) {}
    }

    const [day, month, year] = targetDateStr.split('-').map(Number);
    const prevDate = new Date(Date.UTC(year, month - 1, day - 1, 18, 30, 0, 0));
    const toDate = new Date(Date.UTC(year, month - 1, day, 18, 29, 59, 999));

    const fromDateIso = prevDate.toISOString();
    const toDateIso = toDate.toISOString();

    console.log(`\n[${dIdx + 1}/${dateList.length}] 📅 Fetching list for ${targetDateStr}...`);
    const listUrl = `https://dms-hsfpl.fieldassist.io/api/v1/sales-invoices/?seller-id=19135&from-date=${encodeURIComponent(fromDateIso)}&to-date=${encodeURIComponent(toDateIso)}&beat-name=null&salesman-name=null&payment-status=null&has-sku-detail=false`;

    let listResponse = await page.evaluate(async (url) => {
      try {
        const res = await fetch(url, { headers: { 'Accept': 'application/json, text/plain, */*' } });
        if (res.status === 200) return { status: 200, data: await res.json() };
        return { status: res.status, error: await res.text() };
      } catch (e) {
        return { status: 0, error: e.message };
      }
    }, listUrl);

    if (listResponse.status === 401) {
      console.log('   ⚠️ Session expired. Refreshing token...');
      await page.goto('https://dms-hsfpl.fieldassist.io/home');
      await page.waitForTimeout(4000);
      listResponse = await page.evaluate(async (url) => {
        const res = await fetch(url, { headers: { 'Accept': 'application/json, text/plain, */*' } });
        return { status: res.status, data: await res.json() };
      }, listUrl);
    }

    if (!Array.isArray(listResponse.data)) {
      console.log(`   ⚠️ No invoices or invalid response for ${targetDateStr} (status ${listResponse.status})`);
      fs.writeFileSync(outputFile, JSON.stringify([], null, 2), 'utf-8');
      continue;
    }

    const allInvoices = listResponse.data;
    console.log(`   Found ${allInvoices.length} invoices on ${targetDateStr}`);
    if (allInvoices.length === 0) {
      fs.writeFileSync(outputFile, JSON.stringify([], null, 2), 'utf-8');
      continue;
    }

    const fullInvoices = [];
    for (let i = 0; i < allInvoices.length; i++) {
      const header = allInvoices[i];
      const invoiceId = header.id;
      const invNo = header.invoiceNo;

      process.stdout.write(`      [${i + 1}/${allInvoices.length}] ${invNo}... `);
      const detailUrl = `https://dms-hsfpl.fieldassist.io/api/v1/sales-invoices/${invoiceId}`;

      let success = false;
      for (let attempt = 1; attempt <= 3; attempt++) {
        const detailRes = await page.evaluate(async (url) => {
          try {
            const res = await fetch(url, { headers: { 'Accept': 'application/json, text/plain, */*' } });
            if (res.status === 200) return { status: 200, data: await res.json() };
            return { status: res.status, error: await res.text() };
          } catch (e) {
            return { status: 0, error: e.message };
          }
        }, detailUrl);

        if (detailRes.status === 200 && detailRes.data) {
          const invData = detailRes.data;
          const count = invData.items ? invData.items.length : 0;
          console.log(`OK (${count} items)`);
          fullInvoices.push(invData);
          success = true;
          break;
        } else if (detailRes.status === 401) {
          console.log(`\n         ⚠️ Session expired. Refreshing token...`);
          await page.goto('https://dms-hsfpl.fieldassist.io/home');
          await page.waitForTimeout(4000);
        } else {
          await page.waitForTimeout(1000);
        }
      }

      if (!success) console.log(`FAILED`);
      await page.waitForTimeout(200);
    }

    fs.writeFileSync(outputFile, JSON.stringify(fullInvoices, null, 2), 'utf-8');
    console.log(`   💾 Saved ${fullInvoices.length} invoices -> invoices_${targetDateStr}.json`);
  }

  await browser.close();
  console.log(`\n🎉 All days fetched successfully!`);
}

const args = process.argv.slice(2);
const start = args[0] || '11-10-2026';
const end = args[1] || '28-10-2026';
fetchDateRange(start, end);
